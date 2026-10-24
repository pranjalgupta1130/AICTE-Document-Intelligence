# SIH 26263: APAAR Student Data Platform — Data Dictionary

This document details the core data entities, schemas, enums, relationships, and rule definitions for the APAAR-Based Student Data Management & Verification Platform.

---

## 1. Domain Entities & Fields

### 1.1 `User` (`users`)
Represents system actors across institutions and administrative bodies.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Unique identifier (e.g., `usr-apex-adm-01`) |
| `email` | String (Unique) | No | User login email |
| `hashed_password` | String | No | Salted PBKDF2-HMAC-SHA256 password hash |
| `full_name` | String | No | Full display name |
| `role` | Enum (`UserRole`) | No | System role |
| `institution_id` | String (FK) | Yes | Associated institution (`null` for AICTE/Demo Admin) |
| `is_active` | Boolean | No | Account active status (default: `true`) |
| `created_at` | DateTime | No | Account creation timestamp (UTC) |

---

### 1.2 `Institution` (`institutions`)
AICTE-approved educational institution profile.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Internal identifier (e.g., `INST-001`) |
| `name` | String | No | Legal name of the institution |
| `code` | String (Unique) | No | Authoritative/illustrative institution code |
| `state` | String | No | State/UT |
| `status` | String | No | Status (`ACTIVE`, `INACTIVE`) |
| `created_at` | DateTime | No | Creation timestamp (UTC) |

---

### 1.3 `Programme` (`programmes`)
Academic courses offered by an institution.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Programme ID (e.g., `PROG-001-CSE`) |
| `institution_id` | String (FK) | No | Parent institution |
| `name` | String | No | e.g. "B.Tech Computer Science & Engineering" |
| `degree_level` | String | No | e.g. "UNDERGRADUATE", "POSTGRADUATE" |
| `duration_years` | Integer | No | Duration (e.g. 4) |

---

### 1.4 `ApprovedIntake` (`approved_intakes`)
Authoritative intake limits sanctioned by AICTE per programme and academic year.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Intake record ID (e.g., `INTAKE-001-CSE-2026`) |
| `institution_id` | String (FK) | No | Institution reference |
| `programme_id` | String (FK) | No | Programme reference |
| `academic_year` | String | No | e.g., "2026-2027" |
| `regular_intake` | Integer | No | Approved regular seats (e.g., 120) |
| `supernumerary_intake`| Integer | No | Sanctioned supernumerary seats (e.g., 15) |
| `supernumerary_policy`| String | Yes | Explanatory note/policy reference |

---

### 1.5 `StudentRecord` (`student_records`)
Individual student enrollment records.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Internal UUID (primary key; never expose raw PII) |
| `batch_id` | String (FK) | No | Originating `ImportBatch` ID |
| `institution_id` | String (FK) | No | Enrolling institution |
| `apaar_id` | String | Yes | 12-digit APAAR ID (masked in unprivileged views) |
| `institution_student_id` | String | No | College roll/registration number |
| `student_name` | String | Yes | Student name (synthetic; minimized) |
| `academic_year` | String | No | Enrolled academic year (e.g., "2026-2027") |
| `programme_id` | String (FK) | No | Programme reference |
| `enrolment_status` | Enum (`EnrolmentStatus`) | No | Active/Withdrawn/Completed |
| `seat_type` | Enum (`SeatType`) | No | Sanctioned intake quota category (Canonical model field. Supported external spreadsheet column aliases during import include: `seat_type`, `quota`, `quota_type`, `quota type`, `category`, `seat_category`, `admission_type`, `seat type`). Values: `REGULAR`, `SUPERNUMERARY_EWS`, `SUPERNUMERARY_TFW`, `SUPERNUMERARY_FN`, `SUPERNUMERARY_OTHER`, `MANAGEMENT`, `NRI` |
| `is_nri` | Boolean | No | Non-Resident Indian flag |
| `is_oci` | Boolean | No | Overseas Citizen of India flag |
| `is_fn` | Boolean | No | Foreign National flag |
| `source_row_number` | Integer | Yes | 1-based source spreadsheet row index for discrepancy lineage |
| `created_at` | DateTime | No | Timestamp |

---

