# SIH 26263: APAAR Student Data Platform — API Contract

Version: `v1`
Base URL: `/api/v1`
Format: `application/json`
Authentication: Bearer JWT (`Authorization: Bearer <access_token>`)

---

## 1. Authentication & Session

### POST `/api/v1/auth/login`
Authenticate with email/username and password.

**Request Body:**
```json
{
  "email": "apex_admin@apex.edu.in",
  "password": "DemoPassword@2026"
}
```

**Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in_seconds": 28800,
  "user": {
    "id": "usr-apex-adm-01",
    "email": "apex_admin@apex.edu.in",
    "full_name": "Apex Institution Administrator",
    "role": "INSTITUTION_ADMIN",
    "institution_id": "INST-001",
    "institution_name": "Apex Institute of Technology"
  }
}
```

**Errors:**
- `401 Unauthorized`: Invalid credentials.

---

### GET `/api/v1/auth/me` (or `GET /api/v1/me`)
Retrieve caller's profile and active role/institution scope.

**Headers:**
`Authorization: Bearer <token>`

**Response (`200 OK`):**
```json
{
  "id": "usr-apex-adm-01",
  "email": "apex_admin@apex.edu.in",
  "full_name": "Apex Institution Administrator",
  "role": "INSTITUTION_ADMIN",
  "institution_id": "INST-001",
  "institution_name": "Apex Institute of Technology"
}
```

---

## 2. Institutions & Approved Intake

### GET `/api/v1/institutions`
List institutions permitted for the caller.
- **AICTE_ADMIN / DEMO_ADMIN**: Returns all registered institutions.
- **INSTITUTION_ADMIN / INSTITUTION_OPERATOR**: Returns ONLY the caller's institution (strictly scoped).

**Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "INST-001",
      "name": "Apex Institute of Technology",
      "code": "AIT-DELHI",
      "state": "Delhi",
      "status": "ACTIVE"
    }
  ],
  "total": 1
}
```

---

### GET `/api/v1/intake`
Query approved intake capacity by institution, programme, and academic year.
- Server-side scoped: Institution users cannot query intake of other institutions.

