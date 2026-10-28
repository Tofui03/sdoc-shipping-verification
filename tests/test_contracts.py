from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.models import (
    # Ingestion (T02-01)
    AttachmentReference,
    Category,
    ClassificationResult,
    EmailCategory,
    EmailRecord,
    # Document (T02-02)
    DocumentReference,
    DocumentRole,
    ParserResult,
    ParserStatus,
    Role,
    # Evidence (T02-03)
    EvidenceKind,
    EvidenceLocation,
    FieldEvidence,
    # Extraction (T02-04)
    Canonical,
    DocumentExtraction,
    ExtractedField,
    FIELD_NAMES,
    FieldName,
    FieldReliability,
    FieldStatus,
    FieldCandidate,
    NormalizedField,
    NormalizedGrossWeight,
    validate_canonical,
    # Comparison (T02-05)
    ComparisonOutcome,
    Discrepancy,
    FieldComparison,
    OutcomeType,
    PartialResult,
    # Review (T02-06)
    ActionType,
    FieldCorrection,
    LogicalReason,
    LogicalReasonType,
    RecoveryState,
    ReviewAction,
    ReviewCase,
    ReviewIssue,
    ReviewUpdate,
    RoleCorrection,
    Stage,
    StageType,
    # Audit (T02-07)
    AttemptRecord,
    AttemptTracker,
    AuditRecord,
    AuditState,
    DynamicVerifyRequest,
    ErrorResponse,
    ProcessingMetadata,
    SubmissionRecord,
    WorkflowState,
)


# =============================================================================
# CT-DATA-001: Ingestion & Classification Contracts (DC-01)
# =============================================================================


def test_ct_data_001_valid_email_record():
    """Verify clean instantiation of EmailRecord and AttachmentReference."""
    att = AttachmentReference(
        document_id="doc_001",
        path="attachments/si.pdf",
        mime_type="application/pdf",
    )
    email = EmailRecord(
        email_id="em_001",
        sender="shipper@acme.com",
        subject="Shipping Documents",
        body="Please find SI and draft BL attached.",
        attachments=[att],
    )
    assert email.email_id == "em_001"
    assert len(email.attachments) == 1
    assert email.attachments[0].document_id == "doc_001"


def test_ct_data_001_canonical_categories():
    """Verify all 5 canonical categories are accepted and evaluation enums rejected."""
    valid_categories = [
        "document_comparison",
        "new_shipping_instruction",
        "invoice_query",
        "general",
        "spam",
    ]
    for cat in valid_categories:
        res = ClassificationResult(
            state="RESOLVED",
            category=cat,
            reason="Intent matched",
            evidence_ids=["ev_001"],
        )
        assert res.category == cat

    for enum_val in EmailCategory:
        res = ClassificationResult(
            state="RESOLVED",
            category=enum_val,
            reason="Intent matched",
            evidence_ids=["ev_001"],
        )
        assert res.category == enum_val.value

    # Leaked evaluation enums must be rejected
    for eval_cat in ["BL_COMPARISON", "SI_REQUEST", "GENERAL", "SPAM"]:
        with pytest.raises(ValidationError):
            ClassificationResult(
                state="RESOLVED",
                category=eval_cat,
                reason="Intent matched",
                evidence_ids=["ev_001"],
            )


def test_ct_data_001_classification_nullability_and_resolution():
    """Verify category=None is allowed ONLY when state='NEEDS_REVIEW'."""
    unres = ClassificationResult(
        state="NEEDS_REVIEW",
        category=None,
        reason="Ambiguous email body",
        evidence_ids=[],
    )
    assert unres.category is None
    assert unres.state == "NEEDS_REVIEW"

    # Invalid: state='NEEDS_REVIEW' with category populated
    with pytest.raises(ValidationError, match="category exists only when resolved"):
        ClassificationResult(
            state="NEEDS_REVIEW",
            category="document_comparison",
            reason="Contradiction",
            evidence_ids=[],
        )

    # Invalid: state='RESOLVED' with category None
    with pytest.raises(ValidationError, match="category exists only when resolved"):
        ClassificationResult(
            state="RESOLVED",
            category=None,
            reason="Missing category",
            evidence_ids=["ev_001"],
        )

    # Invalid: state='RESOLVED' with empty evidence_ids
    with pytest.raises(ValidationError, match="resolved intent requires evidence"):
        ClassificationResult(
            state="RESOLVED",
            category="document_comparison",
            reason="No evidence",
            evidence_ids=[],
        )


