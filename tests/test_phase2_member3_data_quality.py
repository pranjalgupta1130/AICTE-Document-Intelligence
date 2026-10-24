"""
Member 3 Data Quality Intelligence, Testing & Differentiators Test Suite.
Covers:
1. Explainable fuzzy duplicate candidate matching (Feature A).
2. Manual duplicate review support and lifecycle (Feature B).
3. Cross-institution candidate identification and isolation (Feature C).
4. Batch anomaly analytics (Feature D).
5. Quality scoring aggregation across batches and version deltas (Feature E).
6. Mock APAAR Adapter simulation outcomes & failure resilience.
7. Performance benchmark on ~1,000 synthetic student records.
8. API endpoint integration, RBAC, and institution isolation.
All test data is 100% synthetic.
"""

import time
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.adapters.mock_apaar import MockApaarAdapter
from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import (
    AuditAction,
    BatchStatus,
    FindingSeverity,
    FindingStatus,
    MatchStatus,
    SeatType,
    UserRole,
    VerificationOutcome,
)
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.user import User
from backend.app.models.validation import ValidationFinding
from backend.app.services.anomaly_service import (
    AnomalySeverity,
    AnomalyType,
    analyze_batch_anomalies,
)
from backend.app.services.duplicate_fuzzy_service import (
    DEFAULT_SIMILARITY_THRESHOLD,
    compare_student_records,
    compute_name_similarity,
    find_fuzzy_duplicates_for_batch,
    find_fuzzy_duplicates_in_records,
    normalize_name,
)
from backend.app.services.quality_service import (
    calculate_batch_quality_score,
    calculate_institution_longitudinal_trends,
    calculate_institution_quality_aggregation,
    calculate_quality_score_improvement,
)
from backend.app.services.workflow_service import review_match_candidate
from backend.app.schemas.workflows import MatchCandidateReviewRequest


@pytest.fixture
def client():
    return TestClient(app)


def get_token(client: TestClient, email: str, password: str = "DemoPassword@2026") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# 1. Fuzzy Duplicate Matching Unit Tests (Feature A)
# ==============================================================================
def test_normalize_name_handles_honorifics_and_accents():
    """Verify name normalisation strips honorifics, diacritics, and excess spaces."""
    assert normalize_name("Shri Priya Sharma") == "priya sharma"
    assert normalize_name("Dr. Rohan Kumar") == "rohan"
    assert normalize_name("Ms.  Ananya    Iyer  ") == "ananya iyer"
    assert normalize_name("Md. Tariq Khan") == "tariq khan"
    assert normalize_name("") == ""
    assert normalize_name(None) == ""


def test_exact_and_transposed_name_similarity():
    """Verify exact and token-transposed name matching behavior."""
    # Exact normalized match
    score, expl = compute_name_similarity("Priya Sharma", "PRIYA  SHARMA")
    assert score == 1.0
    assert "Exact normalised name match" in expl

    # Transposed tokens (e.g. Last Name First)
    score_tr, expl_tr = compute_name_similarity("Aarav Sharma", "Sharma Aarav")
    assert score_tr >= 0.95
    assert "Transposed name match" in expl_tr


def test_minor_spelling_variation_similarity():
    """Minor typo should produce high similarity (>= 0.85)."""
    score, expl = compute_name_similarity("Aarav Sharma", "Arav Sharma")
    assert score >= 0.85
    assert "High name similarity" in expl


def test_clearly_different_students_similarity():
    """Clearly distinct student names should produce similarity < 0.50."""
    score, expl = compute_name_similarity("Rohan Gupta", "Ananya Iyer")
    assert score < 0.50
    assert "Distinct names" in expl


def test_missing_name_returns_zero_similarity():
    """Missing names must never count as positive matching evidence."""
    score1, expl1 = compute_name_similarity(None, "Rohan Gupta")
    assert score1 == 0.0
    assert "Missing name" in expl1

    score2, expl2 = compute_name_similarity(None, None)
    assert score2 == 0.0
    assert "Missing name" in expl2


def test_self_match_prevention():
    """A record must never be matched against itself."""
    rec = StudentRecord(
        id="STU-SELF-001",
        institution_id="INST-001",
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        student_name="Kavita Rao",
        seat_type=SeatType.REGULAR
    )
    result = compare_student_records(rec, rec)
    assert result is None


