from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from backend.app.models.enums import BatchStatus, FindingStatus, MatchStatus

# ------------------------------------------------------------------------------
# Batch Submission Schemas
# ------------------------------------------------------------------------------
class BatchSubmitRequest(BaseModel):
    allow_warnings: bool = Field(True, description="Whether submission is permitted when only warnings exist")
    comments: Optional[str] = Field(None, description="Optional submission notes/comments")

class BatchSubmitResponse(BaseModel):
    batch_id: str
    institution_id: str
    status: BatchStatus
    version: int
    submitted_at: datetime
    submitted_by: str
    valid_rows: int
    error_rows: int
    warning_rows: int
    message: str

# ------------------------------------------------------------------------------
# Review Decision Schemas (Findings & Candidates)
# ------------------------------------------------------------------------------
class FindingReviewRequest(BaseModel):
    decision: FindingStatus = Field(..., description="Review outcome: RESOLVED or DISMISSED")
    reason: str = Field(..., min_length=3, max_length=512, description="Mandatory reason for audit trail")

class FindingReviewResponse(BaseModel):
    finding_id: str
    batch_id: str
    status: FindingStatus
    reviewed_by: str
    reviewed_at: datetime
    reason: str
    message: str

class MatchCandidateReviewRequest(BaseModel):
    status: MatchStatus = Field(..., description="Review outcome: CONFIRMED_DUPLICATE or DISMISSED")
    resolution_reason: str = Field(..., min_length=3, max_length=512, description="Mandatory reason for decision")

class BatchReviewDecision(str, Enum):
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"

class BatchReviewRequest(BaseModel):
    decision: BatchReviewDecision = Field(..., description="Review outcome: UNDER_REVIEW, ACCEPTED, REJECTED, or NEEDS_CORRECTION")
    reason: str = Field(..., min_length=3, max_length=512, description="Mandatory justification/reason for audit trail")

class BatchReviewResponse(BaseModel):
    batch_id: str
    institution_id: str
    previous_status: BatchStatus
    status: BatchStatus
    reviewed_by: str
    reviewed_at: datetime
    reason: str
    message: str

# ------------------------------------------------------------------------------
# Dashboard Metrics Schemas
# ------------------------------------------------------------------------------
class ProgrammeIntakeMetric(BaseModel):
    programme_id: str
    programme_name: str
    regular_approved: int
    regular_enrolled: int
    supernumerary_approved: int
    supernumerary_enrolled: int
    total_approved: int
    total_enrolled: int
    utilization_pct: float
    status: str  # WITHIN_LIMIT or EXCEEDED

class RecentBatchSummary(BaseModel):
    id: str
    source_filename: str
    academic_year: str
    version: int
    status: BatchStatus
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    created_at: datetime

class RecentActivityItem(BaseModel):
    timestamp: datetime
    action: str
    actor_email: str
    actor_role: str
    details: Optional[str] = None
    outcome: str

class InstitutionDashboardMetrics(BaseModel):
    institution_id: str
    institution_name: str
    academic_year: str
    total_batches: int
    latest_batch_status: Optional[BatchStatus] = None
    total_student_records: int
    valid_records_count: int
    error_records_count: int
    missing_apaar_count: int
    duplicate_flags_count: int
    intake_utilization_pct: float
    total_approved_intake: int
    total_enrolled_students: int
    programme_intake_breakdown: List[ProgrammeIntakeMetric]
    recent_batches: List[RecentBatchSummary]
    recent_activity: List[RecentActivityItem]

class InstitutionEnrolmentSummary(BaseModel):
    institution_id: str
    institution_name: str
    state: str
    total_batches: int
    latest_status: Optional[BatchStatus] = None
    total_enrolled: int
    total_approved: int
    intake_utilization_pct: float
    open_exceptions_count: int

class AICTEDashboardMetrics(BaseModel):
    academic_year: str
    total_institutions: int
    total_submissions: int
    total_batches: int
    total_enrolled_students: int
    total_approved_intake: int
    aggregate_intake_utilization_pct: float
    total_open_exceptions: int
    total_candidate_duplicates: int
    confirmed_duplicates_count: int
    dismissed_duplicates_count: int
    institution_breakdown: List[InstitutionEnrolmentSummary]
    recent_activity: List[RecentActivityItem]
