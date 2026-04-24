"""
RAG Pipeline: Chunk → Embed → Index → Retrieve
Uses sentence-transformers for embeddings and FAISS for fast similarity search.
No external API needed — runs fully local.
"""

import re
import numpy as np
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import faiss

# ── Embedding model (downloads once, ~90MB, runs on CPU or GPU) ──
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_embed_model: SentenceTransformer | None = None


def get_embed_model() -> SentenceTransformer:
    """Lazy-load the embedding model (singleton)"""
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


# ──────────────────────────────────────────────
# Step 1 — Chunking
# ──────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = 400,
    overlap: int = 80
) -> List[str]:
    """
    Split text into overlapping word-level chunks.
    chunk_size : target words per chunk
    overlap    : words shared between adjacent chunks
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 50:          # skip tiny fragments
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def chunk_papers(papers: List[Dict]) -> List[Dict]:
    """
    Chunk all papers and tag each chunk with its source filename.
    Returns a flat list of chunk dicts:
      { "filename", "chunk_id", "text" }
    """
    all_chunks = []
    for paper in papers:
        chunks = chunk_text(paper["text"])
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "filename": paper["filename"],
                "chunk_id": f"{paper['filename']}::{i}",
                "text": chunk
            })
    return all_chunks


# ──────────────────────────────────────────────
# Step 2 — Embedding & Indexing
# ──────────────────────────────────────────────

class PaperIndex:
    """
    FAISS vector index over paper chunks.
    Build once per session, query many times.
    """

    def __init__(self):
        self.chunks: List[Dict] = []
        self.index: faiss.Index | None = None
        self.embeddings: np.ndarray | None = None

    def build(self, chunks: List[Dict], batch_size: int = 64) -> None:
        """Embed all chunks and build the FAISS index"""
        self.chunks = chunks
        texts = [c["text"] for c in chunks]

        model = get_embed_model()
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True   # cosine via inner-product
        )
        self.embeddings = embeddings.astype("float32")

        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)   # inner-product = cosine (normalized)
        self.index.add(self.embeddings)

    def retrieve(self, query: str, top_k: int = 6) -> List[Dict]:
        """Return the top-k most relevant chunks for a query"""
        if self.index is None or len(self.chunks) == 0:
            return []

        model = get_embed_model()
        q_emb = model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        ).astype("float32")

        scores, indices = self.index.search(q_emb, min(top_k, len(self.chunks)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                chunk = dict(self.chunks[idx])
                chunk["score"] = float(score)
                results.append(chunk)
        return results

    def retrieve_for_paper(self, filename: str, query: str, top_k: int = 4) -> List[Dict]:
        """Retrieve top-k chunks from a specific paper only"""
        all_results = self.retrieve(query, top_k=top_k * 4)
        filtered = [r for r in all_results if r["filename"] == filename]
        return filtered[:top_k]

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)

    @property
    def papers(self) -> List[str]:
        seen = []
        for c in self.chunks:
            if c["filename"] not in seen:
                seen.append(c["filename"])
        return seen


# ──────────────────────────────────────────────
# Step 3 — Context builder (for LLM prompts)
# ──────────────────────────────────────────────

def build_context(chunks: List[Dict], max_chars: int = 3000) -> str:
    """
    Concatenate retrieved chunks into a context string for the LLM.
    Respects max_chars to stay within the model's context window.
    """
    parts = []
    total = 0
    for chunk in chunks:
        snippet = chunk["text"].strip()
        if total + len(snippet) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                parts.append(snippet[:remaining] + "...")
            break
        parts.append(snippet)
        total += len(snippet)
    return "\n\n---\n\n".join(parts)


def build_paper_context(
    index: PaperIndex,
    filename: str,
    query: str,
    top_k: int = 4,
    max_chars: int = 3000
) -> str:
    """Retrieve and format context for a single paper"""
    chunks = index.retrieve_for_paper(filename, query, top_k=top_k)
    if not chunks:
        # fallback: retrieve globally
        chunks = index.retrieve(query, top_k=top_k)
        chunks = [c for c in chunks if c["filename"] == filename]
    return build_context(chunks, max_chars=max_chars)


def build_cross_paper_context(
    index: PaperIndex,
    query: str,
    top_k_per_paper: int = 2,
    max_chars: int = 4000
) -> str:
    """
    Retrieve chunks from EACH paper for cross-paper analysis (gap detection).
    Ensures every paper contributes at least one chunk.
    """
    all_chunks = []
    for filename in index.papers:
        chunks = index.retrieve_for_paper(filename, query, top_k=top_k_per_paper)
        all_chunks.extend(chunks)
    # sort by relevance score
    all_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
    return build_context(all_chunks, max_chars=max_chars)


if __name__ == "__main__":
    # Quick smoke test
    sample_papers = [
        {
            "filename": "paper1.pdf",
            "text": (
                "This paper proposes a CNN-based approach for car damage detection. "
                "We train on the CarDD dataset with 4000 labeled images. "
                "Our ResNet-50 model achieves 91% accuracy. "
                "Limitations include small dataset size and no night-time images. " * 20
            )
        },
        {
            "filename": "paper2.pdf",
            "text": (
                "We present an EfficientNet model for automated insurance claim processing. "
                "The system classifies damage severity into minor, moderate, and severe. "
                "Evaluated on a private dataset of 10,000 images. Accuracy: 88%. "
                "The model does not support video input or Arabic language reports. " * 20
            )
        }
    ]

    print("Chunking papers...")
    chunks = chunk_papers(sample_papers)
    print(f"Total chunks: {len(chunks)}")

    print("Building index...")
    idx = PaperIndex()
    idx.build(chunks)
    print(f"Index size: {idx.total_chunks} chunks")

    print("\nRetrieval test — query: 'dataset limitations'")
    results = idx.retrieve("dataset limitations", top_k=3)
    for r in results:
        print(f"  [{r['filename']}] score={r['score']:.3f} — {r['text'][:80]}...")

    print("\nCross-paper context for gap detection:")
    ctx = build_cross_paper_context(idx, "research gaps limitations future work")
    print(ctx[:400])
