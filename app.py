import json
import streamlit as st
import plotly.express as px
from pdf_reader import process_pdf
from analyzer import build_index, summarize_paper, detect_gaps, MODEL_ID, load_model
from report import generate_report

st.set_page_config(page_title="Research Gap Finder", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #0C447C, #185FA5);
    color: white; padding: 1.5rem 2rem;
    border-radius: 12px; margin-bottom: 1.5rem;
}
.gap-card {
    background: #EAF3DE; border: 1px solid #C0DD97;
    border-radius: 8px; padding: 1rem; margin: 0.5rem 0;
}
.idea-card {
    background: #EEEDFE; border: 1px solid #CECBF6;
    border-radius: 8px; padding: 1rem; margin: 0.5rem 0;
}
.score-high   { color: #0F6E56; font-weight: bold; font-size: 1.2em; }
.score-medium { color: #185FA5; font-weight: bold; font-size: 1.2em; }
.score-low    { color: #854F0B; font-weight: bold; font-size: 1.2em; }
</style>
""", unsafe_allow_html=True)

# ── Auto-load model on startup ──
if "model_loaded" not in st.session_state:
    st.session_state["model_loaded"] = False

if not st.session_state["model_loaded"]:
    with st.spinner("⏳ Loading Qwen2.5-7B... (3–5 min first time)"):
        load_model()
        st.session_state["model_loaded"] = True

# ── Sidebar ──
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown(f"**Model:** `{MODEL_ID}`")
    st.markdown("**Runtime:** Google Colab T4 GPU")
    st.success("✅ Qwen2.5-7B ready")
    st.markdown("---")
    st.markdown("### How to use")
    st.markdown("1. Upload 2–10 PDF papers\n2. Click **Start Analysis**\n3. View results & download report")
    st.markdown("---")
    st.caption("PDF → chunks → MiniLM → FAISS → RAG → Qwen2.5-7B → report")

# ── Header ──
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size:1.8rem;">🔍 Research Gap Finder</h1>
    <p style="margin:0.3rem 0 0; opacity:0.85;">
        Powered by Qwen2.5-7B + RAG — fully local on Colab T4
    </p>
</div>
""", unsafe_allow_html=True)

# ── File upload ──
st.markdown("### 📂 Upload Research Papers")
uploaded_files = st.file_uploader(
    "Select 2–10 PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    n = len(uploaded_files)
    if n < 2:
        st.warning("⚠️ Upload at least 2 papers.")
    elif n > 10:
        st.warning("⚠️ Maximum 10 papers.")
    else:
        st.success(f"✅ {n} papers ready")
        cols = st.columns(min(n, 5))
        for i, f in enumerate(uploaded_files):
            with cols[i % 5]:
                st.caption(f"📄 {f.name[:22]}...")

# ── Analyze button ──
st.markdown("---")
files_ok    = bool(uploaded_files) and 2 <= len(uploaded_files) <= 10
analyze_btn = st.button(
    "🚀 Start Analysis",
    type="primary",
    disabled=not files_ok,
    use_container_width=True
)

# ── Analysis pipeline ──
if analyze_btn:

    with st.status("📖 Reading PDFs...", expanded=True) as status:
        papers   = []
        progress = st.progress(0)
        for i, f in enumerate(uploaded_files):
            p = process_pdf(f.read(), f.name)
            if p["status"] == "too_short":
                st.warning(f"⚠️ {f.name}: too short or scanned — skipped.")
            else:
                papers.append(p)
                st.write(f"✅ {f.name} — {p['cleaned_length']:,} chars")
            progress.progress((i + 1) / len(uploaded_files))
        status.update(label=f"✅ Loaded {len(papers)} papers", state="complete")

    if len(papers) < 2:
        st.error("❌ Need at least 2 valid papers.")
        st.stop()

    with st.status("🔢 Building RAG index...", expanded=True) as status:
        st.write("Chunking and embedding with MiniLM...")
        index = build_index(papers)
        st.write(f"✅ {index.total_chunks} chunks indexed")
        status.update(label="✅ RAG index ready", state="complete")

    with st.status("🧠 Summarizing papers...", expanded=True) as status:
        summaries = []
        p2        = st.progress(0)
        for i, paper in enumerate(papers):
            st.write(f"Analyzing: {paper['filename']}...")
            s = summarize_paper(index, paper["filename"])
            summaries.append(s)
            st.write(f"✅ {s.get('title', paper['filename'])[:55]}")
            p2.progress((i + 1) / len(papers))
        status.update(label=f"✅ Summarized {len(summaries)} papers", state="complete")

    with st.status("🔍 Detecting research gaps...", expanded=True) as status:
        st.write("Analyzing cross-paper patterns...")
        gaps   = detect_gaps(summaries, index)
        n_gaps = len(gaps.get("research_gaps", []))
        n_ideas= len(gaps.get("suggested_ideas", []))
        if gaps["status"] == "ok":
            status.update(label=f"✅ Found {n_gaps} gaps, {n_ideas} ideas", state="complete")
        else:
            st.warning(gaps.get("error", ""))
            status.update(label="⚠️ Done with warnings", state="complete")

    st.session_state["summaries"] = summaries
    st.session_state["gaps"]      = gaps
    st.rerun()

# ── Results ──
if "summaries" in st.session_state and "gaps" in st.session_state:
    summaries = st.session_state["summaries"]
    gaps      = st.session_state["gaps"]

    st.markdown("---")
    st.markdown("## 📊 Results")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Papers",      len(summaries))
    with c2: st.metric("Gaps Found",  len(gaps.get("research_gaps", [])))
    with c3: st.metric("Ideas",       len(gaps.get("suggested_ideas", [])))
    with c4:
        rg  = gaps.get("research_gaps", [])
        avg = sum(g.get("novelty_score", 0) for g in rg) / len(rg) if rg else 0
        st.metric("Avg Novelty", f"{avg:.1f}/10")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs([
        "📚 Paper Summaries",
        "🕳️ Research Gaps",
        "💡 Suggested Ideas"
    ])

    # Tab 1 — Summaries
    with tab1:
        st.markdown("### Paper Summaries")
        for i, s in enumerate(summaries, 1):
            title = s.get("title", s.get("filename", f"Paper {i}"))
            with st.expander(f"📄 {i}. {title}", expanded=(i == 1)):
                ca, cb = st.columns(2)
                with ca:
                    st.markdown(f"**Problem:** {s.get('problem', '—')}")
                    st.markdown(f"**Method:** {s.get('method', '—')}")
                    st.markdown(f"**Dataset:** {s.get('dataset', '—')}")
                with cb:
                    st.markdown(f"**Result:** {s.get('main_result', '—')}")
                    st.markdown(f"**Authors:** {s.get('authors', '—')} ({s.get('year', '—')})")
                lims = s.get("limitations", [])
                if lims:
                    st.markdown("**Limitations:**")
                    lims_list = lims if isinstance(lims, list) else [str(lims)]
                    for lim in lims_list:
                        st.markdown(f"  - {lim}")

    # Tab 2 — Research Gaps
    with tab2:
        st.markdown("### 🔴 Discovered Research Gaps")
        if gaps.get("overall_summary"):
            st.info(f"**Overview:** {gaps['overall_summary']}")

        ca, cb, cc = st.columns(3)
        with ca:
            st.markdown("**Common Methods**")
            for m in gaps.get("common_methods", []):
                st.markdown(f"- {m}")
        with cb:
            st.markdown("**Common Datasets**")
            for d in gaps.get("common_datasets", []):
                st.markdown(f"- {d}")
        with cc:
            st.markdown("**Common Limitations**")
            for lim in gaps.get("common_limitations", []):
                st.markdown(f"- {lim}")

        st.markdown("---")
        rg_sorted = sorted(
            gaps.get("research_gaps", []),
            key=lambda x: x.get("novelty_score", 0),
            reverse=True
        )
        for i, gap in enumerate(rg_sorted, 1):
            score = gap.get("novelty_score", 0)
            sc    = "score-high" if score >= 8 else ("score-medium" if score >= 6 else "score-low")
            st.markdown(f"""
            <div class="gap-card">
                <div style="display:flex; justify-content:space-between; align-items:center">
                    <b>Gap #{i}</b><span class="{sc}">Novelty: {score}/10</span>
                </div>
                <p style="margin:0.5rem 0 0">{gap.get('gap', '—')}</p>
                <p style="font-size:0.85em; color:#555; margin:0.3rem 0 0">📎 {gap.get('evidence', '—')}</p>
            </div>""", unsafe_allow_html=True)

        if rg_sorted:
            score_df = [{"Gap": f"Gap #{i+1}", "Novelty Score": g.get("novelty_score", 0)}
                        for i, g in enumerate(rg_sorted)]
            import pandas as pd
            fig = px.bar(
                pd.DataFrame(score_df), x="Gap", y="Novelty Score",
                title="Novelty Score Comparison",
                color="Novelty Score",
                color_continuous_scale=[[0, "#FAEEDA"], [0.5, "#185FA5"], [1, "#0F6E56"]],
                range_y=[0, 10]
            )
            fig.add_hline(y=7, line_dash="dash", line_color="#854F0B",
                          annotation_text="Important threshold (7+)")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Tab 3 — Ideas
    with tab3:
        st.markdown("### 💡 Suggested Research Ideas")
        ideas = gaps.get("suggested_ideas", [])
        if not ideas:
            st.warning("No ideas generated.")
        for i, idea in enumerate(ideas, 1):
            feas = idea.get("feasibility", "—")
            fc   = "#0F6E56" if "High" in feas else ("#185FA5" if "Medium" in feas else "#854F0B")
            st.markdown(f"""
            <div class="idea-card">
                <b>💡 Idea #{i}: {idea.get('idea', '—')}</b><br><br>
                <span>📌 Addresses: {idea.get('addresses_gap', '—')}</span><br>
                <span style="color:{fc}; font-weight:bold">⚡ Feasibility: {feas}</span><br>
                <span style="color:#555">🌟 {idea.get('why_promising', '—')}</span>
            </div>""", unsafe_allow_html=True)

    # ── Download ──
    st.markdown("---")
    st.markdown("### 📥 Download Report")
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.spinner("Generating PDF..."):
            try:
                pdf = generate_report(summaries, gaps)
                st.download_button(
                    "⬇️ Download PDF Report", pdf,
                    "research_gap_report.pdf", "application/pdf",
                    use_container_width=True, type="primary"
                )
            except Exception as e:
                st.error(f"PDF error: {e}")

        st.download_button(
            "⬇️ Download JSON",
            json.dumps({"summaries": summaries, "gaps": gaps}, ensure_ascii=False, indent=2),
            "data.json", "application/json",
            use_container_width=True
        )

    st.markdown("---")
    if st.button("🔄 New Analysis", use_container_width=True):
        for k in ["summaries", "gaps"]:
            st.session_state.pop(k, None)
        st.rerun()
