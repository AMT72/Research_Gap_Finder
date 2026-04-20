# 🕵️‍♂️ Research_Gap_Finder — Novelty & Gap Detector

> **Autonomous Research Engine** that processes 20–100 academic papers to synthesize knowledge, map citation networks, and identify unexplored "Research Gaps" using LLMs.

---

## 💡 Overview

**Research_Gap_Finder** is a sophisticated tool designed to help researchers skip the "manual review" phase. Instead of reading 50+ papers to find a thesis topic, this system analyzes the entire corpus to find the **Gold (The Gap)**—the specific areas where current research is lacking.

> Upload PDF Corpus  →  Structured Extraction  →  Synthesis Engine  →  Research Gap Discovery

The system doesn't just summarize; it **critiques** and **compares** to find what *hasn't* been done yet.

---

## 🧠 The 4 Intelligence Layers

| Layer | Function | Value |
|---|---|---|
| **1. Comparison Matrix** | Structured extraction of Methods, Datasets, and Results. | Quick pattern recognition across studies. |
| **2. Gap Detection** | Identifying scenarios or datasets no one has covered. | Direct path to "Novel" research ideas. |
| **3. Citation Graph** | Visualizing the "Academic Lineage" (Who cited whom). | Understanding the evolution of the field. |
| **4. Idea Generator** | Proposing new experiments with a **Novelty Score**. | Validating the feasibility of new research directions. |

---

## 🛠️ Architecture & Tech Stack

| Layer | Technology |
|---|---|
| **Language Model** | GPT-4o / Claude 3.5 Sonnet (via LangChain) |
| **Vector DB** | [ChromaDB](https://www.trychroma.com/) — for Semantic Search |
| **PDF Extraction** | `PyMuPDF` + `Grobid` (for layout-aware parsing) |
| **Graph Logic** | `NetworkX` (Backend) + `D3.js` (Frontend visualization) |
| **UI** | [Streamlit](https://streamlit.io/) — Interactive Research Dashboard |
| **Language** | Python 3.11.9 |

---

## 📁 Project Structure

Research_Gap_Finder/
│
├── corpus/                 # User-uploaded Research PDFs
│   └── medical_rag/        # Example topic folder
│
├── src/                    # Source code
│   ├── extractor.py        # PDF to JSON (Abstract, Methods, Limitations)
│   ├── brain.py            # RAG & Gap Analysis logic
│   ├── graph_gen.py        # Citation network & visualization logic
│   └── novelty_score.py    # Similarity & Originality calculation
│
├── notebooks/              # Testing prompts & embeddings
│
├── app.py                  # Streamlit entry point
├── requirements.txt        # Dependencies
└── .env                    # API Keys

---

## 📊 Comparison Matrix (Sample Output)

| Paper | Method | Dataset | Key Result | The Gap (Limitation) |
|:---:|:---:|:---:|:---:|:---:|
| Paper A | RAG + CNN | MIMIC-III | 91% Acc | Limited to text-only retrieval. |
| Paper B | GraphRAG | PubMed | 93% Acc | High latency in real-time inference. |
| **Discovery** | **???** | **???** | **???** | **No study covers Multimodal RAG for Arabic.** |

---

## 🔄 Pipeline Overview

1. **Structured Ingestion:** Using `PyMuPDF` to extract text and segment it into Methodology, Results, and Future Work.
2. **Semantic Embedding:** Transforming text into vectors to find semantic overlaps.
3. **Cross-Paper Analysis:** The LLM compares all papers simultaneously to find "uncovered" datasets or methods.
4. **Graph Generation:** Building a relationship map based on internal citations.
5. **Novelty Evaluation:** Calculating a score based on how "different" a new idea is from the existing corpus.

---

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone <repo-url>
cd Research_Gap_Finder
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the System

```bash
streamlit run app.py
```

## 👥 Team
Azzam Abdullah 

Samer Mawlawi