### 1.6 `ImportBatch` (`import_batches`)
Tracks bulk ingestion runs, provenance, and row counts.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Batch ID (e.g., `BATCH-20261024-001`) |
| `institution_id` | String (FK) | No | Submitting institution |
| `uploader_user_id`| String (FK) | No | User who initiated the upload |
| `source_filename`| String | No | Original filename (e.g., `students_2026.csv`) |
| `academic_year` | String | No | e.g. "2026-2027" |
| `version` | Integer | No | Batch revision counter (1, 2, ...) |
| `status` | Enum (`BatchStatus`)| No | Current lifecycle state |
| `total_rows` | Integer | No | Total parsed rows |
| `valid_rows` | Integer | No | Rows free of blocking errors |
| `error_rows` | Integer | No | Rows with blocking errors |
| `warning_rows` | Integer | No | Rows with non-blocking warnings |
| `created_at` | DateTime | No | Upload timestamp |
| `updated_at` | DateTime | No | Last update timestamp |

---

### 1.7 `ValidationFinding` (`validation_findings`)
Explainable validation findings produced by the rules engine.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Finding ID |
| `batch_id` | String (FK) | No | Associated batch |
| `record_id` | String (FK) | Yes | Associated student record (if row-specific) |
| `row_number` | Integer | Yes | 1-indexed row number in uploaded file |
| `field_name` | String | Yes | Specific column/field (e.g., `apaar_id`) |
| `rule_code` | String | No | Machine-readable rule ID (e.g., `RULE-APAAR-001`) |
| `severity` | Enum (`FindingSeverity`)| No | `BLOCKING_ERROR`, `WARNING`, `INFO` |
| `message` | String | No | Plain-language explanation of discrepancy |
| `expected_value` | String | Yes | Benchmark or statutory requirement |
| `actual_value` | String | Yes | Value observed in uploaded record |
| `suggested_action`| String | Yes | Actionable remediation guidance for operator |
| `status` | Enum (`FindingStatus`)| No | `OPEN`, `RESOLVED`, `DISMISSED` |
| `created_at` | DateTime | No | Generation timestamp |

---

### 1.8 `MatchCandidate` (`match_candidates`)
Cross-institution or cross-batch duplicate candidates flagged for human triage.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Candidate match ID |
| `record_a_id` | String (FK) | No | Reference to StudentRecord A |
| `record_b_id` | String (FK) | No | Reference to StudentRecord B |
| `institution_a_id`| String (FK) | No | Institution A |
| `institution_b_id`| String (FK) | No | Institution B |
| `matching_signal` | String | No | e.g. "EXACT_APAAR_COLLISION" |
| `confidence` | Float | No | Matching confidence (1.0 for exact ID) |
| `status` | Enum (`MatchStatus`)| No | `CANDIDATE`, `CONFIRMED_DUPLICATE`, `DISMISSED` |
| `resolution_reason`| String | Yes | Mandatory explanation on review |
| `reviewed_by` | String (FK) | Yes | Reviewer user ID |
| `reviewed_at` | DateTime | Yes | Review timestamp |

---

### 1.9 `AuditEvent` (`audit_events`)
Tamper-evident, append-only operational audit log.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | String (PK) | No | Event ID |
| `actor_user_id` | String (FK) | Yes | User who triggered the action |
| `actor_email` | String | No | User email snapshot |
| `actor_role` | String | No | Role snapshot |
| `institution_id` | String (FK) | Yes | Scope of the event |
| `action` | Enum (`AuditAction`)| No | Operational action |
| `object_type` | String | No | e.g., "BATCH", "STUDENT_RECORD", "REVIEW" |
| `object_id` | String | Yes | Target identifier |
| `outcome` | String | No | "SUCCESS", "FAILURE", "BLOCKED" |
| `details` | JSON/Text | Yes | Sanitized context (no raw PII) |
| `timestamp` | DateTime | No | Immutable UTC timestamp |

---

## 2. Standard Enums

