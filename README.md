> [!NOTE]  
> This app is vibe-coded with Antigravity IDE using Gemini 3.5 Flash (Medium) model. The prompt used to make this app can be found in the prompt details folder.

# Summarix AI — PDF Summarizer & Action Extractor

Summarix AI is a PDF summarization tool that transforms long documents into clear, structured summaries and extracts actionable insights.

You can get free Gemini API key from here: https://aistudio.google.com/api-keys

**Key Features:**
- Upload and summarize PDF files
- Professional, Academic, and Simple tone options
- JSON output for summaries and bullet points
- Action item extraction (tasks, deadlines, responsibilities)
- Supports multiple LLM providers (OpenAI, Gemini)
- Streamlined and user-friendly interface


# Get Started

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository (if applicable)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the app:
   ```bash
   python3 app.py
   ```

## Configuration

Create a .env file in the backend directory with your API keys:

```env
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
```

# Quick Start

## 1. Download the App

Download the executable file from [Releases](link-to-releases). Make sure to select the version for your operating system:

- Windows
- macOS
- Linux

## 2. Run the App

### On Windows

1. Double-click the downloaded `.exe` file

### On macOS

1. Open **Terminal**
2. Navigate to the download directory:
   ```bash
   cd ~/Downloads
   ```
3. Run the app:
   ```bash
   ./SummarixAI.app/Contents/MacOS/SummarixAI
   ```

### On Linux

1. Open **Terminal**
2. Navigate to the download directory:
   ```bash
   cd ~/Downloads
   ```
3. Make the file executable:
   ```bash
   chmod +x SummarixAI.AppImage
   ```
4. Run the app:
   ```bash
   ./SummarixAI.AppImage
   ```

## 3. Configure API Key

1. Open the app
2. In the "Settings" tab, enter your Gemini API key
   - Get free Gemini API key from: [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)
3. Click "Save"

## 4. Summarize PDFs

1. In the "Home" tab, upload a PDF file
2. Select summary length
3. Choose tone: Professional, Academic, or Simple
4. Click "Summarize"

## 5. View Results

- **Summary** — Main insights and key points
- **Bullet Points** — Concise key takeaways
- **Action Items** — Tasks, deadlines, and responsibilities

You can copy any section or export the full results as JSON.