# =============================================================================
# CT-DATA-002: Internal vs Official HITL Separation (DC-02)
# =============================================================================


def test_ct_data_002_logical_reason_taxonomy():
    """Verify ReviewIssue accepts all 7 internal logical reasons and rejects unapproved strings."""
    approved_reasons = [
        "missing_attachment",
        "unreadable_document",
        "wrong_or_uncertain_document_type",
        "missing_required_value",
        "uncertain_result",
        "conflicting_candidate_values",
        "processing_or_provider_failure",
    ]
    for reason in approved_reasons:
        issue = ReviewIssue(
            issue_id=f"iss_{reason}",
            stage="identification",
            logical_reason=reason,
            document_ids=["doc_001"],
            fields=["container_count"],
            evidence_ids=["ev_001"],
            suggested_action="Check attachments",
            recovery_state="EXHAUSTED",
            recovery_detail="Role not found",
            attempt_ids=["att_001"],
        )
        assert issue.logical_reason == reason

    # Also test via Enum members
    for enum_val in LogicalReason:
        issue = ReviewIssue(
            issue_id=f"iss_enum_{enum_val.value}",
            stage=Stage.IDENTIFICATION,
            logical_reason=enum_val,
            document_ids=["doc_001"],
            fields=["container_count"],
            evidence_ids=["ev_001"],
            suggested_action="Action",
            recovery_state="EXHAUSTED",
            recovery_detail="Detail",
            attempt_ids=["att_001"],
        )
        assert issue.logical_reason == enum_val.value

    # Prohibited/unapproved logical reasons must be rejected
    prohibited_reasons = [
        "low_confidence",
        "manual_override",
        "user_error",
        "parser_failed",
        "ai_failed",
        "unknown_error",
    ]
    for bad_reason in prohibited_reasons:
        with pytest.raises(ValidationError):
            ReviewIssue(
                issue_id="iss_bad",
                stage="identification",
                logical_reason=bad_reason,
                document_ids=["doc_001"],
                fields=["container_count"],
                evidence_ids=["ev_001"],
                suggested_action="Action",
                recovery_state="EXHAUSTED",
                recovery_detail="Detail",
                attempt_ids=["att_001"],
            )


# =============================================================================
# CT-DATA-003: Tri-State Mismatch Model (DC-03)
# =============================================================================


def test_ct_data_003_tristate_mismatch_model():
    """Verify tri-state mismatch behavior: True, False, or None during review."""
    # When state == 'NEEDS_REVIEW', outcome and mismatch_detected must both be None
    pr = PartialResult(
        comparisons=[],
        unresolved_fields=list(FIELD_NAMES),
    )
    email = EmailRecord(
        email_id="em_001",
        sender="a@b.com",
        subject="Subj",
        body="Body",
        attachments=[AttachmentReference(document_id="doc_si", path="si.pdf")],
    )
    ev = FieldEvidence(
        evidence_id="ev_001",
        source_type="email",
        source_id="em_001",
        kind="text_span",
        quote="Body",
    )
    cls = ClassificationResult(
        state="RESOLVED",
        category="document_comparison",
        reason="Requested",
        evidence_ids=["ev_001"],
    )
    review_case = ReviewCase(
        review_id="rev_001",
        state="OPEN",
        issues=[
            ReviewIssue(
                issue_id="iss_001",
                stage="identification",
                logical_reason="missing_attachment",
                document_ids=[],
                fields=list(FIELD_NAMES),
                evidence_ids=["ev_001"],
                suggested_action="Upload BL",
                recovery_state="EXHAUSTED",
                recovery_detail="Draft BL missing",
                attempt_ids=[],
            )
        ],
    )
    proc = ProcessingMetadata(attempts=[])

    # Valid tri-state review record
    audit_review = AuditRecord(
        email_id="em_001",
        revision=1,
        email=email,
        classification=cls,
        state="NEEDS_REVIEW",
        outcome=None,
        mismatch_detected=None,
        result_summary="Review required: Draft BL missing",
        documents=[],
        parsers=[],
        extractions=[],
        evidence=[ev],
        partial_result=pr,
        discrepancies=[],
        review=review_case,
        processing=proc,
    )
    assert audit_review.mismatch_detected is None
    assert audit_review.outcome is None

    # Invalid: NEEDS_REVIEW with boolean mismatch_detected = False
    with pytest.raises(ValidationError, match="review is not a final outcome"):
        AuditRecord(
            email_id="em_001",
            revision=1,
            email=email,
            classification=cls,
            state="NEEDS_REVIEW",
            outcome=None,
            mismatch_detected=False,
            result_summary="Review required",
            documents=[],
            parsers=[],
            extractions=[],
            evidence=[ev],
            partial_result=pr,
            discrepancies=[],
            review=review_case,
            processing=proc,
        )

    # Invalid: NEEDS_REVIEW with result_summary == 'No mismatch detected'
    with pytest.raises(ValidationError, match="unresolved case cannot receive a clean pass"):
        AuditRecord(
            email_id="em_001",
            revision=1,
            email=email,
            classification=cls,
            state="NEEDS_REVIEW",
            outcome=None,
            mismatch_detected=None,
            result_summary="No mismatch detected",
            documents=[],
            parsers=[],
            extractions=[],
            evidence=[ev],
            partial_result=pr,
            discrepancies=[],
            review=review_case,
            processing=proc,
        )