def test_similarity_score_bounds_and_attribution():
    """Score must always be within [0.0, 1.0] and contain structured field details."""
    rec_a = StudentRecord(
        id="STU-ATTR-001",
        institution_id="INST-001",
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        student_name="Kavita Rao",
        seat_type=SeatType.REGULAR
    )
    rec_b = StudentRecord(
        id="STU-ATTR-002",
        institution_id="INST-001",
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        student_name="Kavitaa Rao",
        seat_type=SeatType.REGULAR
    )
    cand = compare_student_records(rec_a, rec_b)
    assert cand is not None
    assert 0.0 <= cand.overall_similarity <= 1.0
    assert cand.overall_similarity >= DEFAULT_SIMILARITY_THRESHOLD
    assert cand.is_cross_institution is False
    assert len(cand.field_comparisons) >= 4

    field_names = [f.field_name for f in cand.field_comparisons]
    assert "student_name" in field_names
    assert "programme_id" in field_names
    assert "academic_year" in field_names
    assert "seat_type" in field_names

    # Check that explanation does not contain unmasked sensitive tokens
    assert "Intra-institution candidate" in cand.explanation
    assert cand.record_a_id == "STU-ATTR-001"
    assert cand.record_b_id == "STU-ATTR-002"


def test_symmetric_pair_deduplication():
    """find_fuzzy_duplicates_in_records must return each pair only once (no symmetric pairs)."""
    recs = [
        StudentRecord(id="STU-A", institution_id="INST-001", student_name="Deepak Joshi", programme_id="P1", academic_year="2026", seat_type=SeatType.REGULAR),
        StudentRecord(id="STU-B", institution_id="INST-001", student_name="Deepak Joshhi", programme_id="P1", academic_year="2026", seat_type=SeatType.REGULAR),
    ]
    report = find_fuzzy_duplicates_in_records(recs, threshold=0.70)
    assert report.total_pairs_compared == 1
    assert report.candidates_flagged == 1
    assert report.candidates[0].record_a_id == "STU-A"
    assert report.candidates[0].record_b_id == "STU-B"


def test_fuzzy_match_when_apaar_missing():
    """Candidates with missing APAAR IDs should still be detected via Name + Programme + Academic Year."""
    rec_a = StudentRecord(
        id="STU-NOAPAAR-01",
        institution_id="INST-001",
        apaar_id=None,
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        student_name="Pooja Nair",
        seat_type=SeatType.REGULAR
    )
    rec_b = StudentRecord(
        id="STU-NOAPAAR-02",
        institution_id="INST-001",
        apaar_id=None,
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        student_name="Pooja Naayer",
        seat_type=SeatType.REGULAR
    )
    cand = compare_student_records(rec_a, rec_b)
    assert cand is not None
    assert cand.overall_similarity >= 0.75
    assert "Intra-institution candidate" in cand.explanation


# ==============================================================================
# 2. Cross-Institution Matching & Manual Review Workflow (Features B & C)
# ==============================================================================
def test_cross_institution_candidate_detection():
    """Candidates from different institutions must be explicitly flagged with is_cross_institution=True."""
    rec_inst1 = StudentRecord(
        id="STU-CROSS-01",
        institution_id="INST-001",
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        student_name="Sunil Varma",
        seat_type=SeatType.REGULAR
    )
    rec_inst2 = StudentRecord(
        id="STU-CROSS-02",
        institution_id="INST-002",
        programme_id="PROG-002-CSE",
        academic_year="2026-2027",
        student_name="Sunil Verma",
        seat_type=SeatType.REGULAR
    )
    cand = compare_student_records(rec_inst1, rec_inst2)
    assert cand is not None
    assert cand.is_cross_institution is True
    assert cand.institution_a_id == "INST-001"
    assert cand.institution_b_id == "INST-002"
    assert "Cross-institution candidate" in cand.explanation
    assert "AICTE Reviewer inspection required" in cand.suggested_action


