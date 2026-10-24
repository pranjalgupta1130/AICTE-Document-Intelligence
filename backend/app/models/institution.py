from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.db.session import Base

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(64), unique=True, index=True, nullable=False)
    state = Column(String(128), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    programmes = relationship("Programme", back_populates="institution", cascade="all, delete-orphan")
    approved_intakes = relationship("ApprovedIntake", back_populates="institution", cascade="all, delete-orphan")
    student_records = relationship("StudentRecord", back_populates="institution")
    import_batches = relationship("ImportBatch", back_populates="institution")

class Programme(Base):
    __tablename__ = "programmes"

    id = Column(String(64), primary_key=True)
    institution_id = Column(String(64), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    degree_level = Column(String(64), default="UNDERGRADUATE", nullable=False)
    duration_years = Column(Integer, default=4, nullable=False)

    institution = relationship("Institution", back_populates="programmes")
    approved_intakes = relationship("ApprovedIntake", back_populates="programme", cascade="all, delete-orphan")
    student_records = relationship("StudentRecord", back_populates="programme")

class ApprovedIntake(Base):
    __tablename__ = "approved_intakes"

    id = Column(String(64), primary_key=True)
    institution_id = Column(String(64), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    programme_id = Column(String(64), ForeignKey("programmes.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year = Column(String(32), nullable=False, index=True)
    regular_intake = Column(Integer, default=60, nullable=False)
    supernumerary_intake = Column(Integer, default=0, nullable=False)
    supernumerary_policy = Column(String(512), nullable=True)

    institution = relationship("Institution", back_populates="approved_intakes")
    programme = relationship("Programme", back_populates="approved_intakes")
