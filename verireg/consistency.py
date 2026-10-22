"""Cross-document consistency verification module.
Reconciles fields declared across disparate files (e.g. Land Title Deed vs Building Plan vs Affidavit).
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional
from .schemas import (
    CrossDocConsistencyResult,
    DocumentAnalysisResult,
    EvidenceAnnotation,
    SeverityLevel,
)


def normalize_institution_name(name: str) -> str:
    """Normalizes institution names for comparison by stripping punctuation and legal suffixes."""
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    # remove common stop phrases
    cleaned = re.sub(r"\b(the|and|of|college|institute|polytechnic|engineering|technology)\b", "", cleaned)
    return " ".join(cleaned.split())


class CrossDocumentConsistencyEngine:
    """Verifies that key entities remain consistent across all uploaded documents in an application dossier."""

    def evaluate(
        self, documents: List[DocumentAnalysisResult]
    ) -> List[CrossDocConsistencyResult]:
        results: List[CrossDocConsistencyResult] = []

        if len(documents) < 2:
            return results

        # 1. Institution Name Consistency
        inst_fields = []
        for doc in documents:
            if "institution_name" in doc.extracted_fields:
                f = doc.extracted_fields["institution_name"]
                inst_fields.append((doc.metadata.filename, f))

        if len(inst_fields) > 1:
            base_filename, base_field = inst_fields[0]
            base_norm = normalize_institution_name(str(base_field.normalized_value or base_field.value))
            mismatches = []
            evidences: List[EvidenceAnnotation] = [base_field.evidence]

            for other_filename, other_field in inst_fields[1:]:
                evidences.append(other_field.evidence)
                other_norm = normalize_institution_name(str(other_field.normalized_value or other_field.value))
                if base_norm != other_norm:
                    mismatches.append(
                        f"'{base_field.value}' in {base_filename} vs '{other_field.value}' in {other_filename}"
                    )

            is_consistent = len(mismatches) == 0
            results.append(
                CrossDocConsistencyResult(
                    check_name="Institution Name Reconciliation",
                    field_compared="institution_name",
                    is_consistent=is_consistent,
                    severity=SeverityLevel.INFO if is_consistent else SeverityLevel.DEFICIENCY,
                    documents_involved=[doc for doc, _ in inst_fields],
                    discrepancy_details=None if is_consistent else f"Discrepancy in institution names: {'; '.join(mismatches)}",
                    evidences=evidences,
                )
            )

        # 2. Application ID / Permanent Institute ID Consistency
        app_id_fields = []
        for doc in documents:
            if "application_id" in doc.extracted_fields:
                f = doc.extracted_fields["application_id"]
                app_id_fields.append((doc.metadata.filename, f))

        if len(app_id_fields) > 1:
            base_file, base_field = app_id_fields[0]
            base_val = str(base_field.value).strip().upper()
            mismatches = []
            evidences = [base_field.evidence]

            for o_file, o_field in app_id_fields[1:]:
                evidences.append(o_field.evidence)
                o_val = str(o_field.value).strip().upper()
                if base_val != o_val:
                    mismatches.append(f"'{base_val}' in {base_file} vs '{o_val}' in {o_file}")

            is_consistent = len(mismatches) == 0
            results.append(
                CrossDocConsistencyResult(
                    check_name="Application Identifier Matching",
                    field_compared="application_id",
                    is_consistent=is_consistent,
                    severity=SeverityLevel.INFO if is_consistent else SeverityLevel.CRITICAL,
                    documents_involved=[doc for doc, _ in app_id_fields],
                    discrepancy_details=None if is_consistent else f"Mismatched Application IDs: {'; '.join(mismatches)}",
                    evidences=evidences,
                )
            )

        # 3. Trust / Society Name Consistency
        trust_fields = []
        for doc in documents:
            if "trust_society_name" in doc.extracted_fields:
                f = doc.extracted_fields["trust_society_name"]
                trust_fields.append((doc.metadata.filename, f))

        if len(trust_fields) > 1:
            base_file, base_field = trust_fields[0]
            base_val = str(base_field.value).strip().lower()
            mismatches = []
            evidences = [base_field.evidence]

            for o_file, o_field in trust_fields[1:]:
                evidences.append(o_field.evidence)
                o_val = str(o_field.value).strip().lower()
                if base_val != o_val:
                    mismatches.append(f"'{base_field.value}' in {base_file} vs '{o_field.value}' in {o_file}")

            is_consistent = len(mismatches) == 0
            results.append(
                CrossDocConsistencyResult(
                    check_name="Sponsoring Trust / Society Verification",
                    field_compared="trust_society_name",
                    is_consistent=is_consistent,
                    severity=SeverityLevel.INFO if is_consistent else SeverityLevel.DEFICIENCY,
                    documents_involved=[doc for doc, _ in trust_fields],
                    discrepancy_details=None if is_consistent else f"Conflicting Sponsoring Bodies: {'; '.join(mismatches)}",
                    evidences=evidences,
                )
            )

        # 4. Land Area vs Architectural Plan Consistency
        land_doc_fields = []
        bua_doc_fields = []
        for doc in documents:
            if "land_area_acres" in doc.extracted_fields:
                land_doc_fields.append((doc.metadata.filename, doc.extracted_fields["land_area_acres"]))
            if "built_up_area_sqm" in doc.extracted_fields:
                bua_doc_fields.append((doc.metadata.filename, doc.extracted_fields["built_up_area_sqm"]))

        if land_doc_fields and bua_doc_fields:
            # Check physical feasibility: 1 acre = 4046.86 sqm.
            # Built up area across all floors should be within standard FAR (e.g. maximum 4.0 FAR)
            land_acres = float(land_doc_fields[0][1].normalized_value or land_doc_fields[0][1].value)
            bua_sqm = float(bua_doc_fields[0][1].normalized_value or bua_doc_fields[0][1].value)
            land_sqm = land_acres * 4046.86
            far = bua_sqm / land_sqm if land_sqm > 0 else 0

            # Reasonable FAR for educational campus is usually <= 3.5
            is_feasible = far <= 3.5
            evidences = [land_doc_fields[0][1].evidence, bua_doc_fields[0][1].evidence]
            results.append(
                CrossDocConsistencyResult(
                    check_name="Spatial FAR & Land Feasibility Cross-Check",
                    field_compared="spatial_far",
                    is_consistent=is_feasible,
                    severity=SeverityLevel.INFO if is_feasible else SeverityLevel.WARNING,
                    documents_involved=[land_doc_fields[0][0], bua_doc_fields[0][0]],
                    discrepancy_details=None if is_feasible else f"Implied Floor Area Ratio (FAR = {far:.2f}) exceeds normal maximum (3.50). Verify multi-story structural sanction.",
                    evidences=evidences,
                )
            )

        return results
