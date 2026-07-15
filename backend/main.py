import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .pdf_parser import validate_and_extract_pdf, split_text_into_chunks, PDFValidationError
from .summarizer import summarize_pdf_workflow

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AI PDF Summarizer API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: no credentials are used (API keys are supplied per-request via headers),
# so allow_credentials must be False. Restrict origins to known local dev hosts;
# update this list for any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
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
    tone: str = Form("simple"),
    x_provider: str = Header(None, alias="X-Provider"),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    try:
        # Resolve provider with ternary expressions falling back to env variables
        selected_provider = x_provider or (
            "gemini" if os.getenv("GEMINI_API_KEY")
            else "openai" if os.getenv("OPENAI_API_KEY")
            else "gemini"
        )

        # Resolve API Key based on resolved provider
        selected_api_key = x_api_key or os.getenv(
            "GEMINI_API_KEY" if selected_provider == "gemini" else "OPENAI_API_KEY"
        )

        if not selected_api_key:
            raise HTTPException(
                status_code=400,
                detail=f"API key missing for provider '{selected_provider}'. Please set it in the settings panel or environment variables.",
            )

        content = await file.read()
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
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")