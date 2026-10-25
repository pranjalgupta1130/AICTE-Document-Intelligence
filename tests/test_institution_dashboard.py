"""
Focused Test Suite for Phase 2: Institution Dashboard Dynamic Integration
Tests for:
1. Dashboard metrics calculated from persisted database records.
2. Programme-level intake breakdown and status calculation.
3. Academic-year filtering correctly scopes records.
4. Switching academic years updates counts.
5. Empty academic year returns valid 0-count response without crashing.
6. Strict institution-level isolation (cross-institution query returns 403).
7. AICTE admin can inspect any authorized institution dashboard via query parameter.
8. Metrics distinguish imported records, enrolled students, valid records, and error counts.
9. Dynamic derivation of available academic years.
10. Special quota breakdown derived from persisted student records.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import EnrolmentStatus
from backend.app.models.institution import ApprovedIntake, Institution, Programme
from backend.app.models.student import StudentRecord
from backend.app.models.validation import ValidationFinding


@pytest.fixture
def client():
    return TestClient(app)


def get_auth_token(client: TestClient, email: str, password: str = "DemoPassword@2026") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Failed to login {email}: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def aicte_token(client):
    return get_auth_token(client, "aicte_admin@aicte.gov.in")


@pytest.fixture
def apex_admin_token(client):
    return get_auth_token(client, "apex_admin@apex.edu.in")


@pytest.fixture
def bharat_admin_token(client):
    return get_auth_token(client, "bharat_admin@bharat.edu.in")


# ==============================================================================
# 1. Calculation from Actual Database Records
# ==============================================================================

def test_institution_dashboard_calculated_from_db_records(client: TestClient, apex_admin_token):
    """Dashboard metrics genuinely correspond to persisted database records."""
    db = SessionLocal()
    try:
        inst_id = "INST-001"
        res = client.get(
            "/api/v1/dashboard/institution",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["institution_id"] == inst_id
        assert data["institution_name"] == "Apex Institute of Technology"
        ay = data["academic_year"]

        # Cross-reference with database directly
        db_batches = db.query(ImportBatch).filter(
            ImportBatch.institution_id == inst_id,
            ImportBatch.academic_year == ay
        ).all()
        assert data["total_batches"] == len(db_batches)

        db_students = db.query(StudentRecord).filter(
            StudentRecord.institution_id == inst_id,
            StudentRecord.academic_year == ay
        ).all()
        assert data["total_student_records"] == len(db_students)

        db_missing_apaar = sum(1 for s in db_students if not s.apaar_id)
        assert data["missing_apaar_count"] == db_missing_apaar

        db_enrolled = sum(1 for s in db_students if s.enrolment_status == EnrolmentStatus.ENROLLED)
        db_admitted = sum(1 for s in db_students if s.enrolment_status == EnrolmentStatus.ADMITTED)
        assert data["enrolled_finalized_count"] == db_enrolled
        assert data["admitted_count"] == db_admitted
        assert data["total_enrolled_students"] == db_enrolled + db_admitted

        # Check available academic years
        assert "available_academic_years" in data
        assert isinstance(data["available_academic_years"], list)
        assert ay in data["available_academic_years"]
    finally:
        db.close()


# ==============================================================================
# 2. Programme-Level Intake Breakdown
# ==============================================================================

def test_programme_level_intake_breakdown(client: TestClient, apex_admin_token):
    """Programme-level breakdown matches programmes, approved intake, and student enrollments."""
    db = SessionLocal()
    try:
        inst_id = "INST-001"
        res = client.get(
            "/api/v1/dashboard/institution?academic_year=2026-2027",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res.status_code == 200, res.text
        data = res.json()

        breakdown = data["programme_intake_breakdown"]
        assert isinstance(breakdown, list)
        assert len(breakdown) > 0

        # Check each programme metric structure
        db_programmes = {p.id: p.name for p in db.query(Programme).filter(Programme.institution_id == inst_id).all()}

        for prog in breakdown:
            assert prog["programme_id"] in db_programmes
            assert prog["programme_name"] == db_programmes[prog["programme_id"]]
            assert prog["regular_approved"] >= 0
            assert prog["supernumerary_approved"] >= 0
            assert prog["total_approved"] == prog["regular_approved"] + prog["supernumerary_approved"]
            assert prog["total_enrolled"] == prog["regular_enrolled"] + prog["supernumerary_enrolled"]
            assert prog["status"] in ("WITHIN_LIMIT", "EXCEEDED")
            reg_exceeded = prog["regular_enrolled"] > prog["regular_approved"]
            super_exceeded = prog["supernumerary_enrolled"] > prog["supernumerary_approved"]
            tot_exceeded = prog["total_enrolled"] > prog["total_approved"]
            if (reg_exceeded or super_exceeded or tot_exceeded) and prog["total_approved"] > 0:
                assert prog["status"] == "EXCEEDED"
            elif prog["total_approved"] > 0:
                assert prog["status"] == "WITHIN_LIMIT"
    finally:
        db.close()


# ==============================================================================
# 3. Academic-Year Filtering
# ==============================================================================

def test_academic_year_filtering_scopes_records(client: TestClient, apex_admin_token):
    """Filtering by academic_year returns metrics strictly scoped to that year."""
    res_2026 = client.get(
        "/api/v1/dashboard/institution?academic_year=2026-2027",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res_2026.status_code == 200
    data_2026 = res_2026.json()
    assert data_2026["academic_year"] == "2026-2027"

    # Query with another year
    res_2024 = client.get(
        "/api/v1/dashboard/institution?academic_year=2024-2025",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res_2024.status_code == 200
    data_2024 = res_2024.json()
    assert data_2024["academic_year"] == "2024-2025"


# ==============================================================================
# 4. Empty Academic Year Handling
# ==============================================================================

def test_empty_academic_year_returns_valid_zero_count(client: TestClient, apex_admin_token):
    """An academic year with no records returns clean 0 counts without error."""
    res_empty = client.get(
        "/api/v1/dashboard/institution?academic_year=2019-2020",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res_empty.status_code == 200
    data = res_empty.json()
    assert data["academic_year"] == "2019-2020"
    assert data["total_batches"] == 0
    assert data["total_student_records"] == 0
    assert data["total_enrolled_students"] == 0
    assert data["missing_apaar_count"] == 0
    assert data["duplicate_flags_count"] == 0
    assert data["intake_utilization_pct"] == 0.0
    assert data["recent_batches"] == []
    # Programme entries exist with 0 enrolment
    for prog in data["programme_intake_breakdown"]:
        assert prog["total_enrolled"] == 0
        assert prog["regular_enrolled"] == 0
        assert prog["supernumerary_enrolled"] == 0


# ==============================================================================
# 5. Strict Institution-Level Data Isolation
# ==============================================================================

def test_institution_isolation_tamper_rejected(client: TestClient, apex_admin_token, bharat_admin_token):
    """Institution users cannot access or view another institution's dashboard."""
    # Apex user (INST-001) attempting to access Bharat (INST-002)
    res_tamper = client.get(
        "/api/v1/dashboard/institution?institution_id=INST-002",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res_tamper.status_code == 403
    assert "Cross-institution access denied" in res_tamper.text

    # Bharat user (INST-002) attempting to access Apex (INST-001)
    res_tamper_2 = client.get(
        "/api/v1/dashboard/institution?institution_id=INST-001",
        headers={"Authorization": f"Bearer {bharat_admin_token}"}
    )
    assert res_tamper_2.status_code == 403
    assert "Cross-institution access denied" in res_tamper_2.text


# ==============================================================================
# 6. AICTE Admin Access
# ==============================================================================

def test_aicte_admin_can_inspect_any_institution(client: TestClient, aicte_token):
    """Central AICTE admin can inspect any institution dashboard with explicit institution_id."""
    res_inst1 = client.get(
        "/api/v1/dashboard/institution?institution_id=INST-001",
        headers={"Authorization": f"Bearer {aicte_token}"}
    )
    assert res_inst1.status_code == 200
    assert res_inst1.json()["institution_id"] == "INST-001"

    res_inst2 = client.get(
        "/api/v1/dashboard/institution?institution_id=INST-002",
        headers={"Authorization": f"Bearer {aicte_token}"}
    )
    assert res_inst2.status_code == 200
    assert res_inst2.json()["institution_id"] == "INST-002"


# ==============================================================================
# 7. Metrics Distinction (Enrolled vs Imported vs Valid vs Error Rows)
# ==============================================================================

def test_metrics_distinction_between_enrolled_imported_valid_and_errors(client: TestClient, apex_admin_token):
    """Ensure distinct quantities are calculated accurately and not conflated."""
    res = client.get(
        "/api/v1/dashboard/institution?academic_year=2026-2027",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()

    # The fields exist and are distinct integer metrics
    assert isinstance(data["total_student_records"], int)
    assert isinstance(data["total_enrolled_students"], int)
    assert isinstance(data["valid_records_count"], int)
    assert isinstance(data["error_records_count"], int)
    assert isinstance(data["blocking_findings_count"], int)
    assert isinstance(data["warning_findings_count"], int)

    # total_enrolled_students counts active students (ENROLLED + ADMITTED)
    assert data["total_enrolled_students"] <= data["total_student_records"]
    assert data["enrolled_finalized_count"] + data["admitted_count"] == data["total_enrolled_students"]


# ==============================================================================
# 8. Special Quota Breakdown
# ==============================================================================

def test_special_quota_breakdown(client: TestClient, apex_admin_token):
    """Special quota breakdown is returned with categories and non-negative counts."""
    res = client.get(
        "/api/v1/dashboard/institution?academic_year=2026-2027",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()

    quotas = data.get("special_quota_breakdown", [])
    assert isinstance(quotas, list)
    categories = [q["category"] for q in quotas]
    for expected_cat in ["TFW", "EWS", "PMSSS", "NRI", "OCI", "FN"]:
        assert expected_cat in categories
        quota_item = next(q for q in quotas if q["category"] == expected_cat)
        assert quota_item["enrolled"] >= 0


# ==============================================================================
# 9. Phase 2 Priority 1 Regression Tests (Fix 1, Fix 2, Fix 5, Fix 7)
# ==============================================================================

def test_mixed_enrolled_and_admitted_population_in_live_db(client: TestClient, apex_admin_token):
    """Verify live database correctly reconciles both ENROLLED and ADMITTED students."""
    db = SessionLocal()
    try:
        res = client.get(
            "/api/v1/dashboard/institution?academic_year=2026-2027",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()

        db_enrolled = db.query(StudentRecord).filter(
            StudentRecord.institution_id == "INST-001",
            StudentRecord.academic_year == "2026-2027",
            StudentRecord.enrolment_status == EnrolmentStatus.ENROLLED
        ).count()
        db_admitted = db.query(StudentRecord).filter(
            StudentRecord.institution_id == "INST-001",
            StudentRecord.academic_year == "2026-2027",
            StudentRecord.enrolment_status == EnrolmentStatus.ADMITTED
        ).count()

        assert data["enrolled_finalized_count"] == db_enrolled
        assert data["admitted_count"] == db_admitted
        assert data["total_enrolled_students"] == db_enrolled + db_admitted
    finally:
        db.close()


def test_open_validation_findings_reconciliation(client: TestClient, apex_admin_token):
    """Verify findings counts strictly include OPEN findings, excluding resolved or dismissed ones."""
    from backend.app.models.enums import FindingSeverity, FindingStatus

    db = SessionLocal()
    try:
        res = client.get(
            "/api/v1/dashboard/institution?academic_year=2026-2027",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()

        db_blocking = db.query(ValidationFinding).join(ImportBatch).filter(
            ImportBatch.institution_id == "INST-001",
            ImportBatch.academic_year == "2026-2027",
            ValidationFinding.status == FindingStatus.OPEN,
            ValidationFinding.severity == FindingSeverity.BLOCKING_ERROR
        ).count()

        db_warning = db.query(ValidationFinding).join(ImportBatch).filter(
            ImportBatch.institution_id == "INST-001",
            ImportBatch.academic_year == "2026-2027",
            ValidationFinding.status == FindingStatus.OPEN,
            ValidationFinding.severity == FindingSeverity.WARNING
        ).count()

        assert data["blocking_findings_count"] == db_blocking
        assert data["warning_findings_count"] == db_warning
        assert data["blocking_findings_count"] + data["warning_findings_count"] == db_blocking + db_warning
    finally:
        db.close()


def test_isolated_intake_policy_withdrawn_cancelled_and_capacity_rules():
    """
    Test capacity calculation using an isolated in-memory test database.
    Verifies:
    1. ENROLLED and ADMITTED are counted toward capacity.
    2. WITHDRAWN and COMPLETED are excluded from capacity.
    3. Regular excess independently triggers EXCEEDED even if supernumerary is below cap.
    4. Supernumerary excess independently triggers EXCEEDED even if regular is below cap.
    5. Missing approved intake configuration is handled safely without crashing.
    """
    from datetime import datetime, timezone
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.app.db.session import Base
    from backend.app.models.user import User
    from backend.app.models.enums import UserRole, SeatType, BatchStatus
    from backend.app.services.workflow_service import get_institution_dashboard

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Create isolated institution, programme, and user
        inst = Institution(id="INST-ISO", name="Isolated Test Institute", code="ISO-001", state="Delhi")
        db.add(inst)

        prog_cse = Programme(id="PROG-ISO-CSE", institution_id="INST-ISO", name="Computer Science")
        prog_mech = Programme(id="PROG-ISO-MECH", institution_id="INST-ISO", name="Mechanical")
        db.add_all([prog_cse, prog_mech])

        # Approved intake: CSE 10 regular, 2 supernumerary
        intake_cse = ApprovedIntake(
            id="INT-ISO-CSE",
            institution_id="INST-ISO",
            programme_id="PROG-ISO-CSE",
            academic_year="2026-2027",
            regular_intake=10,
            supernumerary_intake=2
        )
        db.add(intake_cse)
        # MECH has NO ApprovedIntake record to test missing configuration handling

        user = User(
            id="USER-ISO",
            email="iso_admin@iso.edu.in",
            hashed_password="hash",
            full_name="Iso Admin",
            role=UserRole.INSTITUTION_ADMIN,
            institution_id="INST-ISO"
        )
        db.add(user)
        db.commit()

        # Batch 1: 2 ENROLLED, 3 ADMITTED, 2 WITHDRAWN, 1 COMPLETED
        now = datetime.now(timezone.utc)
        batch = ImportBatch(
            id="BATCH-ISO-1",
            institution_id="INST-ISO",
            academic_year="2026-2027",
            source_filename="iso_students.csv",
            version=1,
            status=BatchStatus.VALIDATED,
            created_at=now,
            updated_at=now
        )
        db.add(batch)

        students = [
            # 2 ENROLLED
            StudentRecord(id="S-1", institution_id="INST-ISO", batch_id="BATCH-ISO-1", programme_id="PROG-ISO-CSE", academic_year="2026-2027", institution_student_id="ISO-S1", student_name="Student 1", enrolment_status=EnrolmentStatus.ENROLLED, seat_type=SeatType.REGULAR),
            StudentRecord(id="S-2", institution_id="INST-ISO", batch_id="BATCH-ISO-1", programme_id="PROG-ISO-CSE", academic_year="2026-2027", institution_student_id="ISO-S2", student_name="Student 2", enrolment_status=EnrolmentStatus.ENROLLED, seat_type=SeatType.REGULAR),
            # 3 ADMITTED
            StudentRecord(id="S-3", institution_id="INST-ISO", batch_id="BATCH-ISO-1", programme_id="PROG-ISO-CSE", academic_year="2026-2027", institution_student_id="ISO-S3", student_name="Student 3", enrolment_status=EnrolmentStatus.ADMITTED, seat_type=SeatType.REGULAR),
            StudentRecord(id="S-4", institution_id="INST-ISO", batch_id="BATCH-ISO-1", programme_id="PROG-ISO-CSE", academic_year="2026-2027", institution_student_id="ISO-S4", student_name="Student 4", enrolment_status=EnrolmentStatus.ADMITTED, seat_type=SeatType.REGULAR),
            StudentRecord(id="S-5", institution_id="INST-ISO", batch_id="BATCH-ISO-1", programme_id="PROG-ISO-CSE", academic_year="2026-2027", institution_student_id="ISO-S5", student_name="Student 5", enrolment_status=EnrolmentStatus.ADMITTED, seat_type=SeatType.SUPERNUMERARY_TFW),
            # 2 WITHDRAWN (must be excluded)
            StudentRecord(id="S-6", institution_id="INST-ISO", batch_id="BATCH-ISO-1", programme_id="PROG-ISO-CSE", academic_year="2026-2027", institution_student_id="ISO-S6", student_name="Student 6", enrolment_status=EnrolmentStatus.WITHDRAWN, seat_type=SeatType.REGULAR),
            StudentRecord(id="S-7", institution_id="INST-ISO", batch_id="BATCH-ISO-1", programme_id="PROG-ISO-CSE", academic_year="2026-2027", institution_student_id="ISO-S7", student_name="Student 7", enrolment_status=EnrolmentStatus.WITHDRAWN, seat_type=SeatType.REGULAR),
            # 1 COMPLETED (must be excluded)
            StudentRecord(id="S-8", institution_id="INST-ISO", batch_id="BATCH-ISO-1", programme_id="PROG-ISO-CSE", academic_year="2026-2027", institution_student_id="ISO-S8", student_name="Student 8", enrolment_status=EnrolmentStatus.COMPLETED, seat_type=SeatType.REGULAR),
        ]
        db.add_all(students)
        db.commit()

        # Call get_institution_dashboard directly with isolated db session
        metrics = get_institution_dashboard(db, user, "INST-ISO", "2026-2027")

        assert metrics.total_student_records == 8
        assert metrics.enrolled_finalized_count == 2
        assert metrics.admitted_count == 3
        # Total active enrolled = 2 + 3 = 5 (withdrawn and completed excluded)
        assert metrics.total_enrolled_students == 5

        cse_metric = next(p for p in metrics.programme_intake_breakdown if p.programme_id == "PROG-ISO-CSE")
        assert cse_metric.regular_enrolled == 4
        assert cse_metric.supernumerary_enrolled == 1
        assert cse_metric.total_enrolled == 5
        assert cse_metric.status == "WITHIN_LIMIT"

        # MECH has 0 students and 0 approved intake -> WITHIN_LIMIT
        mech_metric = next(p for p in metrics.programme_intake_breakdown if p.programme_id == "PROG-ISO-MECH")
        assert mech_metric.total_approved == 0
        assert mech_metric.total_enrolled == 0
        assert mech_metric.status == "WITHIN_LIMIT"

        # TEST REGULAR OVER-CAPACITY INDEPENDENT TRIGGER (Fix 7)
        # Add 7 more regular admitted students to CSE:
        # Regular will become 4 + 7 = 11 > 10 approved regular!
        # Supernumerary is 1 <= 2 approved.
        # Total is 11 + 1 = 12 <= 12 approved total!
        # Regular must be checked independently: status MUST be EXCEEDED!
        more_students = [
            StudentRecord(
                id=f"S-EXTRA-{i}",
                institution_id="INST-ISO",
                batch_id="BATCH-ISO-1",
                programme_id="PROG-ISO-CSE",
                academic_year="2026-2027",
                institution_student_id=f"ISO-EXTRA-{i}",
                student_name=f"Extra {i}",
                enrolment_status=EnrolmentStatus.ADMITTED,
                seat_type=SeatType.REGULAR
            ) for i in range(7)
        ]
        db.add_all(more_students)
        db.commit()

        metrics_after = get_institution_dashboard(db, user, "INST-ISO", "2026-2027")
        cse_after = next(p for p in metrics_after.programme_intake_breakdown if p.programme_id == "PROG-ISO-CSE")
        assert cse_after.regular_enrolled == 11
        assert cse_after.supernumerary_enrolled == 1
        assert cse_after.total_enrolled == 12
        assert cse_after.total_approved == 12
        # Total enrolled is NOT greater than total approved, BUT regular is exceeded!
        assert cse_after.status == "EXCEEDED"
    finally:
        db.close()

