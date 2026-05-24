import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from langchain_pinecone import PineconeVectorStore
from langchain_pinecone import PineconeEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.core.db import get_db
from app.models.concall import ConcallDocument
from app.services.concall_processor import process_concall_document

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload-and-process")
async def upload_and_process_concall(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_name: str = Form("Unknown"),
    sector: str = Form("Unknown"),
    quarter: str = Form("Q4"),
    fiscal_year: str = Form("N/A"),
    db: Session = Depends(get_db)
):
    # --- Deduplication check ---
    # If a successfully processed document already exists for the same
    # company / sector / quarter / FY, return it immediately — no LLM call,
    # no Pinecone upsert, no wasted tokens.
    existing = db.query(ConcallDocument).filter(
        ConcallDocument.company_name == company_name,
        ConcallDocument.sector == sector,
        ConcallDocument.quarter == quarter,
        ConcallDocument.fiscal_year == fiscal_year,
        ConcallDocument.processed_status == "COMPLETED"
    ).first()

    if existing:
        logger.info(f"Dedup hit: returning existing document {existing.id} for {company_name} {quarter} {fiscal_year}")
        return {
            "document_id": existing.id,
            "company_name": existing.company_name,
            "status": "COMPLETED",
            "message": f"Already processed — returning existing result for {company_name} {quarter} {fiscal_year}"
        }

    document_id = str(uuid.uuid4())

    # Read file entirely into memory — no disk write
    try:
        file_bytes = await file.read()
        filename = file.filename or "upload.pdf"
    except Exception as e:
        logger.error(f"Failed to read uploaded file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read uploaded file")

    # Write initial tracking record to ConcallDocument
    new_doc = ConcallDocument(
        id=document_id,
        company_name=company_name,
        sector=sector,
        quarter=quarter,
        fiscal_year=fiscal_year,
        processed_status="PENDING"
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # Pass raw bytes to background processor — no file path needed
    background_tasks.add_task(process_concall_document, document_id, file_bytes, filename)

    return {
        "document_id": document_id,
        "company_name": company_name,
        "status": "PENDING",
        "message": "Concall transcription processing started in the background"
    }

@router.get("/status/{document_id}")
async def get_concall_status(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(ConcallDocument).filter(ConcallDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Concall document not found")

    return {
        "document_id": doc.id,
        "company_name": doc.company_name,
        "quarter": doc.quarter,
        "fiscal_year": doc.fiscal_year,
        "status": doc.processed_status,
        "error_message": getattr(doc, "error_message", None),
        "summary_data": getattr(doc, "summary_data", None)
    }

class ChatRequest(BaseModel):
    document_id: str
    query: str

@router.post("/chat")
async def chat_with_concall(request: ChatRequest, db: Session = Depends(get_db)):
    doc = db.query(ConcallDocument).filter(ConcallDocument.id == request.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Concall document not found")

    if doc.processed_status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Document processing is not completed yet")

    try:
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME", "financial-reports-index")

        embeddings = PineconeEmbeddings(
            model="multilingual-e5-large",
            pinecone_api_key=api_key
        )

        vectorstore = PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings,
            pinecone_api_key=api_key,
            namespace=request.document_id
        )

        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": 5,
                "filter": {"document_id": request.document_id}
            }
        )

        retrieved_docs = retriever.invoke(request.query)
        context_text = "\n\n".join([d.page_content for d in retrieved_docs])

        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)

        system_prompt = (
            "You are an expert financial analyst. Answer the user's question about the earnings call transcript "
            "based strictly on the context provided. If the answer cannot be found in the context, say so.\n\n"
            "Context:\n{context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{query}")
        ])

        chain = prompt | llm
        response = chain.invoke({"context": context_text, "query": request.query})

        return {
            "answer": response.content,
            "sources": [{"content": d.page_content, "metadata": d.metadata} for d in retrieved_docs]
        }
    except Exception as e:
        logger.error(f"Chat failed for document_id {request.document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate response")
