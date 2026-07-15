import asyncio
import logging
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
        # API keys must never travel in the form body (proxies/access logs
        # routinely capture form fields) — only accept them via headers.
        selected_provider = x_provider

        # Fallbacks for provider
        if not selected_provider:
            import os

            if os.environ.get("GEMINI_API_KEY"):
                selected_provider = "gemini"
            elif os.environ.get("OPENAI_API_KEY"):
                selected_provider = "openai"
            else:
                selected_provider = "gemini"

        # Fallbacks for API Key
        selected_api_key = x_api_key
        if not selected_api_key:
            import os

            if selected_provider == "gemini":
                selected_api_key = os.environ.get("GEMINI_API_KEY")
            elif selected_provider == "openai":
                selected_api_key = os.environ.get("OPENAI_API_KEY")

        # Validate that we have an API Key
        if not selected_api_key:
            raise HTTPException(
                status_code=400,
                detail=f"API key missing for provider '{selected_provider}'. Please set it in the settings panel or environment variables.",
            )

        # Read the file contents
        content = await file.read()

        # Validate and extract text
        try:
            full_text = validate_and_extract_pdf(content, file.filename)
        except PDFValidationError as pve:
            raise HTTPException(status_code=400, detail=str(pve))

        # Split text into chunks
        # 6000 chars is roughly 1500 tokens
        chunks = split_text_into_chunks(full_text, chunk_size_chars=6000, overlap_chars=500)

        def progress_log(message: str):
            logger.info("Summary progress: %s", message)

        # Run workflow in a thread so the blocking LLM calls don't stall the
        # event loop for other concurrent requests.
        result = await asyncio.to_thread(
            summarize_pdf_workflow,
            provider=selected_provider,
            api_key=selected_api_key,
            chunks=chunks,
            full_text=full_text,
            tone=tone,
            progress_callback=progress_log,
        )

        return JSONResponse(content=result)

    except HTTPException as he:
        raise he
    except Exception:
        # Never echo str(e) back to the client: provider SDK exceptions can
        # contain partial API keys, auth headers, or internal endpoint URLs.
        logger.exception("Unexpected server error during summarization")
        raise HTTPException(
            status_code=500,
            detail="An unexpected internal error occurred. Please try again.",
        )


# Mount the static files for CSS, JS, images, etc.
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")