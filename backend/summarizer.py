import os
import json
import re
import openai
from google import genai
from google.genai import types

# Setup fallback clients/credentials
# We will initialize them dynamically per request if keys are passed from the client,
# or use these default initializations if the env variables are present.

def get_client(provider: str, api_key: str):
    """
    Returns an configured client or model runner depending on the provider.
    """
    if provider == "openai":
        return openai.OpenAI(api_key=api_key)
    elif provider == "gemini":
        return genai.Client(api_key=api_key)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

def clean_json_response(text: str) -> dict | list:
    """
    Extracts and parses JSON content from a text response, handling markdown fences.
    """
    text = text.strip()
    # Try finding json code block
    json_block = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_block:
        text = json_block.group(1).strip()
        
    # Attempt parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to fix some common LLM JSON syntax issues
        # (e.g., trailing commas, unescaped quotes)
        # For simplicity, if it fails, we will raise an exception and let the caller handle it.
        raise

def call_llm(provider: str, api_key: str, prompt: str, system_instruction: str = None, json_mode: bool = False) -> str:
    """
    Calls the selected LLM provider with the given prompt and parameters.
    """
    if provider == "openai":
        client = get_client("openai", api_key)
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        extra_args = {}
        if json_mode:
            extra_args["response_format"] = {"type": "json_object"}
            
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            **extra_args
        )
        return response.choices[0].message.content.strip()
        
    elif provider == "gemini":
        client = get_client("gemini", api_key)
        
        config = types.GenerateContentConfig(
            temperature=0.2
        )
        if json_mode:
            config.response_mime_type = "application/json"
            
        if system_instruction:
            config.system_instruction = system_instruction
            
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config=config
        )
        return response.text.strip()
    else:
        raise ValueError(f"Invalid provider: {provider}")

def get_tone_guidelines(tone: str) -> str:
    """
    Returns guidelines based on the selected tone.
    """
    tone = tone.lower()
    if tone == "simple":
        return "Tone Guideline: Use plain, easy-to-read, everyday language. Avoid complex jargon. Write simply and clearly, explaining any terms where necessary."
    elif tone == "academic":
        return "Tone Guideline: Use a formal, scholarly, highly structured tone. Maintain technical precision, academic terminology, and objective narration."
    elif tone == "executive":
        return "Tone Guideline: Use an executive tone. Be brief, high-level, and decision-focused. Highlight key risks, opportunities, actions, and strategic takeaways."
    else:
        return "Tone Guideline: Produce a professional and balanced summary."

def summarize_chunk(provider: str, api_key: str, chunk: str, tone: str) -> str:
    """
    Summarizes an individual text chunk using the selected LLM.
    """
    tone_instructions = get_tone_guidelines(tone)
    
    system_instruction = (
        "You are a document summarization assistant. Your task is to summarize chunks of text accurately and concisely.\n"
        "Rules:\n"
        "- Be concise and focused on the key points.\n"
        "- Avoid repetition or introductory fluff.\n"
        "- Output structured text."
    )
    
    prompt = f"""Given the following chunk of text, produce:
1. A short summary (2-3 sentences)
2. A list of key bullet points

{tone_instructions}

---
TEXT CHUNK:
{chunk}
"""
    return call_llm(provider, api_key, prompt, system_instruction=system_instruction)

def merge_summaries(provider: str, api_key: str, chunk_summaries: list[str], tone: str) -> dict:
    """
    Merges multiple chunk summaries into a single final summary and bullet point list.
    """
    tone_instructions = get_tone_guidelines(tone)
    combined_summaries_text = "\n\n=== SECTION SUMMARY ===\n".join(chunk_summaries)
    
    system_instruction = (
        "You are a document summarization assistant. Your task is to merge section summaries into a single final structured JSON summary.\n"
        "You MUST respond with a JSON object containing two keys:\n"
        "- 'summary': a string containing a concise overall summary (1-2 paragraphs)\n"
        "- 'bullet_points': an array of strings representing key bullet points for the entire document.\n"
        "Ensure there is no redundancy or repetition across bullet points."
    )
    
    prompt = f"""Merge the following section summaries into a single cohesive, non-redundant summary.

{tone_instructions}

Ensure the output is JSON in this format:
{{
  "summary": "A concise paragraph summarizing the entire document.",
  "bullet_points": [
    "Key point 1",
    "Key point 2"
  ]
}}

---
SECTION SUMMARIES TO MERGE:
{combined_summaries_text}
"""
    response_text = call_llm(provider, api_key, prompt, system_instruction=system_instruction, json_mode=True)
    return clean_json_response(response_text)

