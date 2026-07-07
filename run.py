import uvicorn
import os

if __name__ == "__main__":
    print("Starting Summarix AI PDF Summarizer Server...")
    print("Open http://127.0.0.1:8000 in your browser to view the application.")
    
    # Run the uvicorn server programmatically
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
