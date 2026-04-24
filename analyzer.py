"""
Phase 2 & 3: Paper summarization and gap detection
Using Ollama (local LLM) + RAG pipeline — no external API key needed.
"""

import json
import re
import requests
from typing import List, Dict

from rag_pipeline import (
    PaperIndex, chunk_papers,
    build_paper_context, build_cross_paper_context
)

# ── Ollama config ──────────────────────────────
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:14b"   # Change to "llama3:8b" if VRAM < 12GB


def _ollama(prompt: str, temperature: float = 0.1) -> str:
    """
    Send a prompt to the local Ollama server and return the response text.
    Raises RuntimeError if Ollama is not running.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 1024,
        }
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. "
            "Make sure Ollama is running: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out (>180s). Try a smaller model.")


def _parse_json(raw: str) -> dict | list:
    """Strip markdown fences and parse JSON"""
    raw = re.sub(r'^```json\s*', '', raw.strip())
    raw = re.sub(r'^```\s*',     '', raw)
    raw = re.sub(r'\s*```$',     '', raw)
    return json.loads(raw)


def check_ollama() -> dict:
    """
    Check if Ollama is running and the chosen model is available.
    Returns {"ok": bool, "models": [...], "error": str}
    """
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        model_ready = any(OLLAMA_MODEL.split(":")[0] in m for m in models)
        return {"ok": model_ready, "models": models, "error": ""}
    except Exception as e:
        return {"ok": False, "models": [], "error": str(e)}


# ──────────────────────────────────────────────
# Build RAG index
# ──────────────────────────────────────────────

def build_index(papers: List[Dict]) -> PaperIndex:
    """Chunk all papers and build the FAISS vector index"""
    chunks = chunk_papers(papers)
    index = PaperIndex()
    index.build(chunks)
    return index


# ──────────────────────────────────────────────
# Phase 2 — Summarize a single paper via RAG
# ──────────────────────────────────────────────

SUMMARY_PROMPT = """You are an expert research analyst. Analyze the research paper excerpt below and extract key information.

Respond with valid JSON only — no text outside the JSON block.

