# Synthetic Multi-Format Document Fixture Suite (`tests/fixtures/documents/`)

This directory contains fictional multi-format document fixtures for parser, extraction, normalization, OCR recovery, and comparison tests.

---

## 1. Directory Structure

```text
tests/fixtures/documents/
├── manifest.json                  # Decoupled test expectations & pair mappings
├── README.md                      # Documentation & fixture inventory
├── txt/                           # Plain-text SI and Draft BL documents (13 fixtures)
├── docx/                          # Microsoft Word .docx fixtures (5 fixtures: tables & paragraphs)
├── pdf/                           # Standard vector PDFs with extractable text layers (4 fixtures)
├── scanned/                       # Raster image-only PDFs with genuine visible text glyphs & zero text layer (2 fixtures)
├── xlsx/                          # Microsoft Excel .xlsx workbooks (3 fixtures: design extension)
└── malformed/                     # Controlled truncated streams & corrupted structures (3 fixtures)
```

Total fixtures: 30 (28 Baseline Acceptance, 2 Exploratory).

---

## 2. Seven Mandatory Comparison Fields

All fixtures and verification pairs use these seven comparison fields:
1. `shipper`
2. `consignee`
3. `notify_party`
4. `port_of_loading`
5. `port_of_discharge`
6. `container_count`
7. `gross_weight_kg`

---

## 3. Format Inventory & Document Catalogue

| Subdirectory | Fixture File | Role | Scenario / Test Focus | Extractable Text Layer | Acceptance Status |
|---|---|:---:|---|:---:|:---:|
| `txt/` | `txt_si_001_clean.txt` | SI | Baseline clean SI (`PAIR-001`, `002`, `003`) | YES | Baseline |
| `txt/` | `txt_bl_001_clean_match.txt` | BL | Baseline matching BL (`PAIR-001`) | YES | Baseline |
| `txt/` | `txt_bl_002_count_mismatch.txt`| BL | Single mismatch (`container_count` 4 vs 5, `PAIR-002`) | YES | Baseline |
| `txt/` | `txt_bl_003_multi_mismatch.txt`| BL | Multiple mismatches (shipper, POD, weight, `PAIR-003`) | YES | Baseline |
| `txt/` | `txt_si_005_alt_labels.txt` | SI | Authoritative label variant (`Load Port` for `port_of_loading`) | YES | Baseline |
| `txt/` | `txt_si_006_multiline_orgs.txt`| SI | Multi-line postal address preservation (explicit notify party) | YES | Baseline |
| `txt/` | `txt_si_007_missing_field.txt` | SI | Missing required field (`notify_party`, `PAIR-004`) | YES | Baseline |
| `txt/` | `txt_si_008_conflicting_candidates.txt`| SI | Conflicting candidate values (gross weight, `PAIR-005`)| YES | Baseline |
| `txt/` | `txt_si_009_short_valid.txt` | SI | Short qualitative usability verification | YES | Baseline |
| `txt/` | `txt_si_010_long_unusable.txt` | SI | Long garbled text lacking 7 fields (`PAR-USAB-002`) | YES (Garbled) | Baseline |
| `txt/` | `txt_si_011_unit_mt` | SI | Metric Ton weight representation (`22 MT`, `PAIR-006`) | YES | Baseline |
| `txt/` | `txt_si_012_exploratory_aliases.txt` | SI | Non-baseline aliases (`POL`, `POD`, `Total Containers`) | YES | **Exploratory** |
| `txt/` | `txt_si_013_exploratory_same_as_consignee.txt` | SI | Literal `"SAME AS CONSIGNEE"` (not dereferenced) | YES | **Exploratory** |
| `docx/` | `docx_si_001_paragraph.docx` | SI | Clean paragraph-formatted SI (`PAIR-DOCX-001`) | YES | Baseline |
| `docx/` | `docx_bl_001_table.docx` | BL | Clean table-formatted Draft BL (`PAIR-DOCX-001`) | YES | Baseline |
| `docx/` | `docx_si_003_multiline_cell.docx`| SI | Table with multi-line cell addresses | YES | Baseline |
| `docx/` | `docx_si_004_missing_field.docx` | SI | Missing required field (`port_of_discharge`) | YES | Baseline |
| `docx/` | `docx_si_005_conflicting_values.docx`| SI | Conflicting container counts in paragraph vs table | YES | Baseline |
| `pdf/` | `pdf_si_001_clean.pdf` | SI | Vector PDF with extractable text layer (`PAIR-PDF-001`) | **YES** | Baseline |
| `pdf/` | `pdf_bl_001_clean_match.pdf` | BL | Vector PDF matching SI (`PAIR-PDF-001`) | **YES** | Baseline |
| `pdf/` | `pdf_si_003_missing_field.pdf` | SI | Vector PDF missing `consignee` | **YES** | Baseline |
| `pdf/` | `pdf_si_004_conflicting_values.pdf`| SI | Vector PDF with conflicting weight specifications | **YES** | Baseline |
| `scanned/` | `scan_si_001_readable.pdf` | SI | Raster image-only PDF with genuine visible text (OCR input) | **NO (Empty)** | Baseline |
| `scanned/` | `scan_si_002_degraded.pdf` | SI | Degraded raster image-only PDF with genuine visible text | **NO (Empty)** | Baseline |
| `malformed/` | `corrupt_stream.pdf` | N/A | Truncated stream missing `%%EOF` marker (`is_corrupted`)| N/A | Baseline |
| `malformed/` | `corrupt_structure.docx` | N/A | Corrupted non-ZIP byte sequence (`is_corrupted`) | N/A | Baseline |
| `malformed/` | `empty_zero_bytes.pdf` | N/A | 0-byte PDF file (`is_corrupted`) | N/A | Baseline |
| `xlsx/` | `xlsx_si_001_clean.xlsx` | SI | Clean multi-sheet workbook (Design Extension, `PAIR-XLSX-001`) | YES | Baseline |
| `xlsx/` | `xlsx_bl_001_clean_match.xlsx` | BL | Table-format Draft BL workbook (`PAIR-XLSX-001`) | YES | Baseline |
| `xlsx/` | `xlsx_si_002_missing_field.xlsx`| SI | Incomplete workbook missing `port_of_loading` | YES | Baseline |

