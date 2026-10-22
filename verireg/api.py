"""FastAPI Integration Router for Member 2.
Member 2 can include this APIRouter directly: `app.include_router(member1_router, prefix="/api/v1/member1")`.
"""

from __future__ import annotations
import os
import shutil
import tempfile
from typing import List
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
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
