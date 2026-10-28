#!/usr/bin/env python3
"""
generate_review_fixtures.py — Deterministic Generator for Synthetic Review Fixtures

Creates offline test fixtures in tests/fixtures/review/:
- cases/       : 10 synthetic audit record states covering all 7 LogicalReasons, partial preservation, tri-state
- updates/     : 18 valid ReviewUpdate request payloads (classification, roles, 7 fields, confirm, evidence)
- concurrency/ : 3 optimistic revision scenarios (match, stale 409, race condition)
- invalid/     : 17 intentionally invalid payloads (direct mismatch mutations, wrong enums, bad bboxes, etc.)
- manifest.json: Catalogue of the generated fixtures
- README.md    : Fixture reference

Payloads follow the review models in src.models.
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "review"
CASES_DIR = BASE_DIR / "cases"
UPDATES_DIR = BASE_DIR / "updates"
CONC_DIR = BASE_DIR / "concurrency"
INVALID_DIR = BASE_DIR / "invalid"

FIELD_NAMES = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]

APPROVED_CATEGORIES = [
    "document_comparison",
    "new_shipping_instruction",
    "invoice_query",
    "general",
    "spam",
]

APPROVED_LOGICAL_REASONS = [
    "missing_attachment",
    "unreadable_document",
    "wrong_or_uncertain_document_type",
    "missing_required_value",
    "uncertain_result",
    "conflicting_candidate_values",
    "processing_or_provider_failure",
]

APPROVED_ACTIONS = ["CONFIRM", "CORRECT"]

def make_clean_extractions(doc_id: str, role: str, count: int = 2, weight: str = "22000"):
    """Helper to generate a clean 7-field DocumentExtraction."""
    return {
        "document_id": doc_id,
        "role": role,
        "fields": {
            "shipper": {
                "field": "shipper",
                "reliability": "RELIABLE",
                "candidates": [{
                    "raw_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI",
                    "source_unit": None,
                    "evidence_ids": [f"ev_{doc_id}_shipper"]
                }],
                "selected_candidate": 0,
                "normalized": {
                    "field": "shipper",
                    "state": "VALID",
                    "value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI",
                    "rule_version": "v1.0"
                },
                "explanation": "Extracted from shipper block"
            },
            "consignee": {
                "field": "consignee",
                "reliability": "RELIABLE",
                "candidates": [{
                    "raw_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM",
                    "source_unit": None,
                    "evidence_ids": [f"ev_{doc_id}_consignee"]
                }],
                "selected_candidate": 0,
                "normalized": {
                    "field": "consignee",
                    "state": "VALID",
                    "value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM",
                    "rule_version": "v1.0"
                },
                "explanation": "Extracted from consignee block"
            },
            "notify_party": {
                "field": "notify_party",
                "reliability": "RELIABLE",
                "candidates": [{
                    "raw_value": "SAME AS CONSIGNEE",
                    "source_unit": None,
                    "evidence_ids": [f"ev_{doc_id}_notify_party"]
                }],
                "selected_candidate": 0,
                "normalized": {
                    "field": "notify_party",
                    "state": "VALID",
                    "value": "SAME AS CONSIGNEE",
                    "rule_version": "v1.0"
                },
                "explanation": "Extracted from notify party block"
            },
            "port_of_loading": {
                "field": "port_of_loading",
                "reliability": "RELIABLE",
                "candidates": [{
                    "raw_value": "SHANGHAI, CHINA",
                    "source_unit": None,
                    "evidence_ids": [f"ev_{doc_id}_pol"]
                }],
                "selected_candidate": 0,
                "normalized": {
                    "field": "port_of_loading",
                    "state": "VALID",
                    "value": "SHANGHAI, CHINA",
                    "rule_version": "v1.0"
                },
                "explanation": "Extracted from POL field"
            },
            "port_of_discharge": {
                "field": "port_of_discharge",
                "reliability": "RELIABLE",
                "candidates": [{
                    "raw_value": "ROTTERDAM, NETHERLANDS",
                    "source_unit": None,
                    "evidence_ids": [f"ev_{doc_id}_pod"]
                }],
                "selected_candidate": 0,
                "normalized": {
                    "field": "port_of_discharge",
                    "state": "VALID",
                    "value": "ROTTERDAM, NETHERLANDS",
                    "rule_version": "v1.0"
                },
                "explanation": "Extracted from POD field"
            },
            "container_count": {
                "field": "container_count",
                "reliability": "RELIABLE",
                "candidates": [{
                    "raw_value": str(count),
                    "source_unit": None,
                    "evidence_ids": [f"ev_{doc_id}_container_count"]
                }],
                "selected_candidate": 0,
                "normalized": {
                    "field": "container_count",
                    "state": "VALID",
                    "value": count,
                    "rule_version": "v1.0"
                },
                "explanation": "Extracted container count"
            },
            "gross_weight_kg": {
                "field": "gross_weight_kg",
                "reliability": "RELIABLE",
                "candidates": [{
                    "raw_value": f"{weight} KG",
                    "source_unit": "KG",
                    "evidence_ids": [f"ev_{doc_id}_gross_weight_kg"]
                }],
                "selected_candidate": 0,
                "normalized": {
                    "field": "gross_weight_kg",
                    "state": "VALID",
                    "value": weight,
                    "rule_version": "v1.0"
                },
                "explanation": "Extracted gross weight"
            }
        }
    }

def make_evidence_list(doc_id: str):
    """Helper to generate baseline evidence list for a document."""
    return [
        {
            "evidence_id": f"ev_{doc_id}_shipper",
            "source_type": "document",
            "source_id": doc_id,
            "kind": "text_span",
            "quote": "SHIPPER: ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI",
            "location": {"page": 1, "section": "Header"},
            "detail": None
        },
        {
            "evidence_id": f"ev_{doc_id}_consignee",
            "source_type": "document",
            "source_id": doc_id,
            "kind": "text_span",
            "quote": "CONSIGNEE: GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM",
            "location": {"page": 1, "section": "Header"},
            "detail": None
        },
        {
            "evidence_id": f"ev_{doc_id}_notify_party",
            "source_type": "document",
            "source_id": doc_id,
            "kind": "text_span",
            "quote": "NOTIFY PARTY: SAME AS CONSIGNEE",
            "location": {"page": 1, "section": "Header"},
            "detail": None
        },
        {
            "evidence_id": f"ev_{doc_id}_pol",
            "source_type": "document",
            "source_id": doc_id,
            "kind": "text_span",
            "quote": "PORT OF LOADING: SHANGHAI, CHINA",
            "location": {"page": 1, "section": "Transport Details"},
            "detail": None
        },
        {
            "evidence_id": f"ev_{doc_id}_pod",
            "source_type": "document",
            "source_id": doc_id,
            "kind": "text_span",
            "quote": "PORT OF DISCHARGE: ROTTERDAM, NETHERLANDS",
            "location": {"page": 1, "section": "Transport Details"},
            "detail": None
        },
        {
            "evidence_id": f"ev_{doc_id}_container_count",
            "source_type": "document",
            "source_id": doc_id,
            "kind": "text_span",
            "quote": "TOTAL CONTAINERS: 2",
            "location": {"page": 1, "section": "Cargo Particulars"},
            "detail": None
        },
        {
            "evidence_id": f"ev_{doc_id}_gross_weight_kg",
            "source_type": "document",
            "source_id": doc_id,
            "kind": "text_span",
            "quote": "GROSS WEIGHT: 22,000 KGS",
            "location": {"page": 1, "section": "Cargo Particulars"},
            "detail": None
        }
    ]

def build_all_fixtures():
    for d in [CASES_DIR, UPDATES_DIR, CONC_DIR, INVALID_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    fixtures_meta = {}

    # =========================================================================
    # A. REVIEW CASES (10 cases)
    # =========================================================================

    # Case 1: missing_attachment
    c01 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_001",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_001",
            "sender": "shipper@acme.com",
            "subject": "Comparison Request - SI Attached, BL Pending",
            "body": "Please review our shipping instructions attached. Draft BL will follow shortly.",
            "attachments": [
                {"document_id": "doc_si_001", "path": "attachments/si_001.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "RESOLVED",
            "category": "document_comparison",
            "reason": "Email body requests document comparison review",
            "evidence_ids": ["ev_em_001_body"],
            "confidence_indicator": "HIGH"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: mandatory Draft BL document missing from attachments",
        "documents": [
            {"document_id": "doc_si_001", "role": "SI", "identification_evidence_ids": ["ev_doc_si_001_header"]}
        ],
        "parsers": [
            {
                "document_id": "doc_si_001",
                "status": "SUCCESS",
                "text": "SHIPPING INSTRUCTION\nShipper: ACME...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_si_001_header"],
                "attempt_ids": ["att_parse_001"]
            }
        ],
        "extractions": [],
        "evidence": [
            {
                "evidence_id": "ev_em_001_body",
                "source_type": "email",
                "source_id": "em_case_001",
                "kind": "text_span",
                "quote": "Please review our shipping instructions attached",
                "location": None,
                "detail": None
            },
            {
                "evidence_id": "ev_doc_si_001_header",
                "source_type": "document",
                "source_id": "doc_si_001",
                "kind": "text_span",
                "quote": "SHIPPING INSTRUCTION FORM",
                "location": {"page": 1, "section": "Header"},
                "detail": None
            }
        ],
        "partial_result": {
            "comparisons": [],
            "unresolved_fields": FIELD_NAMES
        },
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_001",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_001_missing_bl",
                    "stage": "identification",
                    "logical_reason": "missing_attachment",
                    "evaluation_reason": "missing_attachment",
                    "document_ids": [],
                    "expected_role": "BL",
                    "fields": FIELD_NAMES,
                    "evidence_ids": ["ev_em_001_body"],
                    "suggested_action": "Request draft Bill of Lading from carrier or check for additional thread attachments",
                    "recovery_state": "EXHAUSTED",
                    "recovery_detail": "Email contains only 1 attachment; draft BL role absent",
                    "attempt_ids": ["att_parse_001"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_parse_001",
                    "operation_id": "op_parse_si",
                    "stage": "parsing",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "pdf_parser",
                    "model_identifier": None,
                    "prompt_version": None,
                    "token_usage": None,
                    "latency_ms": 120
                }
            ]
        }
    }
    with open(CASES_DIR / "case_01_missing_attachment.json", "w", encoding="utf-8") as f:
        json.dump(c01, f, indent=2)

    # Case 2: unreadable_document
    c02 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_002",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_002",
            "sender": "carrier@oceanline.com",
            "subject": "SI and Draft BL Attached",
            "body": "Find SI and draft BL attached for verification.",
            "attachments": [
                {"document_id": "doc_si_002", "path": "attachments/si_002.pdf", "mime_type": "application/pdf"},
                {"document_id": "doc_bl_002", "path": "attachments/bl_002_corrupt.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "RESOLVED",
            "category": "document_comparison",
            "reason": "Comparison request with both documents referenced",
            "evidence_ids": ["ev_em_002_body"],
            "confidence_indicator": "HIGH"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: draft BL file stream corrupted and unreadable",
        "documents": [
            {"document_id": "doc_si_002", "role": "SI", "identification_evidence_ids": ["ev_doc_si_002_id"]},
            {"document_id": "doc_bl_002", "role": "BL", "identification_evidence_ids": ["ev_doc_bl_002_id"]}
        ],
        "parsers": [
            {
                "document_id": "doc_si_002",
                "status": "SUCCESS",
                "text": "SHIPPING INSTRUCTION...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_si_002_id"],
                "attempt_ids": ["att_parse_002_si"]
            },
            {
                "document_id": "doc_bl_002",
                "status": "UNREADABLE",
                "text": None,
                "usable_for_extraction": False,
                "diagnostic_evidence_ids": ["ev_doc_bl_002_diag"],
                "attempt_ids": ["att_parse_002_bl"]
            }
        ],
        "extractions": [],
        "evidence": [
            {
                "evidence_id": "ev_em_002_body",
                "source_type": "email",
                "source_id": "em_case_002",
                "kind": "text_span",
                "quote": "Find SI and draft BL attached",
                "location": None,
                "detail": None
            },
            {
                "evidence_id": "ev_doc_si_002_id",
                "source_type": "document",
                "source_id": "doc_si_002",
                "kind": "text_span",
                "quote": "SHIPPING INSTRUCTION",
                "location": {"page": 1},
                "detail": None
            },
            {
                "evidence_id": "ev_doc_bl_002_id",
                "source_type": "document",
                "source_id": "doc_bl_002",
                "kind": "document_metadata",
                "quote": None,
                "location": None,
                "detail": "Filename bl_002_corrupt.pdf indicates draft BL role"
            },
            {
                "evidence_id": "ev_doc_bl_002_diag",
                "source_type": "processing",
                "source_id": "doc_bl_002",
                "kind": "processing_error",
                "quote": None,
                "location": None,
                "detail": "PdfStreamError: EOF marker not found; stream truncated at byte 1024"
            }
        ],
        "partial_result": {
            "comparisons": [],
            "unresolved_fields": FIELD_NAMES
        },
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_002",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_002_corrupt_bl",
                    "stage": "parsing",
                    "logical_reason": "unreadable_document",
                    "evaluation_reason": "unreadable_document",
                    "document_ids": ["doc_bl_002"],
                    "expected_role": "BL",
                    "fields": FIELD_NAMES,
                    "evidence_ids": ["ev_doc_bl_002_diag"],
                    "suggested_action": "Request uncorrupted PDF draft BL from carrier",
                    "recovery_state": "EXHAUSTED",
                    "recovery_detail": "Both primary PDF reader and OCR repair failed due to truncated file stream",
                    "attempt_ids": ["att_parse_002_bl"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_parse_002_si",
                    "operation_id": "op_parse_si_002",
                    "stage": "parsing",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "pdf_parser",
                    "model_identifier": None,
                    "prompt_version": None,
                    "token_usage": None,
                    "latency_ms": 110
                },
                {
                    "attempt_id": "att_parse_002_bl",
                    "operation_id": "op_parse_bl_002",
                    "stage": "parsing",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "FAILED",
                    "error_code": "STREAM_TRUNCATED",
                    "provider_adapter": "pdf_parser",
                    "model_identifier": None,
                    "prompt_version": None,
                    "token_usage": None,
                    "latency_ms": 45
                }
            ]
        }
    }
    with open(CASES_DIR / "case_02_unreadable_document.json", "w", encoding="utf-8") as f:
        json.dump(c02, f, indent=2)

    # Case 3: wrong_or_uncertain_document_type
    c03 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_003",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_003",
            "sender": "forwarder@logistics.com",
            "subject": "Comparison Files Attached",
            "body": "Attached please find files for verification.",
            "attachments": [
                {"document_id": "doc_cand_a", "path": "attachments/si_doc.pdf", "mime_type": "application/pdf"},
                {"document_id": "doc_cand_b", "path": "attachments/bl_rev1.pdf", "mime_type": "application/pdf"},
                {"document_id": "doc_cand_c", "path": "attachments/bl_rev2.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "RESOLVED",
            "category": "document_comparison",
            "reason": "Document comparison requested with multi-file attachment set",
            "evidence_ids": ["ev_em_003_body"],
            "confidence_indicator": "HIGH"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: multiple candidate Draft BL files attached; role assignment ambiguous",
        "documents": [
            {"document_id": "doc_cand_a", "role": "SI", "identification_evidence_ids": ["ev_cand_a_id"]},
            {"document_id": "doc_cand_b", "role": "UNKNOWN", "identification_evidence_ids": ["ev_cand_b_id"]},
            {"document_id": "doc_cand_c", "role": "UNKNOWN", "identification_evidence_ids": ["ev_cand_c_id"]}
        ],
        "parsers": [
            {
                "document_id": "doc_cand_a",
                "status": "SUCCESS",
                "text": "SHIPPING INSTRUCTION...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_cand_a_id"],
                "attempt_ids": ["att_parse_003"]
            }
        ],
        "extractions": [],
        "evidence": [
            {
                "evidence_id": "ev_em_003_body",
                "source_type": "email",
                "source_id": "em_case_003",
                "kind": "text_span",
                "quote": "Attached please find files for verification",
                "location": None,
                "detail": None
            },
            {
                "evidence_id": "ev_cand_a_id",
                "source_type": "document",
                "source_id": "doc_cand_a",
                "kind": "text_span",
                "quote": "SHIPPING INSTRUCTION",
                "location": {"page": 1},
                "detail": None
            },
            {
                "evidence_id": "ev_cand_b_id",
                "source_type": "document",
                "source_id": "doc_cand_b",
                "kind": "text_span",
                "quote": "DRAFT BILL OF LADING - REVISION 1",
                "location": {"page": 1},
                "detail": None
            },
            {
                "evidence_id": "ev_cand_c_id",
                "source_type": "document",
                "source_id": "doc_cand_c",
                "kind": "text_span",
                "quote": "DRAFT BILL OF LADING - REVISION 2",
                "location": {"page": 1},
                "detail": None
            }
        ],
        "partial_result": {
            "comparisons": [],
            "unresolved_fields": FIELD_NAMES
        },
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_003",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_003_duplicate_bl",
                    "stage": "identification",
                    "logical_reason": "wrong_or_uncertain_document_type",
                    "evaluation_reason": "wrong_or_uncertain_document_type",
                    "document_ids": ["doc_cand_b", "doc_cand_c"],
                    "expected_role": "BL",
                    "fields": FIELD_NAMES,
                    "evidence_ids": ["ev_cand_b_id", "ev_cand_c_id"],
                    "suggested_action": "Select the authoritative Draft BL candidate between bl_rev1.pdf and bl_rev2.pdf",
                    "recovery_state": "UNRELIABLE",
                    "recovery_detail": "Heuristic identification found 2 valid BL candidate files",
                    "attempt_ids": ["att_parse_003"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_parse_003",
                    "operation_id": "op_ident_003",
                    "stage": "identification",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "role_resolver",
                    "model_identifier": None,
                    "prompt_version": None,
                    "token_usage": None,
                    "latency_ms": 85
                }
            ]
        }
    }
    with open(CASES_DIR / "case_03_wrong_or_uncertain_document_type.json", "w", encoding="utf-8") as f:
        json.dump(c03, f, indent=2)

    # Case 4: missing_required_value (port_of_discharge missing in SI)
    si_ext_c04 = make_clean_extractions("doc_si_004", "SI")
    si_ext_c04["fields"]["port_of_discharge"] = {
        "field": "port_of_discharge",
        "reliability": "MISSING",
        "candidates": [],
        "selected_candidate": None,
        "normalized": None,
        "explanation": "Field port_of_discharge not found in document text"
    }
    bl_ext_c04 = make_clean_extractions("doc_bl_004", "BL")

    ev_list_c04 = [
        {
            "evidence_id": "ev_em_004_body",
            "source_type": "email",
            "source_id": "em_case_004",
            "kind": "text_span",
            "quote": "Please verify SI and BL attached",
            "location": None,
            "detail": None
        },
        {
            "evidence_id": "ev_doc_si_004_id",
            "source_type": "document",
            "source_id": "doc_si_004",
            "kind": "text_span",
            "quote": "SHIPPING INSTRUCTION",
            "location": {"page": 1},
            "detail": None
        },
        {
            "evidence_id": "ev_doc_bl_004_id",
            "source_type": "document",
            "source_id": "doc_bl_004",
            "kind": "text_span",
            "quote": "DRAFT BILL OF LADING",
            "location": {"page": 1},
            "detail": None
        }
    ]
    ev_list_c04.extend(make_evidence_list("doc_si_004"))
    ev_list_c04.extend(make_evidence_list("doc_bl_004"))

    c04 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_004",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_004",
            "sender": "ops@shipping.com",
            "subject": "Comparison - Port Missing",
            "body": "Please verify SI and BL attached.",
            "attachments": [
                {"document_id": "doc_si_004", "path": "attachments/si_004.pdf", "mime_type": "application/pdf"},
                {"document_id": "doc_bl_004", "path": "attachments/bl_004.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "RESOLVED",
            "category": "document_comparison",
            "reason": "Clean document comparison intent",
            "evidence_ids": ["ev_em_004_body"],
            "confidence_indicator": "HIGH"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: mandatory port_of_discharge value missing from SI document",
        "documents": [
            {"document_id": "doc_si_004", "role": "SI", "identification_evidence_ids": ["ev_doc_si_004_id"]},
            {"document_id": "doc_bl_004", "role": "BL", "identification_evidence_ids": ["ev_doc_bl_004_id"]}
        ],
        "parsers": [
            {
                "document_id": "doc_si_004",
                "status": "SUCCESS",
                "text": "SHIPPING INSTRUCTION...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_si_004_id"],
                "attempt_ids": ["att_ext_004"]
            },
            {
                "document_id": "doc_bl_004",
                "status": "SUCCESS",
                "text": "DRAFT BILL OF LADING...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_bl_004_id"],
                "attempt_ids": ["att_ext_004"]
            }
        ],
        "extractions": [si_ext_c04, bl_ext_c04],
        "evidence": ev_list_c04,
        "partial_result": {
            "comparisons": [
                {"field": "shipper", "si_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI", "bl_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "consignee", "si_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM", "bl_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "notify_party", "si_value": "SAME AS CONSIGNEE", "bl_value": "SAME AS CONSIGNEE", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "port_of_loading", "si_value": "SHANGHAI, CHINA", "bl_value": "SHANGHAI, CHINA", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "container_count", "si_value": 2, "bl_value": 2, "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "gross_weight_kg", "si_value": "22000", "bl_value": "22000", "outcome": "MATCH", "rule_version": "v1.0"}
            ],
            "unresolved_fields": ["port_of_discharge"]
        },
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_004",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_004_missing_pod",
                    "stage": "extraction",
                    "logical_reason": "missing_required_value",
                    "evaluation_reason": "missing_required_value",
                    "document_ids": ["doc_si_004"],
                    "expected_role": "SI",
                    "fields": ["port_of_discharge"],
                    "evidence_ids": ["ev_doc_si_004_id"],
                    "suggested_action": "Manually inspect SI document to supply missing port_of_discharge candidate",
                    "recovery_state": "EXHAUSTED",
                    "recovery_detail": "Deterministic extraction found no POD token or table cell",
                    "attempt_ids": ["att_ext_004"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_ext_004",
                    "operation_id": "op_ext_004",
                    "stage": "extraction",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "gemini_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": {"prompt_tokens": 1200, "completion_tokens": 300},
                    "latency_ms": 650
                }
            ]
        }
    }
    with open(CASES_DIR / "case_04_missing_required_value.json", "w", encoding="utf-8") as f:
        json.dump(c04, f, indent=2)

    # Case 5: uncertain_result (vague email body -> category is null)
    c05 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_005",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_005",
            "sender": "unknown@partner.com",
            "subject": "Quick question regarding documents",
            "body": "Hi team, please see attached documents for your review and let us know what you think.",
            "attachments": [
                {"document_id": "doc_vague_001", "path": "attachments/vague_doc.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "NEEDS_REVIEW",
            "category": None,
            "reason": "Email body lacks specific shipping intent keywords; ambiguous context",
            "evidence_ids": ["ev_em_005_body"],
            "confidence_indicator": "LOW"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: email intent is ambiguous and unresolved (category is null)",
        "documents": [],
        "parsers": [],
        "extractions": [],
        "evidence": [
            {
                "evidence_id": "ev_em_005_body",
                "source_type": "email",
                "source_id": "em_case_005",
                "kind": "text_span",
                "quote": "please see attached documents for your review and let us know what you think",
                "location": None,
                "detail": None
            }
        ],
        "partial_result": None,
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_005",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_005_ambiguous_intent",
                    "stage": "classification",
                    "logical_reason": "uncertain_result",
                    "evaluation_reason": "uncertain_result",
                    "document_ids": [],
                    "expected_role": None,
                    "fields": [],
                    "evidence_ids": ["ev_em_005_body"],
                    "suggested_action": "Confirm authoritative email intent category among canonical options",
                    "recovery_state": "UNRELIABLE",
                    "recovery_detail": "Model confidence below reliability threshold; category remains null",
                    "attempt_ids": ["att_cls_005"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_cls_005",
                    "operation_id": "op_cls_005",
                    "stage": "classification",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "classifier_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": {"prompt_tokens": 400, "completion_tokens": 80},
                    "latency_ms": 320
                }
            ]
        }
    }
    with open(CASES_DIR / "case_05_uncertain_result.json", "w", encoding="utf-8") as f:
        json.dump(c05, f, indent=2)

    # Case 6: conflicting_candidate_values (conflicting gross weight in SI)
    si_ext_c06 = make_clean_extractions("doc_si_006", "SI")
    si_ext_c06["fields"]["gross_weight_kg"] = {
        "field": "gross_weight_kg",
        "reliability": "CONFLICTING",
        "candidates": [
            {
                "raw_value": "22000 KG",
                "source_unit": "KG",
                "evidence_ids": ["ev_si_weight_cand1"]
            },
            {
                "raw_value": "24500 KG",
                "source_unit": "KG",
                "evidence_ids": ["ev_si_weight_cand2"]
            }
        ],
        "selected_candidate": None,
        "normalized": None,
        "explanation": "Multiple conflicting candidate weights found in SI document"
    }
    bl_ext_c06 = make_clean_extractions("doc_bl_006", "BL")

    ev_list_c06 = [
        {
            "evidence_id": "ev_em_006_body",
            "source_type": "email",
            "source_id": "em_case_006",
            "kind": "text_span",
            "quote": "Please verify SI vs Draft BL",
            "location": None,
            "detail": None
        },
        {
            "evidence_id": "ev_doc_si_006_id",
            "source_type": "document",
            "source_id": "doc_si_006",
            "kind": "text_span",
            "quote": "SHIPPING INSTRUCTION",
            "location": {"page": 1},
            "detail": None
        },
        {
            "evidence_id": "ev_doc_bl_006_id",
            "source_type": "document",
            "source_id": "doc_bl_006",
            "kind": "text_span",
            "quote": "DRAFT BILL OF LADING",
            "location": {"page": 1},
            "detail": None
        },
        {
            "evidence_id": "ev_si_weight_cand1",
            "source_type": "document",
            "source_id": "doc_si_006",
            "kind": "text_span",
            "quote": "GROSS WEIGHT: 22,000 KGS",
            "location": {"page": 1, "section": "Header Summary"},
            "detail": None
        },
        {
            "evidence_id": "ev_si_weight_cand2",
            "source_type": "document",
            "source_id": "doc_si_006",
            "kind": "text_span",
            "quote": "TOTAL WEIGHT: 24,500 KGS",
            "location": {"page": 2, "section": "Cargo Breakdown Table"},
            "detail": None
        }
    ]
    ev_list_c06.extend(make_evidence_list("doc_si_006"))
    ev_list_c06.extend(make_evidence_list("doc_bl_006"))

    c06 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_006",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_006",
            "sender": "shipper@cargo.com",
            "subject": "Comparison - Weight Discrepancy",
            "body": "Please verify SI vs Draft BL.",
            "attachments": [
                {"document_id": "doc_si_006", "path": "attachments/si_006.pdf", "mime_type": "application/pdf"},
                {"document_id": "doc_bl_006", "path": "attachments/bl_006.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "RESOLVED",
            "category": "document_comparison",
            "reason": "Clean document comparison intent",
            "evidence_ids": ["ev_em_006_body"],
            "confidence_indicator": "HIGH"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: conflicting candidate gross weights found in SI (22000 KG vs 24500 KG)",
        "documents": [
            {"document_id": "doc_si_006", "role": "SI", "identification_evidence_ids": ["ev_doc_si_006_id"]},
            {"document_id": "doc_bl_006", "role": "BL", "identification_evidence_ids": ["ev_doc_bl_006_id"]}
        ],
        "parsers": [
            {
                "document_id": "doc_si_006",
                "status": "SUCCESS",
                "text": "SHIPPING INSTRUCTION...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_si_006_id"],
                "attempt_ids": ["att_ext_006"]
            },
            {
                "document_id": "doc_bl_006",
                "status": "SUCCESS",
                "text": "DRAFT BILL OF LADING...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_bl_006_id"],
                "attempt_ids": ["att_ext_006"]
            }
        ],
        "extractions": [si_ext_c06, bl_ext_c06],
        "evidence": ev_list_c06,
        "partial_result": {
            "comparisons": [
                {"field": "shipper", "si_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI", "bl_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "consignee", "si_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM", "bl_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "notify_party", "si_value": "SAME AS CONSIGNEE", "bl_value": "SAME AS CONSIGNEE", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "port_of_loading", "si_value": "SHANGHAI, CHINA", "bl_value": "SHANGHAI, CHINA", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "port_of_discharge", "si_value": "ROTTERDAM, NETHERLANDS", "bl_value": "ROTTERDAM, NETHERLANDS", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "container_count", "si_value": 2, "bl_value": 2, "outcome": "MATCH", "rule_version": "v1.0"}
            ],
            "unresolved_fields": ["gross_weight_kg"]
        },
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_006",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_006_conflicting_weight",
                    "stage": "extraction",
                    "logical_reason": "conflicting_candidate_values",
                    "evaluation_reason": "conflicting_candidate_values",
                    "document_ids": ["doc_si_006"],
                    "expected_role": "SI",
                    "fields": ["gross_weight_kg"],
                    "evidence_ids": ["ev_si_weight_cand1", "ev_si_weight_cand2"],
                    "suggested_action": "Select authoritative gross weight candidate between 22000 KG and 24500 KG",
                    "recovery_state": "UNRELIABLE",
                    "recovery_detail": "Extracted multiple distinct weights with conflicting evidence",
                    "attempt_ids": ["att_ext_006"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_ext_006",
                    "operation_id": "op_ext_006",
                    "stage": "extraction",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "gemini_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": {"prompt_tokens": 1400, "completion_tokens": 320},
                    "latency_ms": 710
                }
            ]
        }
    }
    with open(CASES_DIR / "case_06_conflicting_candidate_values.json", "w", encoding="utf-8") as f:
        json.dump(c06, f, indent=2)

    # Case 7: processing_or_provider_failure
    c07 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_007",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_007",
            "sender": "partner@global.com",
            "subject": "Comparison Files Attached",
            "body": "Please process attached SI and draft BL documents.",
            "attachments": [
                {"document_id": "doc_si_007", "path": "attachments/si_007.pdf", "mime_type": "application/pdf"},
                {"document_id": "doc_bl_007", "path": "attachments/bl_007.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "RESOLVED",
            "category": "document_comparison",
            "reason": "Standard document comparison intent",
            "evidence_ids": ["ev_em_007_body"],
            "confidence_indicator": "HIGH"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: AI provider technical retries exhausted (HTTP 503 outage); manual review required",
        "documents": [
            {"document_id": "doc_si_007", "role": "SI", "identification_evidence_ids": ["ev_doc_si_007_id"]},
            {"document_id": "doc_bl_007", "role": "BL", "identification_evidence_ids": ["ev_doc_bl_007_id"]}
        ],
        "parsers": [
            {
                "document_id": "doc_si_007",
                "status": "SUCCESS",
                "text": "SHIPPING INSTRUCTION...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_si_007_id"],
                "attempt_ids": ["att_ext_007_1", "att_ext_007_2", "att_ext_007_3"]
            }
        ],
        "extractions": [],
        "evidence": [
            {
                "evidence_id": "ev_em_007_body",
                "source_type": "email",
                "source_id": "em_case_007",
                "kind": "text_span",
                "quote": "Please process attached SI and draft BL documents",
                "location": None,
                "detail": None
            },
            {
                "evidence_id": "ev_doc_si_007_id",
                "source_type": "document",
                "source_id": "doc_si_007",
                "kind": "text_span",
                "quote": "SHIPPING INSTRUCTION",
                "location": {"page": 1},
                "detail": None
            },
            {
                "evidence_id": "ev_doc_bl_007_id",
                "source_type": "document",
                "source_id": "doc_bl_007",
                "kind": "text_span",
                "quote": "DRAFT BILL OF LADING",
                "location": {"page": 1},
                "detail": None
            },
            {
                "evidence_id": "ev_prov_err_007",
                "source_type": "processing",
                "source_id": "doc_si_007",
                "kind": "processing_error",
                "quote": None,
                "location": None,
                "detail": "AI Provider 503 Service Unavailable: connection attempts 1, 2, 3 exhausted"
            }
        ],
        "partial_result": {
            "comparisons": [],
            "unresolved_fields": FIELD_NAMES
        },
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_007",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_007_provider_exhaustion",
                    "stage": "extraction",
                    "logical_reason": "processing_or_provider_failure",
                    "evaluation_reason": "processing_or_provider_failure",
                    "document_ids": ["doc_si_007"],
                    "expected_role": "SI",
                    "fields": FIELD_NAMES,
                    "evidence_ids": ["ev_prov_err_007"],
                    "suggested_action": "Manually inspect documents or retry extraction after provider recovery",
                    "recovery_state": "EXHAUSTED",
                    "recovery_detail": "All 3 technical retry attempts returned HTTP 503; deterministic fallback parser unavailable for scanned pages",
                    "attempt_ids": ["att_ext_007_1", "att_ext_007_2", "att_ext_007_3"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_ext_007_1",
                    "operation_id": "op_ext_007",
                    "stage": "extraction",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "FAILED",
                    "error_code": "503_UNAVAILABLE",
                    "provider_adapter": "gemini_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": None,
                    "latency_ms": 2500
                },
                {
                    "attempt_id": "att_ext_007_2",
                    "operation_id": "op_ext_007",
                    "stage": "extraction",
                    "kind": "technical_retry",
                    "attempt_number": 2,
                    "outcome": "FAILED",
                    "error_code": "503_UNAVAILABLE",
                    "provider_adapter": "gemini_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": None,
                    "latency_ms": 5000
                },
                {
                    "attempt_id": "att_ext_007_3",
                    "operation_id": "op_ext_007",
                    "stage": "extraction",
                    "kind": "technical_retry",
                    "attempt_number": 3,
                    "outcome": "FAILED",
                    "error_code": "503_UNAVAILABLE",
                    "provider_adapter": "gemini_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": None,
                    "latency_ms": 10000
                }
            ]
        }
    }
    with open(CASES_DIR / "case_07_processing_or_provider_failure.json", "w", encoding="utf-8") as f:
        json.dump(c07, f, indent=2)

    # Case 8: partial_preservation_6_of_7 (6 fields reliable & MATCH, gross_weight unresolved)
    si_ext_c08 = make_clean_extractions("doc_si_008", "SI")
    bl_ext_c08 = make_clean_extractions("doc_bl_008", "BL")
    bl_ext_c08["fields"]["gross_weight_kg"] = {
        "field": "gross_weight_kg",
        "reliability": "MISSING",
        "candidates": [],
        "selected_candidate": None,
        "normalized": None,
        "explanation": "Gross weight missing from Draft BL scan"
    }

    ev_list_c08 = [
        {
            "evidence_id": "ev_em_008_body",
            "source_type": "email",
            "source_id": "em_case_008",
            "kind": "text_span",
            "quote": "Verify SI vs BL attached",
            "location": None,
            "detail": None
        },
        {
            "evidence_id": "ev_doc_si_008_id",
            "source_type": "document",
            "source_id": "doc_si_008",
            "kind": "text_span",
            "quote": "SHIPPING INSTRUCTION",
            "location": {"page": 1},
            "detail": None
        },
        {
            "evidence_id": "ev_doc_bl_008_id",
            "source_type": "document",
            "source_id": "doc_bl_008",
            "kind": "text_span",
            "quote": "DRAFT BILL OF LADING",
            "location": {"page": 1},
            "detail": None
        }
    ]
    ev_list_c08.extend(make_evidence_list("doc_si_008"))
    ev_list_c08.extend(make_evidence_list("doc_bl_008"))

    c08 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_008",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_008",
            "sender": "logistics@global.com",
            "subject": "Comparison - 6 Fields Matching",
            "body": "Verify SI vs BL attached.",
            "attachments": [
                {"document_id": "doc_si_008", "path": "attachments/si_008.pdf", "mime_type": "application/pdf"},
                {"document_id": "doc_bl_008", "path": "attachments/bl_008.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "RESOLVED",
            "category": "document_comparison",
            "reason": "Standard document comparison intent",
            "evidence_ids": ["ev_em_008_body"],
            "confidence_indicator": "HIGH"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: 6 mandatory fields verified and match; gross_weight_kg is missing from BL",
        "documents": [
            {"document_id": "doc_si_008", "role": "SI", "identification_evidence_ids": ["ev_doc_si_008_id"]},
            {"document_id": "doc_bl_008", "role": "BL", "identification_evidence_ids": ["ev_doc_bl_008_id"]}
        ],
        "parsers": [
            {
                "document_id": "doc_si_008",
                "status": "SUCCESS",
                "text": "SHIPPING INSTRUCTION...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_si_008_id"],
                "attempt_ids": ["att_ext_008"]
            },
            {
                "document_id": "doc_bl_008",
                "status": "SUCCESS",
                "text": "DRAFT BILL OF LADING...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_bl_008_id"],
                "attempt_ids": ["att_ext_008"]
            }
        ],
        "extractions": [si_ext_c08, bl_ext_c08],
        "evidence": ev_list_c08,
        "partial_result": {
            "comparisons": [
                {"field": "shipper", "si_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI", "bl_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "consignee", "si_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM", "bl_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "notify_party", "si_value": "SAME AS CONSIGNEE", "bl_value": "SAME AS CONSIGNEE", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "port_of_loading", "si_value": "SHANGHAI, CHINA", "bl_value": "SHANGHAI, CHINA", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "port_of_discharge", "si_value": "ROTTERDAM, NETHERLANDS", "bl_value": "ROTTERDAM, NETHERLANDS", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "container_count", "si_value": 2, "bl_value": 2, "outcome": "MATCH", "rule_version": "v1.0"}
            ],
            "unresolved_fields": ["gross_weight_kg"]
        },
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_008",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_008_weight_missing",
                    "stage": "extraction",
                    "logical_reason": "missing_required_value",
                    "evaluation_reason": "missing_required_value",
                    "document_ids": ["doc_bl_008"],
                    "expected_role": "BL",
                    "fields": ["gross_weight_kg"],
                    "evidence_ids": ["ev_doc_bl_008_id"],
                    "suggested_action": "Correct or supply gross_weight_kg candidate on Draft BL; 6 reliable matching fields must be preserved",
                    "recovery_state": "EXHAUSTED",
                    "recovery_detail": "Weight field obscured in BL draft footer",
                    "attempt_ids": ["att_ext_008"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_ext_008",
                    "operation_id": "op_ext_008",
                    "stage": "extraction",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "gemini_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": {"prompt_tokens": 1250, "completion_tokens": 310},
                    "latency_ms": 680
                }
            ]
        }
    }
    with open(CASES_DIR / "case_08_partial_preservation_6_of_7.json", "w", encoding="utf-8") as f:
        json.dump(c08, f, indent=2)

    # Case 9: tristate_known_mismatch_plus_unresolved
    # 5 matching, 1 known mismatch (container_count 2 vs 3), 1 unresolved (gross_weight_kg missing in BL)
    # Crucial tri-state test: mismatch_detected MUST BE null while any required field is unresolved!
    si_ext_c09 = make_clean_extractions("doc_si_009", "SI", count=2)
    bl_ext_c09 = make_clean_extractions("doc_bl_009", "BL", count=3)
    bl_ext_c09["fields"]["gross_weight_kg"] = {
        "field": "gross_weight_kg",
        "reliability": "MISSING",
        "candidates": [],
        "selected_candidate": None,
        "normalized": None,
        "explanation": "Gross weight unextracted"
    }

    ev_list_c09 = [
        {
            "evidence_id": "ev_em_009_body",
            "source_type": "email",
            "source_id": "em_case_009",
            "kind": "text_span",
            "quote": "Verify attached files",
            "location": None,
            "detail": None
        },
        {
            "evidence_id": "ev_doc_si_009_id",
            "source_type": "document",
            "source_id": "doc_si_009",
            "kind": "text_span",
            "quote": "SHIPPING INSTRUCTION",
            "location": {"page": 1},
            "detail": None
        },
        {
            "evidence_id": "ev_doc_bl_009_id",
            "source_type": "document",
            "source_id": "doc_bl_009",
            "kind": "text_span",
            "quote": "DRAFT BILL OF LADING",
            "location": {"page": 1},
            "detail": None
        }
    ]
    ev_list_c09.extend(make_evidence_list("doc_si_009"))
    ev_list_c09.extend(make_evidence_list("doc_bl_009"))

    c09 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_009",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_009",
            "sender": "ops@freight.com",
            "subject": "Comparison - Discrepancy Found But Incomplete",
            "body": "Verify attached files.",
            "attachments": [
                {"document_id": "doc_si_009", "path": "attachments/si_009.pdf", "mime_type": "application/pdf"},
                {"document_id": "doc_bl_009", "path": "attachments/bl_009.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "RESOLVED",
            "category": "document_comparison",
            "reason": "Standard document comparison intent",
            "evidence_ids": ["ev_em_009_body"],
            "confidence_indicator": "HIGH"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: partial mismatch confirmed on container_count (SI: 2 / BL: 3), but gross_weight_kg remains unresolved",
        "documents": [
            {"document_id": "doc_si_009", "role": "SI", "identification_evidence_ids": ["ev_doc_si_009_id"]},
            {"document_id": "doc_bl_009", "role": "BL", "identification_evidence_ids": ["ev_doc_bl_009_id"]}
        ],
        "parsers": [
            {
                "document_id": "doc_si_009",
                "status": "SUCCESS",
                "text": "SHIPPING INSTRUCTION...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_si_009_id"],
                "attempt_ids": ["att_ext_009"]
            },
            {
                "document_id": "doc_bl_009",
                "status": "SUCCESS",
                "text": "DRAFT BILL OF LADING...",
                "usable_for_extraction": True,
                "diagnostic_evidence_ids": ["ev_doc_bl_009_id"],
                "attempt_ids": ["att_ext_009"]
            }
        ],
        "extractions": [si_ext_c09, bl_ext_c09],
        "evidence": ev_list_c09,
        "partial_result": {
            "comparisons": [
                {"field": "shipper", "si_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI", "bl_value": "ACME SHIPPING CORP, 100 OCEAN WAY, SHANGHAI", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "consignee", "si_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM", "bl_value": "GLOBAL LOGISTICS B.V., 45 HAVENLAAN, ROTTERDAM", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "notify_party", "si_value": "SAME AS CONSIGNEE", "bl_value": "SAME AS CONSIGNEE", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "port_of_loading", "si_value": "SHANGHAI, CHINA", "bl_value": "SHANGHAI, CHINA", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "port_of_discharge", "si_value": "ROTTERDAM, NETHERLANDS", "bl_value": "ROTTERDAM, NETHERLANDS", "outcome": "MATCH", "rule_version": "v1.0"},
                {"field": "container_count", "si_value": 2, "bl_value": 3, "outcome": "MISMATCH", "rule_version": "v1.0"}
            ],
            "unresolved_fields": ["gross_weight_kg"]
        },
        "discrepancies": [
            {"field": "container_count", "si_value": 2, "bl_value": 3}
        ],
        "review": {
            "review_id": "rev_case_009",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_009_unresolved_weight",
                    "stage": "extraction",
                    "logical_reason": "missing_required_value",
                    "evaluation_reason": "missing_required_value",
                    "document_ids": ["doc_bl_009"],
                    "expected_role": "BL",
                    "fields": ["gross_weight_kg"],
                    "evidence_ids": ["ev_doc_bl_009_id"],
                    "suggested_action": "Supply gross_weight_kg on Draft BL; tri-state rule requires mismatch_detected = null until all 7 fields resolved",
                    "recovery_state": "EXHAUSTED",
                    "recovery_detail": "Weight unextracted; partial discrepancy on container_count preserved",
                    "attempt_ids": ["att_ext_009"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_ext_009",
                    "operation_id": "op_ext_009",
                    "stage": "extraction",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "gemini_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": {"prompt_tokens": 1300, "completion_tokens": 315},
                    "latency_ms": 690
                }
            ]
        }
    }
    with open(CASES_DIR / "case_09_tristate_known_mismatch_plus_unresolved.json", "w", encoding="utf-8") as f:
        json.dump(c09, f, indent=2)

    # Case 10: unresolved_classification (DC-01 baseline: category is null, attachments not processed)
    c10 = {
        "schema_version": "1.0-draft",
        "email_id": "em_case_010",
        "revision": 1,
        "previous_revision": None,
        "email": {
            "email_id": "em_case_010",
            "sender": "partner@unknown.com",
            "subject": "Fwd: Documents",
            "body": "FYI",
            "attachments": [
                {"document_id": "doc_unresolved_001", "path": "attachments/doc_unresolved.pdf", "mime_type": "application/pdf"}
            ]
        },
        "classification": {
            "state": "NEEDS_REVIEW",
            "category": None,
            "reason": "Single acronym email body; intent undetermined",
            "evidence_ids": ["ev_em_010_body"],
            "confidence_indicator": "LOW"
        },
        "state": "NEEDS_REVIEW",
        "outcome": None,
        "mismatch_detected": None,
        "result_summary": "Review required: unresolved classification (category = null); attachments unparsed pending intent",
        "documents": [],
        "parsers": [],
        "extractions": [],
        "evidence": [
            {
                "evidence_id": "ev_em_010_body",
                "source_type": "email",
                "source_id": "em_case_010",
                "kind": "text_span",
                "quote": "FYI",
                "location": None,
                "detail": None
            }
        ],
        "partial_result": None,
        "discrepancies": [],
        "review": {
            "review_id": "rev_case_010",
            "state": "OPEN",
            "issues": [
                {
                    "issue_id": "iss_010_unresolved_cat",
                    "stage": "classification",
                    "logical_reason": "uncertain_result",
                    "evaluation_reason": "uncertain_result",
                    "document_ids": [],
                    "expected_role": None,
                    "fields": [],
                    "evidence_ids": ["ev_em_010_body"],
                    "suggested_action": "Review email context and assign canonical internal category",
                    "recovery_state": "UNRELIABLE",
                    "recovery_detail": "Heuristic classifier unable to resolve intent from 3-letter body",
                    "attempt_ids": ["att_cls_010"]
                }
            ]
        },
        "processing": {
            "technical_attempt_limit": 3,
            "semantic_attempt_limit": 2,
            "attempts": [
                {
                    "attempt_id": "att_cls_010",
                    "operation_id": "op_cls_010",
                    "stage": "classification",
                    "kind": "primary",
                    "attempt_number": 1,
                    "outcome": "SUCCEEDED",
                    "error_code": None,
                    "provider_adapter": "classifier_adapter",
                    "model_identifier": "gemini-2.5-flash",
                    "prompt_version": "v1.0",
                    "token_usage": {"prompt_tokens": 150, "completion_tokens": 40},
                    "latency_ms": 190
                }
            ]
        }
    }
    with open(CASES_DIR / "case_10_unresolved_classification.json", "w", encoding="utf-8") as f:
        json.dump(c10, f, indent=2)

    # Register cases in metadata
    case_ids = [
        ("case_01_missing_attachment", "missing_attachment", "em_case_001", "Draft BL missing from email attachments"),
        ("case_02_unreadable_document", "unreadable_document", "em_case_002", "Corrupted PDF stream unreadable"),
        ("case_03_wrong_or_uncertain_document_type", "wrong_or_uncertain_document_type", "em_case_003", "Duplicate Draft BL candidates attached"),
        ("case_04_missing_required_value", "missing_required_value", "em_case_004", "Mandatory port_of_discharge missing in SI"),
        ("case_05_uncertain_result", "uncertain_result", "em_case_005", "Vague email body leaves category = null"),
        ("case_06_conflicting_candidate_values", "conflicting_candidate_values", "em_case_006", "Conflicting candidate weights in SI"),
        ("case_07_processing_or_provider_failure", "processing_or_provider_failure", "em_case_007", "AI provider repeated 503 outage"),
        ("case_08_partial_preservation_6_of_7", "missing_required_value", "em_case_008", "6 matching fields reliable, 1 weight field missing"),
        ("case_09_tristate_known_mismatch_plus_unresolved", "missing_required_value", "em_case_009", "Confirmed container count mismatch while weight is unresolved"),
        ("case_10_unresolved_classification", "uncertain_result", "em_case_010", "Unresolved classification baseline DC-01"),
    ]
    for cid, reason, em_id, desc in case_ids:
        fixtures_meta[cid] = {
            "file": f"cases/{cid}.json",
            "fixture_type": "review_case",
            "scenario": cid,
            "valid_payload": True,
            "starting_revision": 1,
            "expected_validation_result": "VALID",
            "expected_http_status": 200,
            "expected_review_reason": reason,
            "tags": ["case", reason, "hitl"],
            "rationale": desc
        }

    # =========================================================================
    # B. REVIEW UPDATES (18 valid payloads)
    # =========================================================================

    # 1. Classification: null -> document_comparison
    u01 = {
        "review_id": "rev_case_010",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Attachment inspection confirms document comparison pair attached",
        "category": "document_comparison",
        "classification_evidence_ids": ["ev_added_em_010_header"],
        "role_corrections": [],
        "corrections": [],
        "added_evidence": [
            {
                "evidence_id": "ev_added_em_010_header",
                "source_type": "email",
                "source_id": "em_case_010",
                "kind": "text_span",
                "quote": "Subject: Fwd: Documents",
                "location": None,
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_cls_unresolved_to_comparison.json", "w", encoding="utf-8") as f:
        json.dump(u01, f, indent=2)

    # 2. Classification: invoice_query -> general
    u02 = {
        "review_id": "rev_case_inv_001",
        "expected_revision": 1,
        "actor_id": "operator_bob",
        "action": "CORRECT",
        "rationale": "Email is a general inquiry about terminal operating hours, not an invoice dispute",
        "category": "general",
        "classification_evidence_ids": ["ev_added_em_gen_001"],
        "role_corrections": [],
        "corrections": [],
        "added_evidence": [
            {
                "evidence_id": "ev_added_em_gen_001",
                "source_type": "email",
                "source_id": "em_case_gen_001",
                "kind": "text_span",
                "quote": "What are your terminal opening hours this Sunday?",
                "location": None,
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_cls_invoice_to_general.json", "w", encoding="utf-8") as f:
        json.dump(u02, f, indent=2)

    # 3. Classification: general -> new_shipping_instruction
    u03 = {
        "review_id": "rev_case_gen_002",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Customer is submitting new shipping instructions for an upcoming booking",
        "category": "new_shipping_instruction",
        "classification_evidence_ids": ["ev_added_em_new_si_001"],
        "role_corrections": [],
        "corrections": [],
        "added_evidence": [
            {
                "evidence_id": "ev_added_em_new_si_001",
                "source_type": "email",
                "source_id": "em_case_new_si_001",
                "kind": "text_span",
                "quote": "Please find our shipping instruction for booking BKG-99201",
                "location": None,
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_cls_general_to_new_si.json", "w", encoding="utf-8") as f:
        json.dump(u03, f, indent=2)

    # 4. Role: Swap SI and BL
    u04 = {
        "review_id": "rev_case_swap_001",
        "expected_revision": 1,
        "actor_id": "operator_carol",
        "action": "CORRECT",
        "rationale": "Initial heuristic mistakenly inverted SI and Draft BL attachments",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [
            {
                "document_id": "doc_file_001",
                "assigned_role": "BL",
                "evidence_ids": ["ev_swap_doc1_header"],
                "rationale": "doc_file_001 header contains BILL OF LADING title"
            },
            {
                "document_id": "doc_file_002",
                "assigned_role": "SI",
                "evidence_ids": ["ev_swap_doc2_header"],
                "rationale": "doc_file_002 header contains SHIPPING INSTRUCTION title"
            }
        ],
        "corrections": [],
        "added_evidence": [
            {
                "evidence_id": "ev_swap_doc1_header",
                "source_type": "document",
                "source_id": "doc_file_001",
                "kind": "text_span",
                "quote": "NON-NEGOTIABLE DRAFT BILL OF LADING",
                "location": {"page": 1, "section": "Title"},
                "detail": None
            },
            {
                "evidence_id": "ev_swap_doc2_header",
                "source_type": "document",
                "source_id": "doc_file_002",
                "kind": "text_span",
                "quote": "SHIPPING INSTRUCTION FORM",
                "location": {"page": 1, "section": "Title"},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_role_swap_si_bl.json", "w", encoding="utf-8") as f:
        json.dump(u04, f, indent=2)

    # 5. Role: Select SI candidate among ambiguous files
    u05 = {
        "review_id": "rev_case_003",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Selected doc_cand_a as authoritative SI",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [
            {
                "document_id": "doc_cand_a",
                "assigned_role": "SI",
                "evidence_ids": ["ev_cand_a_id"],
                "rationale": "Document title explicitly identifies Shipping Instruction"
            }
        ],
        "corrections": [],
        "added_evidence": []
    }
    with open(UPDATES_DIR / "update_role_select_si_candidate.json", "w", encoding="utf-8") as f:
        json.dump(u05, f, indent=2)

    # 6. Role: Select Draft BL candidate among multiple versions
    u06 = {
        "review_id": "rev_case_003",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Selected bl_rev2.pdf (doc_cand_c) as authoritative final Draft BL",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [
            {
                "document_id": "doc_cand_c",
                "assigned_role": "BL",
                "evidence_ids": ["ev_cand_c_id"],
                "rationale": "doc_cand_c contains final timestamped Draft BL revision 2"
            },
            {
                "document_id": "doc_cand_b",
                "assigned_role": "UNKNOWN",
                "evidence_ids": ["ev_cand_b_id"],
                "rationale": "Superceded draft version marked UNKNOWN"
            }
        ],
        "corrections": [],
        "added_evidence": []
    }
    with open(UPDATES_DIR / "update_role_select_bl_candidate.json", "w", encoding="utf-8") as f:
        json.dump(u06, f, indent=2)

    # 7. Role: One role assigned, other document remains missing
    u07 = {
        "review_id": "rev_case_001",
        "expected_revision": 1,
        "actor_id": "operator_carol",
        "action": "CORRECT",
        "rationale": "Confirmed attachment is SI, but Draft BL remains unreceived",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [
            {
                "document_id": "doc_si_001",
                "assigned_role": "SI",
                "evidence_ids": ["ev_doc_si_001_header"],
                "rationale": "Validated SI document role"
            }
        ],
        "corrections": [],
        "added_evidence": []
    }
    with open(UPDATES_DIR / "update_role_one_remains_missing.json", "w", encoding="utf-8") as f:
        json.dump(u07, f, indent=2)

    # 8. Field: container_count correction
    u08 = {
        "review_id": "rev_case_009",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Operator verifies BL container schedule on page 2 lists 4 containers",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [
            {
                "document_id": "doc_bl_009",
                "field": "container_count",
                "raw_value": "4",
                "evidence_ids": ["ev_added_bl_count_009"],
                "rationale": "Page 2 container summary table lists 4x40ft containers"
            }
        ],
        "added_evidence": [
            {
                "evidence_id": "ev_added_bl_count_009",
                "source_type": "document",
                "source_id": "doc_bl_009",
                "kind": "table_cell",
                "quote": "TOTAL UNITS: 4",
                "location": {"page": 2, "table": "ContainerDetails", "row": 5, "column": 2},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_field_container_count.json", "w", encoding="utf-8") as f:
        json.dump(u08, f, indent=2)

    # 9. Field: gross_weight_kg correction (e.g. "22 MT" -> normalizes to 22000)
    u09 = {
        "review_id": "rev_case_008",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Found gross weight in BL table cell 3, column 4",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [
            {
                "document_id": "doc_bl_008",
                "field": "gross_weight_kg",
                "raw_value": "22 MT",
                "evidence_ids": ["ev_added_bl_wt_008"],
                "rationale": "Extracted from weight column in metric tons"
            }
        ],
        "added_evidence": [
            {
                "evidence_id": "ev_added_bl_wt_008",
                "source_type": "document",
                "source_id": "doc_bl_008",
                "kind": "table_cell",
                "quote": "22.000 MT",
                "location": {"page": 1, "table": "CargoManifest", "row": 2, "column": 3},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_field_gross_weight_kg.json", "w", encoding="utf-8") as f:
        json.dump(u09, f, indent=2)

    # 10. Field: Organization text correction (shipper)
    u10 = {
        "review_id": "rev_case_004",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Corrected shipper legal name from full letterhead",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [
            {
                "document_id": "doc_si_004",
                "field": "shipper",
                "raw_value": "ACME GLOBAL SHIPPING CORP, 100 OCEAN WAY, SHANGHAI",
                "evidence_ids": ["ev_added_shipper_full"],
                "rationale": "Letterhead top left includes GLOBAL in corporate entity"
            }
        ],
        "added_evidence": [
            {
                "evidence_id": "ev_added_shipper_full",
                "source_type": "document",
                "source_id": "doc_si_004",
                "kind": "text_span",
                "quote": "SHIPPER: ACME GLOBAL SHIPPING CORP, 100 OCEAN WAY, SHANGHAI",
                "location": {"page": 1, "section": "Letterhead"},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_field_org_shipper.json", "w", encoding="utf-8") as f:
        json.dump(u10, f, indent=2)

    # 11. Field: Port field correction (port_of_discharge)
    u11 = {
        "review_id": "rev_case_004",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Supplied missing port_of_discharge found in SI page 2 routing schedule",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [
            {
                "document_id": "doc_si_004",
                "field": "port_of_discharge",
                "raw_value": "ROTTERDAM, NETHERLANDS",
                "evidence_ids": ["ev_added_pod_004"],
                "rationale": "Located POD in Section 4 Routing Schedule"
            }
        ],
        "added_evidence": [
            {
                "evidence_id": "ev_added_pod_004",
                "source_type": "document",
                "source_id": "doc_si_004",
                "kind": "text_span",
                "quote": "DISCHARGE PORT: ROTTERDAM, NETHERLANDS",
                "location": {"page": 2, "section": "Routing Schedule"},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_field_port_discharge.json", "w", encoding="utf-8") as f:
        json.dump(u11, f, indent=2)

    # 12. Field: Previously missing value (notify_party)
    u12 = {
        "review_id": "rev_case_004",
        "expected_revision": 1,
        "actor_id": "operator_bob",
        "action": "CORRECT",
        "rationale": "Supplied notify_party from page 1 special instructions box",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [
            {
                "document_id": "doc_si_004",
                "field": "notify_party",
                "raw_value": "APEX LOGISTICS SERVICES LTD, 12 TERMINAL ROAD, ROTTERDAM",
                "evidence_ids": ["ev_added_notify_004"],
                "rationale": "Special instructions section identifies notify party"
            }
        ],
        "added_evidence": [
            {
                "evidence_id": "ev_added_notify_004",
                "source_type": "document",
                "source_id": "doc_si_004",
                "kind": "text_span",
                "quote": "NOTIFY: APEX LOGISTICS SERVICES LTD, 12 TERMINAL ROAD, ROTTERDAM",
                "location": {"page": 1, "section": "Special Instructions"},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_field_previously_missing.json", "w", encoding="utf-8") as f:
        json.dump(u12, f, indent=2)

    # 13. Field: Resolve conflicting candidate field
    u13 = {
        "review_id": "rev_case_006",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Adjudicated conflicting gross weight candidates: header summary 22000 KG is authoritative over sub-total breakdown",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [
            {
                "document_id": "doc_si_006",
                "field": "gross_weight_kg",
                "raw_value": "22000 KG",
                "evidence_ids": ["ev_si_weight_cand1"],
                "rationale": "Header summary represents verified billable gross weight"
            }
        ],
        "added_evidence": []
    }
    with open(UPDATES_DIR / "update_field_resolve_conflict.json", "w", encoding="utf-8") as f:
        json.dump(u13, f, indent=2)

    # 14. Action: CONFIRM valid as-is
    u14 = {
        "review_id": "rev_case_005",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CONFIRM",
        "rationale": "Confirmed email is general inquiry based on lack of booking number or cargo manifests",
        "category": "general",
        "classification_evidence_ids": ["ev_em_005_body"],
        "role_corrections": [],
        "corrections": [],
        "added_evidence": []
    }
    with open(UPDATES_DIR / "update_confirm_valid_as_is.json", "w", encoding="utf-8") as f:
        json.dump(u14, f, indent=2)

    # 15. Evidence update: text_span
    u15 = {
        "review_id": "rev_case_004",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Added grounded text span citation for consignee address clarification",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [],
        "added_evidence": [
            {
                "evidence_id": "ev_span_consignee_clarified",
                "source_type": "document",
                "source_id": "doc_si_004",
                "kind": "text_span",
                "quote": "CONSIGNEE: GLOBAL LOGISTICS B.V. (TAX ID: NL123456789B01), 45 HAVENLAAN, ROTTERDAM",
                "location": {"page": 1, "section": "Consignee Box"},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_evidence_text_span.json", "w", encoding="utf-8") as f:
        json.dump(u15, f, indent=2)

    # 16. Evidence update: table_cell
    u16 = {
        "review_id": "rev_case_006",
        "expected_revision": 1,
        "actor_id": "operator_bob",
        "action": "CORRECT",
        "rationale": "Added grounded table cell citation for cargo container count",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [],
        "added_evidence": [
            {
                "evidence_id": "ev_cell_container_verified",
                "source_type": "document",
                "source_id": "doc_si_006",
                "kind": "table_cell",
                "quote": "2 x 40HC",
                "location": {"page": 2, "table": "EquipmentSummary", "row": 1, "column": 2},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_evidence_table_cell.json", "w", encoding="utf-8") as f:
        json.dump(u16, f, indent=2)

    # 17. Evidence update: page_location (valid bbox)
    u17 = {
        "review_id": "rev_case_008",
        "expected_revision": 1,
        "actor_id": "operator_carol",
        "action": "CORRECT",
        "rationale": "Added OCR bounding box region coordinates for blurry draft seal",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [],
        "added_evidence": [
            {
                "evidence_id": "ev_region_bl_seal",
                "source_type": "document",
                "source_id": "doc_bl_008",
                "kind": "page_region",
                "quote": None,
                "location": {"page": 1, "section": "CarrierStamp", "bbox": [0.12, 0.35, 0.48, 0.42]},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_evidence_page_location.json", "w", encoding="utf-8") as f:
        json.dump(u17, f, indent=2)

    # 18. Evidence addition for previously missing field
    u18 = {
        "review_id": "rev_case_004",
        "expected_revision": 1,
        "actor_id": "operator_alice",
        "action": "CORRECT",
        "rationale": "Attached newly identified document snippet for missing port_of_discharge",
        "category": None,
        "classification_evidence_ids": [],
        "role_corrections": [],
        "corrections": [],
        "added_evidence": [
            {
                "evidence_id": "ev_snippet_pod_clause",
                "source_type": "document",
                "source_id": "doc_si_004",
                "kind": "text_span",
                "quote": "FINAL DESTINATION: ROTTERDAM PORT TERMINAL 3",
                "location": {"page": 2, "section": "Delivery Clause"},
                "detail": None
            }
        ]
    }
    with open(UPDATES_DIR / "update_evidence_addition_missing_field.json", "w", encoding="utf-8") as f:
        json.dump(u18, f, indent=2)

    update_ids = [
        ("update_cls_unresolved_to_comparison", "classification", "Unresolved intent corrected to document_comparison"),
        ("update_cls_invoice_to_general", "classification", "Incorrect invoice_query corrected to general"),
        ("update_cls_general_to_new_si", "classification", "Incorrect general corrected to new_shipping_instruction"),
        ("update_role_swap_si_bl", "role", "Swapped SI and Draft BL role assignments"),
        ("update_role_select_si_candidate", "role", "Selected SI candidate from ambiguous file set"),
        ("update_role_select_bl_candidate", "role", "Selected Draft BL candidate from duplicate revisions"),
        ("update_role_one_remains_missing", "role", "Role correction where one document remains missing"),
        ("update_field_container_count", "field", "Corrected container count to 4"),
        ("update_field_gross_weight_kg", "field", "Corrected gross weight to 22 MT"),
        ("update_field_org_shipper", "field", "Corrected shipper organization legal name"),
        ("update_field_port_discharge", "field", "Supplied missing port_of_discharge"),
        ("update_field_previously_missing", "field", "Supplied previously missing notify_party"),
        ("update_field_resolve_conflict", "field", "Adjudicated conflicting gross weight candidates"),
        ("update_confirm_valid_as_is", "confirm", "Valid confirmation of general intent"),
        ("update_evidence_text_span", "evidence", "Added grounded text span quote evidence"),
        ("update_evidence_table_cell", "evidence", "Added grounded table cell coordinates evidence"),
        ("update_evidence_page_location", "evidence", "Added grounded page bbox coordinates evidence"),
        ("update_evidence_addition_missing_field", "evidence", "Added evidence snippet for missing POD"),
    ]
    for uid, kind, desc in update_ids:
        fixtures_meta[uid] = {
            "file": f"updates/{uid}.json",
            "fixture_type": "review_update",
            "scenario": uid,
            "valid_payload": True,
            "starting_revision": 1,
            "expected_revision": 2,
            "expected_validation_result": "VALID",
            "expected_http_status": 200,
            "tags": ["update", kind],
            "rationale": desc
        }

    # =========================================================================
    # C. OPTIMISTIC CONCURRENCY SCENARIOS (3 files)
    # =========================================================================

    c_scen_1 = {
        "scenario_id": "CONC-001",
        "description": "Matching expected_revision proceeds successfully and increments revision",
        "current_server_revision": 3,
        "review_update_payload": {
            "review_id": "rev_case_conc_001",
            "expected_revision": 3,
            "actor_id": "operator_alice",
            "action": "CORRECT",
            "rationale": "Correcting container count with matching revision",
            "category": None,
            "classification_evidence_ids": [],
            "role_corrections": [],
            "corrections": [
                {
                    "document_id": "doc_bl_001",
                    "field": "container_count",
                    "raw_value": "2",
                    "evidence_ids": ["ev_conc_001"],
                    "rationale": "Matched container count"
                }
            ],
            "added_evidence": [
                {
                    "evidence_id": "ev_conc_001",
                    "source_type": "document",
                    "source_id": "doc_bl_001",
                    "kind": "text_span",
                    "quote": "CONTAINERS: 2",
                    "location": {"page": 1},
                    "detail": None
                }
            ]
        },
        "expected_result": "SUCCESS",
        "expected_http_status": 200,
        "expected_resulting_revision": 4
    }
    with open(CONC_DIR / "conc_01_valid_revision_match.json", "w", encoding="utf-8") as f:
        json.dump(c_scen_1, f, indent=2)

    c_scen_2 = {
        "scenario_id": "CONC-002",
        "description": "Stale expected_revision causes HTTP 409 revision conflict rejection",
        "current_server_revision": 4,
        "review_update_payload": {
            "review_id": "rev_case_conc_002",
            "expected_revision": 3,
            "actor_id": "operator_bob",
            "action": "CORRECT",
            "rationale": "Attempting update based on stale revision 3",
            "category": None,
            "classification_evidence_ids": [],
            "role_corrections": [],
            "corrections": [
                {
                    "document_id": "doc_bl_002",
                    "field": "gross_weight_kg",
                    "raw_value": "22000 KG",
                    "evidence_ids": ["ev_conc_002"],
                    "rationale": "Stale weight update"
                }
            ],
            "added_evidence": [
                {
                    "evidence_id": "ev_conc_002",
                    "source_type": "document",
                    "source_id": "doc_bl_002",
                    "kind": "text_span",
                    "quote": "WEIGHT: 22000 KG",
                    "location": {"page": 1},
                    "detail": None
                }
            ]
        },
        "expected_result": "REVISION_CONFLICT",
        "expected_http_status": 409,
        "expected_resulting_revision": 4
    }
    with open(CONC_DIR / "conc_02_stale_revision_conflict.json", "w", encoding="utf-8") as f:
        json.dump(c_scen_2, f, indent=2)

    c_scen_3 = {
        "scenario_id": "CONC-003",
        "description": "Two reviewers concurrently load revision 5; first succeeds, second receives HTTP 409",
        "initial_server_revision": 5,
        "step_1_reviewer_a": {
            "actor_id": "operator_alice",
            "expected_revision": 5,
            "expected_result": "SUCCESS",
            "expected_http_status": 200,
            "resulting_revision": 6
        },
        "step_2_reviewer_b": {
            "actor_id": "operator_bob",
            "expected_revision": 5,
            "expected_result": "REVISION_CONFLICT",
            "expected_http_status": 409,
            "resulting_revision": 6
        }
    }
    with open(CONC_DIR / "conc_03_race_two_reviewers.json", "w", encoding="utf-8") as f:
        json.dump(c_scen_3, f, indent=2)

    conc_ids = [
        ("conc_01_valid_revision_match", "Matching revision proceeds to rev 4"),
        ("conc_02_stale_revision_conflict", "Stale revision rejected with HTTP 409"),
        ("conc_03_race_two_reviewers", "Concurrent submissions: first advances revision, second receives 409"),
    ]
    for cid, desc in conc_ids:
        fixtures_meta[cid] = {
            "file": f"concurrency/{cid}.json",
            "fixture_type": "concurrency_scenario",
            "scenario": cid,
            "valid_payload": True,
            "expected_validation_result": "VALID",
            "tags": ["concurrency", "optimistic_locking"],
            "rationale": desc
        }

    # =========================================================================
    # D. INVALID PAYLOAD FIXTURES (17 files)
    # =========================================================================

    inv_fixtures = [
        (
            "inv_missing_expected_revision",
            "Missing mandatory expected_revision field",
            {
                "review_id": "rev_case_inv_001",
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Missing expected revision key",
                "category": None,
                "corrections": []
            }
        ),
        (
            "inv_negative_revision",
            "expected_revision is negative integer (-1) violating ge=1",
            {
                "review_id": "rev_case_inv_002",
                "expected_revision": -1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Negative revision",
                "category": None,
                "corrections": []
            }
        ),
        (
            "inv_unsupported_action_override",
            "Action enum OVERRIDE is unapproved (only CONFIRM, CORRECT)",
            {
                "review_id": "rev_case_inv_003",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "OVERRIDE",
                "rationale": "Attempting unapproved OVERRIDE action",
                "category": None,
                "corrections": []
            }
        ),
        (
            "inv_unsupported_action_approve",
            "Action enum APPROVE is unapproved",
            {
                "review_id": "rev_case_inv_004",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "APPROVE",
                "rationale": "Attempting unapproved APPROVE action",
                "category": None,
                "corrections": []
            }
        ),
        (
            "inv_unsupported_action_force_match",
            "Action enum FORCE_MATCH is unapproved",
            {
                "review_id": "rev_case_inv_005",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "FORCE_MATCH",
                "rationale": "Attempting unapproved FORCE_MATCH action",
                "category": None,
                "corrections": []
            }
        ),
        (
            "inv_unknown_field_name",
            "Field name vessel_name is not one of the 7 mandatory comparison fields",
            {
                "review_id": "rev_case_inv_006",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Attempting to correct non-existent field",
                "corrections": [
                    {
                        "document_id": "doc_si_001",
                        "field": "vessel_name",
                        "raw_value": "EVER GIVEN",
                        "evidence_ids": ["ev_001"],
                        "rationale": "Unapproved field name"
                    }
                ]
            }
        ),
        (
            "inv_invalid_container_count_type",
            "container_count value is non-numeric text that cannot be normalized to integer",
            {
                "review_id": "rev_case_inv_007",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Invalid container count string",
                "corrections": [
                    {
                        "document_id": "doc_si_001",
                        "field": "container_count",
                        "raw_value": "four containers approx",
                        "evidence_ids": ["ev_001"],
                        "rationale": "Prose string cannot convert to strict integer"
                    }
                ]
            }
        ),
        (
            "inv_invalid_gross_weight_type",
            "gross_weight_kg value is non-numeric prose that cannot be normalized to Decimal",
            {
                "review_id": "rev_case_inv_008",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Invalid weight prose",
                "corrections": [
                    {
                        "document_id": "doc_si_001",
                        "field": "gross_weight_kg",
                        "raw_value": "approx two truckloads",
                        "evidence_ids": ["ev_001"],
                        "rationale": "Prose string cannot convert to plain decimal"
                    }
                ]
            }
        ),
        (
            "inv_direct_mismatch_detected_mutation",
            "Reviewer payload attempts to directly set mismatch_detected = false (REG-012 forbidden)",
            {
                "review_id": "rev_case_inv_009",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Direct mismatch override attempt",
                "mismatch_detected": False,
                "corrections": []
            }
        ),
        (
            "inv_direct_outcome_mutation",
            "Reviewer payload attempts to directly set outcome = MATCH (DC-07 forbidden)",
            {
                "review_id": "rev_case_inv_010",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Direct outcome override attempt",
                "outcome": "MATCH",
                "corrections": []
            }
        ),
        (
            "inv_direct_comparison_result_mutation",
            "Reviewer payload attempts to directly set field outcome comparison_result = MATCH",
            {
                "review_id": "rev_case_inv_011",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Direct comparison_result override attempt",
                "comparison_result": "MATCH",
                "corrections": []
            }
        ),
        (
            "inv_evaluation_enum_category",
            "Evaluation enum BL_COMPARISON leaked into internal ReviewUpdate category",
            {
                "review_id": "rev_case_inv_012",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Leaked evaluation enum",
                "category": "BL_COMPARISON",
                "corrections": []
            }
        ),
        (
            "inv_same_document_both_roles",
            "RoleCorrection assigns same document doc_001 to both SI and BL",
            {
                "review_id": "rev_case_inv_013",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Attempting to assign same document to both roles",
                "role_corrections": [
                    {
                        "document_id": "doc_001",
                        "assigned_role": "SI",
                        "evidence_ids": ["ev_001"],
                        "rationale": "Assign SI"
                    },
                    {
                        "document_id": "doc_001",
                        "assigned_role": "BL",
                        "evidence_ids": ["ev_001"],
                        "rationale": "Assign BL"
                    }
                ]
            }
        ),
        (
            "inv_fabricated_evidence_bbox",
            "EvidenceLocation bbox has x0 >= x1 ([0.8, 0.2, 0.3, 0.5]) violating non-empty region invariant",
            {
                "review_id": "rev_case_inv_014",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Invalid bbox coordinates",
                "added_evidence": [
                    {
                        "evidence_id": "ev_bad_bbox",
                        "source_type": "document",
                        "source_id": "doc_001",
                        "kind": "page_region",
                        "quote": None,
                        "location": {"page": 1, "bbox": [0.8, 0.2, 0.3, 0.5]},
                        "detail": None
                    }
                ]
            }
        ),
        (
            "inv_table_cell_missing_coords",
            "kind=table_cell evidence missing required location.row and location.column",
            {
                "review_id": "rev_case_inv_015",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Missing table cell coordinates",
                "added_evidence": [
                    {
                        "evidence_id": "ev_bad_cell",
                        "source_type": "document",
                        "source_id": "doc_001",
                        "kind": "table_cell",
                        "quote": "22 MT",
                        "location": {"page": 1, "table": "CargoManifest"},
                        "detail": None
                    }
                ]
            }
        ),
        (
            "inv_forbidden_extra_property",
            "Payload contains unexpected extra property violating extra='forbid'",
            {
                "review_id": "rev_case_inv_016",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CORRECT",
                "rationale": "Extra forbidden property",
                "unapproved_bypass_flag": True,
                "corrections": []
            }
        ),
        (
            "inv_confirm_forcing_unextracted_field",
            "CONFIRM action attempting to force resolution with force_complete flag",
            {
                "review_id": "rev_case_inv_017",
                "expected_revision": 1,
                "actor_id": "operator_alice",
                "action": "CONFIRM",
                "rationale": "Attempting to force complete unextracted fields without candidates",
                "force_complete": True,
                "corrections": []
            }
        ),
    ]

    for fid, desc, payload in inv_fixtures:
        with open(INVALID_DIR / f"{fid}.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        fixtures_meta[fid] = {
            "file": f"invalid/{fid}.json",
            "fixture_type": "invalid_review_payload",
            "scenario": fid,
            "valid_payload": False,
            "expected_validation_result": "REJECTED",
            "expected_http_status": 422,
            "tags": ["invalid", "schema_violation"],
            "rationale": desc
        }

    # =========================================================================
    # RECOMPUTATION & TRISTATE SCENARIOS (Metadata Catalogs)
    # =========================================================================

    recomputations = {
        "RECOMP-001": {
            "name": "Container Count Mismatch Deterministic Resolution",
            "base_case": "case_09_tristate_known_mismatch_plus_unresolved",
            "update_applied": "update_field_container_count",
            "field": "container_count",
            "before_review": {"si_value": 2, "bl_value": 3, "outcome": "MISMATCH"},
            "correction": {"document_id": "doc_bl_009", "raw_value": "4"},
            "after_recompute": {
                "normalized_si": 2,
                "normalized_bl": 4,
                "outcome": "MISMATCH",
                "is_discrepancy": True
            },
            "rule": "Exact integer equality: 2 != 4 -> MISMATCH"
        },
        "RECOMP-002": {
            "name": "Gross Weight Unit Normalization Deterministic Resolution",
            "base_case": "case_08_partial_preservation_6_of_7",
            "update_applied": "update_field_gross_weight_kg",
            "field": "gross_weight_kg",
            "before_review": {"si_value": "22000", "bl_value": None, "reliability": "MISSING"},
            "correction": {"document_id": "doc_bl_008", "raw_value": "22 MT"},
            "after_recompute": {
                "normalized_si": "22000",
                "normalized_bl": "22000",
                "outcome": "MATCH",
                "is_discrepancy": False
            },
            "rule": "Unit conversion: 22 MT -> 22000 KG; exact equality: Decimal('22000') == Decimal('22000') -> MATCH"
        },
        "RECOMP-003": {
            "name": "Port of Discharge Missing Value Resolution",
            "base_case": "case_04_missing_required_value",
            "update_applied": "update_field_port_discharge",
            "field": "port_of_discharge",
            "before_review": {"si_value": None, "bl_value": "ROTTERDAM, NETHERLANDS", "reliability": "MISSING"},
            "correction": {"document_id": "doc_si_004", "raw_value": "ROTTERDAM, NETHERLANDS"},
            "after_recompute": {
                "normalized_si": "ROTTERDAM, NETHERLANDS",
                "normalized_bl": "ROTTERDAM, NETHERLANDS",
                "outcome": "MATCH",
                "is_discrepancy": False
            },
            "rule": "Exact text equality after approved normalization: MATCH"
        }
    }

    tristate_scenarios = {
        "TRISTATE-001": {
            "name": "Null Mismatch Detected Maintained While Work Unresolved",
            "case_id": "case_09_tristate_known_mismatch_plus_unresolved",
            "invariant": "mismatch_detected must remain null while any mandatory field is unresolved",
            "known_discrepancy": {"field": "container_count", "si": 2, "bl": 3},
            "unresolved_field": "gross_weight_kg",
            "audit_state": "NEEDS_REVIEW",
            "outcome": None,
            "mismatch_detected": None,
            "prohibited_values": [
                {"field": "mismatch_detected", "prohibited": False, "reason": "Cannot be false because a confirmed mismatch exists"},
                {"field": "mismatch_detected", "prohibited": True, "reason": "Cannot be true because workflow is incomplete and unresolved fields remain"},
                {"field": "result_summary", "prohibited": "No mismatch detected", "reason": "Unresolved case cannot receive a clean pass"}
            ]
        }
    }

    # =========================================================================
    # BUILD MANIFEST.JSON
    # =========================================================================

    manifest = {
        "manifest_version": "1.0",
        "counts": {
            "total_review_case_fixtures": len(case_ids),
            "total_update_fixtures": len(update_ids),
            "total_concurrency_fixtures": len(conc_ids),
            "total_invalid_fixtures": len(inv_fixtures),
            "total_fixture_payloads": len(case_ids) + len(update_ids) + len(conc_ids) + len(inv_fixtures),
            "metadata_files_count": 2,
            "generator_validator_files_count": 2,
            "total_filesystem_files": len(case_ids) + len(update_ids) + len(conc_ids) + len(inv_fixtures) + 4
        },
        "approved_internal_categories": APPROVED_CATEGORIES,
        "approved_logical_reasons": APPROVED_LOGICAL_REASONS,
        "approved_review_actions": APPROVED_ACTIONS,
        "approved_field_names": FIELD_NAMES,
        "breakdown_by_category": {
            "cases": len(case_ids),
            "updates": len(update_ids),
            "concurrency": len(conc_ids),
            "invalid": len(inv_fixtures)
        },
        "fixtures": fixtures_meta,
        "recomputation_scenarios": recomputations,
        "tristate_scenarios": tristate_scenarios
    }

    with open(BASE_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {manifest['counts']['total_fixture_payloads']} fixture payloads in {BASE_DIR}")
    print(f"Manifest written to {BASE_DIR / 'manifest.json'}")

if __name__ == "__main__":
    build_all_fixtures()
