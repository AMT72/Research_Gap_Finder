import json
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from rag_pipeline import PaperIndex, chunk_papers, build_paper_context, build_cross_paper_context

MODEL_ID   = "Qwen/Qwen2.5-7B-Instruct"
_tokenizer = None
_model     = None


def load_model():
    global _tokenizer, _model
    if _model is not None:
        return _tokenizer, _model
    print(f"Loading {MODEL_ID} with 4-bit quantization...")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16
    )
    _model.eval()
    print("Model loaded.")
    return _tokenizer, _model


def _infer(prompt, max_new_tokens=800, temperature=0.1):
    tokenizer, model = load_model()
    msgs = [
        {"role": "system", "content": "You are an expert research analyst. Always respond with valid JSON only."},
        {"role": "user",   "content": prompt}
    ]
    text   = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=(temperature > 0),
            pad_token_id=tokenizer.eos_token_id
        )
    generated = out[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def _parse_json(raw):
    raw = re.sub(r"^```json\s*", "", raw.strip())
    raw = re.sub(r"^```\s*",     "", raw)
    raw = re.sub(r"\s*```$",     "", raw)
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        raw = m.group(0)
    return json.loads(raw)


def build_index(papers):
    chunks = chunk_papers(papers)
    index  = PaperIndex()
    index.build(chunks)
    return index


SUMMARY_PROMPT = """Analyze the research paper excerpt below. Return valid JSON only, no extra text.

{{
  "title": "Paper title",
  "year": "year or unknown",
  "authors": "authors or unknown",
  "problem": "one-sentence problem statement",
  "method": "method or algorithm used",
  "dataset": "dataset(s) used",
  "main_result": "key result",
  "limitations": ["limitation 1", "limitation 2", "limitation 3"],
  "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"]
}}

--- PAPER EXCERPT ---
{context}
--- END ---"""


def summarize_paper(index, filename):
    context = build_paper_context(
        index, filename,
        query="title authors abstract problem method dataset results limitations keywords",
        top_k=4,
        max_chars=2500
    )
    if not context.strip():
        return {
            "filename": filename, "status": "error", "error": "No RAG content",
            "title": filename, "year": "?", "authors": "?", "problem": "?",
            "method": "?", "dataset": "?", "main_result": "?",
            "limitations": [], "keywords": []
        }
    try:
        raw    = _infer(SUMMARY_PROMPT.format(context=context), max_new_tokens=600)
        result = _parse_json(raw)
        if isinstance(result, dict):
            result["filename"] = filename
            result["status"]   = "ok"
            return result
        raise ValueError("Response is not a dict")
    except Exception as e:
        return {
            "filename": filename, "status": "error", "error": str(e),
            "title": filename, "year": "?", "authors": "?", "problem": "?",
            "method": "?", "dataset": "?", "main_result": "?",
            "limitations": [], "keywords": []
        }


GAP_PROMPT = """Identify research gaps from {n_papers} research paper excerpts below.
Return valid JSON only, no extra text.

{{
  "common_methods": ["method1", "method2", "method3"],
  "common_datasets": ["dataset1", "dataset2"],
  "common_limitations": ["limitation1", "limitation2", "limitation3"],
  "research_gaps": [
    {{"gap": "gap description", "evidence": "evidence from papers", "novelty_score": 8.5}},
    {{"gap": "gap 2",           "evidence": "evidence",             "novelty_score": 7.0}},
    {{"gap": "gap 3",           "evidence": "evidence",             "novelty_score": 6.0}}
  ],
  "suggested_ideas": [
    {{"idea": "idea title", "addresses_gap": "gap it targets", "feasibility": "High",   "why_promising": "reason"}},
    {{"idea": "idea 2",     "addresses_gap": "gap it targets", "feasibility": "Medium", "why_promising": "reason"}}
  ],
  "overall_summary": "2-3 sentence overview of the field"
}}

--- CROSS-PAPER EXCERPTS ---
{context}

--- PAPER SUMMARIES ---
{summaries_text}"""


def _build_summaries_text(summaries):
    lines = []
    for i, s in enumerate(summaries, 1):
        title    = s.get("title",    s.get("filename", f"Paper {i}"))
        method   = s.get("method",   "N/A")
        dataset  = s.get("dataset",  "N/A")
        lims     = s.get("limitations", [])
        lims_str = "; ".join(lims) if isinstance(lims, list) else str(lims)
        lines.append(f"Paper {i}: {title}")
        lines.append(f"  Method: {method}")
        lines.append(f"  Dataset: {dataset}")
        lines.append(f"  Limitations: {lims_str}")
        lines.append("")
    return "\n".join(lines)


def detect_gaps(summaries, index):
    context = build_cross_paper_context(
        index,
        query="research gaps limitations future work unexplored directions",
        top_k_per_paper=2,
        max_chars=3000
    )
    prompt = GAP_PROMPT.format(
        n_papers=len(summaries),
        context=context,
        summaries_text=_build_summaries_text(summaries)
    )
    try:
        raw    = _infer(prompt, max_new_tokens=900, temperature=0.2)
        result = _parse_json(raw)
        if isinstance(result, dict):
            result["status"] = "ok"
            return result
        raise ValueError("Response is not a dict")
    except Exception as e:
        return {
            "status": "error", "error": str(e),
            "common_methods": [], "common_datasets": [], "common_limitations": [],
            "research_gaps": [], "suggested_ideas": [],
            "overall_summary": "Analysis failed."
        }
