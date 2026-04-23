"""
Phase 2 & 3: Paper summarization and research gap detection via Claude API
"""



import json
import re
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)

client = anthropic.Anthropic()
MODEL = "claude-3-5-sonnet-20240620"


# ──────────────────────────────────────────────
# Phase 2: Summarize each research paper
# ──────────────────────────────────────────────

SUMMARY_PROMPT = """You are an expert research analyst. Analyze the following research paper and extract key information.

Reply with JSON only — no text outside the JSON — using this exact structure:

{{
  "title": "Paper title",
  "year": "Publication year or unknown",
  "authors": "Main authors",
  "problem": "The problem this paper solves in one sentence",
  "method": "The method or model used",
  "dataset": "Dataset(s) used for experiments",
  "main_result": "The most important numerical or qualitative result",
  "limitations": ["limitation 1", "limitation 2", "limitation 3"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}

Research paper:
{paper_text}"""


def summarize_paper(paper_text: str, filename: str = "") -> dict:
    """Summarize a single research paper using Claude"""
    prompt = SUMMARY_PROMPT.format(paper_text=paper_text)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        result = json.loads(raw)
        result["filename"] = filename
        result["status"] = "ok"
        return result

    except json.JSONDecodeError as e:
        return {
            "filename": filename,
            "status": "parse_error",
            "error": str(e),
            "title": filename,
            "year": "unknown",
            "authors": "unknown",
            "problem": "Failed to extract information",
            "method": "unknown",
            "dataset": "unknown",
            "main_result": "unknown",
            "limitations": [],
            "keywords": []
        }
    except Exception as e:
        return {
            "filename": filename,
            "status": "api_error",
            "error": str(e),
            "title": filename,
            "year": "unknown",
            "authors": "unknown",
            "problem": "API connection error",
            "method": "unknown",
            "dataset": "unknown",
            "main_result": "unknown",
            "limitations": [],
            "keywords": []
        }


def summarize_all_papers(papers: list[dict]) -> list[dict]:
    """Summarize a list of research papers"""
    summaries = []
    for paper in papers:
        summary = summarize_paper(paper["text"], paper["filename"])
        summaries.append(summary)
    return summaries


# ──────────────────────────────────────────────
# Phase 3: Research Gap Detection
# ──────────────────────────────────────────────

GAP_PROMPT = """You are an expert at analyzing research literature and identifying research gaps.

Based on the following paper summaries, perform a comprehensive analysis:

{summaries_text}

Reply with JSON only — no text outside the JSON — using this exact structure:

{{
  "common_methods": ["most used method", "second", "third"],
  "common_datasets": ["most used dataset", "second"],
  "common_limitations": ["shared limitation 1", "shared limitation 2", "shared limitation 3"],
  "research_gaps": [
    {{
      "gap": "Description of the research gap",
      "evidence": "Evidence from the papers supporting this gap",
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
      "novelty_score": 6.5
    }}
  ],
  "suggested_ideas": [
    {{
      "idea": "A promising research idea that addresses the gap",
      "addresses_gap": "Which gap it addresses",
      "feasibility": "High / Medium / Low",
      "why_promising": "Why this idea is promising"
    }},
    {{
      "idea": "Second idea",
      "addresses_gap": "Gap it addresses",
      "feasibility": "High",
      "why_promising": "Reason"
    }}
  ],
  "overall_summary": "A 2-3 sentence overview of the field and its main trends"
}}"""


def detect_gaps(summaries: list[dict]) -> dict:
    """Detect research gaps from paper summaries"""
    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += f"""
Paper {i}: {s.get('title', s.get('filename', f'Paper {i}'))}
- Problem: {s.get('problem', 'N/A')}
- Method: {s.get('method', 'N/A')}
- Dataset: {s.get('dataset', 'N/A')}
- Result: {s.get('main_result', 'N/A')}
- Limitations: {', '.join(s.get('limitations', []))}
- Keywords: {', '.join(s.get('keywords', []))}
"""

    prompt = GAP_PROMPT.format(summaries_text=summaries_text)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        result = json.loads(raw)
        result["status"] = "ok"
        return result

    except json.JSONDecodeError as e:
        return {
            "status": "parse_error",
            "error": str(e),
            "common_methods": [],
            "common_datasets": [],
            "common_limitations": [],
            "research_gaps": [],
            "suggested_ideas": [],
            "overall_summary": "Failed to analyze data"
        }
    except Exception as e:
        return {
            "status": "api_error",
            "error": str(e),
            "common_methods": [],
            "common_datasets": [],
            "common_limitations": [],
            "research_gaps": [],
            "suggested_ideas": [],
            "overall_summary": "Connection error"
        }


# ──────────────────────────────────────────────
# Citation Graph: Relations between papers
# ──────────────────────────────────────────────

CITATION_PROMPT = """Based on the following paper summaries, identify logical relationships between them.

{summaries_text}

Reply with JSON only:
{{
  "relations": [
    {{"from": "paper number", "to": "paper number", "type": "extends / compares / uses_same_dataset / contradicts"}},
    {{"from": "...", "to": "...", "type": "..."}}
  ]
}}

Use paper numbers (1, 2, 3...) as identifiers."""


def build_citation_relations(summaries: list[dict]) -> list[dict]:
    """Extract relationships between papers"""
    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += f"Paper {i}: {s.get('title', f'Paper {i}')} — Method: {s.get('method', '')} — Dataset: {s.get('dataset', '')}\n"

    prompt = CITATION_PROMPT.format(summaries_text=summaries_text)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        return data.get("relations", [])
    except Exception:
        return []


if __name__ == "__main__":
    print("Testing analyzer.py")
    test_text = """
    This paper presents a deep learning approach for car damage detection using CNNs.
    We use the CarDD dataset with 4000 images. Our model achieves 91% accuracy.
    However, the model struggles with low-light conditions and rare damage types.
    Keywords: damage detection, CNN, automotive, deep learning, insurance
    """
    result = summarize_paper(test_text, "test_paper.pdf")
    print(json.dumps(result, ensure_ascii=False, indent=2))
