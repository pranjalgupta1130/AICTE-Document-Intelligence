from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional SQLAlchemy session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    Initialize all database tables.
    """
    # Import all models to ensure they are registered with Base.metadata
    from backend.app.models.user import User  # noqa
    from backend.app.models.institution import Institution, Programme, ApprovedIntake  # noqa
    from backend.app.models.student import StudentRecord  # noqa
    from backend.app.models.batch import ImportBatch  # noqa
    from backend.app.models.validation import ValidationFinding  # noqa
    from backend.app.models.match import MatchCandidate  # noqa
    from backend.app.models.verification import VerificationAttempt  # noqa
    from backend.app.models.audit import AuditEvent  # noqa

    Base.metadata.create_all(bind=engine)
