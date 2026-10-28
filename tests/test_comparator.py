from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.comparator.field_comparator import (
    DEFAULT_RULE_VERSION,
    ComparatorResult,
    FieldComparator,
    canonical_equal,
    compare_canonical_field,
    compare_extracted_fields,
    compare_seven_fields,
    is_field_reliable_and_valid,
)
from src.models.comparison import (
    ComparisonOutcome,
    Discrepancy,
    FieldComparison,
    PartialResult,
)
from src.models.extraction import (
    FIELD_NAMES,
    Canonical,
    DocumentExtraction,
    ExtractedField,
    FieldName,
    NormalizedField,
    validate_canonical,
)


# Helper to construct a canonical 7-field dictionary
def make_matching_canonical_fields() -> dict[FieldName, Canonical]:
    return {
        "shipper": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI",
        "consignee": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM",
        "notify_party": "SAME AS CONSIGNEE",
        "port_of_loading": "SHANGHAI",
        "port_of_discharge": "ROTTERDAM",
        "container_count": 2,
        "gross_weight_kg": Decimal("22000.00"),
    }


# Helper to build a valid reliable ExtractedField
def make_reliable_extracted_field(
    field: FieldName,
    val: Canonical,
    rule_version: str = "v1.0",
) -> ExtractedField:
    from src.models.extraction import FieldCandidate

    candidate = FieldCandidate(
        raw_value=str(val),
        source_unit=None,
        evidence_ids=["ev_test_1"],
    )
    return ExtractedField(
        field=field,
        reliability="RELIABLE",
        candidates=[candidate],
        selected_candidate=0,
        normalized=NormalizedField(
            field=field,
            state="VALID",
            value=val,
            rule_version=rule_version,
        ),
        explanation=f"Reliably extracted {field}",
    )


# Helper to build an unreliable ExtractedField
def make_unreliable_extracted_field(
    field: FieldName,
    val: Canonical | None = None,
    reliability: str = "UNREADABLE",
    state: str = "INVALID",
) -> ExtractedField:
    from src.models.extraction import FieldCandidate

    candidates: list[FieldCandidate] = []
    if reliability == "CONFLICTING":
        candidates = [
            FieldCandidate(raw_value="val1", evidence_ids=["ev_1"]),
            FieldCandidate(raw_value="val2", evidence_ids=["ev_2"]),
        ]

    norm = None
    if state != "INVALID" or val is not None:
        norm = NormalizedField(
            field=field,
            state=state,  # type: ignore[arg-type]
            value=None,  # unsuccessful normalization has no trusted value
            rule_version="v1.0",
        )
    return ExtractedField(
        field=field,
        reliability=reliability,  # type: ignore[arg-type]
        candidates=candidates,
        selected_candidate=None,
        normalized=norm,
        explanation=f"Unreliable extraction for {field}",
    )


# =============================================================================
# SCENARIO A: PIPE-CMP-001 (Complete Match across all 7 fields)
# =============================================================================


def test_scenario_a_pipe_cmp_001_complete_match_canonical():
    """PIPE-CMP-001: All 7 fields identical between SI and BL -> outcome=MATCH, mismatch_detected=False."""
    si = make_matching_canonical_fields()
    bl = make_matching_canonical_fields()

    res = compare_seven_fields(si, bl)

    assert res.outcome == ComparisonOutcome.MATCH
    assert res.outcome == "MATCH"
    assert res.mismatch_detected is False
    assert res.result_summary == "No mismatch detected"
    assert res.is_complete_match is True
    assert len(res.comparisons) == 7
    assert len(res.unresolved_fields) == 0
    assert len(res.discrepancies) == 0

    for c in res.comparisons:
        assert c.outcome == "MATCH"
        assert c.si_value == c.bl_value


def test_scenario_a_pipe_cmp_001_complete_match_document_extraction():
    """PIPE-CMP-001: All 7 fields identical using DocumentExtraction contract models."""
    si_canon = make_matching_canonical_fields()
    si_fields = {f: make_reliable_extracted_field(f, v) for f, v in si_canon.items()}
    bl_fields = {f: make_reliable_extracted_field(f, v) for f, v in si_canon.items()}

    si_doc = DocumentExtraction(document_id="doc_si", role="SI", fields=si_fields)
    bl_doc = DocumentExtraction(document_id="doc_bl", role="BL", fields=bl_fields)

    comparator = FieldComparator(rule_version="norm-v1.0")
    res = comparator.compare(si_doc, bl_doc)

    assert res.outcome == ComparisonOutcome.MATCH
    assert res.mismatch_detected is False
    assert res.result_summary == "No mismatch detected"
    assert res.is_complete_match is True
    assert len(res.comparisons) == 7
    assert len(res.unresolved_fields) == 0
    assert len(res.discrepancies) == 0