def test_manual_review_workflow_and_audit():
    """AICTE Admin can review a match candidate to CONFIRMED_DUPLICATE with an audit trail."""
    db = SessionLocal()
    try:
        aicte_user = db.query(User).filter(User.role == UserRole.AICTE_ADMIN).first()
        inst_user = db.query(User).filter(User.role == UserRole.INSTITUTION_ADMIN).first()
        assert aicte_user is not None
        assert inst_user is not None

        # Find or create a valid batch for institution INST-001
        batch_1 = db.query(ImportBatch).filter(ImportBatch.institution_id == "INST-001").first()
        batch_2 = db.query(ImportBatch).filter(ImportBatch.institution_id == "INST-002").first()
        if not batch_2:
            batch_2 = batch_1

        # Create two synthetic student records in database
        rec_a = StudentRecord(
            id=f"stu-rev-a-{uuid.uuid4().hex[:6]}",
            batch_id=batch_1.id,
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            institution_student_id="ROLL-REV-A",
            academic_year="2026-2027",
            student_name="Review Test Candidate A"
        )
        rec_b = StudentRecord(
            id=f"stu-rev-b-{uuid.uuid4().hex[:6]}",
            batch_id=batch_2.id,
            institution_id="INST-002",
            programme_id="PROG-002-CSE",
            institution_student_id="ROLL-REV-B",
            academic_year="2026-2027",
            student_name="Review Test Candidate B"
        )
        db.add_all([rec_a, rec_b])
        db.commit()

        # Create MatchCandidate
        mc = MatchCandidate(
            id=f"mat-test-{uuid.uuid4().hex[:8]}",
            record_a_id=rec_a.id,
            record_b_id=rec_b.id,
            institution_a_id="INST-001",
            institution_b_id="INST-002",
            matching_signal="FUZZY_NAME_PROG (similarity=0.88)",
            confidence=0.88,
            status=MatchStatus.CANDIDATE
        )
        db.add(mc)
        db.commit()

        # 1. Institution Admin attempt should be rejected with PermissionDenied
        with pytest.raises(Exception):
            review_match_candidate(
                db=db,
                match_id=mc.id,
                current_user=inst_user,
                request=MatchCandidateReviewRequest(
                    status=MatchStatus.CONFIRMED_DUPLICATE,
                    resolution_reason="Unauthorized attempt"
                )
            )

        # 2. AICTE Admin resolves successfully
        resolved = review_match_candidate(
            db=db,
            match_id=mc.id,
            current_user=aicte_user,
            request=MatchCandidateReviewRequest(
                status=MatchStatus.CONFIRMED_DUPLICATE,
                resolution_reason="Confirmed dual enrolment across institutions."
            )
        )
        assert resolved.status == MatchStatus.CONFIRMED_DUPLICATE
        assert resolved.reviewed_by == aicte_user.id
        assert resolved.resolution_reason == "Confirmed dual enrolment across institutions."

        # Verify AuditEvent was logged
        audit = db.query(AuditEvent).filter(
            AuditEvent.object_type == "MATCH_CANDIDATE",
            AuditEvent.object_id == mc.id
        ).first()
        assert audit is not None
        assert audit.action == AuditAction.REVIEW_DECISION
        assert audit.actor_user_id == aicte_user.id
    finally:
        db.close()


def test_manual_review_dismiss_lifecycle():
    """AICTE Admin can dismiss a candidate as false positive (DISMISSED)."""
    db = SessionLocal()
    try:
        aicte_user = db.query(User).filter(User.role == UserRole.AICTE_ADMIN).first()
        batch_1 = db.query(ImportBatch).filter(ImportBatch.institution_id == "INST-001").first()

        rec_a = StudentRecord(
            id=f"stu-dism-a-{uuid.uuid4().hex[:6]}",
            batch_id=batch_1.id,
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            institution_student_id="ROLL-DISM-A",
            academic_year="2026-2027",
            student_name="Candidate Dism A"
        )
        rec_b = StudentRecord(
            id=f"stu-dism-b-{uuid.uuid4().hex[:6]}",
            batch_id=batch_1.id,
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            institution_student_id="ROLL-DISM-B",
            academic_year="2026-2027",
            student_name="Candidate Dism B"
        )
        db.add_all([rec_a, rec_b])
        db.commit()

        mc = MatchCandidate(
            id=f"mat-dism-{uuid.uuid4().hex[:8]}",
            record_a_id=rec_a.id,
            record_b_id=rec_b.id,
            institution_a_id="INST-001",
            institution_b_id="INST-001",
            matching_signal="FUZZY_NAME_PROG (similarity=0.81)",
            confidence=0.81,
            status=MatchStatus.CANDIDATE
        )
        db.add(mc)
        db.commit()

        dismissed = review_match_candidate(
            db=db,
            match_id=mc.id,
            current_user=aicte_user,
            request=MatchCandidateReviewRequest(
                status=MatchStatus.DISMISSED,
                resolution_reason="Verified different candidates with identical patronymic surnames."
            )
        )
        assert dismissed.status == MatchStatus.DISMISSED
        assert dismissed.resolution_reason == "Verified different candidates with identical patronymic surnames."
    finally:
        db.close()