---

## 4. Reusable Verification Pairs Catalogue

| Pair ID | SI Fixture | Draft BL Fixture | Scenario | Expected Mismatches | Mismatch Detected | Rationale |
|---|---|---|---|---|:---:|---|
| `PAIR-001` | `txt_si_001_clean` | `txt_bl_001_clean_match` | Exact match | `[]` | `False` | 100% field equality across all 7 fields. |
| `PAIR-002` | `txt_si_001_clean` | `txt_bl_002_count_mismatch` | Single mismatch | `["container_count"]` | `True` | SI specifies 4, Draft BL specifies 5. |
| `PAIR-003` | `txt_si_001_clean` | `txt_bl_003_multi_mismatch` | Multi mismatch | `["shipper", "port_of_discharge", "gross_weight_kg"]` | `True` | 3 mandatory fields differ. |
| `PAIR-004` | `txt_si_007_missing_field` | `txt_bl_001_clean_match` | Incomplete SI | None (Tri-state) | `None` | Missing `notify_party` routes case to `missing_required_value` HITL. |
| `PAIR-005` | `txt_si_008_conflicting_candidates` | `txt_bl_001_clean_match` | Conflict | None (Tri-state) | `None` | Conflicting weights route case to `conflicting_candidate_values` HITL. |
| `PAIR-006` | `txt_si_011_unit_mt` | `txt_bl_001_clean_match` | Unit conversion | `[]` | `False` | `22 MT` ($22 \times 1000 = 22000\text{ KG}$) matches `22000 KG`. |
| `PAIR-DOCX-001` | `docx_si_001_paragraph` | `docx_bl_001_table` | Cross-format DOCX | `[]` | `False` | Paragraph SI vs table BL with exact match. |
| `PAIR-PDF-001` | `pdf_si_001_clean` | `pdf_bl_001_clean_match` | Vector PDF match | `[]` | `False` | Extractable vector PDF pair with exact match. |
| `PAIR-XLSX-001`| `xlsx_si_001_clean` | `xlsx_bl_001_clean_match` | Excel match | `[]` | `False` | Multi-sheet workbook SI vs Draft BL workbook. |

---

## 5. Critical Verification Distinctions

1. **Vector PDF vs. Scanned/Image-Only PDF**:
   - `pdf/pdf_si_001_clean.pdf` contains a genuine extractable text layer (`pypdf.extract_text()` returns complete text).
   - `scanned/scan_si_001_readable.pdf` and `scanned/scan_si_002_degraded.pdf` contain genuine visible character glyphs for all seven mandatory shipping fields rendered into an 8-bit grayscale bitmap with zero extractable PDF text layer (`pypdf.extract_text()` returns `""`). These serve as offline inputs for OCR/Vision recovery tests without performing OCR now.
2. **Deterministic Usability**:
   - `txt_si_009_short_valid.txt` (short text) contains sufficient required fields and passes usability checks.
   - `txt_si_010_long_unusable.txt` (long text) contains boilerplate legal disclaimer repetitions with zero shipping fields and fails usability checks (`PAR-USAB-002`). This proves usability is qualitative, not length-based.
3. **Strict Baseline Normalization**:
   - Tests enforce exact string/decimal equality after approved whitespace, casing, and metric unit conversion (`MT` $\rightarrow$ `KG`).
   - Open TBDs (`DEC-P06C`, `DEC-P06D`, `DEC-P06E`) are strictly preserved without unapproved tolerances or suffix stripping.
4. **Governance on Aliases & Entity Dereferencing**:
   - Only authoritative source-supported label variants (`Load Port` for `port_of_loading`), supported by the original use case and baselined specification, are baseline acceptance criteria.
   - Non-baseline aliases (`POL`, `POD`, `Total Containers`) are isolated in `txt_si_012_exploratory_aliases.txt` and marked `PROPOSED / EXPLORATORY — NOT A BASELINE ACCEPTANCE EXPECTATION`.
   - Literal `"SAME AS CONSIGNEE"` is isolated in `txt_si_013_exploratory_same_as_consignee.txt` and marked `PROPOSED / EXPLORATORY — NOT A BASELINE ACCEPTANCE EXPECTATION`, asserting the literal string without automatic dereferencing.

---

## 6. Fixture Governance & Discovery Rules

1. **Default Baseline Acceptance Discovery**:
   - Automated test runners and verification suites must discover only fixtures where:
     `is_baseline_acceptance == true`
   - Default acceptance test suites MUST NOT load or assert exploratory fixtures.

2. **Exploratory Fixtures Require Explicit Opt-In**:
   - Any fixture where `is_baseline_acceptance == false` is purely exploratory.
   - The following MUST NEVER silently become baseline acceptance requirements:
     - `POL` (port of loading shorthand)
     - `POD` (port of discharge shorthand)
     - `Total Containers` (container count shorthand)
     - `SAME AS CONSIGNEE` entity dereferencing / cross-field binding
