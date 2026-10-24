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

## 3. Core System Health

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

## 4. Standard Error Response Shape

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
- `VALIDATION_ERROR` (422): Malformed payload or query parameter.
- `INTERNAL_SERVER_ERROR` (500): Unhandled exception (sanitized; stack traces never leaked).

---

## 5. Upcoming Phase Contracts (Phases 2 – 5)

For coordination with Member 2 (Frontend) and Member 3 (QA):

| Method | Path | Phase | Description |
|---|---|---|---|
| `POST` | `/api/v1/imports/preview` | Phase 2 | Multipart CSV/XLSX upload, parse headers, validate types, sample preview |
| `POST` | `/api/v1/imports` | Phase 2 | Commit parsed file, persist `ImportBatch` and raw `StudentRecord` rows |
| `POST` | `/api/v1/batches/{id}/validate` | Phase 3 | Execute rules engine, compute findings, calculate intake exceedance |
| `GET` | `/api/v1/batches/{id}` | Phase 3 | Get batch status, summary metrics, completion state |
| `GET` | `/api/v1/batches/{id}/findings` | Phase 3 | Paginated findings with rule, severity, record reference, suggested action |
| `POST` | `/api/v1/batches/{id}/submit` | Phase 4 | Transition batch from Draft/Validated to Submitted; locks batch |
| `GET` | `/api/v1/dashboard/institution` | Phase 4 | Institution metrics: total records, valid/invalid, missing APAAR, intake % |
| `GET` | `/api/v1/dashboard/aicte` | Phase 4 | AICTE monitoring: aggregate enrollment, exception queue, duplicate flags |
| `POST` | `/api/v1/reviews/{finding_id}` | Phase 4 | Record human review outcome (Dismiss/Confirm) with mandatory reason |
| `GET` | `/api/v1/verification/{student_ref}` | Phase 5 | Privacy-restricted single-record lookup (returns `MOCK_VERIFIED`) |
| `GET` | `/api/v1/reports/export` | Phase 5 | CSV export of validated student batches and finding reports |
