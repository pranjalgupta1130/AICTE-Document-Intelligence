# VeriReg AI — Member 1: Document Intelligence & Validation

## Overview
This module implements **Member 1: Document Intelligence & Validation** for VeriReg AI. It provides an explainable, deterministic document extraction, regulatory compliance verification, duplicate detection, signature inspection, and risk stratification engine designed to integrate cleanly with Member 2’s backend.

---

## Architecture & Modules

```
verireg/
├── __init__.py               # Public API exports
├── schemas.py                # Stable Pydantic v2 JSON contracts
├── extractor.py              # PDF parsing, metadata, bounding box coordinates, and perceptual dHash
├── field_extraction.py       # Grounded structured field extraction with verbatim evidence
├── signatures.py             # PDF CMS / PKCS#7 /Sig digital signature inspection
├── rules_engine.py           # Configurable AICTE Approval Process Handbook (APH) regulatory rules
├── consistency.py            # Cross-document consistency & entity reconciliation
├── duplicate_detector.py     # SHA-256 exact & perceptual image duplicate detection
├── risk_scoring.py           # Anomaly risk score calculation & 3-tier workflow routing
├── pipeline.py               # End-to-end pipeline orchestrator
├── api.py                    # Ready-to-mount FastAPI APIRouter for Member 2
└── synthetic_docs.py         # Synthetic PDF generator for automated testing
```

---

## Member 2 Backend Integration Contract

Member 2 can integrate Member 1 via Python module or via FastAPI:

### 1. Python Direct Integration

```python
from verireg import DocumentIntelligencePipeline

pipeline = DocumentIntelligencePipeline()

# Process an entire application filing (multiple PDFs):
result = pipeline.process_application(
    application_id="APP-2026-001",
    document_paths=["/path/to/land_title.pdf", "/path/to/building_plan.pdf"]
)

# Access JSON-serializable Pydantic model
print(result.risk_tier)  # ACCELERATED | CLARIFICATION | ESCALATION
print(result.risk_score) # 0.0 - 100.0
print(result.model_dump())
```

### 2. FastAPI Mount Integration

```python
from fastapi import FastAPI
from verireg.api import router as member1_router

app = FastAPI()
app.include_router(member1_router, prefix="/api/v1/member1")
```

#### Available Endpoints:
- `POST /api/v1/member1/process-document`: Ingests a single PDF and returns document metadata, pages, extracted fields grounded with bounding boxes, and digital signature status.
- `POST /api/v1/member1/process-application`: Ingests an `application_id` and a batch of multipart PDF files; executes extraction, statutory rule verification, cross-document reconciliation, duplicate detection, and risk tier prioritization.

---

## Regulatory Rules & Statutory Provenance

In accordance with the project specification audit, all rules declare whether their numerical threshold is authoritatively verified or an unverified configurable benchmark:

| Rule ID | Standard / Threshold | Category | Provenance Status | Deficient Action |
|---|---|---|---|---|
| `RULE-LAND-001` | `>= 2.50 Acres` (Configured default) | Land | **Unverified Benchmark** (Location dependent in APH) | DEFICIENCY |
| `RULE-ARCH-002` | `>= 4000.0 Sqm` Carpet Area | Building | **Unverified Benchmark** (Intake dependent in APH) | DEFICIENCY |
| `RULE-FIN-003` | `>= INR 1,500,000.00` Joint FDR | FDR | **Unverified Benchmark** (Program dependent in APH) | DEFICIENCY |
| `RULE-FIRE-004` | Active Fire & Life Safety NOC | FireSafety | **Authoritatively Verified** (AICTE Statutory Mandate) | CRITICAL |
| `RULE-ACAD-005` | `<= 20.0:1` Student-Faculty Ratio | Faculty | **Authoritatively Verified** (AICTE Handbook Mandate) | DEFICIENCY |
| `RULE-AUTH-006` | Valid PKCS#7 / CMS Digital Signature | Authentication | **Authoritatively Verified** (AICTE IT Guidelines) | CRITICAL / INDETERMINATE |

---

## Digital Signature Inspection Architecture

Digital signatures are inspected across four separate, genuine verification levels without fabricated claims:
1. **Signature Detection (`signatures_detected`)**: Checks PDF document catalog, form widgets, and internal `/Sig` dictionary xrefs.
2. **Byte-Range Integrity (`integrity_verified`)**: Evaluates byte-range hash digests. Explicitly marked `None` / unverified if external cryptographic engines (pyHanko) are not configured.
3. **Certificate Chain Trust (`certificate_chain_trusted`)**: Checks validation up to a Root CA. Explicitly marked `None` / unverified when no local trust store is configured.
4. **Signer Identity (`signer_identity`)**: Captures signer Common Name / DN from certificate dictionary.

---

## Risk Scoring, Explainability & Non-Forgery Notice

- Every point in `risk_score` (0.0 to 100.0) is transparently traceable in `findings_audit_trail`.
- **Statutory Non-Forgery Notice**: Every pipeline run outputs an explicit legal notice stating that risk scores and rule findings are algorithmic prioritization observations to guide human scrutiny, and do not constitute proof of fraud or forgery, nor automatic grounds for rejection.

---

## Workflow Risk Tiers

- **`ACCELERATED` (Score 0 – 20)**: All statutory rules satisfied, no cryptographic anomalies, no duplicate assets detected. Eligible for fast-track clearance.
- **`CLARIFICATION` (Score 21 – 60)**: Minor clerical discrepancies or indeterminate non-critical parameters. Automated deficiency memo generated for 14-day institutional response.
- **`ESCALATION` (Score 61 – 100)**: Major statutory deficit (sub-standard land, invalid/missing fire NOC, altered documents, duplicate campus photos). Routed to Standing Hearing Committee (SHC) and Expert Visit Committee (EVC).

---

## Automated Test Suite

Run all tests:
```powershell
python -m pytest tests/test_member1.py -v
```
All 8 test suites pass deterministically using synthetic test documents.
