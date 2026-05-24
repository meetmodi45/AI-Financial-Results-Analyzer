import io
import logging
import traceback

import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from langchain_pinecone import PineconeEmbeddings
import os

try:
    from pinecone.exceptions import PineconeException
except ImportError:
    class PineconeException(Exception):
        pass

from app.core.db import SessionLocal
from app.models.concall import ConcallDocument

logger = logging.getLogger(__name__)

def process_concall_document(document_id: str, file_bytes: bytes, filename: str):
    """
    Background worker to parse text from in-memory bytes, chunk into vectors,
    and store in Pinecone. No file is written to disk.
    """
    db = SessionLocal()
    doc_record = db.query(ConcallDocument).filter(ConcallDocument.id == document_id).first()

    if not doc_record:
        logger.error(f"[ConcallProcessor] Document not found in DB: {document_id}")
        db.close()
        return

    try:
        # 1. Parse text directly from bytes — no disk I/O
        text_content = ""
        if filename.lower().endswith(".pdf"):
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text_content += page.get_text() + "\n"
        else:
            # Treat as plain text / txt file
            text_content = file_bytes.decode("utf-8", errors="replace")

        if not text_content.strip():
            raise ValueError("Extracted text content is empty.")

        # 2. Chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150
        )
        chunks = text_splitter.split_text(text_content)

        documents = []
        for chunk in chunks:
            doc = Document(
                page_content=chunk,
                metadata={
                    "document_id": document_id,
                    "company_name": doc_record.company_name,
                    "content_type": "concall_transcript"
                }
            )
            documents.append(doc)

        if not documents:
            raise ValueError("No chunks generated from document text.")

        # 3. Embeddings & Pinecone Setup
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME", "financial-reports-index")

        embeddings = PineconeEmbeddings(
            model="multilingual-e5-large",
            pinecone_api_key=api_key
        )

        # 4. Push to Pinecone
        PineconeVectorStore.from_documents(
            documents=documents,
            embedding=embeddings,
            index_name=index_name,
            pinecone_api_key=api_key,
            namespace=document_id  # Isolate per session
        )

        # 4.5 Run 3-Stage Summarization
        try:
            from app.services.summarizer import ConcallSummarizer
            summarizer = ConcallSummarizer()
            
            # Stage 1
            guide = summarizer.stage_1_get_domain_guide(
                company_name=doc_record.company_name,
                sector=doc_record.sector,
                quarter=doc_record.quarter,
                fy=doc_record.fiscal_year
            )
            
            # Stage 2
            filtered_transcript = summarizer.stage_2_tfidf_filter(text_content, guide)
            
            # Stage 3
            summary_data = summarizer.stage_3_summarize(
                company_name=doc_record.company_name,
                sector=doc_record.sector,
                quarter=doc_record.quarter,
                fy=doc_record.fiscal_year,
                filtered_transcript=filtered_transcript
            )
            
            doc_record.summary_data = summary_data
            logger.info(f"[ConcallProcessor] Generated summary for {document_id}")
        except Exception as e:
            logger.error(f"[ConcallProcessor] Failed to generate summary for {document_id}: {e}\n{traceback.format_exc()}")
            # We continue even if summary fails, so user can at least chat

        # 5. Flip status
        doc_record.processed_status = "COMPLETED"
        db.commit()
        logger.info(f"[ConcallProcessor] Successfully processed and indexed document: {document_id}")

    except PineconeException as pe:
        logger.error(f"[ConcallProcessor] Pinecone error for {document_id}: {pe}\n{traceback.format_exc()}")
        doc_record.processed_status = "FAILED"
        doc_record.error_message = f"Pinecone Error: {pe}"
        db.commit()
    except Exception as e:
        logger.error(f"[ConcallProcessor] Processing fault for {document_id}: {e}\n{traceback.format_exc()}")
        doc_record.processed_status = "FAILED"
        doc_record.error_message = f"Processing Error: {e}"
        db.commit()
    finally:
        db.close()