def extract_action_items(provider: str, api_key: str, final_summary_text: str, full_document_text: str = "") -> list:
    """
    Extracts actionable items (tasks, deadlines, and responsibilities) from the document summary.
    If full_document_text is provided, it can be used for extra context or fallback.
    """
    system_instruction = (
        "You are an action item extraction assistant.\n"
        "Your task is to identify and extract clear, actionable items, decisions, and assignments from the text.\n"
        "You MUST respond with a JSON object containing an 'actions' key, which is a list of action item objects.\n"
        "Each action item object MUST have:\n"
        "- 'task': a string describing the clear action to be taken\n"
        "- 'deadline': a string containing the due date, time frame, or milestone mentioned, or null if not specified\n"
        "- 'responsible': a string containing the person, role, or team responsible, or null if not specified\n"
        "Rules:\n"
        "- Only extract clear, actionable items.\n"
        "- Do NOT hallucinate deadlines or responsible parties. If not explicitly mentioned, use null."
    )
    
    prompt = f"""Given the following document summary and context, extract all actionable items.

Ensure the output is JSON in this format:
{{
  "actions": [
    {{
      "task": "Develop the initial project plan",
      "deadline": "End of Q3",
      "responsible": "Engineering Team"
    }}
  ]
}}

---
DOCUMENT SUMMARY:
{final_summary_text}

---
ADDITIONAL CONTEXT (if helpful):
{full_document_text[:15000]}  # limit context to avoid exceeding token limits
"""
    response_text = call_llm(provider, api_key, prompt, system_instruction=system_instruction, json_mode=True)
    parsed = clean_json_response(response_text)
    if isinstance(parsed, dict) and "actions" in parsed:
        return parsed["actions"]
    elif isinstance(parsed, list):
        return parsed
    return []

def summarize_pdf_workflow(provider: str, api_key: str, chunks: list[str], full_text: str, tone: str, progress_callback = None) -> dict:
    """
    Main orchestrator for the PDF summarization workflow.
    """
    # 1. Summarize chunks
    chunk_summaries = []
    total_chunks = len(chunks)
    
    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(f"Summarizing section {i+1} of {total_chunks}...")
        summary = summarize_chunk(provider, api_key, chunk, tone)
        chunk_summaries.append(summary)
        
    # 2. Merge chunk summaries
    if progress_callback:
        progress_callback("Synthesizing final summary...")
        
    if total_chunks == 1:
        # If there's only one chunk, format it into the expected JSON
        # Instead of calling LLM merge, we can do a simplified structured call
        tone_instructions = get_tone_guidelines(tone)
        system_instruction = (
            "You are a document summarization assistant. Structure the summary into a JSON object.\n"
            "You MUST respond with a JSON object containing two keys:\n"
            "- 'summary': a string containing a concise overall summary (1-2 paragraphs)\n"
            "- 'bullet_points': an array of strings representing key bullet points."
        )
        prompt = f"""Convert the following summary notes into a clean JSON structure:
Notes:
{chunk_summaries[0]}

{tone_instructions}

Format:
{{
  "summary": "Concise paragraph",
  "bullet_points": ["bullet 1", "bullet 2"]
}}
"""
        merged = clean_json_response(call_llm(provider, api_key, prompt, system_instruction=system_instruction, json_mode=True))
    else:
        merged = merge_summaries(provider, api_key, chunk_summaries, tone)
        
    # 3. Extract action items
    if progress_callback:
        progress_callback("Extracting actionable items...")
        
    actions = extract_action_items(provider, api_key, merged.get("summary", ""), full_document_text=full_text)
    
    # 4. Return final structured JSON
    return {
        "summary": merged.get("summary", ""),
        "bullet_points": merged.get("bullet_points", []),
        "actions": actions
    }
