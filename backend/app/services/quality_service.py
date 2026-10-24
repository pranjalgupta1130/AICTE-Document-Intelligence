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


class InstitutionQualitySummary(BaseModel):
    institution_id: str
    academic_year: Optional[str] = None
    total_batches: int
    total_records: int
    overall_quality_score: float = Field(..., ge=0.0, le=100.0)
    grade: str
    completeness_score: float = Field(..., ge=0.0, le=100.0)
    validity_score: float = Field(..., ge=0.0, le=100.0)
    consistency_score: float = Field(..., ge=0.0, le=100.0)
    uniqueness_score: float = Field(..., ge=0.0, le=100.0)
    batch_scores: List[DataQualityScore]
    summary_explanation: str


def calculate_institution_quality_aggregation(
    db: Session,
    institution_id: str,
    academic_year: Optional[str] = None
) -> InstitutionQualitySummary:
    """
    Calculate an institution-wide data quality aggregation across batches.
    Uses record-weighted averages of dimensional scores across batches.
    Handles empty batches and institutions with no records gracefully.
    """
    query = db.query(ImportBatch).filter(ImportBatch.institution_id == institution_id)
    if academic_year:
        query = query.filter(ImportBatch.academic_year == academic_year)

    batches = query.order_by(ImportBatch.created_at.desc()).all()

    if not batches:
        return InstitutionQualitySummary(
            institution_id=institution_id,
            academic_year=academic_year,
            total_batches=0,
            total_records=0,
            overall_quality_score=100.0,
            grade="EXCELLENT",
            completeness_score=100.0,
            validity_score=100.0,
            consistency_score=100.0,
            uniqueness_score=100.0,
            batch_scores=[],
            summary_explanation="No import batches found for this institution; baseline default score."
        )

    batch_scores: List[DataQualityScore] = []
    total_records = 0

    for b in batches:
        b_score = calculate_batch_quality_score(db, b)
        batch_scores.append(b_score)
        total_records += b_score.total_records

    if total_records == 0:
        return InstitutionQualitySummary(
            institution_id=institution_id,
            academic_year=academic_year,
            total_batches=len(batches),
            total_records=0,
            overall_quality_score=100.0,
            grade="EXCELLENT",
            completeness_score=100.0,
            validity_score=100.0,
            consistency_score=100.0,
            uniqueness_score=100.0,
            batch_scores=batch_scores,
            summary_explanation="Institution batches contain no student records; baseline default score."
        )

    # Record-weighted aggregation across dimensions
    weighted_comp = 0.0
    weighted_val = 0.0
    weighted_cons = 0.0
    weighted_uniq = 0.0

    for bs in batch_scores:
        weight = bs.total_records / total_records
        weighted_comp += bs.completeness.score * weight
        weighted_val += bs.validity.score * weight
        weighted_cons += bs.consistency.score * weight
        weighted_uniq += bs.uniqueness.score * weight

    weighted_comp = round(weighted_comp, 1)
    weighted_val = round(weighted_val, 1)
    weighted_cons = round(weighted_cons, 1)
    weighted_uniq = round(weighted_uniq, 1)

    overall = round(
        (weighted_comp * 0.25) +
        (weighted_val * 0.30) +
        (weighted_cons * 0.25) +
        (weighted_uniq * 0.20),
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

    explanation = (
        f"Institution-wide aggregate quality score: {overall}/100 ({grade}) across {len(batches)} batches "
        f"and {total_records} student records. Completeness: {weighted_comp}%, Validity: {weighted_val}%, "
        f"Consistency: {weighted_cons}%, Uniqueness: {weighted_uniq}%."
    )

    return InstitutionQualitySummary(
        institution_id=institution_id,
        academic_year=academic_year,
        total_batches=len(batches),
        total_records=total_records,
        overall_quality_score=overall,
        grade=grade,
        completeness_score=weighted_comp,
        validity_score=weighted_val,
        consistency_score=weighted_cons,
        uniqueness_score=weighted_uniq,
        batch_scores=batch_scores,
        summary_explanation=explanation
    )


class QualityScoreDelta(BaseModel):
    batch_a_id: str
    batch_b_id: str
    batch_a_version: int
    batch_b_version: int
    score_before: float
    score_after: float
    score_delta: float
    grade_before: str
    grade_after: str
    completeness_delta: float
    validity_delta: float
    consistency_delta: float
    uniqueness_delta: float
    summary: str


def calculate_quality_score_improvement(
    db: Session,
    batch_before: ImportBatch,
    batch_after: ImportBatch
) -> QualityScoreDelta:
    """
    Compute explainable quality score improvement/delta between two batch versions
    (e.g., initial upload vs revalidated batch after clerical corrections).
    """
    score_a = calculate_batch_quality_score(db, batch_before)
    score_b = calculate_batch_quality_score(db, batch_after)

    delta_overall = round(score_b.overall_score - score_a.overall_score, 1)
    delta_comp = round(score_b.completeness.score - score_a.completeness.score, 1)
    delta_val = round(score_b.validity.score - score_a.validity.score, 1)
    delta_cons = round(score_b.consistency.score - score_a.consistency.score, 1)
    delta_uniq = round(score_b.uniqueness.score - score_a.uniqueness.score, 1)

    direction = "improved by" if delta_overall > 0 else "decreased by" if delta_overall < 0 else "remained unchanged at"
    diff_val = abs(delta_overall)

    summary = (
        f"Data quality {direction} {diff_val} points ({score_a.overall_score} -> {score_b.overall_score}) "
        f"from v{batch_before.version} ({score_a.grade}) to v{batch_after.version} ({score_b.grade}). "
        f"Deltas — Completeness: {delta_comp:+0.1f}, Validity: {delta_val:+0.1f}, "
        f"Consistency: {delta_cons:+0.1f}, Uniqueness: {delta_uniq:+0.1f}."
    )

    return QualityScoreDelta(
        batch_a_id=batch_before.id,
        batch_b_id=batch_after.id,
        batch_a_version=batch_before.version,
        batch_b_version=batch_after.version,
        score_before=score_a.overall_score,
        score_after=score_b.overall_score,
        score_delta=delta_overall,
        grade_before=score_a.grade,
        grade_after=score_b.grade,
        completeness_delta=delta_comp,
        validity_delta=delta_val,
        consistency_delta=delta_cons,
        uniqueness_delta=delta_uniq,
        summary=summary
    )


class LongitudinalTrendPoint(BaseModel):
    batch_id: str
    academic_year: str
    version: int
    created_at: str
    status: str
    total_records: int
    overall_quality_score: float
    grade: str
    completeness_score: float
    validity_score: float
    consistency_score: float
    uniqueness_score: float
    delta_from_previous: Optional[float] = None


class LongitudinalTrendReport(BaseModel):
    institution_id: str
    academic_year_filter: Optional[str] = None
    total_batches: int
    overall_trend: str  # "IMPROVING", "DEGRADING", "STABLE", or "INSUFFICIENT_DATA"
    net_quality_change: float
    datapoints: List[LongitudinalTrendPoint]
    summary: str


def calculate_institution_longitudinal_trends(
    db: Session,
    institution_id: str,
    academic_year: Optional[str] = None
) -> LongitudinalTrendReport:
    """
    Calculate longitudinal data quality and enrolment trends across historical batches for an institution.
    Brief Section 11 (USP 8) & Section 12 (P2).
    """
    query = db.query(ImportBatch).filter(ImportBatch.institution_id == institution_id)
    if academic_year:
        query = query.filter(ImportBatch.academic_year == academic_year)

    batches = query.order_by(
        ImportBatch.academic_year.asc(),
        ImportBatch.version.asc(),
        ImportBatch.created_at.asc()
    ).all()

    if not batches:
        return LongitudinalTrendReport(
            institution_id=institution_id,
            academic_year_filter=academic_year,
            total_batches=0,
            overall_trend="INSUFFICIENT_DATA",
            net_quality_change=0.0,
            datapoints=[],
            summary=f"No batch records found for institution '{institution_id}'."
        )

    datapoints: List[LongitudinalTrendPoint] = []
    prev_score: Optional[float] = None

    for b in batches:
        b_score = calculate_batch_quality_score(db, b)
        delta_prev = round(b_score.overall_score - prev_score, 1) if prev_score is not None else None

        created_str = b.created_at.isoformat() if hasattr(b.created_at, "isoformat") else str(b.created_at)
        datapoints.append(LongitudinalTrendPoint(
            batch_id=b.id,
            academic_year=b.academic_year,
            version=b.version,
            created_at=created_str,
            status=b.status.value if hasattr(b.status, "value") else str(b.status),
            total_records=b_score.total_records,
            overall_quality_score=b_score.overall_score,
            grade=b_score.grade,
            completeness_score=b_score.completeness.score,
            validity_score=b_score.validity.score,
            consistency_score=b_score.consistency.score,
            uniqueness_score=b_score.uniqueness.score,
            delta_from_previous=delta_prev
        ))
        prev_score = b_score.overall_score

    if len(datapoints) < 2:
        trend = "STABLE"
        net_change = 0.0
    else:
        first_score = datapoints[0].overall_quality_score
        last_score = datapoints[-1].overall_quality_score
        net_change = round(last_score - first_score, 1)
        if net_change > 1.0:
            trend = "IMPROVING"
        elif net_change < -1.0:
            trend = "DEGRADING"
        else:
            trend = "STABLE"

    summary = (
        f"Institution '{institution_id}' has {len(datapoints)} evaluated batches. "
        f"Longitudinal trend is {trend} with a net quality score delta of {net_change:+0.1f} points "
        f"across evaluated submissions."
    )

    return LongitudinalTrendReport(
        institution_id=institution_id,
        academic_year_filter=academic_year,
        total_batches=len(datapoints),
        overall_trend=trend,
        net_quality_change=net_change,
        datapoints=datapoints,
        summary=summary
    )