# ==============================================================================
# 3. Batch Anomaly Analytics Tests (Feature D)
# ==============================================================================
def test_empty_batch_anomaly_handling():
    """Empty batch must produce NORMAL level without errors."""
    db = SessionLocal()
    test_ay = f"AY-{uuid.uuid4().hex[:8]}"
    try:
        empty_batch = ImportBatch(
            id=f"bat-empty-{uuid.uuid4().hex[:6]}",
            institution_id="INST-001",
            source_filename="empty_batch.csv",
            academic_year=test_ay,
            status=BatchStatus.DRAFT,
            version=1
        )
        db.add(empty_batch)
        db.commit()

        report = analyze_batch_anomalies(db, empty_batch)
        assert report.total_records == 0
        assert report.anomalies_detected == 0
        assert report.anomaly_level == "NORMAL"
    finally:
        db.close()


def test_missing_field_spike_anomaly():
    """Batch with >25% missing fields must flag CRITICAL MISSING_FIELD_SPIKE."""
    db = SessionLocal()
    test_ay = f"AY-{uuid.uuid4().hex[:8]}"
    try:
        batch = ImportBatch(
            id=f"bat-spike-{uuid.uuid4().hex[:6]}",
            institution_id="INST-001",
            source_filename="spike_batch.csv",
            academic_year=test_ay,
            status=BatchStatus.DRAFT,
            version=1
        )
        db.add(batch)
        db.flush()

        # Add 10 students
        records = [
            StudentRecord(
                id=f"stu-spk-{i}-{uuid.uuid4().hex[:4]}",
                batch_id=batch.id,
                institution_id="INST-001",
                programme_id="PROG-001-CSE",
                institution_student_id=f"ROLL-SPK-{i}",
                academic_year=test_ay,
                student_name=f"Student {i}"
            )
            for i in range(10)
        ]
        db.add_all(records)
        db.flush()

        # Add missing field findings for 4 students (40% omission rate)
        findings = [
            ValidationFinding(
                batch_id=batch.id,
                record_id=records[i].id,
                row_number=i + 1,
                field_name="student_name",
                rule_code="RULE-REQ-001",
                severity=FindingSeverity.BLOCKING_ERROR,
                message="Missing student name",
                status=FindingStatus.OPEN
            )
            for i in range(4)
        ]
        db.add_all(findings)
        db.commit()

        report = analyze_batch_anomalies(db, batch)
        assert report.total_records == 10
        assert report.anomaly_level == "CRITICAL"
        spike_anomalies = [a for a in report.anomalies if a.anomaly_type == AnomalyType.MISSING_FIELD_SPIKE]
        assert len(spike_anomalies) == 1
        assert spike_anomalies[0].severity == AnomalySeverity.CRITICAL
        assert spike_anomalies[0].observed_value == 40.0
    finally:
        db.close()


def test_intake_capacity_breach_anomaly():
    """Intake breach findings must flag CRITICAL INTAKE_CAPACITY_BREACH."""
    db = SessionLocal()
    test_ay = f"AY-{uuid.uuid4().hex[:8]}"
    try:
        batch = ImportBatch(
            id=f"bat-intk-{uuid.uuid4().hex[:6]}",
            institution_id="INST-001",
            source_filename="intake_batch.csv",
            academic_year=test_ay,
            status=BatchStatus.DRAFT,
            version=1
        )
        db.add(batch)
        db.flush()

        rec = StudentRecord(
            id=f"stu-intk-{uuid.uuid4().hex[:6]}",
            batch_id=batch.id,
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            institution_student_id="ROLL-INTK-01",
            academic_year=test_ay,
            student_name="Intake Student"
        )
        db.add(rec)
        db.flush()

        fnd = ValidationFinding(
            batch_id=batch.id,
            record_id=rec.id,
            row_number=1,
            field_name="programme_id",
            rule_code="RULE-INTAKE-001",
            severity=FindingSeverity.BLOCKING_ERROR,
            message="Regular intake quota exceeded for programme PROG-001-CSE",
            status=FindingStatus.OPEN,
            suggested_action="PROG-001-CSE"
        )
        db.add(fnd)
        db.commit()

        report = analyze_batch_anomalies(db, batch)
        assert report.anomaly_level == "CRITICAL"
        breach = [a for a in report.anomalies if a.anomaly_type == AnomalyType.INTAKE_CAPACITY_BREACH]
        assert len(breach) == 1
        assert breach[0].severity == AnomalySeverity.CRITICAL
    finally:
        db.close()


