"""
Batch Anomaly Analytics Service (SIH 26263 - Member 3).

Analyzes an import batch for statistical anomalies and suspicious patterns:
1. Missing mandatory field spikes (abnormal omission rates).
2. Malformed identifier concentrations (syntax / Verhoeff checksum errors).
3. Intra-batch duplicate concentrations (roll number / ID collisions).
4. Seat-type distribution anomalies (zero regular seats, abnormal quotas).
5. Intake capacity breaches (exceeding approved AICTE quotas).
6. Cross-institution collision spikes (multiple dual-enrolment candidates).

Guarantees & Safeguards:
- Pure rule-based transparency: documented deterministic thresholds.
- Statistical warnings are distinct from verified rule violations.
- Never labels statistical patterns as 'fraud' or 'malpractice'.
- Handles empty batches and low-volume data gracefully.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.models.batch import ImportBatch
from backend.app.models.enums import FindingSeverity, FindingStatus, SeatType
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.validation import ValidationFinding


# ---------------------------------------------------------------------------
# Anomaly Enums & Pydantic Models
# ---------------------------------------------------------------------------
class AnomalySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class AnomalyType(str, Enum):
    MISSING_FIELD_SPIKE = "MISSING_FIELD_SPIKE"
    INVALID_IDENTIFIER_RATE = "INVALID_IDENTIFIER_RATE"
    DUPLICATE_CONCENTRATION = "DUPLICATE_CONCENTRATION"
    UNUSUAL_SEAT_DISTRIBUTION = "UNUSUAL_SEAT_DISTRIBUTION"
    INTAKE_CAPACITY_BREACH = "INTAKE_CAPACITY_BREACH"
    CROSS_INSTITUTION_COLLISION_SPIKE = "CROSS_INSTITUTION_COLLISION_SPIKE"


class AnomalyFinding(BaseModel):
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    metric_name: str
    observed_value: float
    threshold_value: float
    unit: str  # "percentage", "count", "ratio"
    evidence: Dict[str, Any] = Field(default_factory=dict)
    message: str
    suggested_action: str


class BatchAnomalyReport(BaseModel):
    batch_id: str
    institution_id: str
    academic_year: str
    total_records: int
    total_findings: int
    anomalies_detected: int
    anomaly_level: str  # "NORMAL", "ELEVATED", "CRITICAL"
    anomalies: List[AnomalyFinding]
    summary: str


# ---------------------------------------------------------------------------
# Threshold Constants
# ---------------------------------------------------------------------------
THRESHOLD_MISSING_FIELD_WARNING = 10.0   # > 10% records with missing fields
THRESHOLD_MISSING_FIELD_CRITICAL = 25.0  # > 25% records with missing fields

THRESHOLD_INVALID_IDENTIFIER_WARNING = 5.0   # > 5% records with invalid syntax/checksum
THRESHOLD_INVALID_IDENTIFIER_CRITICAL = 15.0 # > 15% records with invalid syntax/checksum

THRESHOLD_DUPLICATE_WARNING = 5.0    # > 5% records with duplicate collisions
THRESHOLD_DUPLICATE_CRITICAL = 15.0  # > 15% records with duplicate collisions

THRESHOLD_CROSS_INSTITUTION_SPIKE_COUNT = 3  # >= 3 cross-institution matches in single batch


# ---------------------------------------------------------------------------
# Core Anomaly Evaluation Engine
# ---------------------------------------------------------------------------
def analyze_batch_anomalies(db: Session, batch: ImportBatch) -> BatchAnomalyReport:
    """
    Execute statistical and pattern anomaly detection for an ImportBatch.
    Integrates persisted records, validation findings, and match candidate data.
    """
    records = db.query(StudentRecord).filter(StudentRecord.batch_id == batch.id).all()
    total_records = len(records)

    # Fetch all findings for this batch
    findings = db.query(ValidationFinding).filter(ValidationFinding.batch_id == batch.id).all()
    total_findings = len(findings)
    open_findings = [f for f in findings if f.status == FindingStatus.OPEN]

    anomalies: List[AnomalyFinding] = []

    # Handle empty batch gracefully
    if total_records == 0:
        return BatchAnomalyReport(
            batch_id=batch.id,
            institution_id=batch.institution_id,
            academic_year=batch.academic_year,
            total_records=0,
            total_findings=0,
            anomalies_detected=0,
            anomaly_level="NORMAL",
            anomalies=[],
            summary="Batch contains no records. No anomalies detected."
        )

    # -----------------------------------------------------------------------
    # 1. Missing Required Field Spike
    # -----------------------------------------------------------------------
    missing_findings = [
        f for f in open_findings
        if f.rule_code in ("RULE-REQ-001", "RULE-APAAR-001")
    ]
    missing_records_count = len({f.record_id for f in missing_findings if f.record_id})
    missing_pct = round((missing_records_count / total_records) * 100.0, 1)

    if missing_pct >= THRESHOLD_MISSING_FIELD_CRITICAL:
        anomalies.append(AnomalyFinding(
            anomaly_type=AnomalyType.MISSING_FIELD_SPIKE,
            severity=AnomalySeverity.CRITICAL,
            metric_name="missing_mandatory_fields_pct",
            observed_value=missing_pct,
            threshold_value=THRESHOLD_MISSING_FIELD_CRITICAL,
            unit="percentage",
            evidence={
                "affected_records": missing_records_count,
                "total_records": total_records,
                "findings_count": len(missing_findings)
            },
            message=f"Critical omission rate: {missing_pct}% of student records ({missing_records_count}/{total_records}) have missing required fields.",
            suggested_action="Reject or correct batch at source institution: verify data extraction from SIS/ERP before resubmission."
        ))
    elif missing_pct >= THRESHOLD_MISSING_FIELD_WARNING:
        anomalies.append(AnomalyFinding(
            anomaly_type=AnomalyType.MISSING_FIELD_SPIKE,
            severity=AnomalySeverity.WARNING,
            metric_name="missing_mandatory_fields_pct",
            observed_value=missing_pct,
            threshold_value=THRESHOLD_MISSING_FIELD_WARNING,
            unit="percentage",
            evidence={
                "affected_records": missing_records_count,
                "total_records": total_records,
                "findings_count": len(missing_findings)
            },
            message=f"Elevated omission rate: {missing_pct}% of student records have missing required fields.",
            suggested_action="Review missing student names or identifier fields before submitting batch."
        ))

    # -----------------------------------------------------------------------
    # 2. Invalid Identifier Rate (Verhoeff checksum or syntax failures)
    # -----------------------------------------------------------------------
    invalid_id_findings = [
        f for f in open_findings
        if f.rule_code in ("RULE-APAAR-002", "RULE-SYNTAX-001")
    ]
    invalid_id_count = len({f.record_id for f in invalid_id_findings if f.record_id})
    invalid_id_pct = round((invalid_id_count / total_records) * 100.0, 1)

    if invalid_id_pct >= THRESHOLD_INVALID_IDENTIFIER_CRITICAL:
        anomalies.append(AnomalyFinding(
            anomaly_type=AnomalyType.INVALID_IDENTIFIER_RATE,
            severity=AnomalySeverity.CRITICAL,
            metric_name="invalid_identifier_pct",
            observed_value=invalid_id_pct,
            threshold_value=THRESHOLD_INVALID_IDENTIFIER_CRITICAL,
            unit="percentage",
            evidence={
                "affected_records": invalid_id_count,
                "total_records": total_records,
                "findings_count": len(invalid_id_findings)
            },
            message=f"Critical identifier invalidity rate: {invalid_id_pct}% of records ({invalid_id_count}/{total_records}) failed APAAR format or Verhoeff checksum validation.",
            suggested_action="Re-verify source APAAR IDs against official DigiLocker/APAAR registry before batch submission."
        ))
    elif invalid_id_pct >= THRESHOLD_INVALID_IDENTIFIER_WARNING:
        anomalies.append(AnomalyFinding(
            anomaly_type=AnomalyType.INVALID_IDENTIFIER_RATE,
            severity=AnomalySeverity.WARNING,
            metric_name="invalid_identifier_pct",
            observed_value=invalid_id_pct,
            threshold_value=THRESHOLD_INVALID_IDENTIFIER_WARNING,
            unit="percentage",
            evidence={
                "affected_records": invalid_id_count,
                "total_records": total_records,
                "findings_count": len(invalid_id_findings)
            },
            message=f"Elevated invalid identifier rate: {invalid_id_pct}% of records have invalid APAAR formatting.",
            suggested_action="Inspect flagged records in batch validation findings to correct clerical typos."
        ))

    # -----------------------------------------------------------------------
    # 3. Duplicate Concentration (Intra-batch collisions)
    # -----------------------------------------------------------------------
    dup_findings = [
        f for f in open_findings
        if f.rule_code in ("RULE-DUP-001", "RULE-DUP-002", "RULE-DUP-003")
    ]
    dup_records_count = len({f.record_id for f in dup_findings if f.record_id})
    dup_pct = round((dup_records_count / total_records) * 100.0, 1)

    if dup_pct >= THRESHOLD_DUPLICATE_CRITICAL:
        anomalies.append(AnomalyFinding(
            anomaly_type=AnomalyType.DUPLICATE_CONCENTRATION,
            severity=AnomalySeverity.CRITICAL,
            metric_name="duplicate_concentration_pct",
            observed_value=dup_pct,
            threshold_value=THRESHOLD_DUPLICATE_CRITICAL,
            unit="percentage",
            evidence={
                "duplicate_records": dup_records_count,
                "total_records": total_records,
                "findings_count": len(dup_findings)
            },
            message=f"High duplicate collision concentration: {dup_pct}% of records in this batch share identical roll numbers or APAAR IDs.",
            suggested_action="Audit import file for repeated student rows or accidental re-ingestion of identical student sections."
        ))
    elif dup_pct >= THRESHOLD_DUPLICATE_WARNING:
        anomalies.append(AnomalyFinding(
            anomaly_type=AnomalyType.DUPLICATE_CONCENTRATION,
            severity=AnomalySeverity.WARNING,
            metric_name="duplicate_concentration_pct",
            observed_value=dup_pct,
            threshold_value=THRESHOLD_DUPLICATE_WARNING,
            unit="percentage",
            evidence={
                "duplicate_records": dup_records_count,
                "total_records": total_records,
                "findings_count": len(dup_findings)
            },
            message=f"Moderate duplicate collision rate: {dup_pct}% of records have duplicate roll numbers or IDs.",
            suggested_action="Review and resolve open duplicate findings before batch finalization."
        ))

    # -----------------------------------------------------------------------
    # 4. Unusual Seat Type Distribution
    # -----------------------------------------------------------------------
    if total_records >= 10:
        regular_count = sum(1 for r in records if r.seat_type == SeatType.REGULAR)
        supernumerary_count = sum(
            1 for r in records
            if r.seat_type in (
                SeatType.SUPERNUMERARY_EWS,
                SeatType.SUPERNUMERARY_TFW,
                SeatType.SUPERNUMERARY_FN,
                SeatType.SUPERNUMERARY_OTHER
            )
        )
        management_count = sum(1 for r in records if r.seat_type in (SeatType.MANAGEMENT, SeatType.NRI))

        # Check if 0 regular seats with all other quotas
        if regular_count == 0 and total_records > 0:
            anomalies.append(AnomalyFinding(
                anomaly_type=AnomalyType.UNUSUAL_SEAT_DISTRIBUTION,
                severity=AnomalySeverity.WARNING,
                metric_name="regular_seat_ratio",
                observed_value=0.0,
                threshold_value=0.10,
                unit="ratio",
                evidence={
                    "regular_seats": regular_count,
                    "supernumerary_seats": supernumerary_count,
                    "management_seats": management_count,
                    "total_records": total_records
                },
                message=f"Unusual seat distribution: Batch contains 0 regular quota students across all {total_records} records.",
                suggested_action="Verify if this batch was intended strictly for lateral/supernumerary admissions."
            ))
        elif management_count > (total_records * 0.70):
            anomalies.append(AnomalyFinding(
                anomaly_type=AnomalyType.UNUSUAL_SEAT_DISTRIBUTION,
                severity=AnomalySeverity.WARNING,
                metric_name="management_quota_ratio",
                observed_value=round(management_count / total_records, 2),
                threshold_value=0.70,
                unit="ratio",
                evidence={
                    "management_seats": management_count,
                    "total_records": total_records
                },
                message=f"Disproportionate management quota allocation ({management_count}/{total_records} records).",
                suggested_action="Confirm management quota ceiling limits against institutional approval letter."
            ))

    # -----------------------------------------------------------------------
    # 5. Intake Capacity Breach
    # -----------------------------------------------------------------------
    intake_findings = [
        f for f in open_findings
        if f.rule_code in ("RULE-INTAKE-001", "RULE-INTAKE-002")
    ]
    if intake_findings:
        anomalies.append(AnomalyFinding(
            anomaly_type=AnomalyType.INTAKE_CAPACITY_BREACH,
            severity=AnomalySeverity.CRITICAL,
            metric_name="intake_violations_count",
            observed_value=float(len(intake_findings)),
            threshold_value=0.0,
            unit="count",
            evidence={
                "violations_count": len(intake_findings),
                "violated_programmes": list({f.suggested_action for f in intake_findings if f.suggested_action})
            },
            message=f"Intake capacity breach detected: {len(intake_findings)} programme quotas exceeded.",
            suggested_action="Blocking issue: adjust student roll list or apply to AICTE for supernumerary intake expansion."
        ))

    # -----------------------------------------------------------------------
    # 6. Cross-Institution Collision Spike
    # -----------------------------------------------------------------------
    # Check MatchCandidates involving records in this batch
    batch_rec_ids = {r.id for r in records}
    match_candidates = db.query(MatchCandidate).filter(
        (MatchCandidate.record_a_id.in_(batch_rec_ids)) |
        (MatchCandidate.record_b_id.in_(batch_rec_ids))
    ).all()
    cross_inst_matches = [
        m for m in match_candidates
        if m.institution_a_id != m.institution_b_id
    ]
    cross_count = len(cross_inst_matches)

    if cross_count >= THRESHOLD_CROSS_INSTITUTION_SPIKE_COUNT:
        anomalies.append(AnomalyFinding(
            anomaly_type=AnomalyType.CROSS_INSTITUTION_COLLISION_SPIKE,
            severity=AnomalySeverity.WARNING,
            metric_name="cross_institution_matches_count",
            observed_value=float(cross_count),
            threshold_value=float(THRESHOLD_CROSS_INSTITUTION_SPIKE_COUNT),
            unit="count",
            evidence={
                "cross_institution_matches": cross_count,
                "partner_institutions": list({
                    m.institution_a_id if m.institution_b_id == batch.institution_id else m.institution_b_id
                    for m in cross_inst_matches
                })
            },
            message=f"Cross-institution dual registration spike: {cross_count} student records matched against other institutions.",
            suggested_action="Coordinate with AICTE central portal to verify inter-institution transfer or dual registration status."
        ))

    # Determine overall anomaly level
    has_critical = any(a.severity == AnomalySeverity.CRITICAL for a in anomalies)
    has_warning = any(a.severity == AnomalySeverity.WARNING for a in anomalies)

    if has_critical:
        anomaly_level = "CRITICAL"
        summary = f"CRITICAL ANOMALIES DETECTED: {len(anomalies)} pattern warnings flagged, including critical blocking issues. Review remediation actions."
    elif has_warning:
        anomaly_level = "ELEVATED"
        summary = f"ELEVATED ANOMALIES DETECTED: {len(anomalies)} pattern warnings flagged. Institutional review advised."
    else:
        anomaly_level = "NORMAL"
        summary = "Dataset patterns within normal statistical parameters. No critical anomalies flagged."

    return BatchAnomalyReport(
        batch_id=batch.id,
        institution_id=batch.institution_id,
        academic_year=batch.academic_year,
        total_records=total_records,
        total_findings=total_findings,
        anomalies_detected=len(anomalies),
        anomaly_level=anomaly_level,
        anomalies=anomalies,
        summary=summary
    )
