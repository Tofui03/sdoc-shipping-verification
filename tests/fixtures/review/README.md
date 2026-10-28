# Synthetic Human Review, Correction & Concurrency Fixtures (`tests/fixtures/review/`)

This directory contains deterministic offline fixtures supporting tests for:
- Human-in-the-Loop (HITL) review case generation across all 7 baselined `LogicalReason` values
- Classification intent correction (`category = null` $\rightarrow$ canonical internal category)
- Document role binding correction (SI vs Draft BL assignment and disambiguation)
- Field-level candidate corrections across the 7 mandatory comparison fields
- Valid and invalid confirmation actions (`CONFIRM` vs `CORRECT`)
- Structured source evidence citation and addition (`FieldEvidence`)
- Partial-work preservation (retaining 6 reliable fields during single-field review)
- Deterministic recomputation scenarios (before/after review outcomes)
- Tri-state outcome resolution (`mismatch_detected = null` while work remains unresolved)
- Optimistic concurrency control (`expected_revision` and HTTP 409 conflict scenarios)
- Intentionally invalid payloads enforcing schema and security boundaries

These payloads follow the review models in `src/models` (`AuditRecord`, `ReviewUpdate`, evidence, and revision locking).

---

## 1. Directory Structure & Count Taxonomy

```text
tests/fixtures/review/
├── manifest.json                     # Complete metadata catalogue and mapping
├── README.md                         # Documentation & governance guidelines
├── cases/                            # 10 synthetic audit record before-review states
│   ├── case_01_missing_attachment.json
│   ├── case_02_unreadable_document.json
│   ├── case_03_wrong_or_uncertain_document_type.json
│   ├── case_04_missing_required_value.json
│   ├── case_05_uncertain_result.json
│   ├── case_06_conflicting_candidate_values.json
│   ├── case_07_processing_or_provider_failure.json
│   ├── case_08_partial_preservation_6_of_7.json
│   ├── case_09_tristate_known_mismatch_plus_unresolved.json
│   └── case_10_unresolved_classification.json
├── updates/                          # 18 valid ReviewUpdate request payloads
│   ├── update_cls_unresolved_to_comparison.json
│   ├── update_cls_invoice_to_general.json
│   ├── update_cls_general_to_new_si.json
│   ├── update_role_swap_si_bl.json
│   ├── update_role_select_si_candidate.json
│   ├── update_role_select_bl_candidate.json
│   ├── update_role_one_remains_missing.json
│   ├── update_field_container_count.json
│   ├── update_field_gross_weight_kg.json
│   ├── update_field_org_shipper.json
│   ├── update_field_port_discharge.json
│   ├── update_field_previously_missing.json
│   ├── update_field_resolve_conflict.json
│   ├── update_confirm_valid_as_is.json
│   ├── update_evidence_text_span.json
│   ├── update_evidence_table_cell.json
│   ├── update_evidence_page_location.json
│   └── update_evidence_addition_missing_field.json
├── concurrency/                      # 3 optimistic revision locking scenarios
│   ├── conc_01_valid_revision_match.json
│   ├── conc_02_stale_revision_conflict.json
│   └── conc_03_race_two_reviewers.json
└── invalid/                          # 17 intentionally invalid payloads
    ├── inv_missing_expected_revision.json
    ├── inv_negative_revision.json
    ├── inv_unsupported_action_override.json
    ├── inv_unsupported_action_approve.json
    ├── inv_unsupported_action_force_match.json
    ├── inv_unknown_field_name.json
    ├── inv_invalid_container_count_type.json
    ├── inv_invalid_gross_weight_type.json
    ├── inv_direct_mismatch_detected_mutation.json
    ├── inv_direct_outcome_mutation.json
    ├── inv_direct_comparison_result_mutation.json
    ├── inv_evaluation_enum_category.json
    ├── inv_same_document_both_roles.json
    ├── inv_fabricated_evidence_bbox.json
    ├── inv_table_cell_missing_coords.json
    ├── inv_forbidden_extra_property.json
    └── inv_confirm_forcing_unextracted_field.json
```

