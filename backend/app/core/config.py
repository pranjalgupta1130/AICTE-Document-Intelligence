import os
from typing import List
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "SIH 26263 APAAR Student Data Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./apaar_platform.db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sih26263-apaar-insecure-dev-secret-replace-in-production-7f8a9b")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    # Synthetic / Demo mode
    DEMO_MODE: bool = True

    # Ingestion & Parsing Safeguards
    MAX_CSV_UPLOAD_BYTES: int = int(os.getenv("MAX_CSV_UPLOAD_BYTES", 50 * 1024 * 1024))   # 50 MB
    MAX_XLSX_UPLOAD_BYTES: int = int(os.getenv("MAX_XLSX_UPLOAD_BYTES", 25 * 1024 * 1024)) # 25 MB
    MAX_IMPORT_ROWS: int = int(os.getenv("MAX_IMPORT_ROWS", 100000))                        # 100,000 rows
    MAX_CELL_LENGTH: int = int(os.getenv("MAX_CELL_LENGTH", 10000))                         # 10,000 chars per cell
    MAX_ZIP_ENTRIES: int = int(os.getenv("MAX_ZIP_ENTRIES", 100))                           # XLSX zip bomb entry limit
    MAX_UNCOMPRESSED_XLSX_BYTES: int = int(os.getenv("MAX_UNCOMPRESSED_XLSX_BYTES", 100 * 1024 * 1024)) # 100 MB decompressed limit

settings = Settings()
