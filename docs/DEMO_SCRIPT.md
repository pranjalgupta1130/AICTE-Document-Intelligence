# SIH 26263: Live Demonstration Script & Evaluator Guide

## Overview
This document guides evaluators, judges, and developers through a complete, reproducible walk-through of the **APAAR ID-Based Student Data Management & Verification Platform** (SIH 26263).

All demo records are synthetic and pre-configured. Mock verification is explicitly labelled as simulated.

---

## 1. Preconfigured Demo Accounts

All accounts use the password: `DemoPassword@2026`

| Role | Email | Institution Scope | Purpose in Demo |
|---|---|---|---|
| **AICTE Admin** | `aicte_admin@aicte.gov.in` | National (All Institutions) | Central monitoring, cross-institution duplicate review, national analytics |
| **Institution Admin** | `apex_admin@apex.edu.in` | `INST-001` (Apex Institute) | Intake review, batch submission, quality scoring, finding resolution |
| **Institution Operator** | `apex_operator@apex.edu.in` | `INST-001` (Apex Institute) | CSV/XLSX upload, preview, validation execution |
| **Bharat Admin** | `bharat_admin@bharat.edu.in` | `INST-002` (Bharat Eng College) | Demonstrating strict cross-tenant boundary isolation |
| **Demo Admin** | `demo_admin@apaar.gov.in` | National Scope | Demonstration management and synthetic resets |

---

## 2. End-to-End Workflow Demonstration

### Step 1: Health Check & System Readiness
- **Endpoint**: `GET /health`
- **Verification**: Confirms API liveness and database connectivity (`status: "healthy"`).

### Step 2: Role Authentication
- **Endpoint**: `POST /api/v1/auth/login`
- **Action**: Authenticate as `apex_operator@apex.edu.in`.
- **Outcome**: Returns Bearer JWT and user profile scoped strictly to `INST-001`.

### Step 3: Template Download & Data Ingestion
- **Endpoint**: `GET /api/v1/imports/template?format=csv`
- **Endpoint**: `POST /api/v1/imports/preview` (verify column mapping and pre-import validation).
- **Endpoint**: `POST /api/v1/imports` (commit CSV batch).
- **Outcome**: Batch created in `DRAFT` status with monotonic versioning and audit record.

### Step 4: Deterministic Validation & Intake Reconciliation
- **Endpoint**: `POST /api/v1/batches/{batch_id}/validate`
- **Engine Execution**:
  - Syntactic checks (12-digit numeric APAAR + Verhoeff checksum algorithm).
  - Exact duplicates and cross-institution duplicate detection.
  - Category and quota consistency checks.
  - Cumulative intake reconciliation against approved AICTE capacity limits.
- **Outcome**: Batch status set to `VALIDATED` (or `NEEDS_CORRECTION` if blocking errors exist).

### Step 5: Explainable Findings & Human Review
- **Endpoint**: `GET /api/v1/batches/{batch_id}/findings` (traceable to row, field, rule code, and suggested action).
- **Endpoint**: `POST /api/v1/reviews/{finding_id}` (resolve or dismiss findings with mandatory audit reasoning).
- **Outcome**: Resolving blocking findings decrements `batch.error_rows` and transitions batch to `VALIDATED`.

### Step 6: Transparent Data-Quality Scoring
- **Endpoint**: `GET /api/v1/batches/{batch_id}/quality`
- **Outcome**: Returns explainable 0–100 score across 4 documented dimensions:
  - Completeness (25%)
  - Validity (30%)
  - Consistency (25%)
  - Uniqueness (20%)
  - Framed strictly as dataset hygiene (not a fraud score).

### Step 7: Formally Lock & Submit Batch
- **Endpoint**: `POST /api/v1/batches/{batch_id}/submit`
- **Outcome**: Transitions batch to `SUBMITTED`, locks data, and records `AuditEvent` (`BATCH_SUBMIT`).

### Step 8: Operational & National Dashboards
- **Institution Dashboard**: `GET /api/v1/dashboard/institution` (intake usage %, batch status, recent activity).
- **AICTE Central Dashboard**: `GET /api/v1/dashboard/aicte` (national enrolled students, approved intake, open exceptions, duplicate breakdown).

### Step 9: Cross-Institution Duplicate Adjudication
- **Endpoint**: `GET /api/v1/reviews/matches` (list cross-institution duplicate candidates).
- **Endpoint**: `POST /api/v1/reviews/matches/{match_id}` (AICTE reviewer records decision; records remain separate, never auto-merged).

### Step 10: Privacy-Preserving Verification & Degree Certificate Preview
- **Verification Lookup**: `GET /api/v1/verification/{student_ref}` (returns `MOCK_VERIFIED` with `is_official=False`).
- **Certificate Preview**: `GET /api/v1/verification/{student_ref}/certificate` (renders student ID alongside APAAR ID for degree-awarding bodies).

### Step 11: Actionable CSV Report Export
- **Endpoint**: `GET /api/v1/reports/export?report_type=findings` (streaming row-level issues).
- **Endpoint**: `GET /api/v1/reports/export?report_type=quality_summary` (batch-level quality metrics).

---

## 3. Security & Isolation Verification Scenarios

| Test Scenario | Evaluator Action | Expected System Response |
|---|---|---|
| **Cross-Tenant Access** | Apex user requests Bharat's batch or intake | HTTP `403 INSTITUTION_SCOPE_VIOLATION` |
| **Role Escalation** | Operator attempts to submit batch | HTTP `403 PERMISSION_DENIED` |
| **Unauthorized Export** | External Verifier requests bulk CSV export | HTTP `403 PERMISSION_DENIED` |
| **Provider Resilience** | Verification request with `simulate_outage=True` | Returns `MOCK_UNAVAILABLE` gracefully; does not crash |
| **Audit Immutability** | Inspect audit trail after any mutation | All events captured in `audit_events` with actor, action, timestamp |
