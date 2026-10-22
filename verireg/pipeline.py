"""End-to-end Document Intelligence & Validation Pipeline orchestrator.
Coordinates extraction, signature inspection, rule checks, duplicate analysis, and risk scoring.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from .consistency import CrossDocumentConsistencyEngine
from .duplicate_detector import DuplicateDetector
from .extractor import PDFExtractor
from .field_extraction import FieldExtractor
from .risk_scoring import RiskPrioritizationEngine
from .rules_engine import RegulatoryRulesEngine
from .schemas import (
    DocumentAnalysisResult,
    EvidenceAnnotation,
    PipelineRunResult,
)
from .signatures import SignatureInspector


class DocumentIntelligencePipeline:
    """Main pipeline class providing a single, robust entry point for Member 2 backend."""

    def __init__(self, rules_config: Optional[Dict[str, Any]] = None, hamming_threshold: int = 5):
        self.rules_engine = RegulatoryRulesEngine(config=rules_config)
        self.consistency_engine = CrossDocumentConsistencyEngine()
        self.duplicate_detector = DuplicateDetector(hamming_threshold=hamming_threshold)
        self.risk_engine = RiskPrioritizationEngine()

    def process_document(self, file_path: str) -> DocumentAnalysisResult:
        """Processes an individual PDF document: extracts metadata, pages, fields, and signatures."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with PDFExtractor(file_path) as extractor:
            metadata = extractor.get_metadata()
            pages = extractor.extract_pages()
            field_extractor = FieldExtractor(extractor)
            extracted_fields = field_extractor.extract_fields(pages)

        sig_inspector = SignatureInspector(file_path)
        signatures = sig_inspector.inspect()

        return DocumentAnalysisResult(
            metadata=metadata,
            pages=pages,
            extracted_fields=extracted_fields,
            signatures=signatures,
        )

    def process_application(
        self, application_id: str, document_paths: List[str]
    ) -> PipelineRunResult:
        """Runs the full validation suite across all documents submitted under an application."""
        analyzed_docs: List[DocumentAnalysisResult] = []

        for p in document_paths:
            analyzed = self.process_document(p)
            analyzed_docs.append(analyzed)

        # Aggregate fields and evidences across documents
        combined_fields: Dict[str, Any] = {}
        evidences: Dict[str, List[EvidenceAnnotation]] = {}

        for doc in analyzed_docs:
            for field_name, fld in doc.extracted_fields.items():
                if field_name not in combined_fields or combined_fields[field_name] is None:
                    combined_fields[field_name] = fld.normalized_value or fld.value
                evidences.setdefault(field_name, []).append(fld.evidence)

        # 1. Run Regulatory Rule Checks
        rule_results = self.rules_engine.evaluate(
            documents=analyzed_docs,
            combined_fields=combined_fields,
            evidences=evidences,
        )

        # 2. Run Cross-Document Consistency Checks
        consistency_results = self.consistency_engine.evaluate(documents=analyzed_docs)

        # 3. Run Exact and Perceptual Duplicate Checks
        duplicate_results = self.duplicate_detector.evaluate_documents(documents=analyzed_docs)

        # 4. Stratify Risk and Prioritize Findings
        risk_tier, risk_score, audit_trail, critical_defs, clarif_notes, recomms = self.risk_engine.evaluate(
            rule_evaluations=rule_results,
            consistency_evaluations=consistency_results,
            duplicate_evaluations=duplicate_results,
        )

        return PipelineRunResult(
            application_id=application_id,
            analyzed_documents=analyzed_docs,
            rule_evaluations=rule_results,
            consistency_evaluations=consistency_results,
            duplicate_evaluations=duplicate_results,
            risk_tier=risk_tier,
            risk_score=risk_score,
            findings_audit_trail=audit_trail,
            critical_deficiencies=critical_defs,
            clarification_notes=clarif_notes,
            recommendations=recomms,
        )
