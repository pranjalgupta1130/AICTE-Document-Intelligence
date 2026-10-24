from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.db.session import Base
from backend.app.models.enums import MatchStatus

class MatchCandidate(Base):
    __tablename__ = "match_candidates"

    id = Column(String(64), primary_key=True, default=lambda: f"mat-{uuid.uuid4().hex[:12]}")
    record_a_id = Column(String(64), ForeignKey("student_records.id", ondelete="CASCADE"), nullable=False, index=True)
    record_b_id = Column(String(64), ForeignKey("student_records.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_a_id = Column(String(64), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_b_id = Column(String(64), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    matching_signal = Column(String(128), nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    status = Column(Enum(MatchStatus), default=MatchStatus.CANDIDATE, nullable=False)
    resolution_reason = Column(String(512), nullable=True)
    reviewed_by = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    record_a = relationship("StudentRecord", foreign_keys=[record_a_id])
    record_b = relationship("StudentRecord", foreign_keys=[record_b_id])
    institution_a = relationship("Institution", foreign_keys=[institution_a_id])
    institution_b = relationship("Institution", foreign_keys=[institution_b_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
