from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.db.session import Base
from backend.app.models.enums import EnrolmentStatus, SeatType

class StudentRecord(Base):
    __tablename__ = "student_records"

    id = Column(String(64), primary_key=True, default=lambda: f"stu-{uuid.uuid4().hex[:12]}")
    batch_id = Column(String(64), ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = Column(String(64), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    programme_id = Column(String(64), ForeignKey("programmes.id", ondelete="CASCADE"), nullable=False, index=True)
    apaar_id = Column(String(32), nullable=True, index=True)
    institution_student_id = Column(String(64), nullable=False, index=True)
    student_name = Column(String(255), nullable=True)
    academic_year = Column(String(32), nullable=False, index=True)
    enrolment_status = Column(Enum(EnrolmentStatus), default=EnrolmentStatus.ENROLLED, nullable=False)
    seat_type = Column(Enum(SeatType), default=SeatType.REGULAR, nullable=False)
    is_nri = Column(Boolean, default=False, nullable=False)
    is_oci = Column(Boolean, default=False, nullable=False)
    is_fn = Column(Boolean, default=False, nullable=False)
    source_row_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    batch = relationship("ImportBatch", back_populates="student_records")
    institution = relationship("Institution", back_populates="student_records")
    programme = relationship("Programme", back_populates="student_records")
    findings = relationship("ValidationFinding", back_populates="student_record", cascade="all, delete-orphan")
