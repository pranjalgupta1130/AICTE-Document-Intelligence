# Hardcoded Demo & Test Data Fixtures Manifest

This directory contains permanent, deterministic CSV fixtures extracted from hardcoded constants, mock profiles, fallback datasets, and sample state across the SIH APAAR frontend application. These fixtures allow reproducibility during testing, demonstrations, and regression audits.

---

## Datasets Overview

| Output CSV | Source File | Constant / Identifier | Records | Description |
| :--- | :--- | :--- | :--- | :--- |
| `department_data.csv` | `frontend/src/pages/InstitutionDashboardPage.tsx` | `DEPARTMENT_DATA` | 4 | Departmental intake capacity, supernumerary quotas, actual enrolments, and quota breach tags. |
| `initial_diagnostics.csv` | `frontend/src/pages/BulkImportValidationPage.tsx` | `INITIAL_DIAGNOSTICS` | 8 | Pre-validation diagnostic console sample rows (`NITT-2025-*`), checking APAAR syntax and duplicate rules. |
| `initial_findings.csv` | `frontend/src/pages/DataQualityFindingsPage.tsx` | `INITIAL_FINDINGS` | 5 | In-depth student data quality exception items with root explanations and suggested corrective actions. |
| `mock_profiles.csv` | `frontend/src/pages/StudentRecordCertificatePage.tsx` | `MOCK_PROFILES` | 3 | Sovereign credential registry student cards with cryptographic verification references. |
| `mock_profile_audit_trail.csv`| `frontend/src/pages/StudentRecordCertificatePage.tsx` | `MOCK_PROFILES[key].auditTrail` | 8 | Relational audit log entries linked to `mock_profiles.csv` via `apaarId`. |
| `triage_cases.csv` | `frontend/src/pages/AicteCentralReviewPage.tsx` | `TRIAGE_CASES` | 3 | Cross-campus duplicate admission conflicts (e.g. NIT Trichy vs. VIT, COEP vs. SPIT) with match correlations. |
| `initial_audit_events.csv` | `frontend/src/pages/AuditLogsReportsPage.tsx` | `INITIAL_AUDIT_EVENTS` | 8 | Immutable sovereign ledger audit entries with cryptographic SHA-256 block hashes. |
| `initial_breach_records.csv` | `frontend/src/pages/AicteCentralReviewPage.tsx` | `INITIAL_BREACH_RECORDS` | 6 | Institutional intake threshold overage records across Indian colleges with statutory citations. |
| `role_datasets.csv` | `frontend/src/data/rolesData.ts` | `ROLE_DATASETS` | 5 | RBAC preset profiles (Admin, Operator, AICTE Reviewer, Verifier, Evaluator) with demo credentials. |

---

## Detailed Schema & Column Documentation

### 1. `department_data.csv`
* **Source:** `InstitutionDashboardPage.tsx` -> `DEPARTMENT_DATA`
* **Columns:**
  - `id`: Internal department key (`dept-cse`, `dept-ece`, etc.)
  - `code`: Approved program code (`BTECH-CSE-01`, etc.)
  - `name`: Full department name
  - `sanctioned`: AICTE approved intake capacity
  - `supernumerary`: Approved supernumerary seat quota
  - `actualRegular`: Actual admitted regular students
  - `actualSuper`: Actual admitted supernumerary students
  - `totalEnrolled`: Total enrolled (`actualRegular + actualSuper`)
  - `utilization`: Percentage seat utilization string
  - `hasViolation`: Boolean flag indicating ceiling breach
  - `excessCount`: Number of excess seats over approved cap (empty if no violation)
  - `statusText`: Visual indicator badge text (`Within Quota`, `Exceeded (+2)`, `At Capacity`)

### 2. `initial_diagnostics.csv`
* **Source:** `BulkImportValidationPage.tsx` -> `INITIAL_DIAGNOSTICS`
* **Columns:**
  - `row`: Source CSV row index
  - `studentId`: Institution roll number (`NITT-2025-014`, etc.)
  - `apaarId`: 12-digit APAAR or error placeholder (`[NULL / EMPTY]`, `[MALFORMED_REGEX]`)
  - `category`: Seat category (`REGULAR`, `EWS`, `TFW`, `NRI`, `SUPERNUMERARY`)
  - `status`: Diagnostic severity (`VALID`, `BLOCKING`, `DUPLICATE`, `WARNING`)
  - `note`: Diagnostic reason and rule code explanation

