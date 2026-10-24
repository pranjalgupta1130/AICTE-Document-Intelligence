from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.db.session import Base
from backend.app.models.enums import FindingSeverity, FindingStatus

class ValidationFinding(Base):
    __tablename__ = "validation_findings"

    id = Column(String(64), primary_key=True, default=lambda: f"fnd-{uuid.uuid4().hex[:12]}")
    batch_id = Column(String(64), ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    record_id = Column(String(64), ForeignKey("student_records.id", ondelete="CASCADE"), nullable=True, index=True)
    row_number = Column(Integer, nullable=True)
    field_name = Column(String(64), nullable=True)
    rule_code = Column(String(64), nullable=False, index=True)
    severity = Column(Enum(FindingSeverity), default=FindingSeverity.BLOCKING_ERROR, nullable=False)
    message = Column(String(512), nullable=False)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    suggested_action = Column(String(512), nullable=True)
    status = Column(Enum(FindingStatus), default=FindingStatus.OPEN, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    batch = relationship("ImportBatch", back_populates="findings")
    student_record = relationship("StudentRecord", back_populates="findings")
