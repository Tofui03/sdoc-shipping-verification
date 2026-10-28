# Synthetic Email Fixtures (`tests/fixtures/emails/`)

This directory contains synthetic email fixtures for Stage 1 intent classification, attachment metadata, and early human-review routing.

---

## 1. Schema & Structure

Each `.json` file contains one email payload in the `EmailRecord` shape:

```json
{
  "email_id": "syn_email_001_doc_compare_clear",
  "sender": "ops@synthetic-maritime.com",
  "subject": "Comparison Request: SI vs Draft BL for Booking BM-9921",
  "body": "Dear Documentation Team...",
  "attachments": [
    {
      "document_id": "doc_syn_001_si",
      "path": "attachments/syn_email_001_SI.txt",
      "mime_type": "text/plain"
    }
  ]
}
```

### Separation of Input Data vs Test Expectations:
- Individual email fixture files contain **only** the application input payload (`EmailRecord`).
- Test assertions, expected canonical category, HITL escalation expectations, and rationale are decoupled into [`manifest.json`](manifest.json).

---

## 2. Inventory & Canonical Category Coverage

| Fixture File | Category | Attachments | Primary Test Focus |
|---|---|---|---|
| `syn_email_001_doc_compare_clear.json` | `document_comparison` | 2 (SI, BL) | Standard unambiguous SI vs Draft BL comparison request (`PIPE-CLS-001`). |
| `syn_email_002_doc_compare_zero_att.json` | `document_comparison` | 0 | **Critical Regression Invariant** (`EC-002` / `REG-001`): Intent is comparison; Stage 1 must classify as `document_comparison`. Stage 2 escalates to `missing_attachment`. |
| `syn_email_003_doc_compare_vague_subject.json` | `document_comparison` | 2 (SI, BL) | Vague subject (`FW: Urgent Review Needed`), clear body intent (`PIPE-CLS-001`). |
| `syn_email_004_doc_compare_generic_filenames.json`| `document_comparison` | 2 (`Doc_A`, `Doc_B`)| Generic attachment filenames; body defines document roles (`PIPE-CLS-002`). |
| `syn_email_005_doc_compare_misleading_filenames.json`| `document_comparison`| 2 (`Invoice_Summary`, `PackingList_Draft`)| Misleading filenames explicitly overridden by body text (`PIPE-CLS-002`). |
| `syn_email_006_doc_compare_excel_si.json` | `document_comparison` | 2 (Excel SI, PDF BL) | Multi-format comparison request (`PIPE-CLS-001`). |
| `syn_email_007_new_si_clear.json` | `new_shipping_instruction` | 1 (SI docx) | Clear submission of new Shipping Instruction (`PIPE-CLS-003`, `FR-004`). |
| `syn_email_008_new_si_vague_subject.json` | `new_shipping_instruction` | 1 (SI txt) | Vague subject, clear body submitting new instruction (`PIPE-CLS-003`). |
| `syn_email_009_new_si_multiple_att.json` | `new_shipping_instruction` | 3 (SI, Inv, PL) | Multiple attachments present; must not force comparison (`PIPE-CLS-003`). |
| `syn_email_010_invoice_query_clear.json` | `invoice_query` | 0 | Explicit freight invoice and demurrage dispute (`PIPE-CLS-005`, `FR-004`). |
| `syn_email_011_invoice_query_with_att.json` | `invoice_query` | 1 (Invoice PDF) | Invoice question with attached invoice PDF (`PIPE-CLS-005`). |
| `syn_email_012_general_update.json` | `general` | 0 | Operational vessel delay notice (`PIPE-CLS-005`, `FR-004`). |
| `syn_email_013_general_mentions_docs.json` | `general` | 0 | Broadcast mentioning SI and BL cutoff without verification request (`PIPE-CLS-005`). |
| `syn_email_014_spam_promotional.json` | `spam` | 0 | Unsolicited office furniture promotion (`PIPE-CLS-005`, `FR-004`). |
| `syn_email_015_spam_phishing.json` | `spam` | 0 | Phishing alert pretending to be mailbox quota notice (`PIPE-CLS-005`). |
| `syn_email_016_unresolved_conflicting_intent.json` | `null` | 2 (PDFs) | Conflicting intent across new SI, comparison, and invoice cancellation (`DC-01`, `PIPE-CLS-006`). |
| `syn_email_017_unresolved_vague_minimal.json` | `null` | 1 (PDF) | Minimal text ("Please check attached and confirm"); inconclusive context (`DC-01`, `PIPE-CLS-006`). |
| `syn_email_018_unresolved_empty_body.json` | `null` | 1 (PDF) | Empty body text with scanned attachment; requires human review (`DC-01`, `PIPE-CLS-006`). |

---

## 3. Data Integrity & Privacy Protection

- All sender addresses use the reserved `.test` pseudo-TLD (RFC 2606 / RFC 6761).
- Entity names in these fixtures are fictional.

---

## 4. Contract Alignment & Intent Principles

- **Schema Alignment**: All fixtures structurally align with the documented target `EmailRecord` contract. Full Pydantic contract validation will occur after the canonical models are implemented in Wave 1.
- **Attachment Intent Boundary**: Attachment count does not determine or veto email intent. Attachment metadata may be used as supporting email-level context. Under `EC-002` / `REG-001`, an email expressing intent to compare an SI against a draft BL is classified as `document_comparison` even with 0 attachments.
- **Diagnostic Confidence**: Model self-confidence is diagnostic only and is excluded from fixture acceptance criteria and pipeline gatekeeping.
