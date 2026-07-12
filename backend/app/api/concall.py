import os
import uuid
import logging
import hashlib
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
from app.services.transcript_chunker import retrieve_with_neighbors

logger = logging.getLogger(__name__)

router = APIRouter()

from app.utils.download_utils import get_pdf_from_upload_or_url

@router.post("/upload-and-process")
async def upload_and_process_concall(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    url: str = Form(None),
    company_name: str = Form("Unknown"),
    sector: str = Form("Unknown"),
    quarter: str = Form("Q4"),
    fiscal_year: str = Form("N/A"),
    db: Session = Depends(get_db)
):
    # Normalize inputs so "union bank", "Union Bank", "UNION BANK" all match
    company_name = company_name.strip().title()
    sector = sector.strip().title()
    quarter = quarter.strip().upper()
    fiscal_year = fiscal_year.strip().upper()

    file_bytes, filename = await get_pdf_from_upload_or_url(file, url)

    # Calculate SHA-256 hash of the file contents
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # --- Deduplication check ---
    # We now strictly deduplicate by File Hash ONLY.
    # If a user uploads the exact same PDF but types "Transrail Limited" instead
    # of "Transrail", we still instantly hit the cache because the binary file
    # is mathematically identical. This prevents cache misses due to typos.
    existing = db.query(ConcallDocument).filter(
        ConcallDocument.file_hash == file_hash,
        ConcallDocument.processed_status == "COMPLETED"
    ).first()

    if existing:
        logger.info(f"Dedup hit: returning existing document {existing.id} for {company_name} {quarter} {fiscal_year} (hash: {file_hash[:8]}...)")
        return {
            "document_id": existing.id,
            "company_name": existing.company_name,
            "status": "COMPLETED",
            "message": f"Already processed — returning existing result for {company_name} {quarter} {fiscal_year}"
        }

    document_id = str(uuid.uuid4())

    # Read file entirely into memory — no disk write
    # Read file entirely into memory — no disk write
    # (Moved above for hashing)

    # Write initial tracking record to ConcallDocument
    new_doc = ConcallDocument(
        id=document_id,
        company_name=company_name,
        sector=sector,
        quarter=quarter,
        fiscal_year=fiscal_year,
        file_hash=file_hash,
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

        # Generate alternative queries for Multi-Query Expansion
        try:
            import re
            query_gen_llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.1)
            query_gen_prompt = (
                "You are an AI language model assistant. Your task is to generate 3 alternative versions of the "
                "user query to retrieve relevant documents from a vector database.\n"
                "By generating multiple perspectives on the user query, your goal is to help the user retrieve "
                "non-contiguous key contexts (e.g., physical assets, locations, audit/monitoring, or partner/order details) "
                "that may be split across different sections of a transcript.\n\n"
                "Generate exactly 3 alternative queries, focusing on different aspects of the topic:\n"
                "1. General financial/audit/compliance monitoring of the topic\n"
                "2. Physical assets, locations, projects, or factories related to the topic\n"
                "3. Operational partners, collaborations, or initial orders related to the topic\n\n"
                "Provide these alternative queries separated by newlines, one per line. Do not include any extra text, numbers, prefix labels, or explanation.\n\n"
                f"Original query: {request.query}"
            )
            query_gen_res = query_gen_llm.invoke(query_gen_prompt)
            alt_queries = [request.query]
            for q in query_gen_res.content.strip().split("\n"):
                q_clean = q.strip().strip("-*").strip()
                q_clean = re.sub(r'^\d+\.\s*', '', q_clean)
                if q_clean:
                    alt_queries.append(q_clean)
            alt_queries = list(dict.fromkeys(alt_queries))
            logger.info(f"Multi-Query Expansion generated queries: {alt_queries}")
        except Exception as q_err:
            logger.warning(f"Failed to generate alternative queries: {q_err}. Falling back to original query.")
            alt_queries = [request.query]

        # Execute multi-query retrieval with deduplication
        all_retrieved_docs = []
        seen_chunk_ids = set()
        for q in alt_queries:
            docs = retrieve_with_neighbors(
                vectorstore=vectorstore,
                query=q,
                document_id=request.document_id,
                k=4
            )
            for d in docs:
                c_id = d.metadata.get("chunk_id") or d.metadata.get("chunk_index") or d.page_content
                if c_id not in seen_chunk_ids:
                    seen_chunk_ids.add(c_id)
                    all_retrieved_docs.append(d)

        # Chronological sort & limit to top 8 chunks to keep context size safe
        all_retrieved_docs.sort(key=lambda d: int(d.metadata.get("chunk_index") or 0))
        retrieved_docs = all_retrieved_docs[:8]
        context_text = "\n\n".join([d.page_content for d in retrieved_docs])

        llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.2)

        system_prompt = (
            "You are an expert financial analyst. Answer the user's question about the earnings call transcript "
            "based strictly on the context provided. If the answer cannot be found in the context, say so.\n\n"
            "Format your answer cleanly using Markdown:\n"
            "- Use bold formatting (**bold**) for key metrics, numbers, company names, and crucial conclusions.\n"
            "- Present lists using clean bullet points (* or 1., 2., 3.) and ALWAYS place each list item on its own new line with spacing.\n"
            "- Use double newlines to separate distinct paragraphs or points for readability.\n"
            "- Keep descriptions sharp, clear, and professional.\n\n"
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