```python
class UserRole(str, Enum):
    INSTITUTION_ADMIN = "INSTITUTION_ADMIN"
    INSTITUTION_OPERATOR = "INSTITUTION_OPERATOR"
    AICTE_ADMIN = "AICTE_ADMIN"
    EXTERNAL_VERIFIER = "EXTERNAL_VERIFIER"
    DEMO_ADMIN = "DEMO_ADMIN"

class EnrolmentStatus(str, Enum):
    ENROLLED = "ENROLLED"
    ADMITTED = "ADMITTED"
    WITHDRAWN = "WITHDRAWN"
    COMPLETED = "COMPLETED"

class SeatType(str, Enum):
    REGULAR = "REGULAR"
    SUPERNUMERARY_EWS = "SUPERNUMERARY_EWS"
    SUPERNUMERARY_TFW = "SUPERNUMERARY_TFW"
    SUPERNUMERARY_FN = "SUPERNUMERARY_FN"
    SUPERNUMERARY_OTHER = "SUPERNUMERARY_OTHER"
    MANAGEMENT = "MANAGEMENT"
    NRI = "NRI"

class BatchStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"
    REJECTED = "REJECTED"

class FindingSeverity(str, Enum):
    BLOCKING_ERROR = "BLOCKING_ERROR"
    WARNING = "WARNING"
    INFO = "INFO"

class FindingStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class MatchStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"
    DISMISSED = "DISMISSED"

class VerificationOutcome(str, Enum):
    MOCK_VERIFIED = "MOCK_VERIFIED"
    MOCK_NOT_VERIFIED = "MOCK_NOT_VERIFIED"
    MOCK_UNAVAILABLE = "MOCK_UNAVAILABLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"

class AuditAction(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    IMPORT_UPLOAD = "IMPORT_UPLOAD"
    BATCH_VALIDATE = "BATCH_VALIDATE"
    BATCH_SUBMIT = "BATCH_SUBMIT"
    RECORD_CORRECTION = "RECORD_CORRECTION"
    REVIEW_DECISION = "REVIEW_DECISION"
    REPORT_EXPORT = "REPORT_EXPORT"
    VERIFICATION_LOOKUP = "VERIFICATION_LOOKUP"
```

---

## 3. Seeded Demo Users

| Email | Password | Role | Institution | Name |
|---|---|---|---|---|
| `aicte_admin@aicte.gov.in` | `DemoPassword@2026` | `AICTE_ADMIN` | `null` (All) | AICTE National Reviewer |
| `apex_admin@apex.edu.in` | `DemoPassword@2026` | `INSTITUTION_ADMIN` | `INST-001` | Apex Institution Admin |
| `apex_operator@apex.edu.in` | `DemoPassword@2026` | `INSTITUTION_OPERATOR` | `INST-001` | Apex Ingestion Operator |
| `bharat_admin@bharat.edu.in` | `DemoPassword@2026` | `INSTITUTION_ADMIN` | `INST-002` | Bharat Institution Admin |
| `demo_admin@apaar.gov.in` | `DemoPassword@2026` | `DEMO_ADMIN` | `null` | Hackathon Demonstration Lead |

---

## 4. Member 3: Data Quality Intelligence Schemas

### 4.1 `FuzzyCandidateResult`
Explainable fuzzy candidate entity flagged by multi-field similarity engine.

| Field | Type | Description |
|---|---|---|
| `candidate_id` | String | Unique candidate match identifier (e.g., `fuz-9e2c4d1a5b8e`) |
| `record_a_id` | String (FK) | First candidate student record |
| `record_b_id` | String (FK) | Second candidate student record |
| `institution_a_id` | String (FK) | Institution of record A |
| `institution_b_id` | String (FK) | Institution of record B |
| `is_cross_institution`| Boolean | True if pair spans different institutions |
| `overall_similarity`| Float | Composite similarity confidence in [0.0, 1.0] |
| `field_comparisons` | List[FieldComparisonDetail] | Attributed field scores, weights, contributions, and explanations |
| `explanation` | String | Plain-language human-readable match rationale |
| `suggested_action` | String | Operational next step for reviewer |

---

### 4.2 `BatchAnomalyReport` & `AnomalyFinding`
Statistical and pattern anomaly report for import batches.

| Field | Type | Description |
|---|---|---|
| `batch_id` | String (FK) | Evaluated batch identifier |
| `institution_id` | String (FK) | Associated institution |
| `academic_year` | String | Academic year of batch |
| `anomaly_level` | String | Overall hygiene assessment (`NORMAL`, `ELEVATED`, `CRITICAL`) |
| `anomalies` | List[AnomalyFinding] | Structured anomaly indicators |

---

### 4.3 `InstitutionQualitySummary` & `QualityScoreDelta`
Aggregated institutional quality summaries and version delta tracking.


---

### 4.4 LongitudinalTrendReport & LongitudinalTrendPoint
Timeline tracking for institutional quality and enrolment changes.

| Field | Type | Description |
|---|---|---|
| institution_id | String (FK) | Evaluated institution |
| cademic_year_filter | Optional[String] | Applied year filter |
| 	otal_batches | Integer | Total evaluated submissions |
| overall_trend | String | Trajectory: \IMPROVING\, \DEGRADING\, \STABLE\, or \INSUFFICIENT_DATA\ |
| 
et_quality_change | Float | Net delta between earliest and latest batch scores |
| datapoints | List[LongitudinalTrendPoint] | Detailed chronological batch quality metrics |
