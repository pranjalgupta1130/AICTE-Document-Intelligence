import json
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.errors import AppException
from backend.app.core.permissions import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.imports import ImportCommitResponse, ImportPreviewResponse
from backend.app.services.import_parser import generate_csv_template
from backend.app.services.import_service import commit_import_data, preview_import_data

router = APIRouter(prefix="/imports", tags=["Imports"])

async def read_upload_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    """
    Read uploaded file chunk by chunk to prevent unbounded memory buffering.
    Raises AppException with HTTP 413 if upload exceeds max_bytes.
    """
    chunk_size = 64 * 1024  # 64 KB chunks
    total_read = 0
    buffer = io_buffer = bytearray()

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_bytes:
            raise AppException(
                code="FILE_TOO_LARGE",
                message=f"Uploaded file exceeds maximum limit of {max_bytes // (1024 * 1024)}MB.",
                status_code=413
            )
        io_buffer.extend(chunk)

    return bytes(io_buffer)

def resolve_format_limit(filename: str) -> int:
    """
    Determine format-specific upload limit based on file extension.
    """
    fname = filename.lower()
    if fname.endswith(".xlsx"):
        return settings.MAX_XLSX_UPLOAD_BYTES
    return settings.MAX_CSV_UPLOAD_BYTES

@router.get("/template", summary="Download standard CSV import template")
def download_template(
    current_user: User = Depends(get_current_user)
):
    """
    Generate and download the standard CSV template for tabular student records.
    """
    csv_content = generate_csv_template()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=apaar_student_template.csv"}
    )

@router.post("/preview", response_model=ImportPreviewResponse, summary="Preview uploaded CSV or XLSX file")
async def preview_import(
    file: UploadFile = File(..., description="CSV or XLSX file to preview"),
    current_user: User = Depends(get_current_user)
):
    """
    Inspect uploaded file structure, detect columns, suggest mappings, and preview sample rows.
    Enforces format-specific streaming upload limits.
    """
    filename = file.filename or "upload.csv"
    if not (filename.lower().endswith(".csv") or filename.lower().endswith(".xlsx") or filename.lower().endswith(".txt")):
        raise AppException("UNSUPPORTED_MEDIA_TYPE", "Only CSV (.csv) and Excel (.xlsx) files are supported.", status_code=415)

    limit = resolve_format_limit(filename)
    content = await read_upload_with_limit(file, limit)

    if len(content) == 0:
        raise AppException("EMPTY_FILE", "Uploaded file is empty.", status_code=400)

    return preview_import_data(filename, content)

@router.post("", response_model=ImportCommitResponse, summary="Ingest and persist tabular student dataset")
async def commit_import(
    file: UploadFile = File(..., description="CSV or XLSX file to ingest"),
    academic_year: Optional[str] = Form(None, description="Enrolled academic year (e.g. 2026-2027)"),
    programme_id: Optional[str] = Form(None, description="Academic programme reference ID"),
    institution_id: Optional[str] = Form(None, description="Target institution ID (validated against caller scope)"),
    column_mapping: Optional[str] = Form(None, description="JSON string of column mapping overrides"),
    mapping: Optional[str] = Form(None, description="Alias for column_mapping"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Commit uploaded tabular file, persist ImportBatch and StudentRecord rows, record row-level parse findings and audit events.
    Enforces streaming upload limits and atomic persistence.
    """
    filename = file.filename or "students.csv"
    if not (filename.lower().endswith(".csv") or filename.lower().endswith(".xlsx") or filename.lower().endswith(".txt")):
        raise AppException("UNSUPPORTED_MEDIA_TYPE", "Only CSV (.csv) and Excel (.xlsx) files are supported.", status_code=415)

    limit = resolve_format_limit(filename)
    content = await read_upload_with_limit(file, limit)

    if len(content) == 0:
        raise AppException("EMPTY_FILE", "Uploaded file is empty.", status_code=400)

    # Parse column mapping if supplied as JSON
    parsed_mapping = None
    raw_mapping = column_mapping or mapping
    if raw_mapping:
        try:
            parsed_mapping = json.loads(raw_mapping)
        except Exception:
            raise AppException("INVALID_MAPPING", "column_mapping form parameter must be valid JSON.", status_code=400)

    return commit_import_data(
        db=db,
        current_user=current_user,
        filename=filename,
        content=content,
        academic_year=academic_year,
        programme_id=programme_id,
        column_mapping=parsed_mapping,
        target_institution_id=institution_id
    )