### Fixture Counts Summary (Single Source of Truth: `manifest.json`)
- **Review Case States**: 10
- **Valid Review Updates**: 18
- **Concurrency Scenarios**: 3
- **Invalid Payloads**: 17
- **Total Fixture Payloads**: **48**
- **Metadata Files**: 2 (`manifest.json`, `README.md`)
- **Generator & Validator Scripts**: 2 (`generate_review_fixtures.py`, `validate_review_fixtures.py`)
- **Total Filesystem Files**: **52**

---

## 2. Authoritative Governance Principles

### 2.1 Source-Level Operation vs. Final Outcome Override
- **Operator Role**: Supply source-backed candidate values, assign document roles, resolve email intent, and cite grounded evidence.
- **System Role**: Re-run deterministic normalization, validate schema, evaluate evidence grounding, execute deterministic comparator, and derive outcome.
- **Strict Guardrail**: Human reviewers **CANNOT** directly set `mismatch_detected`, `outcome`, or `comparison_result`. Attempting to submit outcome override booleans triggers HTTP 422 validation rejection (`REG-012`).

### 2.2 Tri-State Outcome Invariant (`mismatch_detected = null`)
- While any mandatory field remains unextracted, unreadable, or ambiguous, the case state is strictly `NEEDS_REVIEW`.
- `outcome` must be `null`.
- `mismatch_detected` must be `null` (never coerced to `false` or `true`).
- `result_summary` must **NEVER** emit `"No mismatch detected"` while review is open.
- Even when a known mismatch is already confirmed on one field, the overall case remains unresolved (`mismatch_detected = null`) until all 7 fields are dependable.

### 2.3 Partial-Work Preservation
- In a case where 6 of the 7 mandatory fields are reliable, an operator correction to the 7th field updates only that field.
- The 6 reliable fields, their grounded evidence, and their comparisons are preserved untouched without re-running parsing or resetting completed work.

### 2.4 Optimistic Concurrency Control (`expected_revision`)
- Every `ReviewUpdate` requires `expected_revision: int >= 1`.
- If `expected_revision == audit.revision`: the update proceeds and increments the revision ($r_{N} \rightarrow r_{N+1}$).
- If `expected_revision < audit.revision`: the update is stale and is rejected with **HTTP 409 Conflict** (`code = "REVISION_CONFLICT"`).

### 2.5 Canonical Internal Enums
- Only the 5 canonical internal categories are valid:
  - `document_comparison`
  - `new_shipping_instruction`
  - `invoice_query`
  - `general`
  - `spam`
- Evaluation uppercase enums (`BL_COMPARISON`, `SI_REQUEST`, etc.) are strictly prohibited inside internal review payloads.

### 2.6 Strict LogicalReason Guardrail
All review escalations map strictly to the 7 baselined `LogicalReason` values:
1. `missing_attachment`
2. `unreadable_document`
3. `wrong_or_uncertain_document_type`
4. `missing_required_value`
5. `uncertain_result`
6. `conflicting_candidate_values`
7. `processing_or_provider_failure`

Unapproved reasons (`low_confidence`, `manual_override`, `user_error`, `parser_failed`, `ai_failed`, `unknown_error`) are strictly prohibited.

### 2.7 Strict Review Action Guardrail
Only two review actions are permitted:
- `CORRECT`: Supplies source-backed candidates, role assignments, category corrections, or evidence.
- `CONFIRM`: Confirms findings as-is where supported (e.g. non-comparison classification). Cannot force unextracted fields into reliability.
- Unapproved actions (`OVERRIDE`, `APPROVE`, `REJECT`, `FORCE_MATCH`, `FORCE_MISMATCH`) are strictly rejected.

---

## 3. Fixture Inventory

