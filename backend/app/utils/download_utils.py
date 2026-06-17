import requests
from fastapi import UploadFile, HTTPException
import logging

logger = logging.getLogger(__name__)

async def get_pdf_from_upload_or_url(file: UploadFile = None, url: str = None) -> tuple[bytes, str]:
    """
    Given an optional uploaded file and an optional URL, this function returns the PDF bytes and filename.
    It prefers the uploaded file if both are provided.
    
    Raises HTTPException for validation or download errors.
    """
    if file and file.filename:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        try:
            file_bytes = await file.read()
            return file_bytes, file.filename
        except Exception as e:
            logger.error(f"Failed to read uploaded file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail="Failed to read uploaded file")

    if url:
        if not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(status_code=400, detail="Invalid URL provided")

        logger.info(f"Attempting to download PDF from URL: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.bseindia.com/",
            "Connection": "keep-alive"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to download. HTTP Status Code: {response.status_code}. Response snippet: {response.text[:200]}")
                raise HTTPException(status_code=400, detail=f"Failed to download. HTTP Status Code: {response.status_code}")
                
            content_type = response.headers.get("Content-Type", "")
            if "application/pdf" not in content_type.lower():
                logger.warning(f"Warning: Response content-type is '{content_type}', which might not be a PDF.")
            
            content = response.content
            # Quick verification that the file is actually a PDF by checking the magic bytes
            if not content.startswith(b"%PDF"):
                raise HTTPException(status_code=400, detail="Downloaded file is not a valid PDF")
                
            logger.info("Successfully downloaded PDF from URL")
            return content, "downloaded_from_url.pdf"
            
        except requests.RequestException as e:
            logger.error(f"An error occurred during download: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to download PDF from URL: {str(e)}")

    raise HTTPException(status_code=400, detail="Either a file or a URL must be provided")