{{
  "title": "Paper title (or 'Unknown' if not found)",
  "year": "Publication year or 'unknown'",
  "authors": "Main authors or 'unknown'",
  "problem": "The specific problem this paper solves — one sentence",
  "method": "The method, model, or algorithm used",
  "dataset": "Dataset(s) used for experiments",
  "main_result": "Most important numerical or qualitative result",
  "limitations": ["limitation 1", "limitation 2", "limitation 3"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}

--- PAPER EXCERPT ---
{context}
--- END EXCERPT ---

JSON response:"""


def summarize_paper(index: PaperIndex, filename: str) -> dict:
    """
    Summarize one paper using RAG:
    1. Retrieve the most relevant chunks from that paper.
    2. Feed them to the local LLM.
    """
    # Retrieve chunks covering the key sections
    context = build_paper_context(
        index, filename,
        query="title authors abstract problem method dataset results limitations keywords",
        top_k=5,
        max_chars=3200
    )

    if not context.strip():
        return _error_summary(filename, "No content retrieved from RAG index")

    prompt = SUMMARY_PROMPT.format(context=context)

    try:
        raw = _ollama(prompt)
        result = _parse_json(raw)
        if isinstance(result, dict):
            result["filename"] = filename
            result["status"]   = "ok"
            return result
        return _error_summary(filename, "LLM returned non-dict JSON")
    except json.JSONDecodeError as e:
        return _error_summary(filename, f"JSON parse error: {e}")
    except RuntimeError as e:
        return _error_summary(filename, str(e))
    except Exception as e:
        return _error_summary(filename, str(e))


def _error_summary(filename: str, error: str) -> dict:
    return {
        "filename": filename, "status": "error", "error": error,
        "title": filename, "year": "unknown", "authors": "unknown",
        "problem": "Failed to extract information",
        "method": "unknown", "dataset": "unknown", "main_result": "unknown",
        "limitations": [], "keywords": []
    }


# ──────────────────────────────────────────────
# Phase 3 — Gap detection via RAG
# ──────────────────────────────────────────────

GAP_PROMPT = """You are an expert at identifying research gaps in scientific literature.

Below are excerpts retrieved from {n_papers} research papers on the same topic.
Analyze them carefully and produce a structured gap analysis.

Respond with valid JSON only — no text outside the JSON block.

{{
  "common_methods": ["method 1", "method 2", "method 3"],
  "common_datasets": ["dataset 1", "dataset 2"],
  "common_limitations": ["shared limitation 1", "shared limitation 2", "shared limitation 3"],
  "research_gaps": [
    {{
      "gap": "Precise description of the research gap",
      "evidence": "Which papers or patterns reveal this gap",
      "novelty_score": 8.5
    }},
    {{
      "gap": "Second gap",
      "evidence": "Evidence",
      "novelty_score": 7.0
    }},
    {{
      "gap": "Third gap",
      "evidence": "Evidence",
      "novelty_score": 6.0
    }}
  ],
  "suggested_ideas": [
    {{
      "idea": "A concrete research idea that addresses the gap",
      "addresses_gap": "Which gap it targets",
      "feasibility": "High / Medium / Low",
      "why_promising": "Why this direction is worth pursuing"
    }},
    {{
      "idea": "Second idea",
      "addresses_gap": "Gap it targets",
      "feasibility": "High",
      "why_promising": "Reason"
    }}
  ],
  "overall_summary": "2-3 sentence overview of the field's current state and main trends"
}}

--- RETRIEVED EXCERPTS ---
{context}
--- END EXCERPTS ---

Also consider this structured summary of all papers:
{summaries_text}

JSON response:"""


def detect_gaps(summaries: List[Dict], index: PaperIndex) -> dict:
    """
    Detect research gaps using RAG:
    1. Retrieve cross-paper chunks most relevant to gap analysis.
    2. Also pass structured summaries for grounding.
    3. Feed everything to the local LLM.
    """
    # Cross-paper retrieval focused on gaps & limitations
    context = build_cross_paper_context(
        index,
        query="research gaps limitations future work unexplored directions",
        top_k_per_paper=2,
        max_chars=4000
    )

    # Build a compact text table of all summaries
    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += (
            f"Paper {i}: {s.get('title', s.get('filename', f'Paper {i}'))}\n"
            f"  Method: {s.get('method', 'N/A')}\n"
            f"  Dataset: {s.get('dataset', 'N/A')}\n"
            f"  Result: {s.get('main_result', 'N/A')}\n"
            f"  Limitations: {'; '.join(s.get('limitations', []))}\n\n"
        )

    prompt = GAP_PROMPT.format(
        n_papers=len(summaries),
        context=context,
        summaries_text=summaries_text
    )

    try:
        raw = _ollama(prompt, temperature=0.2)
        result = _parse_json(raw)
        if isinstance(result, dict):
            result["status"] = "ok"
            return result
        return _error_gaps("LLM returned non-dict JSON")
    except json.JSONDecodeError as e:
        return _error_gaps(f"JSON parse error: {e}")
    except RuntimeError as e:
        return _error_gaps(str(e))
    except Exception as e:
        return _error_gaps(str(e))


def _error_gaps(error: str) -> dict:
    return {
        "status": "error", "error": error,
        "common_methods": [], "common_datasets": [], "common_limitations": [],
        "research_gaps": [], "suggested_ideas": [],
        "overall_summary": "Analysis failed."
    }


# ──────────────────────────────────────────────
# Citation graph relations
# ──────────────────────────────────────────────

CITATION_PROMPT = """Based on the summaries below, identify logical relationships between the papers.

{summaries_text}

Respond with valid JSON only:
{{
  "relations": [
    {{"from": "1", "to": "2", "type": "extends / compares / uses_same_dataset / contradicts"}},
    {{"from": "2", "to": "3", "type": "extends"}}
  ]
}}

Use paper numbers (1, 2, 3...) as identifiers. Only include meaningful relations.

JSON response:"""


def build_citation_relations(summaries: List[Dict]) -> List[Dict]:
    """Extract inter-paper relationships using the local LLM"""
    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += (
            f"Paper {i}: {s.get('title', f'Paper {i}')} "
            f"— Method: {s.get('method', '')} "
            f"— Dataset: {s.get('dataset', '')}\n"
        )

    prompt = CITATION_PROMPT.format(summaries_text=summaries_text)

    try:
        raw = _ollama(prompt)
        data = _parse_json(raw)
        return data.get("relations", []) if isinstance(data, dict) else []
    except Exception:
        return []


if __name__ == "__main__":
    status = check_ollama()
    print("Ollama status:", status)