# =============================================================================
# SCENARIO B: PIPE-CMP-002 (Single Mismatch on container_count)
# =============================================================================


def test_scenario_b_pipe_cmp_002_single_mismatch():
    """PIPE-CMP-002: Only container_count differs (2 vs 3) -> outcome=MISMATCH, mismatch_detected=True."""
    si = make_matching_canonical_fields()
    bl = make_matching_canonical_fields()
    bl["container_count"] = 3  # differs from SI (2)

    res = compare_seven_fields(si, bl)

    assert res.outcome == ComparisonOutcome.MISMATCH
    assert res.outcome == "MISMATCH"
    assert res.mismatch_detected is True
    assert res.is_complete_match is False
    assert "container_count" in res.result_summary
    assert res.result_summary != "No mismatch detected"

    assert len(res.comparisons) == 7
    assert len(res.unresolved_fields) == 0
    assert len(res.discrepancies) == 1

    disc = res.discrepancies[0]
    assert disc.field == "container_count"
    assert disc.si_value == 2
    assert disc.bl_value == 3


# =============================================================================
# SCENARIO C: PIPE-CMP-003 (Multiple Mismatches)
# =============================================================================


def test_scenario_c_pipe_cmp_003_multiple_mismatches():
    """PIPE-CMP-003: shipper and gross_weight_kg differ -> outcome=MISMATCH, mismatch_detected=True."""
    si = make_matching_canonical_fields()
    bl = make_matching_canonical_fields()
    bl["shipper"] = "DIFFERENT SHIPPER CO, BEIJING"
    bl["gross_weight_kg"] = Decimal("25000.00")

    res = compare_seven_fields(si, bl)

    assert res.outcome == ComparisonOutcome.MISMATCH
    assert res.mismatch_detected is True
    assert res.is_complete_match is False
    assert len(res.comparisons) == 7
    assert len(res.unresolved_fields) == 0
    assert len(res.discrepancies) == 2

    disc_fields = {d.field for d in res.discrepancies}
    assert disc_fields == {"shipper", "gross_weight_kg"}


# =============================================================================
# SCENARIO D: Exact Unit-Normalized Gross Weight Match
# =============================================================================


def test_scenario_d_exact_unit_normalized_gross_weight_match():
    """Decimal mathematical equality: Decimal('22000') == Decimal('22000.00')."""
    assert canonical_equal("gross_weight_kg", Decimal("22000"), Decimal("22000.00")) is True
    assert canonical_equal("gross_weight_kg", Decimal("22000.0"), Decimal("22000.00")) is True

    # String values must NOT be coerced to Decimal by T04; must be rejected
    with pytest.raises(ValueError, match="gross_weight_kg canonical value must be a finite Decimal"):
        canonical_equal("gross_weight_kg", "22000", Decimal("22000.0"))

    # Floats must be rejected
    with pytest.raises(ValueError):
        canonical_equal("gross_weight_kg", 22000.0, Decimal("22000.0"))

    si = make_matching_canonical_fields()
    bl = make_matching_canonical_fields()
    si["gross_weight_kg"] = Decimal("22000")
    bl["gross_weight_kg"] = Decimal("22000.00")

    res = compare_seven_fields(si, bl)
    assert res.outcome == ComparisonOutcome.MATCH
    assert res.mismatch_detected is False


# =============================================================================
# SCENARIO E: REG-004 (No Numeric Weight Tolerance)
# =============================================================================


def test_scenario_e_reg_004_no_numeric_weight_tolerance():
    """REG-004: Decimal('22000') vs Decimal('22001') MUST evaluate to MISMATCH."""
    assert canonical_equal("gross_weight_kg", Decimal("22000"), Decimal("22001")) is False
    assert canonical_equal("gross_weight_kg", Decimal("22000.00"), Decimal("22000.01")) is False

    fc = compare_canonical_field("gross_weight_kg", Decimal("22000"), Decimal("22001"))
    assert fc.outcome == "MISMATCH"
    assert fc.si_value == Decimal("22000")
    assert fc.bl_value == Decimal("22001")


