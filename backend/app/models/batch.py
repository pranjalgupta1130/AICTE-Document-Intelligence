from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.db.session import Base
from backend.app.models.enums import BatchStatus

class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(String(64), primary_key=True, default=lambda: f"BATCH-{uuid.uuid4().hex[:12]}")
    institution_id = Column(String(64), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    uploader_user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_filename = Column(String(255), nullable=False)
    academic_year = Column(String(32), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(Enum(BatchStatus), default=BatchStatus.DRAFT, nullable=False)
    total_rows = Column(Integer, default=0, nullable=False)
    valid_rows = Column(Integer, default=0, nullable=False)
    error_rows = Column(Integer, default=0, nullable=False)
    warning_rows = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    institution = relationship("Institution", back_populates="import_batches")
    uploader = relationship("User")
    student_records = relationship("StudentRecord", back_populates="batch", cascade="all, delete-orphan")
    findings = relationship("ValidationFinding", back_populates="batch", cascade="all, delete-orphan")