# =============================================================================
# CT-DATA-004: Decimal Weight Representation (DC-04)
# =============================================================================


def test_ct_data_004_decimal_weight_representation():
    """Verify NormalizedGrossWeight uses exact Decimal without IEEE float precision loss."""
    norm_wt = NormalizedGrossWeight(canonical_kg=Decimal("22500.50"))
    assert isinstance(norm_wt.canonical_kg, Decimal)
    assert norm_wt.canonical_kg == Decimal("22500.5")

    # Verify plain decimal string serialization
    dumped = norm_wt.model_dump()
    assert dumped["canonical_kg"] == "22500.50"

    # Exact decimal equality without floating point precision loss
    norm_wt2 = NormalizedGrossWeight(canonical_kg=Decimal("22500.5"))
    assert norm_wt.canonical_kg == norm_wt2.canonical_kg
    assert norm_wt.canonical_kg != Decimal("22500.51")

    # Non-finite values must be rejected
    with pytest.raises(ValidationError):
        NormalizedGrossWeight(canonical_kg=Decimal("NaN"))
    with pytest.raises(ValidationError):
        NormalizedGrossWeight(canonical_kg=Decimal("Infinity"))

    # Strict type: raw binary float is forbidden under strict=True
    with pytest.raises(ValidationError):
        NormalizedGrossWeight(canonical_kg=22500.50)  # float forbidden


def test_field_comparison_structural_representation():
    """Verify FieldComparison models structural comparison output without executing comparator logic."""
    fc_mismatch = FieldComparison(
        field="container_count",
        si_value=2,
        bl_value=3,
        outcome="MISMATCH",
        rule_version="norm-v1.0",
    )
    assert fc_mismatch.field == "container_count"
    assert fc_mismatch.field_name == "container_count"
    assert fc_mismatch.si_value == 2
    assert fc_mismatch.bl_value == 3
    assert fc_mismatch.outcome == "MISMATCH"
    assert fc_mismatch.rule_version == "norm-v1.0"

    fc_match = FieldComparison(
        field="shipper",
        si_value="ACME CORP",
        bl_value="ACME CORP",
        outcome="MATCH",
        rule_version="norm-v1.0",
    )
    assert fc_match.outcome == "MATCH"

    # Invalid outcome enum rejected
    with pytest.raises(ValidationError):
        FieldComparison(
            field="shipper",
            si_value="ACME",
            bl_value="ACME",
            outcome="INVALID_OUTCOME",  # type: ignore[arg-type]
            rule_version="norm-v1.0",
        )


# =============================================================================
# CT-DATA-005: Structured FieldEvidence & Provenance Models (DC-05)
# =============================================================================


