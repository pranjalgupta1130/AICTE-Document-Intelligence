import sys
import os
from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.db import session as db_session
from backend.app.db.session import init_db, Base
from backend.app.models.enums import UserRole
from backend.app.models.institution import Institution, Programme, ApprovedIntake
from backend.app.models.user import User

DEFAULT_PASSWORD = "DemoPassword@2026"

INSTITUTIONS_SEED = [
    {
        "id": "INST-001",
        "name": "Apex Institute of Technology",
        "code": "AIT-DELHI",
        "state": "Delhi",
        "status": "ACTIVE",
        "programmes": [
            {
                "id": "PROG-001-CSE",
                "name": "B.Tech Computer Science & Engineering",
                "degree_level": "UNDERGRADUATE",
                "duration_years": 4,
                "intakes": [
                    {
                        "id": "INTAKE-001-CSE-2026",
                        "academic_year": "2026-2027",
                        "regular_intake": 120,
                        "supernumerary_intake": 15,
                        "supernumerary_policy": "AICTE APH Chapter II: 15% supernumerary quota for EWS/TFW/FN candidates"
                    }
                ]
            },
            {
                "id": "PROG-001-ECE",
                "name": "B.Tech Electronics & Communication Engineering",
                "degree_level": "UNDERGRADUATE",
                "duration_years": 4,
                "intakes": [
                    {
                        "id": "INTAKE-001-ECE-2026",
                        "academic_year": "2026-2027",
                        "regular_intake": 60,
                        "supernumerary_intake": 6,
                        "supernumerary_policy": "AICTE APH Chapter II: 10% supernumerary quota for EWS"
                    }
                ]
            },
            {
                "id": "PROG-001-ME",
                "name": "B.Tech Mechanical Engineering",
                "degree_level": "UNDERGRADUATE",
                "duration_years": 4,
                "intakes": [
                    {
                        "id": "INTAKE-001-ME-2026",
                        "academic_year": "2026-2027",
                        "regular_intake": 60,
                        "supernumerary_intake": 6,
                        "supernumerary_policy": "AICTE APH Chapter II: 10% supernumerary quota for EWS"
                    }
                ]
            }
        ]
    },
    {
        "id": "INST-002",
        "name": "Bharat Engineering College",
        "code": "BEC-PUNE",
        "state": "Maharashtra",
        "status": "ACTIVE",
        "programmes": [
            {
                "id": "PROG-002-CSE",
                "name": "B.Tech Computer Science & Engineering",
                "degree_level": "UNDERGRADUATE",
                "duration_years": 4,
                "intakes": [
                    {
                        "id": "INTAKE-002-CSE-2026",
                        "academic_year": "2026-2027",
                        "regular_intake": 180,
                        "supernumerary_intake": 18,
                        "supernumerary_policy": "AICTE APH Chapter II: 10% supernumerary quota"
                    }
                ]
            },
            {
                "id": "PROG-002-IT",
                "name": "B.Tech Information Technology",
                "degree_level": "UNDERGRADUATE",
                "duration_years": 4,
                "intakes": [
                    {
                        "id": "INTAKE-002-IT-2026",
                        "academic_year": "2026-2027",
                        "regular_intake": 60,
                        "supernumerary_intake": 6,
                        "supernumerary_policy": "AICTE APH Chapter II: 10% supernumerary quota"
                    }
                ]
            }
        ]
    },
    {
        "id": "INST-003",
        "name": "Crest Institute of Management & Technology",
        "code": "CIMT-BLR",
        "state": "Karnataka",
        "status": "ACTIVE",
        "programmes": [
            {
                "id": "PROG-003-MCA",
                "name": "Master of Computer Applications",
                "degree_level": "POSTGRADUATE",
                "duration_years": 2,
                "intakes": [
                    {
                        "id": "INTAKE-003-MCA-2026",
                        "academic_year": "2026-2027",
                        "regular_intake": 60,
                        "supernumerary_intake": 6,
                        "supernumerary_policy": "AICTE APH Chapter II: 10% supernumerary quota"
                    }
                ]
            },
            {
                "id": "PROG-003-MBA",
                "name": "Master of Business Administration",
                "degree_level": "POSTGRADUATE",
                "duration_years": 2,
                "intakes": [
                    {
                        "id": "INTAKE-003-MBA-2026",
                        "academic_year": "2026-2027",
                        "regular_intake": 120,
                        "supernumerary_intake": 12,
                        "supernumerary_policy": "AICTE APH Chapter II: 10% supernumerary quota"
                    }
                ]
            }
        ]
    }
]

