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
│       │   └── session.py        # Database engine, sessionmaker, init_db
│       ├── schemas/              # Pydantic v2 schemas
│       │   ├── auth.py           # LoginRequest, UserRead, TokenResponse
│       │   ├── institution.py    # InstitutionRead, ProgrammeRead, ApprovedIntakeRead
│       │   └── common.py         # PaginatedList, HealthResponse, ErrorEnvelope
│       ├── api/
│       │   └── v1/
│       │       ├── router.py     # Master v1 APIRouter
│       │       ├── auth.py       # POST /api/v1/auth/login, GET /api/v1/auth/me
│       │       ├── institutions.py # GET /api/v1/institutions (scoped by institution)
│       │       ├── intake.py     # GET /api/v1/intake (scoped by institution)
│       │       └── health.py     # GET /health, GET /api/v1/health
│       └── seed/
│           └── seed_data.py      # Idempotent synthetic database seeder
├── docs/
│   ├── API.md                    # Frozen v1 API contract & upcoming endpoints
│   └── DATA_DICTIONARY.md        # Data models, field constraints, enums & rule catalog
└── tests/
    └── test_phase1_backend.py    # Automated test suite (21 tests)
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