# =============================================================================
# SCENARIO F: REG-006 (No Port Equivalence / Aliasing)
# =============================================================================


def test_scenario_f_reg_006_no_port_equivalence():
    """REG-006: 'SHANGHAI' vs 'PORT OF SHANGHAI' MUST evaluate to MISMATCH."""
    assert canonical_equal("port_of_loading", "SHANGHAI", "PORT OF SHANGHAI") is False
    assert canonical_equal("port_of_discharge", "ROTTERDAM", "PORT OF ROTTERDAM") is False

    fc = compare_canonical_field("port_of_loading", "SHANGHAI", "PORT OF SHANGHAI")
    assert fc.outcome == "MISMATCH"


# =============================================================================
# SCENARIO G: REG-005 (No Organization Equivalence / Suffix Stripping)
# =============================================================================


def test_scenario_g_reg_005_no_organization_equivalence():
    """REG-005: 'ACME CORP' vs 'ACME CORPORATION' MUST evaluate to MISMATCH."""
    assert canonical_equal("shipper", "ACME CORP", "ACME CORPORATION") is False
    assert canonical_equal("consignee", "GLOBAL LOGISTICS B.V.", "GLOBAL LOGISTICS BV") is False

    fc = compare_canonical_field("shipper", "ACME CORP", "ACME CORPORATION")
    assert fc.outcome == "MISMATCH"


# =============================================================================
# SCENARIO H: PIPE-CMP-004 / REG-010 (One Unresolved Field -> Tri-State None)
# =============================================================================


def test_scenario_h_pipe_cmp_004_reg_010_one_unresolved_field():
    """PIPE-CMP-004, REG-010: 6 fields match, 1 field unresolved (None) -> outcome=None, mismatch_detected=None."""
    si = make_matching_canonical_fields()
    bl = make_matching_canonical_fields()
    # Explicit None under exact 7 keys represents unresolved field
    bl["port_of_discharge"] = None

    res = compare_seven_fields(si, bl)

    assert res.outcome is None
    assert res.mismatch_detected is None
    assert res.is_complete_match is False

    # REG-010: result_summary MUST NEVER be 'No mismatch detected'
    assert res.result_summary != "No mismatch detected"
    assert "Review required" in res.result_summary
    assert "port_of_discharge" in res.result_summary

    assert len(res.comparisons) == 6
    assert res.unresolved_fields == ["port_of_discharge"]
    assert len(res.discrepancies) == 0

    # The 6 matching fields are preserved
    compared_names = {c.field for c in res.comparisons}
    assert "port_of_discharge" not in compared_names
    assert len(compared_names) == 6
    for c in res.comparisons:
        assert c.outcome == "MATCH"


# =============================================================================
# SCENARIO I: PIPE-CMP-005 / HITL-PART-001 / REG-009 (Known Mismatch + Unresolved)
# =============================================================================


def test_scenario_i_pipe_cmp_005_hitl_part_001_reg_009_known_mismatch_plus_unresolved():
    """PIPE-CMP-005, REG-009: Known mismatch on container_count + gross_weight_kg unresolved.

    Invariants:
    - mismatch_detected is strictly None (not False, not True)
    - outcome is strictly None
    - result_summary is NOT 'No mismatch detected'
    - partial_result preserves reliable comparisons (including known mismatch)
    - discrepancies contains the known mismatch
    - unresolved_fields contains gross_weight_kg
    """
    si = make_matching_canonical_fields()
    bl = make_matching_canonical_fields()
    bl["container_count"] = 5  # known mismatch (2 vs 5)
    bl["gross_weight_kg"] = None  # unresolved

    res = compare_seven_fields(si, bl)

    assert res.outcome is None
    assert res.mismatch_detected is None
    assert res.result_summary != "No mismatch detected"
    assert "gross_weight_kg" in res.unresolved_fields
    assert len(res.unresolved_fields) == 1

    # Preserved comparisons: 6 fields
    assert len(res.comparisons) == 6

    # Preserved discrepancies: container_count mismatch
    assert len(res.discrepancies) == 1
    assert res.discrepancies[0].field == "container_count"
    assert res.discrepancies[0].si_value == 2
    assert res.discrepancies[0].bl_value == 5


