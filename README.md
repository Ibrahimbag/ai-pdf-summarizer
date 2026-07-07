> [!NOTE]  
> This app is vibe-coded with Antigravity IDE using Gemini 3.5 Flash (Medium) model. The prompt used to make this app can be found in the prompt details folder.

# Summarix AI — PDF Summarizer & Action Extractor

Summarix AI is a PDF summarization tool that transforms long documents into clear, structured summaries and extracts actionable insights.

**Key Features:**
- Upload and summarize PDF files
- Professional, Academic, and Simple tone options
- JSON output for summaries and bullet points
- Action item extraction (tasks, deadlines, responsibilities)
- Supports multiple LLM providers (OpenAI, Gemini)
- Streamlined and user-friendly interface


## Get Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository (if applicable)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

1. Run the app:
   ```bash
   python3 run.py
   ```

## How To Use

### 1. Configure API Key

1. Open the app
2. In the "API Configuration" panel, enter your Gemini API key
   - Get free Gemini API key from: [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)
3. Click "Save API Configuration" button

### 2. Summarize PDFs

1. In the "Upload Document" panel, upload a PDF file
2. Choose tone: Simple, Academic or Executive from the top navigation bar
3. Click "Summarize PDF" button

### 3. View Results

- **Summary** — Main insights and key points
- **Bullet Points** — Concise key takeaways
- **Action Items** — Tasks, deadlines, and responsibilities

You can copy any section or export the full results as JSON.