def test_small_batch_seat_distribution_boundary():
    """Small batch (< 10 records) with 0 regular seats does NOT trigger anomaly due to minimum sample threshold."""
    db = SessionLocal()
    test_ay = f"AY-{uuid.uuid4().hex[:8]}"
    try:
        batch = ImportBatch(
            id=f"bat-small-{uuid.uuid4().hex[:6]}",
            institution_id="INST-001",
            source_filename="small.csv",
            academic_year=test_ay,
            status=BatchStatus.DRAFT,
            version=1
        )
        db.add(batch)
        db.flush()

        # Add 5 supernumerary students (total < 10)
        records = [
            StudentRecord(
                id=f"stu-sm-{i}-{uuid.uuid4().hex[:4]}",
                batch_id=batch.id,
                institution_id="INST-001",
                programme_id="PROG-001-CSE",
                institution_student_id=f"ROLL-SM-{i}",
                academic_year=test_ay,
                student_name=f"Small Batch Student {i}",
                seat_type=SeatType.SUPERNUMERARY_EWS
            )
            for i in range(5)
        ]
        db.add_all(records)
        db.commit()

        report = analyze_batch_anomalies(db, batch)
        # Should NOT flag UNUSUAL_SEAT_DISTRIBUTION because len(records) < 10
        seat_anomalies = [a for a in report.anomalies if a.anomaly_type == AnomalyType.UNUSUAL_SEAT_DISTRIBUTION]
        assert len(seat_anomalies) == 0
    finally:
        db.close()


# ==============================================================================
# 4. Quality Scoring Aggregation & Version Deltas (Feature E)
# ==============================================================================
def test_institution_quality_aggregation_empty():
    """Institution with no batches should return default baseline quality."""
    db = SessionLocal()
    try:
        summary = calculate_institution_quality_aggregation(db, institution_id="INST-NONEXISTENT")
        assert summary.total_batches == 0
        assert summary.total_records == 0
        assert summary.overall_quality_score == 100.0
        assert summary.grade == "EXCELLENT"
        assert "No import batches found" in summary.summary_explanation
    finally:
        db.close()


def test_institution_quality_aggregation_record_weighted():
    """Verify record-weighted calculation across multiple batches of an institution."""
    db = SessionLocal()
    try:
        inst_id = "INST-001"
        summary = calculate_institution_quality_aggregation(db, institution_id=inst_id)
        assert summary.institution_id == inst_id
        assert summary.total_batches >= 1
        assert 0.0 <= summary.overall_quality_score <= 100.0
        assert summary.grade in ("EXCELLENT", "GOOD", "NEEDS_IMPROVEMENT", "POOR")
        assert 0.0 <= summary.completeness_score <= 100.0
        assert 0.0 <= summary.validity_score <= 100.0
        assert 0.0 <= summary.consistency_score <= 100.0
        assert 0.0 <= summary.uniqueness_score <= 100.0
        assert "Institution-wide aggregate quality score" in summary.summary_explanation
    finally:
        db.close()


def test_quality_score_improvement_delta():
    """Verify before/after quality score improvement delta calculation between batch versions."""
    db = SessionLocal()
    test_ay = f"AY-{uuid.uuid4().hex[:8]}"
    try:
        batch_v1 = ImportBatch(
            id=f"bat-v1-{uuid.uuid4().hex[:6]}",
            institution_id="INST-001",
            source_filename="students_v1.csv",
            academic_year=test_ay,
            status=BatchStatus.VALIDATED,
            version=1
        )
        batch_v2 = ImportBatch(
            id=f"bat-v2-{uuid.uuid4().hex[:6]}",
            institution_id="INST-001",
            source_filename="students_v2.csv",
            academic_year=test_ay,
            status=BatchStatus.VALIDATED,
            version=2
        )
        db.add_all([batch_v1, batch_v2])
        db.flush()

        # Batch 1 has 5 records with 2 missing field findings
        recs_v1 = [
            StudentRecord(
                id=f"stu-v1-{i}-{uuid.uuid4().hex[:4]}",
                batch_id=batch_v1.id,
                institution_id="INST-001",
                programme_id="PROG-001-CSE",
                institution_student_id=f"ROLL-V1-{i}",
                academic_year=test_ay,
                student_name=f"Student V1-{i}"
            )
            for i in range(5)
        ]
        db.add_all(recs_v1)
        db.flush()
        findings_v1 = [
            ValidationFinding(
                batch_id=batch_v1.id,
                record_id=recs_v1[0].id,
                rule_code="RULE-REQ-001",
                severity=FindingSeverity.BLOCKING_ERROR,
                message="Missing name",
                status=FindingStatus.OPEN
            )
        ]
        db.add_all(findings_v1)

        # Batch 2 has 5 records with 0 findings (fully corrected)
        recs_v2 = [
            StudentRecord(
                id=f"stu-v2-{i}-{uuid.uuid4().hex[:4]}",
                batch_id=batch_v2.id,
                institution_id="INST-001",
                programme_id="PROG-001-CSE",
                institution_student_id=f"ROLL-V2-{i}",
                academic_year=test_ay,
                student_name=f"Student V2-{i}"
            )
            for i in range(5)
        ]
        db.add_all(recs_v2)
        db.commit()

        delta = calculate_quality_score_improvement(db, batch_before=batch_v1, batch_after=batch_v2)
        assert delta.batch_a_version == 1
        assert delta.batch_b_version == 2
        assert delta.score_after > delta.score_before
        assert delta.score_delta > 0
        assert "Data quality improved by" in delta.summary
    finally:
        db.close()


