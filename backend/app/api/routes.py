import os
import uuid
import logging
import traceback
from typing import Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import fitz  # PyMuPDF
from app.core.db import get_db
from app.models.document import Document, ProcessingStatus
from app.core.pipeline import run_extraction_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger.info(f"[Agent 1] Upload directory resolved to: {UPLOAD_DIR}")

@router.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)) -> Dict:
    """
    Agent 1: Document Ingestion Agent
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    document_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.pdf")

    # Store raw file
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    file_size = os.path.getsize(file_path)
    logger.info(f"[Agent 1] Saved file to: {file_path} ({file_size} bytes)")

    # Validate PDF — note: HTTPException must NOT be caught here
    total_pages = 0
    try:
        doc = fitz.open(file_path)
        if doc.needs_pass:
            doc.close()
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="PDF is encrypted")
        total_pages = len(doc)
        doc.close()
        logger.info(f"[Agent 1] PDF validated: {total_pages} pages")
    except HTTPException:
        raise  # Re-raise HTTP exceptions without catching them as generic errors
    except Exception as e:
        logger.error(f"[Agent 1] PDF validation failed: {e}\n{traceback.format_exc()}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"PDF is corrupted or invalid: {str(e)}")

    # Database record creation
    new_doc = Document(
        id=document_id,
        filename=file.filename,
        file_size=file_size,
        processing_status=ProcessingStatus.UPLOADED,
        metadata_json={
            "total_pages": total_pages
        }
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    logger.info(f"[Agent 1] Document record created in DB: doc_id={document_id}")

    # Trigger extraction pipeline via BackgroundTasks
    try:
        background_tasks.add_task(run_extraction_pipeline, document_id, file_path)
        logger.info(f"[Agent 1] Dispatched Extraction Pipeline for doc_id={document_id}")
    except Exception as e:
        err_detail = f"Failed to dispatch Extraction Pipeline: {str(e)}"
        logger.error(f"[Agent 1] {err_detail}\n{traceback.format_exc()}")
        db.refresh(new_doc)  # Re-attach to session after any potential stale state
        new_doc.processing_status = ProcessingStatus.FAILED
        new_doc.error_message = err_detail
        db.commit()

    return {
        "document_id": document_id,
        "filename": file.filename,
        "file_size": file_size,
        "total_pages": total_pages,
        "status": new_doc.processing_status
    }

@router.get("/status/{document_id}")
async def get_document_status(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "status": doc.processing_status,
        "metadata": doc.metadata_json,
        "analysis_results": doc.analysis_results,
        "nlp_summary": doc.nlp_summary,
        "verdict": doc.verdict,
        "financial_data": doc.financial_data,
        "error_message": doc.error_message
    }
