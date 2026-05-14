import os
import uuid
from typing import Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import fitz  # PyMuPDF
from app.core.db import get_db
from app.models.document import Document, ProcessingStatus
from app.agents.agent_2_pdf_type import process_pdf_type

router = APIRouter()

UPLOAD_DIR = os.path.join("..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Dict:
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
    
    # Validate PDF corruption / encryption
    try:
        doc = fitz.open(file_path)
        if doc.needs_pass:
            doc.close()
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="PDF is encrypted")
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="PDF is corrupted or invalid")
    
    # Database record creation
    new_doc = Document(
        id=document_id,
        filename=file.filename,
        file_size=file_size,
        processing_status=ProcessingStatus.UPLOADED,
        metadata_json={
            "total_pages": total_pages,
            "file_path": file_path
        }
    )
    
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # Trigger next agent in the pipeline via Celery
    process_pdf_type.delay(document_id)
    
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