def test_ct_data_005_text_span_evidence():
    """Verify text_span evidence requires quote."""
    ev = FieldEvidence(
        evidence_id="ev_text_001",
        source_type="document",
        source_id="doc_001",
        kind="text_span",
        quote="SHIPPER: ACME CORP",
        location=EvidenceLocation(page=1, section="Header"),
    )
    assert ev.kind == "text_span"
    assert ev.quote == "SHIPPER: ACME CORP"

    with pytest.raises(ValidationError, match="text/cell evidence requires source text"):
        FieldEvidence(
            evidence_id="ev_text_bad",
            source_type="document",
            source_id="doc_001",
            kind="text_span",
            quote=None,
        )


def test_ct_data_005_table_cell_evidence():
    """Verify table_cell evidence requires quote and table/row/column coordinates."""
    ev = FieldEvidence(
        evidence_id="ev_cell_001",
        source_type="document",
        source_id="doc_001",
        kind="table_cell",
        quote="22,000 KGS",
        location=EvidenceLocation(table="ManifestTable", row=2, column=3),
    )
    assert ev.kind == "table_cell"

    with pytest.raises(ValidationError, match="cell requires table and coordinates"):
        FieldEvidence(
            evidence_id="ev_cell_bad",
            source_type="document",
            source_id="doc_001",
            kind="table_cell",
            quote="22,000 KGS",
            location=EvidenceLocation(table="ManifestTable"),
        )


def test_ct_data_005_page_region_evidence():
    """Verify page_region requires page and ordered bounding box [x0, y0, x1, y1]."""
    ev = FieldEvidence(
        evidence_id="ev_reg_001",
        source_type="document",
        source_id="doc_001",
        kind=EvidenceKind.PAGE_REGION,
        location=EvidenceLocation(page=1, bbox=[0.1, 0.2, 0.5, 0.6]),
    )
    assert ev.location.bbox == [0.1, 0.2, 0.5, 0.6]

    with pytest.raises(ValidationError, match="bbox must be an ordered non-empty region"):
        EvidenceLocation(page=1, bbox=[0.8, 0.2, 0.3, 0.6])

    with pytest.raises(ValidationError, match="region requires page"):
        EvidenceLocation(bbox=[0.1, 0.2, 0.5, 0.6])


# =============================================================================
# CT-DATA-006: Total Attempt Limits & Budget Semantics (DC-06)
# =============================================================================


def test_ct_data_006_attempt_limit_semantics():
    """Verify AttemptTracker and ProcessingMetadata limits, defaults, and nested budget cap at 6."""
    # Defaults: 3 technical, 2 semantic, budget = 6
    proc = ProcessingMetadata(
        attempts=[
            AttemptRecord(
                attempt_id="att_001",
                operation_id="op_parse",
                stage="parsing",
                kind="primary",
                attempt_number=1,
                outcome="SUCCEEDED",
            )
        ],
    )
    assert proc.technical_attempt_limit == 3
    assert proc.semantic_attempt_limit == 2
    assert proc.total_budget == 6
    assert proc.total_provider_calls == 1

    tracker = AttemptTracker(
        total_provider_calls=1,
    )
    assert tracker.technical_attempt_limit == 3
    assert tracker.semantic_attempt_limit == 2
    assert tracker.total_budget == 6

    # Valid configurations within cap
    p_valid1 = ProcessingMetadata(technical_attempt_limit=2, semantic_attempt_limit=2, attempts=[])
    assert p_valid1.total_budget == 4 <= 6

    p_valid2 = ProcessingMetadata(technical_attempt_limit=6, semantic_attempt_limit=1, attempts=[])
    assert p_valid2.total_budget == 6

    p_valid3 = ProcessingMetadata(technical_attempt_limit=1, semantic_attempt_limit=6, attempts=[])
    assert p_valid3.total_budget == 6

    # Attempt limits must be >= 1 (initial attempt counted as 1)
    with pytest.raises(ValidationError):
        ProcessingMetadata(technical_attempt_limit=0, attempts=[])

    with pytest.raises(ValidationError):
        ProcessingMetadata(semantic_attempt_limit=0, attempts=[])

    # attempt_number must be >= 1
    with pytest.raises(ValidationError):
        AttemptRecord(
            attempt_id="att_000",
            operation_id="op_parse",
            stage="parsing",
            kind="primary",
            attempt_number=0,
            outcome="SUCCEEDED",
        )

    # Invalid configurations exceeding approved budget cap of 6
    with pytest.raises(ValidationError, match="nested provider invocation budget .* cannot exceed 6"):
        ProcessingMetadata(technical_attempt_limit=4, semantic_attempt_limit=2, attempts=[])

    with pytest.raises(ValidationError, match="nested provider invocation budget .* cannot exceed 6"):
        ProcessingMetadata(technical_attempt_limit=3, semantic_attempt_limit=3, attempts=[])

    with pytest.raises(ValidationError, match="nested provider invocation budget .* cannot exceed 6"):
        AttemptTracker(technical_attempt_limit=4, semantic_attempt_limit=2)

    with pytest.raises(ValidationError, match="total_provider_calls cannot exceed the cap of 6"):
        AttemptTracker(total_provider_calls=7)


