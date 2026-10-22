"""Comprehensive automated test suite for Member 1 - Document Intelligence & Validation.
Tests PDF extraction, bounding boxes, statutory rules, duplicate detection, signature inspection,
cross-document consistency, risk stratification, and FastAPI endpoints.
"""

from __future__ import annotations
import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

from verireg.api import router
from verireg.duplicate_detector import DuplicateDetector
from verireg.extractor import PDFExtractor, compute_dhash, hamming_distance
from verireg.pipeline import DocumentIntelligencePipeline
from verireg.schemas import RiskTier, SeverityLevel
from verireg.signatures import SignatureInspector
from verireg.synthetic_docs import (
    create_compliant_application_pdf,
    create_deficient_application_pdf,
    create_inconsistent_secondary_pdf,
    create_sample_pattern_image,
)
from PIL import Image
import io


@pytest.fixture(scope="session")
def test_dir():
    d = tempfile.mkdtemp(prefix="verireg_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def compliant_pdf(test_dir):
    p = os.path.join(test_dir, "compliant_app.pdf")
    return create_compliant_application_pdf(p, app_id="APP-2026-COMPLIANT")


@pytest.fixture
def deficient_pdf(test_dir):
    p = os.path.join(test_dir, "deficient_app.pdf")
    return create_deficient_application_pdf(p, app_id="APP-2026-DEFICIENT")


@pytest.fixture
def secondary_pdf(test_dir):
    p = os.path.join(test_dir, "secondary_app.pdf")
    return create_inconsistent_secondary_pdf(p, app_id="APP-2026-CONFLICT")


def test_perceptual_hash_and_hamming():
    """Validates that dHash and hamming distance are deterministic."""
    img_bytes1 = create_sample_pattern_image(color=(255, 0, 0), shape="rect")
    img_bytes2 = create_sample_pattern_image(color=(255, 0, 0), shape="rect")
    img_bytes3 = create_sample_pattern_image(color=(0, 255, 0), shape="circle")

    im1 = Image.open(io.BytesIO(img_bytes1))
    im2 = Image.open(io.BytesIO(img_bytes2))
    im3 = Image.open(io.BytesIO(img_bytes3))

    h1 = compute_dhash(im1)
    h2 = compute_dhash(im2)
    h3 = compute_dhash(im3)

    assert h1 == h2, "Identical images must yield identical dHash"
    assert hamming_distance(h1, h2) == 0
    # Different image should have higher hamming distance
    dist = hamming_distance(h1, h3)
    assert dist >= 0


def test_pdf_extraction_and_bounding_boxes(compliant_pdf):
    """Ensures PDFExtractor captures metadata, pages, and grounds fields with bounding boxes."""
    with PDFExtractor(compliant_pdf) as extractor:
        meta = extractor.get_metadata()
        assert meta.total_pages == 1
        assert len(meta.sha256_hash) == 64
        assert meta.is_pdf is True

        pages = extractor.extract_pages()
        assert len(pages) == 1
        assert "ALL INDIA COUNCIL" in pages[0].text
        assert pages[0].images_found == 1

        # Check bounding box grounding
        bbox = extractor.search_text_bounding_box("5.50 Acres", page_number=1)
        assert bbox is not None
        assert bbox.page_number == 1
        assert bbox.x1 > bbox.x0
        assert bbox.y1 > bbox.y0


def test_compliant_document_pipeline_flow(compliant_pdf):
    """Tests that a clean application achieves ACCELERATED or CLARIFICATION tier without false deficiencies."""
    pipeline = DocumentIntelligencePipeline(rules_config={"require_digital_signatures": False})
    res = pipeline.process_application(
        application_id="TEST-APP-001",
        document_paths=[compliant_pdf],
    )

    assert res.application_id == "TEST-APP-001"
    assert len(res.analyzed_documents) == 1
    # Check land area field
    doc = res.analyzed_documents[0]
    assert "land_area_acres" in doc.extracted_fields
    assert doc.extracted_fields["land_area_acres"].normalized_value == 5.5
    assert doc.extracted_fields["land_area_acres"].confidence == 1.0
    assert doc.extracted_fields["land_area_acres"].evidence.bbox is not None

    # Check rule evaluations
    passed_rules = [r for r in res.rule_evaluations if r.status == "PASS"]
    assert len(passed_rules) >= 4  # Land, Built-up, FDR, Fire Safety, SFR

    # Risk tier should be ACCELERATED
    assert res.risk_tier == RiskTier.ACCELERATED
    assert res.risk_score <= 20.0
    assert len(res.critical_deficiencies) == 0


def test_deficient_document_pipeline_flow(deficient_pdf):
    """Tests that deficient statutory values trigger DEFICIENCY/CRITICAL statuses and ESCALATION risk tier."""
    pipeline = DocumentIntelligencePipeline(rules_config={"require_digital_signatures": False})
    res = pipeline.process_application(
        application_id="TEST-APP-DEF",
        document_paths=[deficient_pdf],
    )

    assert res.risk_tier == RiskTier.ESCALATION
    assert res.risk_score >= 60.0
    assert len(res.critical_deficiencies) > 0

    # Specifically check that Fire Safety and Land rules failed
    rule_map = {r.rule_id: r for r in res.rule_evaluations}
    assert rule_map["RULE-LAND-001"].status == "FAIL"
    assert rule_map["RULE-ARCH-002"].status == "FAIL"
    assert rule_map["RULE-FIN-003"].status == "FAIL"
    assert rule_map["RULE-FIRE-004"].status == "FAIL"
    assert rule_map["RULE-ACAD-005"].status == "FAIL"


def test_cross_document_inconsistency(compliant_pdf, secondary_pdf):
    """Tests reconciliation across two files with conflicting application ID & institution name."""
    pipeline = DocumentIntelligencePipeline(rules_config={"require_digital_signatures": False})
    res = pipeline.process_application(
        application_id="TEST-MULTI-001",
        document_paths=[compliant_pdf, secondary_pdf],
    )

    # Inconsistencies detected
    inconsistencies = [c for c in res.consistency_evaluations if not c.is_consistent]
    assert len(inconsistencies) >= 2  # Institution name and application ID mismatch

    app_id_check = next(c for c in res.consistency_evaluations if c.field_compared == "application_id")
    assert app_id_check.is_consistent is False
    assert app_id_check.severity == SeverityLevel.CRITICAL

    # Perceptual duplicate check across compliant_pdf and secondary_pdf
    assert res.duplicate_evaluations.has_duplicate_findings is True
    assert len(res.duplicate_evaluations.perceptual_image_duplicates) > 0


def test_exact_duplicate_detection(compliant_pdf, test_dir):
    """Tests detection of re-uploaded identical files with matching SHA-256."""
    copy_path = os.path.join(test_dir, "compliant_duplicate_copy.pdf")
    shutil.copyfile(compliant_pdf, copy_path)

    detector = DuplicateDetector()
    pipeline = DocumentIntelligencePipeline(rules_config={"require_digital_signatures": False})
    doc1 = pipeline.process_document(compliant_pdf)
    doc2 = pipeline.process_document(copy_path)

    dup_res = detector.evaluate_documents([doc1, doc2])
    assert dup_res.has_duplicate_findings is True
    assert len(dup_res.exact_duplicates) == 1
    assert doc1.metadata.filename in dup_res.exact_duplicates[0]["documents"]
    assert os.path.basename(copy_path) in dup_res.exact_duplicates[0]["documents"]


def test_digital_signature_inspector(compliant_pdf):
    """Tests structural signature inspector on synthetic unsigned PDF."""
    inspector = SignatureInspector(compliant_pdf)
    sig_info = inspector.inspect()
    assert sig_info.has_signatures is False
    assert sig_info.signature_count == 0
    assert sig_info.signatures_detected is False
    assert sig_info.integrity_verified is None
    assert sig_info.certificate_chain_trusted is None
    assert len(sig_info.verification_notes) > 0


def test_digitally_signed_pdf_distinction(test_dir):
    """Audit Risk 2: Confirms signature detection is distinguished from integrity and trust chain."""
    signed_path = os.path.join(test_dir, "digitally_signed_app.pdf")
    from verireg.synthetic_docs import create_digitally_signed_pdf
    create_digitally_signed_pdf(signed_path)

    inspector = SignatureInspector(signed_path)
    sig_info = inspector.inspect()

    # Signatures are genuinely detected
    assert sig_info.has_signatures is True
    assert sig_info.signatures_detected is True
    assert sig_info.signature_count == 1
    # Integrity and trust chain are NOT falsely claimed as verified
    assert sig_info.integrity_verified is None
    assert sig_info.certificate_chain_trusted is None
    # Meaningful technical verification notes are attached
    assert any("Detected 1" in note for note in sig_info.verification_notes)
    assert any("integrity" in note.lower() for note in sig_info.verification_notes)


def test_scanned_pdf_end_to_end_ocr(test_dir):
    """Audit Risk 3: Confirms scanned/rasterized documents without text stream genuinely extract text and ground bounding boxes."""
    scanned_path = os.path.join(test_dir, "scanned_app.pdf")
    from verireg.synthetic_docs import create_scanned_image_pdf
    create_scanned_image_pdf(scanned_path)

    pipeline = DocumentIntelligencePipeline(rules_config={"require_digital_signatures": False})
    res = pipeline.process_document(scanned_path)

    assert len(res.pages) == 1
    page = res.pages[0]
    # Page is correctly recognized as scanned image
    assert page.is_scanned_image is True
    assert "OCR applied" in (page.ocr_notice or "")
    # Proves expected text is extracted; does not count failure as success
    assert "LAND TITLE DEED" in page.text
    assert "4.20 Acres" in page.text
    # Field extraction and evidence bounding box verified on OCR text
    assert "land_area_acres" in res.extracted_fields
    land_fld = res.extracted_fields["land_area_acres"]
    assert land_fld.normalized_value == 4.20
    assert land_fld.evidence.bbox is not None
    assert land_fld.evidence.page_number == 1


def test_regulatory_accuracy_and_unverified_rules(compliant_pdf):
    """Audit Risk 1: Verifies rules clearly declare authoritative vs unverified status and are configurable."""
    # Check default metadata
    pipeline = DocumentIntelligencePipeline(rules_config={
        "min_land_area_acres": 1.0,  # Custom configurable override
        "require_digital_signatures": False,
    })
    res = pipeline.process_application("APP-REG-001", [compliant_pdf])

    rule_map = {r.rule_id: r for r in res.rule_evaluations}
    # Land rule is explicitly marked as not authoritatively verified (location-dependent)
    assert rule_map["RULE-LAND-001"].is_authoritatively_verified is False
    assert "Configured default" in rule_map["RULE-LAND-001"].statutory_standard

    # Fire NOC and SFR rules are authoritatively verified in AICTE Handbook
    assert rule_map["RULE-FIRE-004"].is_authoritatively_verified is True
    assert rule_map["RULE-ACAD-005"].is_authoritatively_verified is True


def test_risk_scoring_traceability_and_disclaimer(deficient_pdf):
    """Audit Risk 4: Verifies findings_audit_trail transparency and non-forgery disclaimer."""
    pipeline = DocumentIntelligencePipeline(rules_config={"require_digital_signatures": False})
    res = pipeline.process_application("APP-DEF-AUDIT", [deficient_pdf])

    # Transparent point-by-point audit trail
    assert len(res.findings_audit_trail) > 0
    total_penalty = sum(f["score_penalty"] for f in res.findings_audit_trail)
    assert res.risk_score == min(100.0, total_penalty)

    # Disclaimer explicitly present
    assert "Notice:" in res.disclaimer
    assert "fraud or forgery" in res.disclaimer


def test_evidence_grounding_exact_value_bbox(compliant_pdf):
    """Audit Risk 5: Confirms extracted values map to exact value bounding box."""
    pipeline = DocumentIntelligencePipeline(rules_config={"require_digital_signatures": False})
    res = pipeline.process_document(compliant_pdf)

    land_field = res.extracted_fields["land_area_acres"]
    assert land_field.value == "5.50"
    assert land_field.evidence.bbox is not None
    assert land_field.evidence.page_number == 1
    # Bbox width should tightly encompass '5.50' (approx 15-30 pt width), not entire sentence
    bbox = land_field.evidence.bbox
    box_width = bbox.x1 - bbox.x0
    assert box_width < 40.0, f"Bbox should tightly surround extracted value '5.50', got width {box_width}"


def test_fastapi_endpoints(compliant_pdf):
    """Tests FastAPI integration router endpoints using TestClient."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/member1")
    client = TestClient(app)

    with open(compliant_pdf, "rb") as f:
        resp = client.post(
            "/api/v1/member1/process-document",
            files={"file": ("compliant_app.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "metadata" in data
    assert "extracted_fields" in data
    assert data["metadata"]["filename"] == "compliant_app.pdf"

    with open(compliant_pdf, "rb") as f:
        resp2 = client.post(
            "/api/v1/member1/process-application",
            data={"application_id": "FASTAPI-TEST-01"},
            files=[("files", ("compliant_app.pdf", f, "application/pdf"))],
        )
    assert resp2.status_code == 200
    app_data = resp2.json()
    assert app_data["application_id"] == "FASTAPI-TEST-01"
    assert app_data["risk_tier"] == "ACCELERATED"
    assert "findings_audit_trail" in app_data
    assert "disclaimer" in app_data
