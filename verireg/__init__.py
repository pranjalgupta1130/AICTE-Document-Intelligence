"""VeriReg AI - Member 1: Document Intelligence & Validation Module.
Defines public API and schema exports for Member 2 integration.
"""

from .schemas import (
    BoundingBox,
    EvidenceAnnotation,
    ExtractedField,
    DocumentMetadata,
    PageExtraction,
    DocumentAnalysisResult,
    DigitalSignatureInfo,
    RegulatoryCheckResult,
    CrossDocConsistencyResult,
    DuplicateDetectionResult,
    PipelineRunResult,
    RiskTier,
    SeverityLevel,
)
from .pipeline import DocumentIntelligencePipeline

__all__ = [
    "BoundingBox",
    "EvidenceAnnotation",
    "ExtractedField",
    "DocumentMetadata",
    "PageExtraction",
    "DocumentAnalysisResult",
    "DigitalSignatureInfo",
    "RegulatoryCheckResult",
    "CrossDocConsistencyResult",
    "DuplicateDetectionResult",
    "PipelineRunResult",
    "RiskTier",
    "SeverityLevel",
    "DocumentIntelligencePipeline",
]