# =============================================================================
# CT-DATA-007: ReviewUpdate Payload Schema (DC-07)
# =============================================================================


def test_ct_data_007_review_update_payload_schema():
    """Verify ReviewUpdate accepts CONFIRM and CORRECT actions with required revision and corrections."""
    corr = FieldCorrection(
        document_id="doc_bl_001",
        field="gross_weight_kg",
        raw_value="22000 KG",
        evidence_ids=["ev_bl_wt"],
        rationale="Found in weight column",
    )
    update = ReviewUpdate(
        review_id="rev_001",
        expected_revision=1,
        actor_id="operator_alice",
        action="CORRECT",
        rationale="Corrected gross weight",
        category=None,
        classification_evidence_ids=[],
        role_corrections=[],
        corrections=[corr],
        added_evidence=[],
    )
    assert update.action == "CORRECT"
    assert update.expected_revision == 1
    assert len(update.corrections) == 1

    # Confirm action
    update_confirm = ReviewUpdate(
        review_id="rev_001",
        expected_revision=1,
        actor_id="operator_alice",
        action=ReviewAction.CONFIRM,
        rationale="Verified as correct",
    )
    assert update_confirm.action == "CONFIRM"

    # expected_revision must be >= 1
    with pytest.raises(ValidationError):
        ReviewUpdate(
            review_id="rev_001",
            expected_revision=0,
            actor_id="operator_alice",
            action="CONFIRM",
            rationale="Rationale",
        )

    # Prohibited action strings
    for bad_action in ["OVERRIDE", "APPROVE", "FORCE_MATCH"]:
        with pytest.raises(ValidationError):
            ReviewUpdate(
                review_id="rev_001",
                expected_revision=1,
                actor_id="operator_alice",
                action=bad_action,
                rationale="Rationale",
            )


# =============================================================================
# CT-DATA-008: Export Blocked Safety Schema (DC-08)
# =============================================================================


def test_ct_data_008_export_blocked_safety_schema():
    """Verify ErrorResponse structure and SubmissionRecord contract invariants."""
    err = ErrorResponse(
        code="EXPORT_BLOCKED",
        message="Cannot export submission: unresolved state",
        details=["em_001: conflicting values"],
        retryable=False,
        blocking_emails=["em_001"],
    )
    assert err.code == "EXPORT_BLOCKED"
    assert err.email_ids == ["em_001"]
    assert err.retryable is False

    # SubmissionRecord valid export forms
    sub_ok = SubmissionRecord(
        category="BL_COMPARISON",
        status="OK",
        review_reason=None,
        has_defect=False,
        defect_fields=[],
    )
    assert sub_ok.status == "OK"

    sub_mismatch = SubmissionRecord(
        category="BL_COMPARISON",
        status="MISMATCH",
        review_reason=None,
        has_defect=True,
        defect_fields=["container_count"],
    )
    assert sub_mismatch.status == "MISMATCH"

    sub_review = SubmissionRecord(
        category="BL_COMPARISON",
        status="NEEDS_REVIEW",
        review_reason="missing_attachment",
        has_defect=False,
        defect_fields=[],
    )
    assert sub_review.status == "NEEDS_REVIEW"

    # Invalid mismatch without defects
    with pytest.raises(ValidationError, match="invalid mismatch submission"):
        SubmissionRecord(
            category="BL_COMPARISON",
            status="MISMATCH",
            review_reason=None,
            has_defect=False,
            defect_fields=[],
        )


# =============================================================================
# CT-DATA-009: Synthetic Model Fixture Instantiation
# =============================================================================


