from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from backend.app.models.enums import BatchStatus, FindingSeverity, FindingStatus

class ColumnMapping(BaseModel):
    apaar_id: Optional[str] = "apaar_id"
    institution_student_id: Optional[str] = "institution_student_id"
    student_name: Optional[str] = "student_name"
    academic_year: Optional[str] = "academic_year"
    programme_id: Optional[str] = "programme_id"
    enrolment_status: Optional[str] = "enrolment_status"
    seat_type: Optional[str] = "seat_type"
    is_nri: Optional[str] = "is_nri"
    is_oci: Optional[str] = "is_oci"
    is_fn: Optional[str] = "is_fn"

class ImportPreviewResponse(BaseModel):
    filename: str
    file_type: str
    detected_columns: List[str]
    suggested_mapping: Dict[str, str]
    total_preview_rows: int
    sample_rows: List[Dict[str, Any]]
    structural_errors: List[str]
    is_valid_structure: bool

class RowParseError(BaseModel):
    row_number: int
    field: Optional[str] = None
    value: Optional[str] = None
    message: str

class ImportCommitResponse(BaseModel):
    batch_id: str
    institution_id: str
    source_filename: str
    academic_year: str
    version: int
    status: BatchStatus
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    row_errors: List[RowParseError]
    errors: Optional[List[RowParseError]] = None

    def model_post_init(self, __context: Any) -> None:
        if self.errors is None:
            self.errors = self.row_errors

class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    uploader_user_id: Optional[str] = None
    source_filename: str
    academic_year: str
    version: int
    status: BatchStatus
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    created_at: datetime
    updated_at: datetime

class ValidationFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: str
    record_id: Optional[str] = None
    row_number: Optional[int] = None
    field_name: Optional[str] = None
    rule_code: str
    severity: FindingSeverity
    message: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    suggested_action: Optional[str] = None
    status: FindingStatus
    created_at: datetime
