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

import logging

logger = logging.getLogger("apaar.database")

def init_db() -> None:
    """
    Initialize all database tables and perform non-destructive schema adjustments.
    Detects legacy duplicate records before applying unique constraints and logs
    clear warnings rather than silently suppressing migration errors.
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

    # Safe non-destructive schema and index checks for existing databases
    with engine.connect() as conn:
        try:
            # Check if source_row_number exists in student_records
            result = conn.execute(text("PRAGMA table_info(student_records);"))
            existing_cols = [row[1] for row in result.fetchall()]
            if existing_cols and "source_row_number" not in existing_cols:
                conn.execute(text("ALTER TABLE student_records ADD COLUMN source_row_number INTEGER;"))
                conn.commit()
                logger.info("Added missing column 'source_row_number' to 'student_records'.")
        except Exception as exc:
            logger.error(f"Failed to inspect or alter 'student_records' table: {exc}", exc_info=True)
            raise

        # Check for legacy duplicates in import_batches before creating index
        try:
            batch_dups = conn.execute(text("""
                SELECT institution_id, academic_year, version, COUNT(*) as cnt
                FROM import_batches
                GROUP BY institution_id, academic_year, version
                HAVING cnt > 1;
            """)).fetchall()

            if batch_dups:
                dup_details = [f"institution={r[0]}, ay={r[1]}, v={r[2]} (count={r[3]})" for r in batch_dups]
                err_msg = f"Cannot create unique index 'uq_batch_institution_ay_version': legacy duplicate batch versions detected: {'; '.join(dup_details)}"
                logger.error(err_msg)
                raise RuntimeError(err_msg)

            # Ensure unique index for batch versioning per (institution_id, academic_year, version)
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_batch_institution_ay_version
                ON import_batches(institution_id, academic_year, version);
            """))
            conn.commit()
        except Exception as exc:
            logger.error(f"Failed to verify or create unique index 'uq_batch_institution_ay_version': {exc}", exc_info=True)
            raise

        # Check for legacy duplicates in match_candidates before creating index
        try:
            match_dups = conn.execute(text("""
                SELECT
                    CASE WHEN record_a_id < record_b_id THEN record_a_id ELSE record_b_id END as a_id,
                    CASE WHEN record_a_id < record_b_id THEN record_b_id ELSE record_a_id END as b_id,
                    COUNT(*) as cnt
                FROM match_candidates
                GROUP BY a_id, b_id
                HAVING cnt > 1;
            """)).fetchall()

            if match_dups:
                dup_details = [f"pair=({r[0]}, {r[1]}) (count={r[2]})" for r in match_dups]
                err_msg = f"Cannot create unique index 'uq_match_candidates_pair': legacy duplicate match candidate pairs detected: {'; '.join(dup_details)}"
                logger.error(err_msg)
                raise RuntimeError(err_msg)

            # Ensure symmetric uniqueness index for match candidate record pairs
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_match_candidates_pair
                ON match_candidates(
                    CASE WHEN record_a_id < record_b_id THEN record_a_id ELSE record_b_id END,
                    CASE WHEN record_a_id < record_b_id THEN record_b_id ELSE record_a_id END
                );
            """))
            conn.commit()
        except Exception as exc:
            logger.error(f"Failed to verify or create unique index 'uq_match_candidates_pair': {exc}", exc_info=True)
            raise