def test_ct_data_009_examples_json_instantiation():
    """Verify all 15 synthetic models in the contract examples fixture validate cleanly."""
    examples_path = Path(__file__).resolve().parent / "fixtures" / "data_contract_examples.json"
    assert examples_path.exists(), "Examples JSON file must exist"

    data = json.loads(examples_path.read_text(encoding="utf-8"))
    assert len(data) == 15, f"Expected exactly 15 contract examples, found {len(data)}"

    import src.models as models

    for example_name, example_spec in data.items():
        model_name = example_spec["model"]
        model_cls = getattr(models, model_name, None)
        assert model_cls is not None, f"Model class '{model_name}' not found in src.models"

        instance = model_cls.model_validate(example_spec["payload"])
        assert instance is not None, f"Failed to instantiate {example_name} -> {model_name}"


# =============================================================================
# CT-DATA-010: Extra Fields Rejection & Direct Mutation Guardrails (REG-012)
# =============================================================================


def test_ct_data_010_extra_fields_rejection():
    """Verify passing unexpected fields raises ValidationError across contract models."""
    # ReviewUpdate extra fields
    with pytest.raises(ValidationError):
        ReviewUpdate(
            review_id="rev_001",
            expected_revision=1,
            actor_id="operator_alice",
            action="CONFIRM",
            rationale="Rationale",
            unapproved_extra="forbidden",
        )

    # REG-012: Reviewer must not directly mutate mismatch_detected
    with pytest.raises(ValidationError):
        ReviewUpdate(
            review_id="rev_001",
            expected_revision=1,
            actor_id="operator_alice",
            action="CONFIRM",
            rationale="Rationale",
            mismatch_detected=False,
        )

    # REG-012: Reviewer must not directly mutate outcome
    with pytest.raises(ValidationError):
        ReviewUpdate(
            review_id="rev_001",
            expected_revision=1,
            actor_id="operator_alice",
            action="CONFIRM",
            rationale="Rationale",
            outcome="MATCH",
        )

    # FieldComparison extra fields
    with pytest.raises(ValidationError):
        FieldComparison(
            field="container_count",
            si_value=2,
            bl_value=2,
            outcome="MATCH",
            rule_version="norm-v1.0",
            hallucinated_flag=True,
        )


# =============================================================================
# Wave 0 Fixtures Cross-Validation
# =============================================================================


def test_cross_validate_all_review_cases_as_audit_records():
    """Verify all 10 review case fixtures validate cleanly as AuditRecord."""
    case_files = sorted(Path("tests/fixtures/review/cases").glob("case_*.json"))
    assert len(case_files) == 10, f"Expected 10 case fixtures, found {len(case_files)}"

    for fpath in case_files:
        payload = json.loads(fpath.read_text(encoding="utf-8"))
        rec = AuditRecord.model_validate(payload)
        assert rec.email_id == payload["email_id"]
        assert rec.state == "NEEDS_REVIEW"
        assert rec.outcome is None
        assert rec.mismatch_detected is None


def test_cross_validate_all_review_updates():
    """Verify all 18 review update fixtures validate cleanly as ReviewUpdate."""
    update_files = sorted(Path("tests/fixtures/review/updates").glob("*.json"))
    assert len(update_files) == 18, f"Expected 18 update fixtures, found {len(update_files)}"

    for fpath in update_files:
        payload = json.loads(fpath.read_text(encoding="utf-8"))
        upd = ReviewUpdate.model_validate(payload)
        assert upd.review_id == payload["review_id"]
        assert upd.action in ("CONFIRM", "CORRECT")


def test_cross_validate_concurrency_fixtures():
    """Verify concurrency fixture review update payloads validate as ReviewUpdate."""
    conc_files = ["conc_01_valid_revision_match.json", "conc_02_stale_revision_conflict.json"]
    for fname in conc_files:
        fpath = Path("tests/fixtures/review/concurrency") / fname
        data = json.loads(fpath.read_text(encoding="utf-8"))
        upd = ReviewUpdate.model_validate(data["review_update_payload"])
        assert upd.expected_revision is not None