### 3.1 Review Cases (`cases/`)
| Fixture ID | LogicalReason | Affected Scope | Preserved Work | Test Focus |
|---|---|---|---|---|
| `case_01_missing_attachment` | `missing_attachment` | Draft BL missing | Email context, SI parsed | Missing attachment escalation |
| `case_02_unreadable_document` | `unreadable_document` | Draft BL corrupt stream | SI parsed, BL diagnostic | Corrupted file stream escalation |
| `case_03_wrong_or_uncertain_document_type` | `wrong_or_uncertain_document_type` | Multiple Draft BL files | SI parsed, candidates list | Duplicate candidate role ambiguity |
| `case_04_missing_required_value` | `missing_required_value` | `port_of_discharge` in SI | 6 matching fields preserved | Missing mandatory comparison field |
| `case_05_uncertain_result` | `uncertain_result` | Classification intent | Email context | Ambiguous email body (`category = null`) |
| `case_06_conflicting_candidate_values` | `conflicting_candidate_values` | `gross_weight_kg` in SI | 6 matching fields preserved | Multiple distinct weight candidates |
| `case_07_processing_or_provider_failure` | `processing_or_provider_failure` | AI extraction provider | Parsed document text | Repeated HTTP 503 provider exhaustion |
| `case_08_partial_preservation_6_of_7` | `missing_required_value` | `gross_weight_kg` in BL | 6 MATCH comparisons | Preserving 6 reliable fields |
| `case_09_tristate_known_mismatch_plus_unresolved` | `missing_required_value` | `gross_weight_kg` in BL | 1 MISMATCH, 5 MATCH | Tri-state: `mismatch_detected = null` |
| `case_10_unresolved_classification` | `uncertain_result` | Classification intent | Email context, attachments unparsed | DC-01: non-comparison unparsed invariant |

### 3.2 Review Updates (`updates/`)
| Fixture ID | Category / Target | Action | Key Mutation | Test Focus |
|---|---|:---:|---|---|
| `update_cls_unresolved_to_comparison` | Classification | `CORRECT` | `category = "document_comparison"` | Resolving null category |
| `update_cls_invoice_to_general` | Classification | `CORRECT` | `category = "general"` | Correcting invoice_query |
| `update_cls_general_to_new_si` | Classification | `CORRECT` | `category = "new_shipping_instruction"` | Correcting general inquiry |
| `update_role_swap_si_bl` | Document Roles | `CORRECT` | Swaps `doc_001` $\leftrightarrow$ `doc_002` | Inverted role reassignment |
| `update_role_select_si_candidate` | Document Roles | `CORRECT` | Binds `doc_cand_a` $\rightarrow$ `SI` | Resolving ambiguous SI |
| `update_role_select_bl_candidate` | Document Roles | `CORRECT` | Binds `doc_cand_c` $\rightarrow$ `BL` | Resolving draft revisions |
| `update_role_one_remains_missing` | Document Roles | `CORRECT` | Binds SI; BL remains unassigned | Single document confirmed |
| `update_field_container_count` | Field: `container_count` | `CORRECT` | `raw_value = "4"` | Integer field correction |
| `update_field_gross_weight_kg` | Field: `gross_weight_kg` | `CORRECT` | `raw_value = "22 MT"` | Weight unit conversion (22000 KG) |
| `update_field_org_shipper` | Field: `shipper` | `CORRECT` | Legal name from letterhead | Organization text correction |
| `update_field_port_discharge` | Field: `port_of_discharge` | `CORRECT` | Port from routing schedule | Missing port correction |
| `update_field_previously_missing` | Field: `notify_party` | `CORRECT` | Party from special instructions | Missing party correction |
| `update_field_resolve_conflict` | Field: `gross_weight_kg` | `CORRECT` | Selected header 22000 KG | Conflict adjudication |
| `update_confirm_valid_as_is` | Action: `CONFIRM` | `CONFIRM` | Confirms general inquiry intent | Valid confirmation |
| `update_evidence_text_span` | Evidence Citation | `CORRECT` | Grounded `text_span` quote | Adding text span evidence |
| `update_evidence_table_cell` | Evidence Citation | `CORRECT` | Grounded `table_cell` coordinates | Adding cell evidence |
| `update_evidence_page_location` | Evidence Citation | `CORRECT` | Grounded `page_region` bbox | Adding page bbox evidence |
| `update_evidence_addition_missing_field` | Evidence Citation | `CORRECT` | Grounded delivery clause snippet | Evidence for missing field |

### 3.3 Optimistic Concurrency Scenarios (`concurrency/`)
| Scenario ID | Current Revision | Submitted Revision | Expected Result | Expected HTTP Status | Test Focus |
|---|:---:|:---:|:---:|:---:|---|
| `CONC-001` | 3 | 3 | `SUCCESS` $\rightarrow$ rev 4 | 200 | Clean revision increment |
| `CONC-002` | 4 | 3 | `REVISION_CONFLICT` | 409 | Stale revision collision |
| `CONC-003` | 5 | 5 (two reviewers) | Rev A: 200 (rev 6)<br>Rev B: 409 (conflict) | 200 / 409 | Race condition handling |

