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

## 5. Core System Health

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

## 6. Standard Error Response Shape

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

## 7. Upcoming Phase Contracts (Phases 3 – 5)

For coordination with Member 2 (Frontend) and Member 3 (QA):

| Method | Path | Phase | Description |
|---|---|---|---|
| `POST` | `/api/v1/batches/{id}/validate` | Phase 3 | Execute rules engine, compute findings, calculate intake exceedance |
| `POST` | `/api/v1/batches/{id}/submit` | Phase 4 | Transition batch from Draft/Validated to Submitted; locks batch |
| `GET` | `/api/v1/dashboard/institution` | Phase 4 | Institution metrics: total records, valid/invalid, missing APAAR, intake % |
| `GET` | `/api/v1/dashboard/aicte` | Phase 4 | AICTE monitoring: aggregate enrollment, exception queue, duplicate flags |
| `POST` | `/api/v1/reviews/{finding_id}` | Phase 4 | Record human review outcome (Dismiss/Confirm) with mandatory reason |
| `GET` | `/api/v1/verification/{student_ref}` | Phase 5 | Privacy-restricted single-record lookup (returns `MOCK_VERIFIED`) |
| `GET` | `/api/v1/reports/export` | Phase 5 | CSV export of validated student batches and finding reports |
