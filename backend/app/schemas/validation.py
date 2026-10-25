from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from backend.app.models.enums import BatchStatus, EnrolmentStatus, FindingSeverity, FindingStatus, MatchStatus, SeatType

class ValidationSummary(BaseModel):
    total_records: int
    valid_records: int
    error_count: int
    warning_count: int
    info_count: int
    intake_exceeded_count: int
    duplicate_candidate_count: int

class IntakeReconciliationSummary(BaseModel):
    programme_id: str
    programme_name: str
    academic_year: str
    regular_approved: int
    regular_enrolled: int
    regular_exceeded: int
    supernumerary_approved: int
    supernumerary_enrolled: int
    supernumerary_exceeded: int
    total_approved: int
    total_enrolled: int
    total_exceeded: int
    status: str  # "WITHIN_LIMIT", "EXCEEDED"

class BatchValidationResponse(BaseModel):
    batch_id: str
    institution_id: str
    status: BatchStatus
    validation_summary: ValidationSummary
    intake_reconciliation: List[IntakeReconciliationSummary]
    findings_count: int
    message: str

class CandidateProgrammeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str

class CandidateStudentRecordDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_name: Optional[str] = None
    institution_student_id: Optional[str] = None
    apaar_id: Optional[str] = None
    academic_year: Optional[str] = None
    seat_type: Optional[SeatType] = None
    enrolment_status: Optional[EnrolmentStatus] = None
    programme_id: Optional[str] = None
    programme: Optional[CandidateProgrammeDetail] = None

class CandidateInstitutionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    state: str

class MatchCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    record_a_id: str
    record_b_id: str
    institution_a_id: str
    institution_b_id: str
    matching_signal: str
    confidence: float
    status: MatchStatus
    resolution_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[Any] = None
    created_at: Optional[Any] = None
    record_a: Optional[CandidateStudentRecordDetail] = None
    record_b: Optional[CandidateStudentRecordDetail] = None
    institution_a: Optional[CandidateInstitutionDetail] = None
    institution_b: Optional[CandidateInstitutionDetail] = None
