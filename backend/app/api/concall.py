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

from app.core.config import settings
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
            query_gen_llm = ChatGroq(model=settings.GROQ_MODEL, temperature=0.1)
            query_gen_prompt = (
                "You are an AI assistant helping retrieve relevant passages from an earnings call transcript.\n"
                "Your task is to rephrase the user's query into 2 alternative search queries using different financial terms, synonyms, or related industry jargon.\n"
                "Do NOT change the subject of the question. Keep the alternative queries strictly focused on the exact same topic as the original query.\n"
                "Provide the 2 alternative queries separated by newlines, one per line. Do not include extra text, numbers, or explanations.\n\n"
                f"User Query: {request.query}"
            )
            query_gen_res = query_gen_llm.invoke(query_gen_prompt)
            alt_queries = [request.query]
            for q in query_gen_res.content.strip().split("\n"):
                q_clean = q.strip().strip("-*").strip()
                q_clean = re.sub(r'^\d+\.\s*', '', q_clean)
                if q_clean and q_clean.lower() != request.query.lower():
                    alt_queries.append(q_clean)
            alt_queries = list(dict.fromkeys(alt_queries))
            logger.info(f"Multi-Query Expansion generated queries: {alt_queries}")
        except Exception as q_err:
            logger.warning(f"Failed to generate alternative queries: {q_err}. Falling back to original query.")
            alt_queries = [request.query]

        # Execute multi-query retrieval: prioritize primary query results first
        selected_docs = []
        seen_chunk_ids = set()

        for q_idx, q in enumerate(alt_queries):
            k_val = 5 if q_idx == 0 else 3
            docs = retrieve_with_neighbors(
                vectorstore=vectorstore,
                query=q,
                document_id=request.document_id,
                k=k_val
            )
            for d in docs:
                c_id = d.metadata.get("chunk_id") or d.metadata.get("chunk_index") or d.page_content
                if c_id not in seen_chunk_ids:
                    seen_chunk_ids.add(c_id)
                    selected_docs.append(d)
                if len(selected_docs) >= 12:
                    break
            if len(selected_docs) >= 12:
                break

        # Build structured context with page numbers and speaker headers for precise citations
        formatted_blocks = []
        for d in selected_docs:
            p_start = d.metadata.get("start_page") or d.metadata.get("page") or d.metadata.get("page_num") or 1
            p_end = d.metadata.get("end_page") or p_start
            page_str = f"Page {p_start}" if p_start == p_end else f"Pages {p_start}-{p_end}"
            
            speakers = d.metadata.get("speakers")
            speaker_str = ""
            if speakers:
                if isinstance(speakers, list):
                    speaker_str = f" | Speakers: {', '.join(speakers)}"
                else:
                    speaker_str = f" | Speaker: {speakers}"
                    
            formatted_blocks.append(f"--- [Source: {page_str}{speaker_str}] ---\n{d.page_content}")

        context_text = "\n\n".join(formatted_blocks)[:14000]

        llm = ChatGroq(model=settings.GROQ_MODEL, temperature=0.2)

        system_prompt = (
            "You are an expert financial analyst. Answer the user's question about the earnings call transcript "
            "thoroughly and accurately based on the context provided.\n\n"
            "Guidelines:\n"
            "- Use bold formatting (**bold**) for key metrics, monetary values, percentage numbers, and important conclusions.\n"
            "- Present information using clean, spaced bullet points (* or 1., 2.) so it is easy to read.\n"
            "- Append source citations from the context headers when available, e.g. [Page X, Speaker Name].\n"
            "- If the topic is not mentioned in the transcript, state that it is not covered.\n\n"
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
            "sources": [{"content": d.page_content, "metadata": d.metadata} for d in selected_docs]
        }
    except Exception as e:
        logger.error(f"Chat failed for document_id {request.document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate response")
