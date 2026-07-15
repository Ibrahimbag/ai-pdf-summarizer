import json
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Literal, TypedDict

import openai
from google import genai
from google.genai import types

__all__ = ["summarize_pdf_workflow"]

ToneType = Literal["simple", "academic", "executive"]

TONE_GUIDELINES: dict[str, str] = {
    "simple": "Tone Guideline: Use plain, easy-to-read, everyday language. Avoid complex jargon. Write simply and clearly, explaining any terms where necessary.",
    "academic": "Tone Guideline: Use a formal, scholarly, highly structured tone. Maintain technical precision, academic terminology, and objective narration.",
    "executive": "Tone Guideline: Use an executive tone. Be brief, high-level, and decision-focused. Highlight key risks, opportunities, actions, and strategic takeaways.",
}
DEFAULT_TONE_GUIDELINE = "Tone Guideline: Produce a professional and balanced summary."


class SummaryResult(TypedDict):
    summary: str
    bullet_points: list[str]


@lru_cache(maxsize=8)
def get_client(provider: str, api_key: str) -> openai.OpenAI | genai.Client:
    """
    Returns a configured client, reused across calls for the same
    (provider, api_key) pair so the underlying HTTP connection pool isn't
    torn down and rebuilt on every LLM call.
    """
    match provider:
        case "openai":
            return openai.OpenAI(api_key=api_key)
        case "gemini":
            return genai.Client(api_key=api_key)
        case _:
            raise ValueError(f"Unsupported LLM provider: {provider}")


def clean_json_response(text: str) -> dict | list:
    """
    Extracts and parses JSON content from a text response, handling markdown fences.
    """
    text = text.strip()
    if json_block := re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text):
        text = json_block.group(1).strip()
    return json.loads(text)


def clean_json_dict(text: str) -> dict:
    """
    Like clean_json_response, but raises a clear error if the LLM didn't
    return a JSON object (e.g. returned a bare JSON array instead).
    """
    if not isinstance(result := clean_json_response(text), dict):
        raise ValueError(f"Expected JSON object, got {type(result).__name__}")
    return result

def _validate_llm_text(text: str | None, provider_name: str) -> str:
    if not text or not text.strip():
        raise ValueError(f"{provider_name} returned an empty response (possible content/safety filter block).")
    return text.strip()

def call_llm(
    provider: str,
    api_key: str,
    prompt: str,
    system_instruction: str | None = None,
    json_mode: bool = False,
) -> str:
    """
    Calls the selected LLM provider with the given prompt and parameters.
    """
    match provider:
        case "openai":
            client = get_client("openai", api_key)
            messages = [{"role": "system", "content": system_instruction}] if system_instruction else []
            messages.append({"role": "user", "content": prompt})

            extra_args = {"response_format": {"type": "json_object"}} if json_mode else {}

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                **extra_args,
            )

            return _validate_llm_text(response.choices[0].message.content, "OpenAI")

        case "gemini":
            client = get_client("gemini", api_key)

            # Build the config fully at construction time — mutating a
            # GenerateContentConfig's fields after construction can silently
            # fail validation depending on the SDK's pydantic model settings.
            config = types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json" if json_mode else None,
                system_instruction=system_instruction if system_instruction else None,
            )

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config=config,
            )
            
            return _validate_llm_text(response.text, "Gemini")
        
        case _:
            raise ValueError(f"Invalid provider: {provider}")


def get_tone_guidelines(tone: str) -> str:
    """
    Returns guidelines based on the selected tone. Unrecognized tone values
    fall back to a default guideline rather than raising.
    """
    return TONE_GUIDELINES.get(tone.lower(), DEFAULT_TONE_GUIDELINE)


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


def merge_summaries(provider: str, api_key: str, chunk_summaries: list[str], tone: str) -> SummaryResult:
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
    result = clean_json_dict(response_text)
    if "summary" not in result or "bullet_points" not in result:
        raise ValueError(f"LLM response missing required keys: {list(result.keys())}")
    return SummaryResult(
        summary=str(result["summary"]),
        bullet_points=list(result["bullet_points"]),
    )


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

    # Context is capped to 15000 chars to avoid exceeding token limits.
    context_snippet = full_document_text[:15000]

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
{context_snippet}
"""
    response_text = call_llm(provider, api_key, prompt, system_instruction=system_instruction, json_mode=True)
    
    match clean_json_response(response_text):
        case {"actions": list(actions)}:
            return actions
        case list(actions):
            return actions
        case _:
            return []


def summarize_pdf_workflow(
    provider: str,
    api_key: str,
    chunks: list[str],
    full_text: str,
    tone: str,
    progress_callback: Callable[[str], None] | None = None,
) -> dict:
    """
    Main orchestrator for the PDF summarization workflow.
    """
    # Local helper for progress callback to clean up repeated conditional checks
    def log(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    total_chunks = len(chunks)
    chunk_summaries: list[str | None] = [None] * total_chunks

    log(f"Summarizing {total_chunks} section(s)...")

    with ThreadPoolExecutor(max_workers=min(total_chunks, 5) or 1) as executor:
        futures = {
            executor.submit(summarize_chunk, provider, api_key, chunk, tone): i
            for i, chunk in enumerate(chunks)
        }
        completed = 0
        for future in as_completed(futures):
            idx = futures[future]
            chunk_summaries[idx] = future.result()
            completed += 1
            log(f"Summarized section {completed} of {total_chunks}...")

    log("Synthesizing final summary...")

    if total_chunks == 1:
        # If there's only one chunk, format it into the expected JSON structure
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
        result = clean_json_dict(
            call_llm(provider, api_key, prompt, system_instruction=system_instruction, json_mode=True)
        )
        merged = SummaryResult(
            summary=str(result.get("summary", "")),
            bullet_points=list(result.get("bullet_points", [])),
        )
    else:
        merged = merge_summaries(provider, api_key, chunk_summaries, tone)

    log("Extracting actionable items...")
    actions = extract_action_items(provider, api_key, merged["summary"], full_document_text=full_text)

    return {
        "summary": merged["summary"],
        "bullet_points": merged["bullet_points"],
        "actions": actions,
    }