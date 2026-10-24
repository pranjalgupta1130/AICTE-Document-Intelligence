"""FastAPI Integration Router for Member 2.
Member 2 can include this APIRouter directly: `app.include_router(member1_router, prefix="/api/v1/member1")`.
"""

from __future__ import annotations
import os
import shutil
import tempfile
from typing import List
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from .csv_export import build_findings_csv
from .pipeline import DocumentIntelligencePipeline
from .schemas import DocumentAnalysisResult, PipelineRunResult

router = APIRouter(tags=["Member 1 - Document Intelligence & Validation"])
pipeline = DocumentIntelligencePipeline()


@router.post("/process-document", response_model=DocumentAnalysisResult)
async def process_single_document(file: UploadFile = File(...)):
    """Processes a single PDF document for text, fields, and signature extraction."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = pipeline.process_document(tmp_path)
        # Preserve original uploaded filename in metadata
        result.metadata.filename = file.filename
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/process-application", response_model=PipelineRunResult)
async def process_application_dossier(
    application_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """Processes all uploaded files for an institution application:
    Runs OCR/extraction, rules, cross-doc consistency, duplicate detection, and risk scoring.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file must be provided.")

    tmp_files: List[str] = []
    try:
        for f in files:
            if not f.filename.lower().endswith(".pdf"):
                continue
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{f.filename}")
            shutil.copyfileobj(f.file, tmp)
            tmp.close()
            tmp_files.append(tmp.name)

        if not tmp_files:
            raise HTTPException(status_code=400, detail="No valid PDF documents found in submission.")

        result = pipeline.process_application(
            application_id=application_id, document_paths=tmp_files
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Application validation failed: {str(e)}")
    finally:
        for path in tmp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


@router.post(
    "/export-findings-csv",
    response_class=StreamingResponse,
    summary="Export batch validation findings as a downloadable CSV report",
    description=(
        "Accepts a completed ``PipelineRunResult`` payload (the JSON body returned by "
        "``/process-application``) and streams it back as a UTF-8 encoded CSV file.\n\n"
        "**Permissions**: The caller is responsible for institution-level RBAC before "
        "forwarding a result payload to this endpoint. The endpoint itself does not persist "
        "any data and only operates on the submitted payload.\n\n"
        "**Empty report**: If the application has no findings, a CSV with headers only is "
        "returned (HTTP 200) rather than an error.\n\n"
        "**Formula injection**: All untrusted text values are sanitised against CSV "
        "formula-injection by prefixing dangerous leading characters."
    ),
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "CSV file containing all findings for the application.",
        },
        422: {"description": "Invalid or malformed PipelineRunResult payload."},
    },
)
async def export_findings_csv(result: PipelineRunResult) -> StreamingResponse:
    """Export a ``PipelineRunResult``'s findings as a downloadable CSV.

    The response sets ``Content-Disposition: attachment`` so browsers and HTTP
    clients download the file rather than displaying it inline.  The filename
    embeds the ``application_id`` for traceability.

    Authorization
    -------------
    This endpoint is mounted inside the same ``APIRouter`` as the existing
    document-processing routes.  Member 2's backend is expected to apply its
    own authentication and institution-isolation middleware **before** routing
    the request here, consistent with how it guards ``/process-application``.
    """
    app_id = (result.application_id or "unknown").replace("/", "_").replace("\\", "_")
    filename = f"findings_{app_id}.csv"

    try:
        csv_content = build_findings_csv(result)
    except Exception as exc:  # pragma: no cover  – guard against unexpected serialisation errors
        raise HTTPException(
            status_code=500,
            detail=f"CSV generation failed: {exc}",
        ) from exc

    return StreamingResponse(
        iter([csv_content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
