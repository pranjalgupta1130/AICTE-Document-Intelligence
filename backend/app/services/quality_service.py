"""
Data Quality Engine & Scoring Service.

Computes a transparent, explainable data-quality score across 4 documented criteria:
1. Completeness: Presence of essential identity & academic fields (APAAR ID, Student Name, Roll No, Programme, Year).
2. Validity: Adherence to syntactic formats (12-digit APAAR, Verhoeff checksum, allowed seat types, enrolment status).
3. Consistency: Logical coherence between student category, NRI/OCI/FN flags, and intake quota allocations.
4. Uniqueness: Absence of intra-batch or cross-batch duplicate student IDs or collision candidates.

CRITICAL ARCHITECTURAL SAFEGUARD:
- This metric evaluates dataset fidelity and hygiene.
- It is NEVER presented as a 'fraud' or 'legitimacy' score, nor as an institutional ranking.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.models.batch import ImportBatch
from backend.app.models.enums import FindingSeverity, FindingStatus
from backend.app.models.student import StudentRecord
from backend.app.models.validation import ValidationFinding

class QualityDimension(BaseModel):
    dimension_name: str
    weight: float
    score: float
    total_checks: int
    passed_checks: int
    deductions: float
    explanation: str

class DataQualityScore(BaseModel):
    batch_id: str
    academic_year: str
    total_records: int
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Explainable aggregate data quality percentage (0-100)")
    grade: str  # EXCELLENT (>=90), GOOD (>=75), NEEDS_IMPROVEMENT (>=50), POOR (<50)
    completeness: QualityDimension
    validity: QualityDimension
    consistency: QualityDimension
    uniqueness: QualityDimension
    explanation: str

def calculate_batch_quality_score(db: Session, batch: ImportBatch) -> DataQualityScore:
    """
    Calculate explainable data quality score for an import batch based on persisted findings and records.
    """
    records = db.query(StudentRecord).filter(StudentRecord.batch_id == batch.id).all()
    total_records = len(records)
    if total_records == 0:
        empty_dim = QualityDimension(
            dimension_name="empty",
            weight=0.25,
            score=100.0,
            total_checks=0,
            passed_checks=0,
            deductions=0.0,
            explanation="No records in batch."
        )
        return DataQualityScore(
            batch_id=batch.id,
            academic_year=batch.academic_year,
            total_records=0,
            overall_score=100.0,
            grade="EXCELLENT",
            completeness=empty_dim,
            validity=empty_dim,
            consistency=empty_dim,
            uniqueness=empty_dim,
            explanation="Batch contains no student records; default baseline quality."
        )

    # Fetch all findings for this batch
    findings = db.query(ValidationFinding).filter(ValidationFinding.batch_id == batch.id).all()
    open_findings = [f for f in findings if f.status == FindingStatus.OPEN]

    # --- 1. Completeness Dimension (Weight: 25%) ---
    # Missing required field findings (RULE-REQ-001, RULE-APAAR-001)
    req_findings = [f for f in open_findings if f.rule_code in ("RULE-REQ-001", "RULE-APAAR-001")]
    comp_deduction = min(len(req_findings) / (total_records * 2) * 100.0, 100.0)
    comp_score = round(max(0.0, 100.0 - comp_deduction), 1)
    comp_dim = QualityDimension(
        dimension_name="Completeness",
        weight=0.25,
        score=comp_score,
        total_checks=total_records * 2,
        passed_checks=max(0, (total_records * 2) - len(req_findings)),
        deductions=round(comp_deduction, 1),
        explanation=f"{len(req_findings)} missing field occurrences across student records."
    )

    # --- 2. Validity Dimension (Weight: 30%) ---
    # Syntactic format / checksum errors (RULE-APAAR-002, etc.)
    val_findings = [f for f in open_findings if f.rule_code in ("RULE-APAAR-002", "RULE-SYNTAX-001")]
    val_deduction = min(len(val_findings) / total_records * 100.0, 100.0)
    val_score = round(max(0.0, 100.0 - val_deduction), 1)
    val_dim = QualityDimension(
        dimension_name="Validity",
        weight=0.30,
        score=val_score,
        total_checks=total_records,
        passed_checks=max(0, total_records - len(val_findings)),
        deductions=round(val_deduction, 1),
        explanation=f"{len(val_findings)} records with invalid APAAR syntax or failed Verhoeff checksums."
    )

    # --- 3. Consistency Dimension (Weight: 25%) ---
    # Quota mismatch or intake exceedance (RULE-CAT-001, RULE-INTAKE-001, RULE-INTAKE-002)
    cons_findings = [f for f in open_findings if "RULE-CAT" in f.rule_code or "RULE-INTAKE" in f.rule_code]
    cons_deduction = min(len(cons_findings) / total_records * 100.0, 100.0)
    cons_score = round(max(0.0, 100.0 - cons_deduction), 1)
    cons_dim = QualityDimension(
        dimension_name="Consistency",
        weight=0.25,
        score=cons_score,
        total_checks=total_records,
        passed_checks=max(0, total_records - len(cons_findings)),
        deductions=round(cons_deduction, 1),
        explanation=f"{len(cons_findings)} records with category/seat inconsistency or intake allocation breaches."
    )

    # --- 4. Uniqueness Dimension (Weight: 20%) ---
    # Duplicate records (RULE-DUP-001, RULE-DUP-002)
    dup_findings = [f for f in open_findings if "RULE-DUP" in f.rule_code]
    dup_deduction = min(len(dup_findings) / total_records * 100.0, 100.0)
    dup_score = round(max(0.0, 100.0 - dup_deduction), 1)
    dup_dim = QualityDimension(
        dimension_name="Uniqueness",
        weight=0.20,
        score=dup_score,
        total_checks=total_records,
        passed_checks=max(0, total_records - len(dup_findings)),
        deductions=round(dup_deduction, 1),
        explanation=f"{len(dup_findings)} records with duplicate roll numbers or APAAR collision candidates."
    )

    # Weighted Overall Score
    overall = round(
        (comp_score * comp_dim.weight) +
        (val_score * val_dim.weight) +
        (cons_score * cons_dim.weight) +
        (dup_score * dup_dim.weight),
        1
    )

    if overall >= 90.0:
        grade = "EXCELLENT"
    elif overall >= 75.0:
        grade = "GOOD"
    elif overall >= 50.0:
        grade = "NEEDS_IMPROVEMENT"
    else:
        grade = "POOR"

    return DataQualityScore(
        batch_id=batch.id,
        academic_year=batch.academic_year,
        total_records=total_records,
        overall_score=overall,
        grade=grade,
        completeness=comp_dim,
        validity=val_dim,
        consistency=cons_dim,
        uniqueness=dup_dim,
        explanation=f"Transparent dataset hygiene score: {overall}/100 ({grade}) based on completeness, validity, consistency, and uniqueness."
    )
