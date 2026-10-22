"""Pydantic data schemas representing the stable JSON contract for VeriReg AI Member 1.
Cleanly integrates with Member 2 (FastAPI / backend).
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    DEFICIENCY = "DEFICIENCY"
    CRITICAL = "CRITICAL"


class RiskTier(str, Enum):
    ACCELERATED = "ACCELERATED"          # Fast-track path (all checks pass)
    CLARIFICATION = "CLARIFICATION"      # Minor variances or missing non-critical items
    ESCALATION = "ESCALATION"            # High risk: duplicate detected, sig invalid, major statutory failure


class BoundingBox(BaseModel):
    x0: float = Field(..., description="Top-left X coordinate in points (72 dpi)")
    y0: float = Field(..., description="Top-left Y coordinate in points (72 dpi)")
    x1: float = Field(..., description="Bottom-right X coordinate in points")
    y1: float = Field(..., description="Bottom-right Y coordinate in points")
    page_number: int = Field(..., ge=1, description="1-indexed page number")


class EvidenceAnnotation(BaseModel):
    page_number: int = Field(..., ge=1)
    bbox: Optional[BoundingBox] = None
    snippet: str = Field(..., description="Exact verbatim text snippet extracted from source document")
    source_document: str = Field(..., description="File name or document identifier")


class ExtractedField(BaseModel):
    field_name: str
    value: Any
    raw_text: str
    normalized_value: Optional[Any] = None
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Deterministic extraction confidence based on OCR score or regex match exactness. Never fabricated.",
    )
    evidence: EvidenceAnnotation


class DocumentMetadata(BaseModel):
    filename: str
    sha256_hash: str
    total_pages: int
    file_size_bytes: int
    is_pdf: bool
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None


class PageExtraction(BaseModel):
    page_number: int
    text: str
    word_count: int
    tables_found: int = 0
    images_found: int = 0
    is_scanned_image: bool = False
    ocr_notice: Optional[str] = None
    image_perceptual_hashes: List[str] = Field(default_factory=list)


class DigitalSignatureInfo(BaseModel):
    has_signatures: bool = False
    signature_count: int = 0
    signatures_detected: bool = False
    integrity_verified: Optional[bool] = Field(
        None,
        description="Whether byte-range cryptographic hash could be verified. None if cryptographic validation is unperformed or unsupported."
    )
    certificate_chain_trusted: Optional[bool] = Field(
        None,
        description="Whether X.509 certificate chains up to a trusted Root CA. None if local trust store is not configured."
    )
    signer_identity: Optional[str] = Field(
        None,
        description="Signer common name or certificate subject identified from signature dictionary."
    )
    signatures: List[Dict[str, Any]] = Field(default_factory=list)
    certificate_details: List[Dict[str, Any]] = Field(default_factory=list)
    verification_notes: List[str] = Field(
        default_factory=list,
        description="Explicit technical notes on what could and could not be verified."
    )
    anomalies: List[str] = Field(default_factory=list)


class DuplicateDetectionResult(BaseModel):
    exact_duplicates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of identical files matching SHA-256 hash across documents"
    )
    perceptual_image_duplicates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Matches where embedded raster images have a Hamming distance within threshold"
    )
    has_duplicate_findings: bool = False


class RegulatoryCheckResult(BaseModel):
    rule_id: str
    rule_name: str
    rule_category: str  # Land, Building, FireSafety, FDR, Faculty
    status: str  # "PASS", "FAIL", "INDETERMINATE"
    severity: SeverityLevel
    statutory_standard: str
    is_authoritatively_verified: bool = Field(
        False,
        description="Whether this threshold is authoritatively verified in the statutory handbook or is an unverified user-configurable benchmark.",
    )
    observed_value: Any
    difference: Optional[str] = None
    deficiency_reason: Optional[str] = None
    evidence: List[EvidenceAnnotation] = Field(default_factory=list)


class CrossDocConsistencyResult(BaseModel):
    check_name: str
    field_compared: str
    is_consistent: bool
    discrepancy_details: Optional[str] = None
    severity: SeverityLevel
    documents_involved: List[str]
    evidences: List[EvidenceAnnotation] = Field(default_factory=list)


class DocumentAnalysisResult(BaseModel):
    metadata: DocumentMetadata
    pages: List[PageExtraction]
    extracted_fields: Dict[str, ExtractedField]
    signatures: DigitalSignatureInfo


class PipelineRunResult(BaseModel):
    application_id: str
    analyzed_documents: List[DocumentAnalysisResult]
    rule_evaluations: List[RegulatoryCheckResult]
    consistency_evaluations: List[CrossDocConsistencyResult]
    duplicate_evaluations: DuplicateDetectionResult
    risk_tier: RiskTier
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk anomaly score from 0.0 (clean) to 100.0 (high review priority)")
    findings_audit_trail: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Transparent breakdown showing the exact points contributed by each detected finding to the total risk score.",
    )
    critical_deficiencies: List[str] = Field(default_factory=list)
    clarification_notes: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="Notice: Risk scores, duplicate detections, and rule findings are algorithmic triage observations to prioritize human committee review. They do not constitute proof of fraud or forgery, nor automatic grounds for legal rejection.",
        description="Statutory legal and non-forgery disclaimer.",
    )