**Query Parameters:**
- `institution_id` (optional for AICTE; forced to caller's institution for institution roles)
- `academic_year` (optional, e.g. `2026-2027`)
- `programme_id` (optional)

**Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "INTAKE-001-CSE-2026",
      "institution_id": "INST-001",
      "programme_id": "PROG-001-CSE",
      "programme_name": "B.Tech Computer Science & Engineering",
      "academic_year": "2026-2027",
      "regular_intake": 120,
      "supernumerary_intake": 15,
      "total_approved_intake": 135,
      "supernumerary_policy": "AICTE Handbook Chapter II: Up to 15% supernumerary seats for EWS/TFW/FN where sanctioned"
    }
  ],
  "total": 1
}
```

---

## 3. Data Ingestion & Persistence (Phase 2)

### GET `/api/v1/imports/template`
Download standard CSV import template with required AICTE student fields.
- **Requires Authentication**: Yes (`Bearer <token>`)
- **Response**: `text/csv` attachment (`apaar_student_template.csv`)

---

### POST `/api/v1/imports/preview`
Multipart upload preview for tabular datasets (`.csv`, `.xlsx`).
- Inspects headers, suggests field mappings, checks structure, and returns up to 10 sample rows without writing to the database.

**Form Data:**
- `file`: CSV or XLSX file (required)

**Response (`200 OK`):**
```json
{
  "filename": "students_2026.csv",
  "file_type": "CSV",
  "detected_columns": ["APAAR ID", "Student Name", "Roll No", "Programme ID", "Academic Year"],
  "suggested_mapping": {
    "apaar_id": "APAAR ID",
    "student_name": "Student Name",
    "institution_student_id": "Roll No",
    "programme_id": "Programme ID",
    "academic_year": "Academic Year"
  },
  "total_preview_rows": 120,
  "sample_rows": [
    {
      "APAAR ID": "987654321012",
      "Student Name": "Student One",
      "Roll No": "APEX-2026-001",
      "Programme ID": "PROG-001-CSE",
      "Academic Year": "2026-2027",
      "_file_row_num": 2
    }
  ],
  "structural_errors": [],
  "is_valid_structure": true
}
```

---

### POST `/api/v1/imports`
Ingest and transactionally persist student records into an `ImportBatch`.
- Enforces institution scoping: Institution users can only ingest into their own institution.
- Auto-increments batch `version` per institution and academic year.
- Validates row format, maps columns, and records row-level findings in `validation_findings`.
- Emits an `AuditEvent` with action `IMPORT_UPLOAD`.

**Form Data:**
- `file`: CSV or XLSX file (required)
- `academic_year`: Enrolled academic year (e.g. `2026-2027`)
- `programme_id`: Default programme fallback
- `institution_id`: Explicit institution (validated against caller scope; rejected if cross-institution)
- `column_mapping` (or `mapping`): JSON string of field-to-column overrides

**Response (`200 OK`):**
```json
{
  "batch_id": "BATCH-20261024-5ECD1E",
  "institution_id": "INST-001",
  "source_filename": "students_2026.csv",
  "academic_year": "2026-2027",
  "version": 1,
  "status": "DRAFT",
  "total_rows": 120,
  "valid_rows": 118,
  "error_rows": 2,
  "warning_rows": 1,
  "row_errors": [
    {
      "row_number": 15,
      "field": "institution_student_id",
      "value": "",
      "message": "Institution Student ID (roll/registration number) is mandatory."
    }
  ]
}
```

---

## 4. Import Batches & Lineage

### GET `/api/v1/batches`
List import batches with counts, lineage, and lifecycle status.
- Strictly isolated to the caller's institution unless caller is `AICTE_ADMIN` or `DEMO_ADMIN`.

**Query Parameters:**
- `institution_id` (optional for AICTE; forced to caller's institution)
- `academic_year` (optional filter)
- `status` (optional filter: `DRAFT`, `VALIDATED`, etc.)
- `limit` (default: 50)
- `offset` (default: 0)

**Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "BATCH-20261024-5ECD1E",
      "institution_id": "INST-001",
      "uploader_user_id": "usr-apex-op-01",
      "source_filename": "students_2026.csv",
      "academic_year": "2026-2027",
      "version": 1,
      "status": "DRAFT",
      "total_rows": 120,
      "valid_rows": 118,
      "error_rows": 2,
      "warning_rows": 1,
      "created_at": "2026-10-24T10:15:30Z"
    }
  ],
  "total": 1
}
```

---

### GET `/api/v1/batches/{batch_id}`
Retrieve detailed status and counts for a specific batch. Enforces institution isolation.

---

### GET `/api/v1/batches/{batch_id}/findings`
Retrieve paginated row-level parsing and validation findings for a batch.

**Query Parameters:**
- `severity` (optional filter: `BLOCKING_ERROR`, `WARNING`, `INFO`)
- `limit` (default: 50)
- `offset` (default: 0)

**Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "fnd-9b342e14a1bc",
      "batch_id": "BATCH-20261024-5ECD1E",
      "record_id": null,
      "row_number": 15,
      "field_name": "institution_student_id",
      "rule_code": "RULE-REQ-002",
      "severity": "BLOCKING_ERROR",
      "message": "Missing required institution student identifier.",
      "actual_value": null,
      "suggested_action": "Provide college student roll or registration number.",
      "status": "OPEN",
      "created_at": "2026-10-24T10:15:31Z"
    }
  ],
  "total": 1
}
```

---

### POST `/api/v1/batches/{batch_id}/validate`
Execute Phase 3 deterministic validation rules, duplicate checks, and approved intake reconciliation.
Updates batch status to `VALIDATED` (if 0 blocking errors) or `NEEDS_CORRECTION` (if blocking errors exist).
Records an audit event with action `BATCH_VALIDATE`.

**Response (`200 OK`):**
```json
{
  "batch_id": "BATCH-20261024-5ECD1E",
  "institution_id": "INST-001",
  "status": "NEEDS_CORRECTION",
  "validation_summary": {
    "total_records": 100,
    "valid_records": 95,
    "error_count": 2,
    "warning_count": 4,
    "info_count": 0,
    "intake_exceeded_count": 2,
    "duplicate_candidate_count": 2
  },
  "intake_reconciliation": [
    {
      "programme_id": "PROG-001-CSE",
      "programme_name": "B.Tech Computer Science & Engineering",
      "academic_year": "2026-2027",
      "regular_approved": 60,
      "regular_enrolled": 62,
      "regular_exceeded": 2,
      "supernumerary_approved": 6,
      "supernumerary_enrolled": 2,
      "supernumerary_exceeded": 0,
      "total_approved": 66,
      "total_enrolled": 64,
      "total_exceeded": 0,
      "status": "EXCEEDED"
    }
  ],
  "findings_count": 6,
  "message": "Validation completed. Batch status set to NEEDS_CORRECTION."
}
```

---

### GET `/api/v1/batches/{batch_id}/matches`
Retrieve flagged cross-institution or intra-institution duplicate match candidates associated with student records in this batch for verification.

**Response (`200 OK`):**
```json
[
  {
    "id": "match-uuid-1",
    "record_a_id": "rec-uuid-1",
    "record_b_id": "rec-uuid-2",
    "match_type": "CROSS_INSTITUTION_DUPLICATE_APAAR",
    "confidence_score": 1.0,
    "match_details": {
      "apaar_id": "987654321012",
      "student_name": "Aarav Sharma",
      "other_institution_id": "inst-2"
    },
    "review_status": "FLAGGED",
    "reviewer_user_id": null,
    "created_at": "2026-10-24T12:00:00Z"
  }
]
```

---

## 5. Phase 4 Workflows & Analytics (Batch 2)

### POST `/api/v1/batches/{id}/submit`
Formally submit a validated student record batch and lock it for official AICTE reconciliation.

**Permissions:** `INSTITUTION_ADMIN`, `AICTE_ADMIN`, `DEMO_ADMIN` (Forbidden to `INSTITUTION_OPERATOR` and `EXTERNAL_VERIFIER`).

**Request Body:**
```json
{
  "allow_warnings": true,
  "comments": "Finalized batch after physical document verification."
}
```

**Response (`200 OK`):**
```json
{
  "batch_id": "BATCH-001",
  "institution_id": "INST-001",
  "status": "SUBMITTED",
  "version": 1,
  "submitted_at": "2026-10-24T17:40:00Z",
  "submitted_by": "apex_admin@apex.edu.in",
  "valid_rows": 120,
  "error_rows": 0,
  "warning_rows": 2,
  "message": "Batch has been successfully submitted and locked for review."
}
```

---

### POST `/api/v1/reviews/{finding_id}`
Review an explainable validation finding. Resolving or dismissing a blocking error dynamically recalculates batch error counters.

**Permissions:** `INSTITUTION_ADMIN`, `INSTITUTION_OPERATOR`, `AICTE_ADMIN`, `DEMO_ADMIN` (scoped strictly to own institution).

**Request Body:**
```json
{
  "decision": "RESOLVED",
  "reason": "Student APAAR verified against DigiLocker extract."
}
```

**Response (`200 OK`):**
```json
{
  "finding_id": "fnd-123456",
  "batch_id": "BATCH-001",
  "status": "RESOLVED",
  "reviewed_by": "apex_admin@apex.edu.in",
  "reviewed_at": "2026-10-24T17:40:00Z",
  "reason": "Student APAAR verified against DigiLocker extract.",
  "message": "Finding 'fnd-123456' successfully reviewed as 'RESOLVED'."
}
```

---

### POST `/api/v1/reviews/matches/{match_id}`
Review a cross-institution duplicate candidate.

**Permissions:** `AICTE_ADMIN`, `DEMO_ADMIN` only.

**Request Body:**
```json
{
  "status": "CONFIRMED_DUPLICATE",
  "resolution_reason": "Verified simultaneous enrollment at both institutions."
}
```

**Response (`200 OK`):**
```json
{
  "id": "mat-123456",
  "record_a_id": "stu-001",
  "record_b_id": "stu-002",
  "institution_a_id": "INST-001",
  "institution_b_id": "INST-002",
  "matching_signal": "CROSS_INSTITUTION_DUPLICATE_APAAR",
  "confidence": 1.0,
  "status": "CONFIRMED_DUPLICATE",
  "resolution_reason": "Verified simultaneous enrollment at both institutions.",
  "reviewed_by": "usr-aicte-adm-01",
  "reviewed_at": "2026-10-24T17:40:00Z"
}
```

---

### GET `/api/v1/dashboard/institution`
Retrieve operational dashboard metrics scoped to caller's institution.

**Permissions:** `INSTITUTION_ADMIN`, `INSTITUTION_OPERATOR`, `AICTE_ADMIN`, `DEMO_ADMIN`.

**Response (`200 OK`):**
```json
{
  "institution_id": "INST-001",
  "institution_name": "Apex Institute of Technology",
  "academic_year": "2026-2027",
  "total_batches": 2,
  "latest_batch_status": "VALIDATED",
  "total_student_records": 120,
  "valid_records_count": 120,
  "error_records_count": 0,
  "missing_apaar_count": 5,
  "duplicate_flags_count": 0,
  "intake_utilization_pct": 50.0,
  "total_approved_intake": 240,
  "total_enrolled_students": 120,
  "programme_intake_breakdown": [],
  "recent_batches": [],
  "recent_activity": []
}
```

---

### GET `/api/v1/dashboard/aicte`
Retrieve national aggregate monitoring metrics across all AICTE institutions.

**Permissions:** `AICTE_ADMIN`, `DEMO_ADMIN` only.

**Response (`200 OK`):**
```json
{
  "academic_year": "2024-2025",
  "total_institutions": 3,
  "total_submissions": 0,
  "total_batches": 0,
  "total_enrolled_students": 0,
  "total_approved_intake": 720,
  "aggregate_intake_utilization_pct": 0.0,
  "total_open_exceptions": 0,
  "total_candidate_duplicates": 0,
  "confirmed_duplicates_count": 0,
  "dismissed_duplicates_count": 0,
  "institution_breakdown": [],
  "recent_activity": []
}
```

---

## 6. Core System Health

### GET `/health`
System liveness and readiness probe.

**Response (`200 OK`):**
```json
{
  "status": "healthy",
  "service": "SIH26263-APAAR-Backend",
  "version": "1.0.0",
  "environment": "development",
  "database": "connected"
}
```

---

## 7. Standard Error Response Shape

All non-2xx responses follow a uniform structure:

```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Institution users cannot access other institutions' records",
    "details": null,
    "request_id": "req-5b5832ea-5b12-4e0e"
  }
}
```

### Standard Error Codes:
- `AUTHENTICATION_REQUIRED` (401): Missing or expired bearer token.
- `AUTHENTICATION_FAILED` (401): Incorrect username/password.
- `PERMISSION_DENIED` (403): User role lacks access to endpoint or resource.
- `INSTITUTION_SCOPE_VIOLATION` (403): Attempt to query or alter another institution's data.
- `RESOURCE_NOT_FOUND` (404): Entity not found.
- `EMPTY_FILE` (400): File payload is 0 bytes.
- `UNSUPPORTED_MEDIA_TYPE` (415): File is not CSV or XLSX.
- `VALIDATION_ERROR` (422): Malformed payload or query parameter.
- `INTERNAL_SERVER_ERROR` (500): Unhandled exception (sanitized; stack traces never leaked).

---

## 8. Phase 5 Integration & Differentiators

### GET `/api/v1/verification/{student_ref}`
Privacy-restricted single-record APAAR verification lookup. Clearly marks mock results as simulated and logs an immutable audit event.

**Permissions:** `INSTITUTION_ADMIN`, `INSTITUTION_OPERATOR`, `AICTE_ADMIN`, `DEMO_ADMIN`, `EXTERNAL_VERIFIER`. (Institution users strictly scoped to own institution).

**Response (`200 OK`):**
```json
{
  "apaar_id": "987654321012",
  "provider": "MOCK_APAAR_ADAPTER",
  "outcome": "MOCK_VERIFIED",
  "is_official": false,
  "reference_id": "mock-ref-a1b2c3d4e5f6",
  "student_name": "Verifiable Student",
  "institution_id": "INST-001",
  "message": "[SIMULATED] Synthetically verified against Mock APAAR Adapter.",
  "details": "Valid 12-digit format and Verhoeff checksum. Clearly marked as simulated verification."
}
```

---

### GET `/api/v1/batches/{id}/quality`
Retrieve transparent, explainable data quality score (0-100) and dimensional breakdown (Completeness, Validity, Consistency, Uniqueness). Framed strictly as dataset hygiene, never as a fraud score.

**Permissions:** `INSTITUTION_ADMIN`, `INSTITUTION_OPERATOR`, `AICTE_ADMIN`, `DEMO_ADMIN`.

**Response (`200 OK`):**
```json
{
  "batch_id": "BATCH-001",
  "academic_year": "2026-2027",
  "total_records": 120,
  "overall_score": 96.5,
  "grade": "EXCELLENT",
  "completeness": {
    "dimension_name": "Completeness",
    "weight": 0.25,
    "score": 100.0,
    "total_checks": 240,
    "passed_checks": 240,
    "deductions": 0.0,
    "explanation": "0 missing field occurrences across student records."
  },
  "validity": {
    "dimension_name": "Validity",
    "weight": 0.3,
    "score": 95.0,
    "total_checks": 120,
    "passed_checks": 114,
    "deductions": 5.0,
    "explanation": "6 records with invalid APAAR syntax or failed Verhoeff checksums."
  },
  "consistency": {
    "dimension_name": "Consistency",
    "weight": 0.25,
    "score": 100.0,
    "total_checks": 120,
    "passed_checks": 120,
    "deductions": 0.0,
    "explanation": "0 records with category/seat inconsistency or intake allocation breaches."
  },
  "uniqueness": {
    "dimension_name": "Uniqueness",
    "weight": 0.2,
    "score": 100.0,
    "total_checks": 120,
    "passed_checks": 120,
    "deductions": 0.0,
    "explanation": "0 records with duplicate roll numbers or APAAR collision candidates."
  },
  "explanation": "Transparent dataset hygiene score: 96.5/100 (EXCELLENT) based on completeness, validity, consistency, and uniqueness."
}
```

---

### GET `/api/v1/reports/export`
Export permission-scoped CSV reports with mandatory audit logging.

**Query Parameters:**
- `batch_id`: Optional filter by batch ID.
- `institution_id`: Optional filter by institution (enforced against caller).
- `report_type`: `'findings'` (default) or `'quality_summary'`.

**Permissions:** `INSTITUTION_ADMIN`, `INSTITUTION_OPERATOR`, `AICTE_ADMIN`, `DEMO_ADMIN` (Forbidden to `EXTERNAL_VERIFIER`).

**Response (`200 OK`):**
Streamed CSV file (`Content-Type: text/csv`).

---

## 9. Upcoming Phase Contracts (Phase 6: Hardening & Release Readiness)

For coordination with Member 2 (Frontend) and Member 3 (QA):

| Phase | Objective | Scope |
|---|---|---|
| Phase 6 | System Hardening & Release | Full security review, seed reset routines, performance verification, demo script walk-through |
