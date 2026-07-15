import logging

import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting Summarix AI PDF Summarizer Server...")
    logger.info("Open http://127.0.0.1:8000 in your browser to view the application.")

    # Run the uvicorn server programmatically
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)