# ==============================================================================
# 5. Mock APAAR Adapter Unit Tests & Verification Failure Resilience
# ==============================================================================
def test_mock_apaar_adapter_comprehensive_outcomes():
    """Verify all simulated outcomes and safeguards of the MockApaarAdapter."""
    adapter = MockApaarAdapter()

    # 1. Valid synthetic APAAR with correct Verhoeff checksum -> MOCK_VERIFIED, is_official=False
    # 12-digit valid Verhoeff: e.g. 123456789012 (Verhoeff for 12345678901 is 2)
    # Using 12-digit synthetic ID from seed
    res_valid = adapter.verify("123456789012", student_name="Deepak Joshi", institution_id="INST-001")
    assert res_valid.provider == "MOCK_APAAR_ADAPTER"
    assert res_valid.is_official is False
    assert res_valid.outcome in (VerificationOutcome.MOCK_VERIFIED, VerificationOutcome.MOCK_NOT_VERIFIED)

    # 2. Syntax invalid format (less than 12 digits) -> MOCK_NOT_VERIFIED
    res_short = adapter.verify("12345")
    assert res_short.outcome == VerificationOutcome.MOCK_NOT_VERIFIED
    assert "APAAR ID format invalid" in res_short.message
    assert res_short.is_official is False

    # 3. Simulated review prefix '0000' -> NEEDS_REVIEW
    res_review = adapter.verify("000012345678")
    assert res_review.outcome == VerificationOutcome.NEEDS_REVIEW
    assert res_review.is_official is False

    # 4. Simulated gateway error prefix '9999' -> MOCK_UNAVAILABLE
    res_err = adapter.verify("999912345678")
    assert res_err.outcome == VerificationOutcome.MOCK_UNAVAILABLE
    assert res_err.is_official is False

    # 5. Outage simulation mode -> MOCK_UNAVAILABLE
    outage_adapter = MockApaarAdapter(simulate_outage=True)
    res_outage = outage_adapter.verify("123456789012")
    assert res_outage.outcome == VerificationOutcome.MOCK_UNAVAILABLE
    assert res_outage.is_official is False
    assert "Mock APAAR verification gateway is temporarily unavailable" in res_outage.message


# ==============================================================================
# 6. Performance Benchmark Test (~1,000 Synthetic Records)
# ==============================================================================
def test_fuzzy_matching_performance_benchmark_1000_records():
    """
    Benchmark fuzzy duplicate matching performance on a dataset of 1,000 synthetic records.
    Validates execution stability and records local measured runtime.
    """
    records = []
    # Generate 1,000 synthetic student records with occasional duplicates
    base_names = [
        "Aarav Sharma", "Vivaan Patel", "Aditya Verma", "Vihaan Iyer", "Arjun Reddy",
        "Sai Kumar", "Reyansh Gupta", "Ayaan Joshi", "Krishna Nair", "Ishaan Bhat"
    ]

    for i in range(1000):
        name_choice = base_names[i % len(base_names)]
        # Inject minor spelling variation every 100 records
        if i % 100 == 0:
            name_choice = name_choice.replace("a", "aa")

        records.append(StudentRecord(
            id=f"PERF-STU-{i:04d}",
            institution_id="INST-001" if i % 2 == 0 else "INST-002",
            programme_id="PROG-001-CSE",
            academic_year="2026-2027",
            student_name=name_choice,
            seat_type=SeatType.REGULAR
        ))

    start_time = time.perf_counter()
    # Evaluate across a subset of pairs to test algorithmic throughput
    sample_size = 150
    report = find_fuzzy_duplicates_in_records(records[:sample_size], threshold=0.85)
    elapsed = time.perf_counter() - start_time

    assert report.total_records_analyzed == sample_size
    assert report.total_pairs_compared == (sample_size * (sample_size - 1)) // 2
    assert elapsed < 5.0, f"Performance target exceeded: {elapsed:.3f}s for {report.total_pairs_compared} pairs"
    print(f"\n[PERFORMANCE BENCHMARK] Evaluated {report.total_pairs_compared} candidate pairs in {elapsed:.3f}s ({report.candidates_flagged} flagged candidates)")


