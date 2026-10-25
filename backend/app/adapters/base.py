from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field

from backend.app.models.enums import VerificationOutcome

class VerificationResult(BaseModel):
    """
    Structured outcome of an APAAR verification inquiry.
    Clearly distinguishes:
    1. provider: Name of adapter provider (e.g. MOCK_APAAR_ADAPTER)
    2. outcome: MOCK_VERIFIED, MOCK_NOT_VERIFIED, MOCK_UNAVAILABLE, NEEDS_REVIEW
    3. is_official: Flag explicitly stating whether this inquiry represents official government verification (ALWAYS False for mock).
    4. reference_id: Verifiable transaction tracking receipt.
    5. details: Human-readable explanation.
    """
    apaar_id: str
    provider: str
    outcome: VerificationOutcome
    is_official: bool = Field(False, description="Whether this represents official government verification (False for mock)")
    reference_id: str
    student_name: Optional[str] = None
    institution_id: Optional[str] = None
    message: str
    details: Optional[str] = None
    record_id: Optional[str] = None
    institution_student_id: Optional[str] = None
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    programme_id: Optional[str] = None
    programme_name: Optional[str] = None
    academic_year: Optional[str] = None
    enrolment_status: Optional[str] = None
    seat_type: Optional[str] = None
    audit_trail: list = Field(default_factory=list)

class BaseApaarAdapter(ABC):
    """
    Abstract Provider Interface for APAAR verification.
    Separates format validation, official live verification, and mock inquiry.
    External service outages must never crash batch processing or database operations.
    """

    @abstractmethod
    def verify(
        self,
        apaar_id: str,
        student_name: Optional[str] = None,
        institution_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Conduct verification check against the APAAR service provider.
        """
        pass
