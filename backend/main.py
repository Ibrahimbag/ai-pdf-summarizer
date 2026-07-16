import asyncio
import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .pdf_parser import validate_and_extract_pdf, split_text_into_chunks, PDFValidationError
from .summarizer import summarize_pdf_workflow

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"


def get_real_client_ip(request: Request) -> str:
    """
    Returns the real client IP, considering X-Forwarded-For if request comes
    from a trusted proxy IP defined in the TRUSTED_PROXIES environment variable.
    """
    trusted_proxies_str = os.getenv("TRUSTED_PROXIES", "")
    trusted_proxies = {ip.strip() for ip in trusted_proxies_str.split(",") if ip.strip()}
    
    client_host = request.client.host if request.client else "127.0.0.1"
    
    if "*" in trusted_proxies or client_host in trusted_proxies:
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # First element represents the client
            return x_forwarded_for.split(",")[0].strip()
            
    return client_host


limiter = Limiter(key_func=get_real_client_ip)

app = FastAPI(title="AI PDF Summarizer API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration dynamically configured via environment variables
cors_origins_str = os.getenv("ALLOWED_CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Provider", "X-API-Key"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Root endpoint: Serve the frontend index.html
@app.get("/")
def read_root():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "AI PDF Summarizer Backend is running! UI files not found."}


@app.post("/api/summarize")
@limiter.limit("10/minute")
async def summarize_pdf(
    request: Request,
    file: UploadFile = File(...),
    tone: Literal["simple", "academic", "executive"] = Form("simple"),
    x_provider: str = Header(None, alias="X-Provider"),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    try:
        allow_server_keys = os.getenv("ALLOW_SERVER_KEYS", "false").lower() == "true"
        
        selected_provider = x_provider
        selected_api_key = x_api_key
        
        if not selected_api_key:
            if not allow_server_keys:
                raise HTTPException(
                    status_code=401,
                    detail="API key is required in the X-API-Key header. Server-side API keys are disabled.",
                )
            
            # Resolve provider from server environment
            selected_provider = selected_provider or (
                "gemini" if os.getenv("GEMINI_API_KEY")
                else "openai" if os.getenv("OPENAI_API_KEY")
                else "gemini"
            )
            # Resolve key from server environment
            selected_api_key = os.getenv(
                "GEMINI_API_KEY" if selected_provider == "gemini" else "OPENAI_API_KEY"
            )
        else:
            selected_provider = selected_provider or "gemini"
            
        if not selected_api_key:
            raise HTTPException(
                status_code=400,
                detail=f"API key missing for provider '{selected_provider}'. Please set it in the settings panel.",
            )

        # Stream file reading in chunks to prevent unbounded memory allocation
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        content_chunks = []
        size = 0
        while chunk := await file.read(65536):
            size += len(chunk)
            if size > MAX_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail="The file exceeds the maximum allowed size of 10MB.",
                )
            content_chunks.append(chunk)
        content = b"".join(content_chunks)

        full_text = validate_and_extract_pdf(content, file.filename)
        chunks = split_text_into_chunks(full_text, chunk_size_chars=6000, overlap_chars=500)

        # Run LLM calls in a thread pool to avoid blocking the event loop
        result = await asyncio.to_thread(
            summarize_pdf_workflow,
            provider=selected_provider,
            api_key=selected_api_key,
            chunks=chunks,
            full_text=full_text,
            tone=tone,
            progress_callback=lambda msg: logger.info("Summary progress: %s", msg),
        )
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except PDFValidationError as pve:
        if pve.cause is not None:
            logger.error("PDF validation/parsing failed: %s", str(pve), exc_info=pve.cause)
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is malformed or could not be parsed."
            )
        else:
            raise HTTPException(status_code=400, detail=str(pve))
    except Exception:
        logger.exception("Unexpected server error during summarization")
        raise HTTPException(
            status_code=500,
            detail="An unexpected internal error occurred. Please try again.",
        )


# Mount the static files for CSS, JS, images, etc.
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")