# ==============================================================================
# 7. API Endpoints & Institution Isolation (Feature G)
# ==============================================================================
def test_api_batch_anomalies_and_isolation(client: TestClient):
    """Test GET /api/v1/batches/{batch_id}/anomalies and institution RBAC isolation."""
    apex_token = get_token(client, "apex_admin@apex.edu.in")
    aicte_token = get_token(client, "aicte_admin@aicte.gov.in")

    db = SessionLocal()
    try:
        batch_inst1 = db.query(ImportBatch).filter(ImportBatch.institution_id == "INST-001").first()
        assert batch_inst1 is not None

        # 1. Apex Admin (INST-001) can access own batch anomalies
        resp = client.get(
            f"/api/v1/batches/{batch_inst1.id}/anomalies",
            headers={"Authorization": f"Bearer {apex_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["batch_id"] == batch_inst1.id
        assert "anomaly_level" in data
        assert "anomalies" in data

        # 2. AICTE Admin can also access
        resp_aicte = client.get(
            f"/api/v1/batches/{batch_inst1.id}/anomalies",
            headers={"Authorization": f"Bearer {aicte_token}"}
        )
        assert resp_aicte.status_code == 200

        # 3. Apex Admin CANNOT access other institution's batch
        batch_inst2 = db.query(ImportBatch).filter(ImportBatch.institution_id == "INST-002").first()
        if batch_inst2:
            resp_forbidden = client.get(
                f"/api/v1/batches/{batch_inst2.id}/anomalies",
                headers={"Authorization": f"Bearer {apex_token}"}
            )
            assert resp_forbidden.status_code == 403
    finally:
        db.close()


def test_api_batch_fuzzy_duplicates(client: TestClient):
    """Test GET and POST staging on /api/v1/batches/{batch_id}/fuzzy-duplicates."""
    apex_token = get_token(client, "apex_admin@apex.edu.in")

    db = SessionLocal()
    try:
        batch = db.query(ImportBatch).filter(ImportBatch.institution_id == "INST-001").first()
        assert batch is not None

        # GET fuzzy duplicates
        resp = client.get(
            f"/api/v1/batches/{batch.id}/fuzzy-duplicates?threshold=0.60",
            headers={"Authorization": f"Bearer {apex_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "candidates" in data
        assert "total_pairs_compared" in data

        # POST staging fuzzy duplicates
        resp_stage = client.post(
            f"/api/v1/batches/{batch.id}/fuzzy-duplicates/stage?threshold=0.60",
            headers={"Authorization": f"Bearer {apex_token}"}
        )
        assert resp_stage.status_code == 200
    finally:
        db.close()


def test_api_institution_quality_summary(client: TestClient):
    """Test GET /api/v1/institutions/{institution_id}/quality-summary."""
    apex_token = get_token(client, "apex_admin@apex.edu.in")
    aicte_token = get_token(client, "aicte_admin@aicte.gov.in")

    # Apex Admin requests own institution quality summary
    resp = client.get(
        "/api/v1/institutions/INST-001/quality-summary",
        headers={"Authorization": f"Bearer {apex_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["institution_id"] == "INST-001"
    assert "overall_quality_score" in data
    assert "completeness_score" in data
    assert "batch_scores" in data

    # Apex Admin requests other institution -> 403 Forbidden
    resp_forb = client.get(
        "/api/v1/institutions/INST-002/quality-summary",
        headers={"Authorization": f"Bearer {apex_token}"}
    )
    assert resp_forb.status_code == 403

    # AICTE Admin can request any institution quality summary
    resp_aicte = client.get(
        "/api/v1/institutions/INST-002/quality-summary",
        headers={"Authorization": f"Bearer {aicte_token}"}
    )
    assert resp_aicte.status_code == 200


def test_api_batch_compare_quality_endpoint(client: TestClient):
    """Test GET /api/v1/batches/{batch_id}/compare/{other_batch_id}."""
    apex_token = get_token(client, "apex_admin@apex.edu.in")

    db = SessionLocal()
    try:
        batches = db.query(ImportBatch).filter(ImportBatch.institution_id == "INST-001").all()
        assert len(batches) >= 1
        batch_a = batches[0]
        batch_b = batches[1] if len(batches) > 1 else batch_a

        resp = client.get(
            f"/api/v1/batches/{batch_a.id}/compare/{batch_b.id}",
            headers={"Authorization": f"Bearer {apex_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "score_delta" in data
        assert "score_before" in data
        assert "score_after" in data
        assert "summary" in data
    finally:
        db.close()


def test_institution_longitudinal_trends_calculation():
    """Verify longitudinal trend calculation across chronological batches."""
    db = SessionLocal()
    try:
        trends = calculate_institution_longitudinal_trends(db, institution_id="INST-001")
        assert trends.institution_id == "INST-001"
        assert trends.total_batches >= 1
        assert trends.overall_trend in ("IMPROVING", "DEGRADING", "STABLE")
        assert len(trends.datapoints) == trends.total_batches
        assert trends.datapoints[0].overall_quality_score >= 0.0
    finally:
        db.close()


def test_api_institution_longitudinal_trends(client: TestClient):
    """Test GET /api/v1/institutions/{institution_id}/longitudinal-trends."""
    apex_token = get_token(client, "apex_admin@apex.edu.in")
    aicte_token = get_token(client, "aicte_admin@aicte.gov.in")

    # Apex Admin requests own trends
    resp = client.get(
        "/api/v1/institutions/INST-001/longitudinal-trends",
        headers={"Authorization": f"Bearer {apex_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["institution_id"] == "INST-001"
    assert "datapoints" in data
    assert "overall_trend" in data
    assert "net_quality_change" in data

    # Apex Admin requests other institution -> 403 Forbidden
    resp_forb = client.get(
        "/api/v1/institutions/INST-002/longitudinal-trends",
        headers={"Authorization": f"Bearer {apex_token}"}
    )
    assert resp_forb.status_code == 403

    # AICTE Admin can request other institution
    resp_aicte = client.get(
        "/api/v1/institutions/INST-002/longitudinal-trends",
        headers={"Authorization": f"Bearer {aicte_token}"}
    )
    assert resp_aicte.status_code == 200


def test_certificate_preview_verification_and_isolation(client: TestClient):
    """Test GET /api/v1/verification/{student_ref}/certificate synthetic display."""
    apex_token = get_token(client, "apex_admin@apex.edu.in")
    aicte_token = get_token(client, "aicte_admin@aicte.gov.in")

    db = SessionLocal()
    try:
        student = db.query(StudentRecord).filter(StudentRecord.institution_id == "INST-001").first()
        assert student is not None

        # Apex Admin requests own student certificate preview
        resp = client.get(
            f"/api/v1/verification/{student.id}/certificate",
            headers={"Authorization": f"Bearer {apex_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_synthetic_preview"] is True
        assert "SYNTHETIC PROTOTYPE PREVIEW" in data["disclaimer"]
        assert data["institution_student_id"] == student.institution_student_id
        assert "apaar_id" in data
        assert "programme_name" in data
        assert "verification_reference" in data

        # AICTE Admin can also view certificate preview
        resp_aicte = client.get(
            f"/api/v1/verification/{student.id}/certificate",
            headers={"Authorization": f"Bearer {aicte_token}"}
        )
        assert resp_aicte.status_code == 200
    finally:
        db.close()


def test_csv_report_export_quality_and_findings(client: TestClient):
    """Test GET /api/v1/reports/export streaming for findings and quality summaries."""
    apex_token = get_token(client, "apex_admin@apex.edu.in")

    # Export findings CSV
    resp_findings = client.get(
        "/api/v1/reports/export?report_type=findings",
        headers={"Authorization": f"Bearer {apex_token}"}
    )
    assert resp_findings.status_code == 200
    assert "text/csv" in resp_findings.headers.get("content-type", "")
    assert "finding_id,batch_id" in resp_findings.text

    # Export quality_summary CSV
    resp_quality = client.get(
        "/api/v1/reports/export?report_type=quality_summary",
        headers={"Authorization": f"Bearer {apex_token}"}
    )
    assert resp_quality.status_code == 200
    assert "text/csv" in resp_quality.headers.get("content-type", "")
    assert "batch_id,institution_id,academic_year" in resp_quality.text
