# SIH 26263: APAAR-Based Student Data Management & Verification Platform

## Overview
This repository contains the backend and data platform for **SIH 26263**: an automated, role-aware **APAAR ID-based student data management and verification platform** developed for AICTE-approved institutions.

The platform enables institutions to ingest, validate, and monitor student-level enrollment records, detect cross-institution and within-batch duplicates, perform intake reconciliation against approved capacities, and maintain transparent, explainable audit trails.

---

## Architecture & Technology Stack

- **Framework**: Python 3.11+ / FastAPI
- **Data Validation & Schemas**: Pydantic v2
- **ORM & Persistence**: SQLAlchemy 2.0 / SQLite (dev) / PostgreSQL (production target)
- **Security**:
  - Salted password hashing via standard library PBKDF2-HMAC-SHA256 (100,000 iterations, 16-byte cryptographically secure random salt)
  - Signed JWT bearer tokens (PyJWT, HS256)
  - Server-side Role-Based Access Control (RBAC) and strict institution data isolation
- **Auditing**: Append-only operational audit logging (`audit_events`) capturing actor, action, object, outcome, and timestamp
- **Testing**: Pytest with FastAPI TestClient / HTTPX

---

## Repository Layout

```
SIH_26263/
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py               # FastAPI application, CORS, Request ID middleware, error handlers
│       ├── adapters/             # APAAR Provider Adapter Interface & Mock Adapter
│       │   ├── __init__.py
│       │   ├── base.py           # BaseApaarAdapter & VerificationResult contract
│       │   └── mock_apaar.py     # Labelled MockApaarAdapter (simulated outcomes & outage handling)
│       ├── core/
│       │   ├── config.py         # Application settings & environment configurations
│       │   ├── security.py       # PBKDF2 password hashing & JWT token operations
│       │   ├── permissions.py    # Server-side RBAC & institution boundary enforcement
│       │   └── errors.py         # Standardized error envelopes (code, message, request_id)
│       ├── models/               # SQLAlchemy 2.0 ORM models
│       │   ├── enums.py          # UserRole, EnrolmentStatus, SeatType, BatchStatus, etc.
│       │   ├── user.py           # User account entity
│       │   ├── institution.py    # Institution, Programme, ApprovedIntake entities
│       │   ├── student.py        # StudentRecord entity
│       │   ├── batch.py          # ImportBatch entity
│       │   ├── validation.py     # ValidationFinding entity
│       │   ├── match.py          # MatchCandidate entity
│       │   ├── verification.py   # VerificationAttempt entity
│       │   └── audit.py          # AuditEvent entity
│       ├── db/
│       │   └── session.py        # Database engine, sessionmaker, init_db, schema migrations
│       ├── schemas/              # Pydantic v2 schemas
│       │   ├── auth.py           # LoginRequest, UserRead, TokenResponse
│       │   ├── institution.py    # InstitutionRead, ProgrammeRead, ApprovedIntakeRead
│       │   ├── imports.py        # BatchRead, ImportPreviewResponse, etc.
│       │   ├── validation.py     # BatchValidationResponse, MatchCandidateRead
│       │   ├── workflows.py      # Submission, Review, and Dashboard metric schemas
│       │   └── common.py         # PaginatedList, HealthResponse, ErrorEnvelope
│       ├── services/             # Domain logic & engines
│       │   ├── import_parser.py  # RFC4180 CSV / XLSX streaming parser & sanitization
│       │   ├── import_service.py # Batch staging, column mapping, concurrency-safe versioning
│       │   ├── validation_service.py # Deterministic validation rules & intake reconciliation
│       │   ├── workflow_service.py   # Submission lifecycle, review decisions, dashboards
│       │   └── quality_service.py    # Transparent 4-dimensional data quality scoring
│       ├── api/
│       │   └── v1/
│       │       ├── router.py     # Master v1 APIRouter
│       │       ├── auth.py       # POST /api/v1/auth/login, GET /api/v1/auth/me, GET /api/v1/me
│       │       ├── institutions.py # GET /api/v1/institutions (scoped by institution)
│       │       ├── intake.py     # GET /api/v1/intake (scoped by institution)
│       │       ├── imports.py    # POST /imports/preview, POST /imports, GET /imports/template
│       │       ├── batches.py    # GET /batches, POST /validate, POST /submit, GET /quality
│       │       ├── reviews.py    # POST /reviews/{id}, POST /reviews/matches/{id}, GET /reviews/matches
│       │       ├── dashboard.py  # GET /dashboard/institution, GET /dashboard/aicte
│       │       ├── verification.py # GET /verification/{ref}, GET /verification/{ref}/certificate
│       │       ├── reports.py    # GET /reports/export (streaming CSV findings & quality summaries)
│       │       └── health.py     # GET /health, GET /api/v1/health
│       └── seed/
│           └── seed_data.py      # Idempotent synthetic database seeder
├── docs/
│   ├── API.md                    # Frozen v1 API contract & upcoming endpoints
│   ├── DATA_DICTIONARY.md        # Data models, field constraints, enums & rule catalog
│   └── DEMO_SCRIPT.md            # Step-by-step SIH demonstration workflow
└── tests/
    ├── test_phase1_backend.py    # Phase 1: Authentication, RBAC, Institution Scoping
    ├── test_phase2_imports.py    # Phase 2: CSV/XLSX Ingestion, Lineage, Parser Sanitization
    ├── test_phase3_validation.py # Phase 3: Intake Reconciliation, Rule Engine, Duplicates
    ├── test_phase4_concurrency.py# Phase 4 Batch 1: Concurrency Hardening & Symmetric Pairs
    ├── test_phase4_batch2.py     # Phase 4 Batch 2: Submission, Review Workflows, Dashboards
    ├── test_phase5_integration.py# Phase 5: Verification Adapter, Quality Scoring, CSV Export
    └── test_phase6_hardening.py  # Phase 6: End-to-End Workflow & Release Verification
```


