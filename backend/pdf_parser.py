import re
from io import BytesIO

from pypdf import PdfReader

__all__ = ["PDFValidationError", "validate_and_extract_pdf", "split_text_into_chunks"]

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')
_PDF_MAGIC = b"%PDF-"


class PDFValidationError(Exception):
    """Raised when a PDF file cannot be validated or parsed."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause

    def __repr__(self) -> str:
        return f"PDFValidationError({self.args[0]!r})"


def validate_and_extract_pdf(file_content: bytes, filename: str | None) -> str:
    """
    Validates the PDF file (size, format) and extracts all text content.
    """
    # 1. Reject empty files
    if not file_content:
        raise PDFValidationError("The uploaded file is empty.")

    # 2. Limit file size (max 10MB)
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    if len(file_content) > MAX_SIZE:
        raise PDFValidationError("The file exceeds the maximum allowed size of 10MB.")

    # 3. Validate extension (filename may be None if the client omits it)
    if not filename or not filename.lower().endswith(".pdf"):
        raise PDFValidationError("Invalid file type. Only PDF files are supported.")

    # 4. Validate magic bytes — an extension check alone is trivially bypassed
    if not file_content.startswith(_PDF_MAGIC):
        raise PDFValidationError("File does not appear to be a valid PDF (invalid magic bytes).")

    try:
        pdf_file = BytesIO(file_content)
        reader = PdfReader(pdf_file)

        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)

        full_text = "\n".join(extracted_text).strip()

        if not full_text:
            raise PDFValidationError(
                "Could not extract any readable text from the PDF. The file might be scanned or image-only."
            )

        return full_text
    except PDFValidationError:
        raise
    except Exception as e:
        raise PDFValidationError(f"Failed to parse PDF: {e}", cause=e) from e


def split_text_into_chunks(text: str, chunk_size_chars: int = 6000, overlap_chars: int = 500) -> list[str]:
    """
    Splits the extracted text into chunks of roughly 1000–2000 tokens (4000-8000 characters).
    Ensures that sentences are not broken badly by splitting on sentence boundaries.
    """
    sentences = _SENTENCE_SPLIT_RE.split(text)

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_len = len(sentence)

        # If a single sentence is extremely long (longer than chunk_size_chars),
        # we have to split it by character chunking
        if sentence_len > chunk_size_chars:
            # Finish current chunk if there is anything in it
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0

            # Split the giant sentence into character chunks
            start = 0
            while start < sentence_len:
                end = min(start + chunk_size_chars, sentence_len)
                chunks.append(sentence[start:end])
                start += chunk_size_chars - overlap_chars
            continue

        if current_length + sentence_len + 1 > chunk_size_chars:
            # Current chunk is full, save it
            chunks.append(" ".join(current_chunk))

            # Start new chunk with overlap if possible
            # Find how many sentences to keep from the end of current_chunk for overlap
            overlap_text = []
            overlap_len = 0
            for prev_sentence in reversed(current_chunk):
                if overlap_len + len(prev_sentence) + 1 <= overlap_chars:
                    overlap_text.insert(0, prev_sentence)
                    overlap_len += len(prev_sentence) + 1
                else:
                    break

            current_chunk = overlap_text + [sentence]
            current_length = sum(len(s) for s in current_chunk) + len(current_chunk) - 1
        else:
            current_chunk.append(sentence)
            current_length += sentence_len + (1 if current_length > 0 else 0)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks