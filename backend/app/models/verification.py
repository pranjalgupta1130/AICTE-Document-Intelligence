from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.db.session import Base
from backend.app.models.enums import VerificationOutcome

class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"

    id = Column(String(64), primary_key=True, default=lambda: f"ver-{uuid.uuid4().hex[:12]}")
    record_id = Column(String(64), ForeignKey("student_records.id", ondelete="CASCADE"), nullable=False, index=True)
    apaar_id = Column(String(32), nullable=False, index=True)
    provider = Column(String(64), default="MOCK_APAAR_ADAPTER", nullable=False)
    outcome = Column(Enum(VerificationOutcome), default=VerificationOutcome.MOCK_VERIFIED, nullable=False)
    reference_id = Column(String(128), nullable=True)
    details = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    record = relationship("StudentRecord")