---

## Role-Based Access Control & Institution Scoping

Access control is enforced strictly on the server side:

| Role | Permitted Actions | Restrictions |
|---|---|---|
| **`AICTE_ADMIN`** | View national monitoring summaries, list all institutions, query all intakes, inspect exceptions | Cannot modify institutional records directly without audit |
| **`INSTITUTION_ADMIN`** | Manage own institution profile, query own intake, review own student batches | Strictly restricted to own `institution_id`; access to other institutions returns `403 INSTITUTION_SCOPE_VIOLATION` |
| **`INSTITUTION_OPERATOR`** | Import data batches, preview records, inspect findings | Same institution boundaries; cannot alter administrative settings |
| **`DEMO_ADMIN`** | Reset seed data and configure evaluation demonstrations | National oversight; clear demo labelling |

---

## Preconfigured Seed Accounts

All demo accounts are preconfigured with password: `DemoPassword@2026`

| Role | Email | Institution Scope | Name |
|---|---|---|---|
| `AICTE_ADMIN` | `aicte_admin@aicte.gov.in` | National (All Institutions) | AICTE National Reviewer |
| `INSTITUTION_ADMIN` | `apex_admin@apex.edu.in` | `INST-001` (Apex Institute of Tech) | Apex Institution Admin |
| `INSTITUTION_OPERATOR` | `apex_operator@apex.edu.in` | `INST-001` (Apex Institute of Tech) | Apex Ingestion Operator |
| `INSTITUTION_ADMIN` | `bharat_admin@bharat.edu.in` | `INST-002` (Bharat Eng College) | Bharat Institution Admin |
| `DEMO_ADMIN` | `demo_admin@apaar.gov.in` | National Scope | Hackathon Demonstration Lead |

---

## Quickstart & Commands

### 1. Initialize and Seed the Database
```powershell
python -m backend.app.seed.seed_data --reset
```

### 2. Run the Automated Test Suite
```powershell
python -m pytest -v
```

### 3. Start the Backend API Server
```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running, access:
- **Swagger Interactive API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Contract**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## API Error Handling

All non-2xx API errors return a standardized JSON error envelope:

```json
{
  "error": {
    "code": "INSTITUTION_SCOPE_VIOLATION",
    "message": "Cross-institution access denied. Caller bound to 'INST-001' cannot access records of 'INST-002'.",
    "details": null,
    "request_id": "req-8b6fa201"
  }
}
```

Every response includes an `X-Request-ID` header for end-to-end audit traceability.