def test_scenario_i_cross_check_fixture_case_08_partial_preservation():
    """Cross-validate against Wave 0 case_08 fixture: 6 matching, gross_weight_kg missing."""
    case_path = Path("tests/fixtures/review/cases/case_08_partial_preservation_6_of_7.json")
    assert case_path.exists()
    payload = json.loads(case_path.read_text(encoding="utf-8"))

    si_ext = DocumentExtraction.model_validate(payload["extractions"][0])
    bl_ext = DocumentExtraction.model_validate(payload["extractions"][1])

    res = compare_seven_fields(si_ext, bl_ext)

    assert res.outcome is None
    assert res.mismatch_detected is None
    assert res.result_summary != "No mismatch detected"
    assert res.unresolved_fields == ["gross_weight_kg"]
    assert len(res.comparisons) == 6
    assert len(res.discrepancies) == 0
    for c in res.comparisons:
        assert c.outcome == "MATCH"


def test_scenario_i_cross_check_fixture_case_09_known_mismatch_plus_unresolved():
    """Cross-validate against Wave 0 case_09 fixture: container_count mismatch + gross_weight_kg unreadable."""
    case_path = Path("tests/fixtures/review/cases/case_09_tristate_known_mismatch_plus_unresolved.json")
    assert case_path.exists()
    payload = json.loads(case_path.read_text(encoding="utf-8"))

    si_ext = DocumentExtraction.model_validate(payload["extractions"][0])
    bl_ext = DocumentExtraction.model_validate(payload["extractions"][1])

    res = compare_seven_fields(si_ext, bl_ext)

    assert res.outcome is None
    assert res.mismatch_detected is None
    assert res.result_summary != "No mismatch detected"
    assert res.unresolved_fields == ["gross_weight_kg"]
    assert len(res.comparisons) == 6
    assert len(res.discrepancies) == 1
    assert res.discrepancies[0].field == "container_count"


# =============================================================================
# SCENARIO J: PIPE-CMP-006 (Conflicting / Unreliable Field)
# =============================================================================


def test_scenario_j_pipe_cmp_006_conflicting_or_unreliable_field():
    """PIPE-CMP-006: Field marked UNRELIABLE (e.g. conflicting candidates) -> field placed in unresolved_fields."""
    si_fields = {f: make_reliable_extracted_field(f, v) for f, v in make_matching_canonical_fields().items()}
    bl_fields = {f: make_reliable_extracted_field(f, v) for f, v in make_matching_canonical_fields().items()}

    # Inject conflicting/unreliable state in SI gross_weight_kg
    si_fields["gross_weight_kg"] = make_unreliable_extracted_field("gross_weight_kg")

    si_doc = DocumentExtraction(document_id="doc_si", role="SI", fields=si_fields)
    bl_doc = DocumentExtraction(document_id="doc_bl", role="BL", fields=bl_fields)

    res = compare_seven_fields(si_doc, bl_doc)

    assert res.outcome is None
    assert res.mismatch_detected is None
    assert res.result_summary != "No mismatch detected"
    assert "gross_weight_kg" in res.unresolved_fields
    assert len(res.unresolved_fields) == 1
    assert len(res.comparisons) == 6


def test_both_sides_unreliable_or_missing():
    """When both sides are unreliable or missing, field is unresolved and no equality attempted."""
    si_fields = {f: make_reliable_extracted_field(f, v) for f, v in make_matching_canonical_fields().items()}
    bl_fields = {f: make_reliable_extracted_field(f, v) for f, v in make_matching_canonical_fields().items()}

    si_fields["shipper"] = make_unreliable_extracted_field("shipper")
    bl_fields["shipper"] = make_unreliable_extracted_field("shipper")

    si_doc = DocumentExtraction(document_id="doc_si", role="SI", fields=si_fields)
    bl_doc = DocumentExtraction(document_id="doc_bl", role="BL", fields=bl_fields)

    res = compare_seven_fields(si_doc, bl_doc)

    assert res.outcome is None
    assert res.mismatch_detected is None
    assert "shipper" in res.unresolved_fields
    assert len(res.unresolved_fields) == 1
    assert len(res.comparisons) == 6


# =============================================================================
# CONTRACT GUARDS & INVALID INPUTS
# =============================================================================


def test_non_canonical_types_rejected():
    """Non-canonical types are rejected by validate_canonical and comparator."""
    # container_count cannot be bool
    with pytest.raises(ValueError, match="container_count must be an integer, not bool"):
        compare_canonical_field("container_count", True, 2)

    # container_count cannot be float
    with pytest.raises(ValueError, match="container_count must be an integer, not bool"):
        compare_canonical_field("container_count", 2.5, 2)

    # gross_weight_kg cannot be non-finite or float
    with pytest.raises(ValueError):
        validate_canonical("gross_weight_kg", 22000.0)

    # text fields cannot be empty
    with pytest.raises(ValueError, match="canonical text must be non-empty"):
        compare_canonical_field("shipper", "", "ACME CORP")

    with pytest.raises(ValueError, match="canonical text must be non-empty"):
        compare_canonical_field("shipper", "   ", "ACME CORP")


