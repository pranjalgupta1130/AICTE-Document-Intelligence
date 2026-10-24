# CSV Findings Export API

## Endpoint

```
POST /api/v1/member1/export-findings-csv
```

## Description

Accepts a completed `PipelineRunResult` JSON payload (the body returned by
`POST /api/v1/member1/process-application`) and streams it back as a
downloadable UTF-8 CSV file.

The endpoint **does not persist** any data and does not re-run validation.
It formats the already-evaluated findings from the submitted payload into a
structured, human-readable CSV suitable for AICTE statutory review,
institution audit workflows, and accreditation submissions.

---

## Request

| Property         | Value                      |
|-----------------|----------------------------|
| Method          | `POST`                     |
| Content-Type    | `application/json`         |
| Auth required   | Yes (enforced by Member 2) |

**Body:** A complete `PipelineRunResult` JSON object — the exact response body
from `POST /api/v1/member1/process-application`.

```json
{
  "application_id": "APP-2026-NIT-001",
  "analyzed_documents": [ ... ],
  "rule_evaluations": [ ... ],
  "consistency_evaluations": [ ... ],
  "duplicate_evaluations": { ... },
  "risk_tier": "ESCALATION",
  "risk_score": 85.0,
  "findings_audit_trail": [ ... ],
  "critical_deficiencies": [ ... ],
  "clarification_notes": [ ... ],
  "recommendations": [ ... ],
  "disclaimer": "Notice: ..."
}
```

---

## Response

| Property            | Value                          |
|--------------------|-------------------------------|
| Status code        | `200 OK`                       |
| Content-Type       | `text/csv; charset=utf-8`      |
| Content-Disposition | `attachment; filename="findings_<application_id>.csv"` |

### CSV column schema

| Column | Description |
|--------|-------------|
| `application_id` | Identifier of the application batch |
| `finding_type` | `REGULATORY_RULE`, `CONSISTENCY_CHECK`, or `DUPLICATE_DETECTION` |
| `rule_id` | Rule code, e.g. `RULE-LAND-001` (regulatory findings only) |
| `rule_name` | Human-readable rule name (regulatory findings only) |
| `rule_category` | Statutory category: `Land`, `Building`, `FireSafety`, `FDR`, `Faculty`, `Authentication` |
| `check_name` | Cross-document check name (consistency findings only) |
| `field_compared` | Field under comparison (consistency findings only) |
| `status` | `PASS`, `FAIL`, `INDETERMINATE`, `CONSISTENT`, `INCONSISTENT` |
| `severity` | `INFO`, `WARNING`, `DEFICIENCY`, `CRITICAL` |
| `is_consistent` | `True` / `False` (consistency findings only) |
| `is_authoritatively_verified` | `True` / `False` — whether the rule threshold is in the AICTE APH |
| `statutory_standard` | The threshold or standard the rule checks against |
| `observed_value` | Value extracted from the submitted documents |
| `difference` | Arithmetic delta from threshold (where applicable) |
| `deficiency_reason` | Explanation of why the rule failed |
| `discrepancy_details` | Human-readable description of the consistency mismatch |
| `duplicate_type` | `EXACT_SHA256` or `PERCEPTUAL_IMAGE` (duplicate findings only) |
| `documents_involved` | Semicolon-separated list of filenames involved in the finding |
| `match_detail` | SHA-256 hash or Hamming distance detail (duplicate findings only) |
| `source_documents` | Source document(s) that contributed the observed evidence |
| `correction_guidance` | Actionable remediation instruction |

### Empty report

If the `PipelineRunResult` contains no findings of any kind, the response is
`HTTP 200` with a CSV containing the header row only and zero data rows.

---

## Permissions

The endpoint inherits the authentication and institution-isolation model of
the `verireg` module:

- **Member 2's backend middleware** is responsible for authenticating the
  caller and verifying that the `application_id` in the payload belongs to
  the requesting institution before forwarding the request.
- **Unauthorized users** must be rejected upstream; this endpoint operates
  only on the payload it receives and does not independently query stored data.
- This is consistent with the existing `POST /process-application` contract.

---

## Security: Formula-injection protection

All untrusted text values (deficiency reasons, discrepancy details, document
names, application IDs, observed values, etc.) are sanitised before being
written to the CSV. Any value whose string representation starts with one of
the spreadsheet formula prefix characters (`=`, `+`, `-`, `@`, `|`, `%`) is
prefixed with a single-quote (`'`) so that Microsoft Excel, LibreOffice Calc,
and Google Sheets treat the cell as plain text rather than a formula.

This mitigates the OWASP CSV injection (CWE-1236) attack surface.

---

## Error responses

| Status | Condition |
|--------|-----------|
| `200 OK` | Successful export (even if findings list is empty) |
| `422 Unprocessable Entity` | Request body does not conform to the `PipelineRunResult` schema |
| `500 Internal Server Error` | Unexpected serialisation failure (should not occur with valid input) |

---

## Example usage

### cURL

```bash
# 1. Run the application pipeline and capture the result
curl -s -X POST http://localhost:8000/api/v1/member1/process-application \
  -F "application_id=APP-2026-NIT-001" \
  -F "files=@/path/to/application.pdf" \
  > pipeline_result.json

# 2. Export the findings as CSV
curl -X POST http://localhost:8000/api/v1/member1/export-findings-csv \
  -H "Content-Type: application/json" \
  -d @pipeline_result.json \
  --output "findings_APP-2026-NIT-001.csv"
```

### Python (requests)

```python
import requests, json

with open("pipeline_result.json") as f:
    result = json.load(f)

resp = requests.post(
    "http://localhost:8000/api/v1/member1/export-findings-csv",
    json=result,
)
resp.raise_for_status()

with open("findings.csv", "wb") as f:
    f.write(resp.content)
```

---

## Files changed

| File | Change |
|------|--------|
| `verireg/csv_export.py` | **New** – pure-stdlib CSV serialisation logic |
| `verireg/api.py` | Added `POST /export-findings-csv` endpoint + imports |
| `tests/test_csv_export.py` | **New** – 30 focused tests (unit + integration) |
| `docs/api_csv_export.md` | **New** – this documentation file |

---

## Constraints respected

- ✅ No database models or migrations modified.
- ✅ No authentication or core validation logic modified.
- ✅ No new third-party dependencies — uses only Python stdlib `csv` and `io`.
- ✅ Existing `test_member1.py` suite: **13/13 passed** (zero regressions).
- ✅ New `test_csv_export.py` suite: **30/30 passed**.
- ✅ All synthetic test data — no real student PII.
- ✅ Work on `feature/csv-findings-export` branch — not merged or pushed.