### 3. `initial_findings.csv`
* **Source:** `DataQualityFindingsPage.tsx` -> `INITIAL_FINDINGS`
* **Columns:**
  - `row`: Source file row number
  - `studentId`: Student registration number
  - `name`: Full student name
  - `branch`: Degree program
  - `rule`: Specific regulatory rule violated (`RULE-R6-MISSING-APAAR`, etc.)
  - `severity`: Finding severity (`BLOCKING`, `WARNING`, `RESOLVED`)
  - `field`: Target database field name
  - `explanation`: Detailed explanation of the compliance breach
  - `suggestedAction`: Recommended corrective action
  - `inputLabel`: Label for UI resolution input field
  - `inputHint`: Expected format guide
  - `placeholder`: Sample correction placeholder
  - `defaultVal`: Initial uncorrected value

### 4. `mock_profiles.csv` & `mock_profile_audit_trail.csv`
* **Source:** `StudentRecordCertificatePage.tsx` -> `MOCK_PROFILES`
* **Design:** Normalized relational representation to avoid loss of nested audit trail events.
* **`mock_profiles.csv` Columns:**
  - `apaarId`: Primary key (e.g. `9082-4412-8821`)
  - `instStudentId`: College roll number
  - `fullName`, `initials`, `institution`, `institutionCode`, `programme`, `faculty`, `batch`, `term`
  - `enrolmentStatus`: Active status string
  - `seatQuota`: Seat admission quota
  - `verificationStatus`, `verificationRef`, `verificationHash`, `signatureHash`, `signedDate`, `systemId`
  - `auditTrailJson`: Complete JSON-encoded array for lossless inline representation
* **`mock_profile_audit_trail.csv` Columns:**
  - `apaarId`: Foreign key to `mock_profiles.csv`
  - `auditOrder`: Sequential order of event
  - `timestamp`, `eventType`, `icon`, `iconColor`, `actor`, `actionDetails`, `complianceStatus`, `complianceBadgeClass`

### 5. `triage_cases.csv`
* **Source:** `AicteCentralReviewPage.tsx` -> `TRIAGE_CASES`
* **Columns:**
  - `id`: Triage case ID (`case-1`, `case-2`, `case-3`)
  - `ref`: Reference ticket (`XC-DUP-2025-9941`)
  - `apaarId`: Target student APAAR ID
  - `detectedAt`, `flagType`
  - `correlation_apaarMatch`, `correlation_dobMatch`, `correlation_fuzzyNameMatch`: Biometric match metrics
  - `instA_*` (code, name, location, type, studentName, program, timestamp, quota, tuitionFee, status, officer)
  - `instB_*` (code, name, location, type, studentName, program, timestamp, quota, tuitionFee, status, note)
  - `defaultJustification`: AICTE adjudication officer template statement

### 6. `initial_audit_events.csv`
* **Source:** `AuditLogsReportsPage.tsx` -> `INITIAL_AUDIT_EVENTS`
* **Columns:**
  - `id`: Event token (`EVT-2025-08914`)
  - `timestamp`, `category`, `subCategory`, `actor`, `actorOrg`, `actorIp`
  - `targetEntity`, `targetSub`, `targetDetail`, `outcome`, `notes`
  - `hashShort`: Display hash
  - `hashFull`: Complete SHA-256 block hash
  - `role`: Actor role category

### 7. `initial_breach_records.csv`
* **Source:** `AicteCentralReviewPage.tsx` -> `INITIAL_BREACH_RECORDS`
* **Columns:**
  - `pid`: Permanent AICTE institute code
  - `name`, `location`, `course`, `affiliation`
  - `cap`: Approved ceiling
  - `intake`: Actual reported intake
  - `excess`: Surplus count
  - `excessTag`: Excess label
  - `citation`: AICTE Approval Process Handbook (APH) clause
  - `citationDesc`: Regulatory explanation
  - `actionText`: Statutory notice status
  - `actionStyle`: Visual severity badge style
  - `state`: Geographic territory

### 8. `role_datasets.csv`
* **Source:** `frontend/src/data/rolesData.ts` -> `ROLE_DATASETS`
* **Columns:**
  - `key`: Role key (`admin`, `operator`, `reviewer`, `verifier`, `evaluator`)
  - `shortTitle`, `subtitle`, `icon`, `title`, `tag`, `tagClass`, `description`, `email`, `pid`, `pwd`

---

## Validation Procedure

To verify that all files are valid, present, match the stored SHA-256 checksums, and retain string identifiers:

```bash
python scripts/validate_hardcoded_demo_export.py
```