### 3.4 Invalid Payloads (`invalid/`)
| Fixture ID | Violation Description | Expected Result | Expected HTTP Status |
|---|---|:---:|:---:|
| `inv_missing_expected_revision` | Missing mandatory `expected_revision` key | `REJECTED` | 422 |
| `inv_negative_revision` | `expected_revision = -1` (fails `ge=1`) | `REJECTED` | 422 |
| `inv_unsupported_action_override` | Unapproved action `"OVERRIDE"` | `REJECTED` | 422 |
| `inv_unsupported_action_approve` | Unapproved action `"APPROVE"` | `REJECTED` | 422 |
| `inv_unsupported_action_force_match` | Unapproved action `"FORCE_MATCH"` | `REJECTED` | 422 |
| `inv_unknown_field_name` | Unknown field `"vessel_name"` | `REJECTED` | 422 |
| `inv_invalid_container_count_type` | Non-integer prose for container count | `REJECTED` | 422 |
| `inv_invalid_gross_weight_type` | Un-normalizable prose for gross weight | `REJECTED` | 422 |
| `inv_direct_mismatch_detected_mutation` | Direct mutation of `"mismatch_detected": false` | `REJECTED` | 422 |
| `inv_direct_outcome_mutation` | Direct mutation of `"outcome": "MATCH"` | `REJECTED` | 422 |
| `inv_direct_comparison_result_mutation` | Direct mutation of `"comparison_result": "MATCH"` | `REJECTED` | 422 |
| `inv_evaluation_enum_category` | Leaked evaluation enum `"BL_COMPARISON"` | `REJECTED` | 422 |
| `inv_same_document_both_roles` | Assigns single document to both SI and BL | `REJECTED` | 422 |
| `inv_fabricated_evidence_bbox` | Inverted bbox coordinates (`x0 >= x1`) | `REJECTED` | 422 |
| `inv_table_cell_missing_coords` | `table_cell` evidence missing table coordinates | `REJECTED` | 422 |
| `inv_forbidden_extra_property` | Unexpected extra property (`extra = "forbid"`) | `REJECTED` | 422 |
| `inv_confirm_forcing_unextracted_field` | `CONFIRM` attempting to force complete unextracted fields | `REJECTED` | 422 |

---

## 4. Recomputation & Tri-State Scenarios

### 4.1 Deterministic Recomputation Scenarios
1. **`RECOMP-001` (Container Count Mismatch)**:
   - *Before*: `container_count` SI = 2, BL = 3 (`MISMATCH`).
   - *Update*: BL `container_count` corrected to `"4"`.
   - *After*: SI = 2, BL = 4 $\rightarrow$ deterministic integer equality yields `MISMATCH` (`is_discrepancy = true`).
2. **`RECOMP-002` (Gross Weight Unit Normalization)**:
   - *Before*: `gross_weight_kg` SI = `"22000"`, BL unextracted (`MISSING`).
   - *Update*: BL `gross_weight_kg` supplied as `"22 MT"`.
   - *After*: Unit conversion normalizes `22 MT` $\rightarrow$ `22000 KG`; exact decimal equality yields `MATCH` (`is_discrepancy = false`).
3. **`RECOMP-003` (Port of Discharge Missing Value)**:
   - *Before*: `port_of_discharge` SI = `null` (`MISSING`), BL = `"ROTTERDAM, NETHERLANDS"`.
   - *Update*: SI `port_of_discharge` supplied as `"ROTTERDAM, NETHERLANDS"`.
   - *After*: Text normalization yields exact string match $\rightarrow$ `MATCH` (`is_discrepancy = false`).

### 4.2 Tri-State Outcome Invariant Scenario
- **`TRISTATE-001`**:
  - In `case_09`, `container_count` has a confirmed mismatch (SI: 2 vs BL: 3), but `gross_weight_kg` is unextracted from the Draft BL.
  - The case state remains `NEEDS_REVIEW`.
  - `mismatch_detected` **MUST REMAIN `null`**. It is strictly forbidden to set it to `false` (because a confirmed mismatch exists) or `true` (because workflow is incomplete and additional fields may mismatch or fail normalization).
  - Summary must **NEVER** emit `"No mismatch detected"`.
