import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .pdf_parser import validate_and_extract_pdf, split_text_into_chunks, PDFValidationError
from .summarizer import summarize_pdf_workflow

app = FastAPI(title="AI PDF Summarizer API", version="1.0.0")

# Enable CORS for local testing/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint: Serve the frontend index.html
@app.get("/")
def read_root():
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "AI PDF Summarizer Backend is running! UI files not found."}

@app.post("/api/summarize")
async def summarize_pdf(
    file: UploadFile = File(...),
    tone: str = Form("simple"),
    provider: str = Form(None),
    api_key: str = Form(None),
    x_provider: str = Header(None, alias="X-Provider"),
    x_api_key: str = Header(None, alias="X-API-Key")
):
    try:
        # Determine provider and api key, prioritizing form arguments, then headers, then env vars
        selected_provider = provider or x_provider
        selected_api_key = api_key or x_api_key
        
        # Fallbacks for provider
        if not selected_provider:
            # Detect based on env vars
            if os.environ.get("GEMINI_API_KEY"):
                selected_provider = "gemini"
            elif os.environ.get("OPENAI_API_KEY"):
                selected_provider = "openai"
            else:
                # Default to gemini if nothing is configured (will trigger key check below)
                selected_provider = "gemini"
                
        # Fallbacks for API Key
        if not selected_api_key:
            if selected_provider == "gemini":
                selected_api_key = os.environ.get("GEMINI_API_KEY")
            elif selected_provider == "openai":
                selected_api_key = os.environ.get("OPENAI_API_KEY")
                
        # Validate that we have an API Key
        if not selected_api_key:
            raise HTTPException(
                status_code=400,
                detail=f"API key missing for provider '{selected_provider}'. Please set it in the settings panel or environment variables."
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
        
        # Define progress logger (we can log to console, or support websockets if we want,
        # but print statements are sufficient for server monitoring for now)
        def progress_log(message: str):
            print(f"[Summary Progress]: {message}")
            
        # Run workflow
        result = summarize_pdf_workflow(
            provider=selected_provider,
            api_key=selected_api_key,
            chunks=chunks,
            full_text=full_text,
            tone=tone,
            progress_callback=progress_log
        )
        
        return JSONResponse(content=result)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# Mount the static files for CSS, JS, images, etc.
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")
    # Also mount it directly at root so relative paths work nicely if needed
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
