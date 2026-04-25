# 🔍 Research Gap Finder

> Automatically discover research gaps, compare methodologies, and generate novel research ideas from scientific PDF papers — powered by **RAG + Qwen2.5-7B**, running fully local on Google Colab.

---

## ✨ What It Does

Upload 2–10 research papers (PDF) and the system will:

- 📚 **Summarize** each paper — problem, method, dataset, results, limitations
- 🕳️ **Detect research gaps** ranked by a Novelty Score (0–10)
- 💡 **Generate research ideas** with feasibility ratings (High / Medium / Low)
- 📄 **Export** a professional PDF report + raw JSON data

---

## 🏗️ How It Works

```
PDF files
    │
    ▼
pdf_reader.py      →  extract & clean text from each PDF
    │
    ▼
rag_pipeline.py    →  chunk text → embed (MiniLM-L6) → FAISS index
    │
    ▼
analyzer.py        →  RAG retrieval → Qwen2.5-7B analysis
    │
    ▼
report.py          →  generate downloadable PDF report
    │
    ▼
app.py             →  Streamlit UI
```

**Why RAG?**
Research papers are too long to send entirely to an LLM. RAG retrieves only the most relevant sections per query, which improves accuracy and fits within the model's context window.

---

## 🗂️ Project Structure

```
research-gap-finder/
├── app.py                  ← Streamlit UI (main entry point)
├── analyzer.py             ← Qwen2.5-7B inference + RAG-based analysis
├── rag_pipeline.py         ← Chunking, MiniLM embeddings, FAISS index
├── pdf_reader.py           ← PDF text extraction & cleaning
├── report.py               ← Professional PDF report generation
├── colab_setup.ipynb       ← Google Colab notebook (run this)
├── requirements.txt        ← Python dependencies
├── .gitignore
└── README.md
```

---

## 🚀 How to Run — Google Colab

No API key needed. Runs fully local on a **free T4 GPU**.

### Step 1 — Open the notebook

Open `colab_setup.ipynb` in [Google Colab](https://colab.research.google.com)

### Step 2 — Set runtime to T4 GPU

```
Runtime → Change runtime type → T4 GPU → Save
```

### Step 3 — Run all 8 cells in order

| Cell | What it does |
|------|-------------|
| 1 | Verify GPU is available |
| 2 | Install all Python dependencies |
| 3 | Write `pdf_reader.py` |
| 4 | Write `rag_pipeline.py` |
| 5 | Write `analyzer.py` |
| 6 | Write `report.py` |
| 7 | Write `app.py` |
| 8 | Launch Streamlit via ngrok → get public link |

### Step 4 — Add your ngrok token

In **Cell 8**, paste your free token:

```python
NGROK_TOKEN = 'your_token_here'
```

Get it free at: [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken)

### Step 5 — Open the app

Click the link printed by Cell 8, upload your PDFs, and click **Start Analysis**.

---

## 🤖 Model Details

| Property | Value |
|----------|-------|
| Model | Qwen2.5-7B-Instruct |
| Quantization | 4-bit NF4 (bitsandbytes) |
| VRAM usage | ~6–7 GB |
| First load time | 3–5 minutes |
| GPU required | T4 (16 GB) or better |

The model loads automatically when the Streamlit app starts — no button needed.

---

## 📊 Output Example

**Gap detected:**
> "All reviewed studies use English-only datasets. No work has explored Arabic or multilingual car damage assessment."
> **Novelty Score: 9.2 / 10**

**Idea generated:**
> "Build an Arabic-language damage assessment system using transfer learning on Arabic-annotated images."
> **Feasibility: High**

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `CUDA out of memory` | Restart runtime → Runtime → Restart and run all |
| ngrok tunnel not working | Check token is pasted correctly in Cell 8 |
| Model download slow | Normal — Qwen2.5-7B is ~5 GB, takes ~5 min first time |
| Paper skipped as "too short" | PDF is likely scanned (image-only) — use text-based PDFs |
| PDF report error | Usually caused by special characters in LLM output — download JSON instead |

---

## 🔧 Customization

**Adjust chunk size** (affects how text is split before embedding):
```python
# rag_pipeline.py
def chunk_text(text, chunk_size=400, overlap=80):
```

**Retrieve more context per paper**:
```python
# analyzer.py
context = build_paper_context(index, filename, query=..., top_k=5)  # default: 4
```

**Switch to a larger model** (needs more VRAM — A100 recommended):
```python
# analyzer.py
MODEL_ID = "Qwen/Qwen2.5-14B-Instruct"
```

---

## 🛣️ Roadmap

- [ ] Auto-fetch papers from Arxiv by topic keyword
- [ ] Arabic paper support
- [ ] Support `.docx` and `.txt` input
- [ ] Persistent session history across uploads

---

## 📋 Tech Stack

| Component | Technology |
|-----------|-----------|
| UI | Streamlit |
| PDF parsing | pdfplumber |
| Embeddings | sentence-transformers (MiniLM-L6-v2) |
| Vector search | FAISS |
| LLM | Qwen2.5-7B-Instruct (4-bit quantized) |
| Inference | Transformers + bitsandbytes |
| Report generation | ReportLab |
| Charts | Plotly |
| Deployment | Google Colab + ngrok |

---

## 📄 License

MIT License — free to use, modify, and distribute.