USERS_SEED = [
    {
        "id": "usr-aicte-adm-01",
        "email": "aicte_admin@aicte.gov.in",
        "full_name": "AICTE National Reviewer",
        "role": UserRole.AICTE_ADMIN,
        "institution_id": None,
        "password": DEFAULT_PASSWORD
    },
    {
        "id": "usr-apex-adm-01",
        "email": "apex_admin@apex.edu.in",
        "full_name": "Apex Institution Administrator",
        "role": UserRole.INSTITUTION_ADMIN,
        "institution_id": "INST-001",
        "password": DEFAULT_PASSWORD
    },
    {
        "id": "usr-apex-op-01",
        "email": "apex_operator@apex.edu.in",
        "full_name": "Apex Ingestion Operator",
        "role": UserRole.INSTITUTION_OPERATOR,
        "institution_id": "INST-001",
        "password": DEFAULT_PASSWORD
    },
    {
        "id": "usr-bharat-adm-01",
        "email": "bharat_admin@bharat.edu.in",
        "full_name": "Bharat Institution Administrator",
        "role": UserRole.INSTITUTION_ADMIN,
        "institution_id": "INST-002",
        "password": DEFAULT_PASSWORD
    },
    {
        "id": "usr-demo-adm-01",
        "email": "demo_admin@apaar.gov.in",
        "full_name": "Demonstration & Evaluation Lead",
        "role": UserRole.DEMO_ADMIN,
        "institution_id": None,
        "password": DEFAULT_PASSWORD
    }
]

def seed_database(reset: bool = False, db: Session = None) -> None:
    """
    Seed initial institutions, programmes, approved intake capacities, and demo accounts.
    """
    close_db_at_end = False
    if db is None:
        init_db()
        db = db_session.SessionLocal()
        close_db_at_end = True

    try:
        active_engine = getattr(db_session, "engine", None)
        if reset and active_engine is not None:
            db_path = getattr(active_engine.url, "database", None)
            is_dev_db = False
            if db_path:
                try:
                    dev_db_canonical = os.path.abspath("apaar_platform.db").lower()
                    target_db_canonical = os.path.abspath(db_path).lower()
                    is_dev_db = (target_db_canonical == dev_db_canonical)
                except Exception:
                    is_dev_db = "apaar_platform.db" in str(active_engine.url) and "test" not in str(active_engine.url).lower()

            if is_dev_db and os.getenv("ALLOW_DEV_DB_RESET", "false").lower() != "true":
                raise RuntimeError(
                    f"Destructive reset blocked: Refusing to drop tables on development database ({active_engine.url}). "
                    "Use an isolated test database for testing, or set ALLOW_DEV_DB_RESET=true if explicitly intended."
                )
            # Recreate all tables cleanly
            Base.metadata.drop_all(bind=active_engine)
            Base.metadata.create_all(bind=active_engine)

        # 1. Seed Institutions, Programmes, and Intakes
        for inst_data in INSTITUTIONS_SEED:
            existing_inst = db.query(Institution).filter(Institution.id == inst_data["id"]).first()
            if not existing_inst:
                inst = Institution(
                    id=inst_data["id"],
                    name=inst_data["name"],
                    code=inst_data["code"],
                    state=inst_data["state"],
                    status=inst_data["status"]
                )
                db.add(inst)
                db.flush()

            for prog_data in inst_data["programmes"]:
                existing_prog = db.query(Programme).filter(Programme.id == prog_data["id"]).first()
                if not existing_prog:
                    prog = Programme(
                        id=prog_data["id"],
                        institution_id=inst_data["id"],
                        name=prog_data["name"],
                        degree_level=prog_data["degree_level"],
                        duration_years=prog_data["duration_years"]
                    )
                    db.add(prog)
                    db.flush()

                for intake_data in prog_data["intakes"]:
                    existing_intake = db.query(ApprovedIntake).filter(ApprovedIntake.id == intake_data["id"]).first()
                    if not existing_intake:
                        intake = ApprovedIntake(
                            id=intake_data["id"],
                            institution_id=inst_data["id"],
                            programme_id=prog_data["id"],
                            academic_year=intake_data["academic_year"],
                            regular_intake=intake_data["regular_intake"],
                            supernumerary_intake=intake_data["supernumerary_intake"],
                            supernumerary_policy=intake_data.get("supernumerary_policy")
                        )
                        db.add(intake)

        # 2. Seed Users
        for user_data in USERS_SEED:
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing_user:
                hashed = hash_password(user_data["password"])
                user = User(
                    id=user_data["id"],
                    email=user_data["email"],
                    hashed_password=hashed,
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    institution_id=user_data["institution_id"],
                    is_active=True
                )
                db.add(user)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if close_db_at_end:
            db.close()

if __name__ == "__main__":
    reset_mode = "--reset" in sys.argv
    print(f"Seeding database (reset={reset_mode})...")
    seed_database(reset=reset_mode)
    print("Database seeding completed successfully!")
    print("\nPreconfigured Demo Users:")
    print("------------------------------------------------------------------------------------------------------")
    print(f"{'Role':<22} | {'Email':<30} | {'Password':<18} | {'Scope'}")
    print("------------------------------------------------------------------------------------------------------")
    for u in USERS_SEED:
        inst_label = u['institution_id'] if u['institution_id'] else 'ALL (National Scope)'
        print(f"{u['role'].value:<22} | {u['email']:<30} | {u['password']:<18} | {inst_label}")
    print("------------------------------------------------------------------------------------------------------")
