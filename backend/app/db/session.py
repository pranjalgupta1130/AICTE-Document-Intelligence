from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
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

# Enforce foreign key constraints in SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
    Initialize all database tables and perform non-destructive schema adjustments.
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

    # Safe non-destructive column check for existing databases
    with engine.connect() as conn:
        try:
            # Check if source_row_number exists in student_records
            result = conn.execute(text("PRAGMA table_info(student_records);"))
            existing_cols = [row[1] for row in result.fetchall()]
            if existing_cols and "source_row_number" not in existing_cols:
                conn.execute(text("ALTER TABLE student_records ADD COLUMN source_row_number INTEGER;"))
                conn.commit()
        except Exception:
            pass