def test_is_field_reliable_and_valid():
    """Verify is_field_reliable_and_valid helper rules."""
    assert is_field_reliable_and_valid(None) is False

    # Unreliable field (MISSING)
    missing = ExtractedField(
        field="shipper",
        reliability="MISSING",
        candidates=[],
        selected_candidate=None,
        normalized=None,
        explanation="Field missing from source",
    )
    assert is_field_reliable_and_valid(missing) is False

    # Reliable field with valid value
    rel = make_reliable_extracted_field("shipper", "ACME")
    assert is_field_reliable_and_valid(rel) is True

    # Duck-typed object with missing normalized
    class DummyFieldNoNorm:
        reliability = "RELIABLE"
        normalized = None

    assert is_field_reliable_and_valid(DummyFieldNoNorm()) is False  # type: ignore[arg-type]

    # Duck-typed object with INVALID normalized state
    class DummyFieldInvalid:
        reliability = "RELIABLE"

        class DummyNorm:
            state = "INVALID"
            value = None

        normalized = DummyNorm()

    assert is_field_reliable_and_valid(DummyFieldInvalid()) is False  # type: ignore[arg-type]


def test_compare_extracted_fields_reliability_gate():
    """compare_extracted_fields returns FieldComparison only when both pass reliability gate."""
    rel_si = make_reliable_extracted_field("container_count", 2)
    rel_bl = make_reliable_extracted_field("container_count", 3)
    unrel_bl = make_unreliable_extracted_field("container_count")

    fc = compare_extracted_fields(rel_si, rel_bl)
    assert fc is not None
    assert fc.outcome == "MISMATCH"
    assert fc.si_value == 2
    assert fc.bl_value == 3

    assert compare_extracted_fields(rel_si, unrel_bl) is None
    assert compare_extracted_fields(unrel_bl, rel_bl) is None


def test_partial_result_seven_fields_partition_invariant():
    """PartialResult strictly guarantees disjoint union of exactly the 7 mandatory fields."""
    canon = make_matching_canonical_fields()
    # 3 compared, 4 unresolved
    comps = [
        compare_canonical_field(f, canon[f], canon[f])
        for f in ["shipper", "consignee", "notify_party"]
    ]
    unres = ["port_of_loading", "port_of_discharge", "container_count", "gross_weight_kg"]

    pr = PartialResult(comparisons=comps, unresolved_fields=unres)  # type: ignore[arg-type]
    assert len(pr.comparisons) == 3
    assert len(pr.unresolved_fields) == 4

    # Duplicate comparison rejected
    with pytest.raises(ValidationError, match="duplicate comparison"):
        PartialResult(comparisons=comps + [comps[0]], unresolved_fields=unres)  # type: ignore[arg-type]

    # Duplicate unresolved rejected
    with pytest.raises(ValidationError, match="duplicate unresolved field"):
        PartialResult(comparisons=comps, unresolved_fields=unres + ["container_count"])  # type: ignore[arg-type]

    # Intersection between compared and unresolved rejected
    with pytest.raises(ValidationError, match="compared field cannot be unresolved"):
        PartialResult(comparisons=comps, unresolved_fields=unres + ["shipper"])  # type: ignore[arg-type]

    # Incomplete set (less than 7 fields) rejected
    with pytest.raises(ValidationError, match="partial result must partition seven fields"):
        PartialResult(comparisons=comps, unresolved_fields=["container_count"])


def test_field_comparator_class_wrapper():
    """Verify FieldComparator class properly encapsulates comparison logic and rule_version."""
    comp = FieldComparator(rule_version="norm-custom-v2.0")
    fc = comp.compare_canonical_field("container_count", 5, 5)
    assert fc.outcome == "MATCH"
    assert fc.rule_version == "norm-custom-v2.0"

    si = {f: None for f in FIELD_NAMES}
    bl = {f: None for f in FIELD_NAMES}
    si["container_count"] = 5
    bl["container_count"] = 5

    res = comp.compare(si, bl)
    assert res.outcome is None  # 6 fields unresolved
    assert len(res.comparisons) == 1
    assert res.comparisons[0].rule_version == "norm-custom-v2.0"
    assert len(res.unresolved_fields) == 6


def test_exact_seven_input_fields_dictionary_validation():
    """Verify direct dictionary inputs enforce exactly the 7 approved FIELD_NAMES."""
    valid_si = make_matching_canonical_fields()
    valid_bl = make_matching_canonical_fields()

    # 1. Exact 7 keys accepted
    res = compare_seven_fields(valid_si, valid_bl)
    assert res.outcome == ComparisonOutcome.MATCH

    # 2. 6 keys (missing key) rejected
    missing_si = make_matching_canonical_fields()
    del missing_si["port_of_discharge"]
    with pytest.raises(ValueError, match="SI input must contain exactly the 7 mandatory fields: missing mandatory field.*port_of_discharge"):
        compare_seven_fields(missing_si, valid_bl)

    missing_bl = make_matching_canonical_fields()
    del missing_bl["container_count"]
    with pytest.raises(ValueError, match="BL input must contain exactly the 7 mandatory fields: missing mandatory field.*container_count"):
        compare_seven_fields(valid_si, missing_bl)

    # 3. 8 keys (extra key including vessel_name) rejected
    extra_si = make_matching_canonical_fields()
    extra_si["vessel_name"] = "PACIFIC GLORY"
    with pytest.raises(ValueError, match="SI input must contain exactly the 7 mandatory fields: extra/unknown field.*vessel_name"):
        compare_seven_fields(extra_si, valid_bl)

    extra_bl = make_matching_canonical_fields()
    extra_bl["voyage_number"] = "V102"
    with pytest.raises(ValueError, match="BL input must contain exactly the 7 mandatory fields: extra/unknown field.*voyage_number"):
        compare_seven_fields(valid_si, extra_bl)


def test_gross_weight_decimal_only_guards():
    """Verify gross_weight_kg strictly requires Decimal and rejects str coercion or float."""
    # Valid Decimals compare equal
    fc = compare_canonical_field("gross_weight_kg", Decimal("22000"), Decimal("22000.00"))
    assert fc.outcome == "MATCH"

    # String "22000" rejected (no silent Decimal(str(...)) coercion inside T04)
    with pytest.raises(ValueError, match="gross_weight_kg canonical value must be a finite Decimal"):
        compare_canonical_field("gross_weight_kg", "22000", Decimal("22000"))

    with pytest.raises(ValueError, match="gross_weight_kg canonical value must be a finite Decimal"):
        compare_canonical_field("gross_weight_kg", Decimal("22000"), "22000")

    # Float 22000.0 rejected
    with pytest.raises(ValueError):
        compare_canonical_field("gross_weight_kg", 22000.0, Decimal("22000"))

    with pytest.raises(ValueError):
        compare_canonical_field("gross_weight_kg", Decimal("22000"), 22000.0)

    # Rejection via compare_seven_fields
    si_str_weight = make_matching_canonical_fields()
    si_str_weight["gross_weight_kg"] = "22000"  # invalid canonical type (string)
    bl_valid = make_matching_canonical_fields()
    with pytest.raises(ValueError, match="gross_weight_kg canonical value must be a finite Decimal"):
        compare_seven_fields(si_str_weight, bl_valid)


def test_rule_version_authority_and_validation():
    """Verify rule_version follows authoritative norm-v1.0 baseline and validates non-emptiness."""
    assert DEFAULT_RULE_VERSION == "norm-v1.0"

    fc_default = compare_canonical_field("container_count", 2, 2)
    assert fc_default.rule_version == "norm-v1.0"

    # Custom rule version accepted
    fc_custom = compare_canonical_field("container_count", 2, 2, rule_version="custom-v2.1")
    assert fc_custom.rule_version == "custom-v2.1"

    # Empty or whitespace rule version rejected
    with pytest.raises(ValueError, match="rule_version must be non-empty"):
        compare_canonical_field("container_count", 2, 2, rule_version="")

    with pytest.raises(ValueError, match="rule_version must be non-empty"):
        compare_canonical_field("container_count", 2, 2, rule_version="   ")

    with pytest.raises(ValueError, match="rule_version must be non-empty"):
        FieldComparator(rule_version="")

    with pytest.raises(ValueError, match="rule_version must be non-empty"):
        compare_seven_fields(make_matching_canonical_fields(), make_matching_canonical_fields(), rule_version="")
