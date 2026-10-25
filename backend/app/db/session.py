from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.app.core.config import settings

engine_kwargs = {"echo": False}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
else:
    # Client-server databases (e.g. PostgreSQL, MySQL) benefit from connection pooling
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

# Enforce foreign key constraints, WAL journal mode, and busy timeout in SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
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
    dialect_name = engine.dialect.name.lower()
    with engine.connect() as conn:
        # 1. Check if source_row_number exists in student_records (SQLite PRAGMA or ANSI INFORMATION_SCHEMA)
        try:
            if dialect_name == "sqlite":
                result = conn.execute(text("PRAGMA table_info(student_records);"))
                existing_cols = [row[1] for row in result.fetchall()]
                if existing_cols and "source_row_number" not in existing_cols:
                    conn.execute(text("ALTER TABLE student_records ADD COLUMN source_row_number INTEGER;"))
                    conn.commit()
                    logger.info("Added missing column 'source_row_number' to 'student_records'.")

                # Check if storage_path and file_size_bytes exist in import_batches
                batch_cols_res = conn.execute(text("PRAGMA table_info(import_batches);"))
                batch_cols = [row[1] for row in batch_cols_res.fetchall()]
                if batch_cols and "storage_path" not in batch_cols:
                    conn.execute(text("ALTER TABLE import_batches ADD COLUMN storage_path VARCHAR(512);"))
                    conn.commit()
                    logger.info("Added missing column 'storage_path' to 'import_batches'.")
                if batch_cols and "file_size_bytes" not in batch_cols:
                    conn.execute(text("ALTER TABLE import_batches ADD COLUMN file_size_bytes INTEGER;"))
                    conn.commit()
                    logger.info("Added missing column 'file_size_bytes' to 'import_batches'.")
            elif dialect_name in ("postgresql", "postgres"):
                col_check = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'student_records' AND column_name = 'source_row_number';
                """)).fetchone()
                if not col_check:
                    conn.execute(text("ALTER TABLE student_records ADD COLUMN IF NOT EXISTS source_row_number INTEGER;"))
                    conn.commit()
                    logger.info("Added missing column 'source_row_number' to 'student_records'.")

                conn.execute(text("ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS storage_path VARCHAR(512);"))
                conn.execute(text("ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER;"))
                conn.commit()
        except Exception as exc:
            logger.error(f"Failed to inspect or alter database tables: {exc}", exc_info=True)
            raise

        # 2. Check for legacy duplicates in import_batches before creating index
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

        # 3. Check for legacy duplicates in match_candidates and create symmetric index dialect-safely
        try:
            if dialect_name in ("postgresql", "postgres"):
                # PostgreSQL supports LEAST and GREATEST scalar functions natively
                match_dups = conn.execute(text("""
                    SELECT
                        LEAST(record_a_id, record_b_id) as a_id,
                        GREATEST(record_a_id, record_b_id) as b_id,
                        COUNT(*) as cnt
                    FROM match_candidates
                    GROUP BY a_id, b_id
                    HAVING cnt > 1;
                """)).fetchall()
            else:
                # SQLite and ANSI standard fallback using CASE expressions
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
            if dialect_name in ("postgresql", "postgres"):
                conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_match_candidates_pair
                    ON match_candidates(
                        LEAST(record_a_id, record_b_id),
                        GREATEST(record_a_id, record_b_id)
                    );
                """))
            else:
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
