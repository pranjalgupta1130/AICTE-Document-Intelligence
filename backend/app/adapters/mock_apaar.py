import re
import uuid
from typing import Optional

from backend.app.adapters.base import BaseApaarAdapter, VerificationResult
from backend.app.models.enums import VerificationOutcome
from backend.app.services.validation_service import validate_verhoeff_checksum

class MockApaarAdapter(BaseApaarAdapter):
    """
    Clearly labelled Mock Provider Adapter for development, evaluation, and hackathon demonstration.
    
    IMPORTANT ARCHITECTURAL SAFEGUARDS:
    - Clearly labelled provider identifier: 'MOCK_APAAR_ADAPTER'.
    - Returns 'is_official=False' in all cases; never claims official live verification.
    - Robustly handles simulated outcomes (MOCK_VERIFIED, MOCK_NOT_VERIFIED, MOCK_UNAVAILABLE, NEEDS_REVIEW).
    - Failures or simulated service outages never crash core validation.
    """
    PROVIDER_NAME = "MOCK_APAAR_ADAPTER"

    def __init__(self, simulate_outage: bool = False):
        self.simulate_outage = simulate_outage

    def verify(
        self,
        apaar_id: str,
        student_name: Optional[str] = None,
        institution_id: Optional[str] = None
    ) -> VerificationResult:
        ref_id = f"mock-ref-{uuid.uuid4().hex[:12]}"

        # 1. Check for simulated service outage
        if self.simulate_outage:
            return VerificationResult(
                apaar_id=apaar_id,
                provider=self.PROVIDER_NAME,
                outcome=VerificationOutcome.MOCK_UNAVAILABLE,
                is_official=False,
                reference_id=ref_id,
                student_name=student_name,
                institution_id=institution_id,
                message="[SIMULATED] Mock APAAR verification gateway is temporarily unavailable.",
                details="Adapter configured in simulated outage mode; core workflows proceed uninterrupted."
            )

        # 2. Check for missing or blank identifier
        if not apaar_id or not str(apaar_id).strip():
            return VerificationResult(
                apaar_id="",
                provider=self.PROVIDER_NAME,
                outcome=VerificationOutcome.MOCK_NOT_VERIFIED,
                is_official=False,
                reference_id=ref_id,
                student_name=student_name,
                institution_id=institution_id,
                message="[SIMULATED] Missing APAAR ID cannot be verified.",
                details="Identifier is blank or null."
            )

        clean_id = str(apaar_id).strip()

        # 3. Check syntax format (12 digits numeric)
        if not re.match(r"^\d{12}$", clean_id):
            return VerificationResult(
                apaar_id=clean_id,
                provider=self.PROVIDER_NAME,
                outcome=VerificationOutcome.MOCK_NOT_VERIFIED,
                is_official=False,
                reference_id=ref_id,
                student_name=student_name,
                institution_id=institution_id,
                message="[SIMULATED] APAAR ID format invalid (must be 12 numeric digits).",
                details="Syntactic format check failed before verification lookup."
            )

        # 4. Check simulated test prefixes (e.g. test ranges for simulated NEEDS_REVIEW or UNAVAILABLE)
        if clean_id.startswith("0000"):
            return VerificationResult(
                apaar_id=clean_id,
                provider=self.PROVIDER_NAME,
                outcome=VerificationOutcome.NEEDS_REVIEW,
                is_official=False,
                reference_id=ref_id,
                student_name=student_name,
                institution_id=institution_id,
                message="[SIMULATED] Synthetic record flagged for manual human verification.",
                details="Simulated provider ambiguity requiring human documentation check."
            )

        if clean_id.startswith("9999"):
            return VerificationResult(
                apaar_id=clean_id,
                provider=self.PROVIDER_NAME,
                outcome=VerificationOutcome.MOCK_UNAVAILABLE,
                is_official=False,
                reference_id=ref_id,
                student_name=student_name,
                institution_id=institution_id,
                message="[SIMULATED] Mock gateway error on test synthetic ID prefix.",
                details="Simulated transient upstream timeout."
            )

        # 5. Check Verhoeff checksum
        if not validate_verhoeff_checksum(clean_id):
            return VerificationResult(
                apaar_id=clean_id,
                provider=self.PROVIDER_NAME,
                outcome=VerificationOutcome.MOCK_NOT_VERIFIED,
                is_official=False,
                reference_id=ref_id,
                student_name=student_name,
                institution_id=institution_id,
                message="[SIMULATED] APAAR ID failed Verhoeff checksum validation.",
                details="Syntactic checksum verification failed."
            )


        # 6. Default synthetic success
        return VerificationResult(
            apaar_id=clean_id,
            provider=self.PROVIDER_NAME,
            outcome=VerificationOutcome.MOCK_VERIFIED,
            is_official=False,
            reference_id=ref_id,
            student_name=student_name,
            institution_id=institution_id,
            message="[SIMULATED] Synthetically verified against Mock APAAR Adapter.",
            details="Valid 12-digit format and Verhoeff checksum. Clearly marked as simulated verification."
        )
