# AI PDF Summarizer Agent — Project Specification

## Overview

Build a simple but production-ready AI-powered PDF summarization tool. The system should:

- Accept a PDF upload
- Extract and process text
- Generate a structured summary
- Extract actionable items (tasks, deadlines, responsibilities)
- Return a clean JSON response
- Display results in a simple frontend UI

---

## System Architecture

```
User Upload PDF
      │
      ▼
Backend API (FastAPI / Node.js)
      │
      ▼
PDF Parser (PyPDF / pdfplumber)
      │
      ▼
Split text into chunks (1000–2000 tokens)
      │
      ▼
AI Agent (LLM)
  - Understand document
  - Extract key points
  - Identify decisions
  - Generate tasks
      │
    ┌─┴─────────────────┐
    ▼                   ▼
Summary Output      Action Items
- Short summary     - Tasks
- Bullet points     - Deadlines (if any)
                    - Responsibilities
    └──────┬─────────────┘
           ▼
  Format response as JSON
  {
    "summary": "...",
    "actions": [...]
  }
           │
           ▼
      Frontend UI
  - Show summary
  - Show action list
  - Download / Copy
```

---

## Core Workflow

1. User uploads a PDF
2. Backend validates the file
3. PDF text is extracted
4. Text is split into chunks (1000–2000 tokens)
5. Each chunk is summarized individually
6. Chunk summaries are merged into a final summary
7. A separate agent extracts action items
8. Response is formatted as JSON
9. Frontend displays results

---

## Tech Stack

### Backend
- **Runtime:** Node.js (Express) OR Python (FastAPI)
- **PDF Parsing:** PyPDF / pdfplumber
- **LLM API:** OpenAI or equivalent

### Frontend
- Simple UI (React or plain HTML)
- File upload component
- Summary + action items display

---

## Required Features

### 1. Validation Layer
- Reject empty files
- Limit file size (max 10MB)
- Handle parsing errors gracefully

### 2. Chunking System
- Split extracted text into chunks of 1000–2000 tokens
- Ensure chunks do not break sentences badly

### 3. Summarization Agent

**Per chunk, generate:**
- Short summary (2–3 sentences)
- Key bullet points

**Final merge output:**
- Concise overall summary
- Clean bullet list

### 4. Action Extraction Agent

From the full document summary, extract:
- Tasks
- Deadlines (if mentioned)
- Responsible parties (if mentioned)

---

## LLM Prompt Design

### Summarization Prompt
```
You are a document summarization assistant.

Given the following chunk of text, produce:
1. A short summary (2-3 sentences)
2. A list of key bullet points

Rules:
- Be concise
- Avoid repetition
- Focus on key information
- Output structured text
```

### Action Extraction Prompt
```
You are an action item extraction assistant.

Given the following document summary, extract all actionable items.

Rules:
- Only extract clear, actionable items
- Do NOT hallucinate missing information
- If deadline or responsible party is not mentioned, return null
- Return a structured JSON list
```

---

## Output Format (STRICT)

Return JSON in this exact format:

```json
{
  "summary": "string",
  "bullet_points": [
    "string",
    "string"
  ],
  "actions": [
    {
      "task": "string",
      "deadline": "string or null",
      "responsible": "string or null"
    }
  ]
}
```

---

## Frontend Requirements

| Component | Description |
|---|---|
| File Upload | Drag-and-drop or click-to-upload, PDF only |
| Loading State | Spinner or progress indicator while processing |
| Summary Panel | Display final summary text |
| Bullet Points | Rendered list of key points |
| Action Items | Table or card list of tasks, deadlines, owners |
| Copy Button | Copy full JSON result to clipboard |

---

## Optional Enhancements

> Implement if time permits.

- **Tone Selection:**
  - `Simple` — plain language, easy to read
  - `Academic` — formal, structured
  - `Executive` — brief, decision-focused

- **Download Result:** Export output as `.json` file

---

## Code Quality Expectations

- Clean, modular code structure
- Clear separation of concerns (parsing / AI / API / UI layers)
- Easy to extend with new features
- Minimal but functional UI

---

## Project Goal

Deliver a working MVP that can:

- ✅ Process real PDFs
- ✅ Produce useful, structured summaries
- ✅ Extract meaningful action items
- ✅ Be ready for real-world usage
