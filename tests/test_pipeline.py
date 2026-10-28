import shutil
from pathlib import Path

from src.pipeline.stage1_classify import rule_based_classify
from src.pipeline.stage2_extract import Stage2Extractor
from src.pipeline.stage3_compare import rule_based_compare_audit
from src.pipeline.validator import validate_submission_dict

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DOCUMENTS = FIXTURES / "documents"


def test_classification_heuristics():
    comparison = {
        "subject": "TO CONFIRM DOCS for booking BK-100",
        "body": "Please check the attached SI and draft BL.",
        "attachments": ["attachments/shipment_SI.txt", "attachments/shipment_BL.txt"],
    }
    assert rule_based_classify(comparison) == "BL_COMPARISON"

    invoice = {
        "subject": "Query on local charges",
        "body": "Is the THC included on this invoice?",
        "attachments": [],
    }
    assert rule_based_classify(invoice) == "INVOICE_QUERY"

    instruction = {
        "subject": "Request SI for booking BK-200",
        "body": "Please find the shipping instruction.",
        "attachments": [],
    }
    assert rule_based_classify(instruction) == "SI_REQUEST"

    spam = {
        "subject": "Increase your shipping revenue with this one weird trick",
        "body": "Unsubscribe from these exclusive offers.",
        "attachments": [],
    }
    assert rule_based_classify(spam) == "SPAM"


def test_stage2_missing_attachment():
    extractor = Stage2Extractor(FIXTURES)
    email = {
        "email_id": "synthetic_missing",
        "subject": "TO CONFIRM DOCS",
        "body": "The draft BL is not attached.",
        "attachments": ["attachments/shipment_SI.txt"],
    }
    ready, early = extractor.extract_comparison_pair(email)
    assert ready is None
    assert early is not None
    assert early.hitl_escalation.needed is True
    assert early.hitl_escalation.reason == "missing_attachment"
    assert "attachment" in early.hitl_escalation.evidence

    comp = early.to_competition_dict()
    assert comp["status"] == "NEEDS_REVIEW"
    assert comp["review_reason"] == "missing_attachment"


def test_stage2_corrupted_pdf(tmp_path):
    shutil.copy(DOCUMENTS / "txt" / "txt_si_001_clean.txt", tmp_path / "shipment_SI.txt")
    shutil.copy(DOCUMENTS / "malformed" / "corrupt_stream.pdf", tmp_path / "shipment_BL.pdf")

    extractor = Stage2Extractor(tmp_path)
    email = {
        "email_id": "synthetic_corrupt",
        "subject": "TO CONFIRM DOCS",
        "body": "The BL file will not open.",
        "attachments": ["shipment_SI.txt", "shipment_BL.pdf"],
    }
    ready, early = extractor.extract_comparison_pair(email)
    assert ready is None
    assert early is not None
    assert early.hitl_escalation.needed is True
    assert early.hitl_escalation.reason == "unreadable"

    comp = early.to_competition_dict()
    assert comp["status"] == "NEEDS_REVIEW"
    assert comp["review_reason"] == "unreadable"


def test_stage3_matching_pair():
    si_text = (DOCUMENTS / "txt" / "txt_si_001_clean.txt").read_text()
    bl_text = (DOCUMENTS / "txt" / "txt_bl_001_clean_match.txt").read_text()
    rec = rule_based_compare_audit("synthetic_match", si_text, bl_text)
    assert rec.mismatch_detected is False
    assert rec.result_summary == "No mismatch detected"
    assert len(rec.discrepancies) == 0

    comp = rec.to_competition_dict()
    assert comp["status"] == "OK"
    assert comp["has_defect"] is False
    assert comp["defect_fields"] == []


def test_stage3_discrepancy_pair():
    si_text = (DOCUMENTS / "txt" / "txt_si_001_clean.txt").read_text()
    bl_text = (DOCUMENTS / "txt" / "txt_bl_002_count_mismatch.txt").read_text()
    rec = rule_based_compare_audit("synthetic_mismatch", si_text, bl_text)
    assert rec.mismatch_detected is True
    assert any(d.field == "container_count" for d in rec.discrepancies)

    comp = rec.to_competition_dict()
    assert comp["status"] == "MISMATCH"
    assert comp["has_defect"] is True
    assert "container_count" in comp["defect_fields"]


def test_validator():
    sample_data = {
        "synthetic_001": {
            "category": "GENERAL",
            "status": "OK",
            "review_reason": None,
            "defect_fields": [],
            "has_defect": False,
        }
    }
    valid, errors = validate_submission_dict(sample_data, sample_data)
    assert valid is True
    assert len(errors) == 0