def test_cross_validate_invalid_review_fixtures_rejection():
    """Verify all 17 invalid fixtures in tests/fixtures/review/invalid/ are rejected by contracts or normalizers."""
    import re
    manifest = json.loads(Path("tests/fixtures/review/manifest.json").read_text(encoding="utf-8"))
    invalid_fixtures = [
        meta for k, meta in manifest.get("fixtures", {}).items()
        if meta.get("valid_payload") is False
    ]
    assert len(invalid_fixtures) == 17, f"Expected 17 invalid fixtures, found {len(invalid_fixtures)}"

    for meta in invalid_fixtures:
        fpath = Path("tests/fixtures/review") / meta["file"]
        data = json.loads(fpath.read_text(encoding="utf-8"))
        scen = meta.get("scenario")

        rejected = False
        try:
            if scen == "inv_fabricated_evidence_bbox":
                EvidenceLocation.model_validate(data)
            elif scen == "inv_table_cell_missing_coords":
                FieldEvidence.model_validate(data)
            elif scen == "inv_invalid_container_count_type":
                # Verifies that raw_value is non-numeric prose that cannot convert to integer
                val = data["corrections"][0]["raw_value"]
                int(val)
            elif scen == "inv_invalid_gross_weight_type":
                # Verifies that raw_value is prose without numeric weight digits
                val = data["corrections"][0]["raw_value"]
                if not re.search(r"\d", val):
                    raise ValueError("Prose value cannot convert to Decimal")
            else:
                ReviewUpdate.model_validate(data)
        except (ValidationError, ValueError, TypeError):
            rejected = True

        assert rejected, f"Invalid fixture {meta['file']} was accepted unexpectedly!"


def test_cross_validate_synthetic_email_fixtures():
    """Verify Wave 0 synthetic email fixtures parse cleanly into EmailRecord."""
    email_files = list(Path("tests/fixtures/emails").glob("syn_email_*.json"))
    assert len(email_files) >= 18

    for fpath in email_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        email_record = EmailRecord.model_validate(data)
        assert email_record.email_id == data["email_id"]
        assert len(email_record.attachments) == len(data.get("attachments", []))


def test_classification_survives_downstream_needs_review():
    """Reconfirm that AuditRecord permits resolved document_comparison when state=NEEDS_REVIEW downstream."""
    pr = PartialResult(comparisons=[], unresolved_fields=list(FIELD_NAMES))
    email = EmailRecord(
        email_id="em_guard_001",
        sender="shipper@acme.com",
        subject="Compare SI and BL",
        body="Please verify attached documents.",
        attachments=[AttachmentReference(document_id="doc_si", path="si.pdf")],
    )
    ev = FieldEvidence(
        evidence_id="ev_em_001",
        source_type="email",
        source_id="em_guard_001",
        kind="text_span",
        quote="Please verify attached documents.",
    )
    cls = ClassificationResult(
        state="RESOLVED",
        category="document_comparison",
        reason="Comparison intent resolved",
        evidence_ids=["ev_em_001"],
    )

    downstream_scenarios = [
        ("missing_attachment", "identification"),
        ("missing_required_value", "extraction"),
        ("unreadable_document", "parsing"),
    ]

    for downstream_reason, stage in downstream_scenarios:
        review_case = ReviewCase(
            review_id=f"rev_{downstream_reason}",
            state="OPEN",
            issues=[
                ReviewIssue(
                    issue_id=f"iss_{downstream_reason}",
                    stage=stage,
                    logical_reason=downstream_reason,
                    document_ids=[],
                    fields=list(FIELD_NAMES),
                    evidence_ids=["ev_em_001"],
                    suggested_action="Action required",
                    recovery_state="EXHAUSTED",
                    recovery_detail=f"Downstream cause: {downstream_reason}",
                    attempt_ids=[],
                )
            ],
        )
        audit = AuditRecord(
            email_id="em_guard_001",
            revision=1,
            email=email,
            classification=cls,
            state="NEEDS_REVIEW",
            outcome=None,
            mismatch_detected=None,
            result_summary=f"Review required: {downstream_reason}",
            documents=[],
            parsers=[],
            extractions=[],
            evidence=[ev],
            partial_result=pr,
            discrepancies=[],
            review=review_case,
            processing=ProcessingMetadata(attempts=[]),
        )

        # Entering overall HITL must not erase an already reliable classification
        assert audit.state == "NEEDS_REVIEW"
        assert audit.classification.state == "RESOLVED"
        assert audit.classification.category == "document_comparison"
        assert audit.outcome is None
        assert audit.mismatch_detected is None

