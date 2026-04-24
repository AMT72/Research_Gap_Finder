"""
Main Streamlit application — fully local, no API key required.
Run with: streamlit run app.py
"""

import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx

from pdf_reader import process_pdf
from rag_pipeline import PaperIndex
from analyzer import (
    check_ollama, build_index,
    summarize_paper, detect_gaps, build_citation_relations,
    OLLAMA_MODEL
)
from report import generate_report

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Research Gap Finder",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0C447C, #185FA5);
        color: white; padding: 1.5rem 2rem;
        border-radius: 12px; margin-bottom: 1.5rem;
    }
    .status-ok   { background:#EAF3DE; border:1px solid #C0DD97; border-radius:8px; padding:0.6rem 1rem; }
    .status-err  { background:#FDE8E8; border:1px solid #F5ABAB; border-radius:8px; padding:0.6rem 1rem; }
    .gap-card    { background:#EAF3DE; border:1px solid #C0DD97; border-radius:8px; padding:1rem; margin:0.5rem 0; }
    .idea-card   { background:#EEEDFE; border:1px solid #CECBF6; border-radius:8px; padding:1rem; margin:0.5rem 0; }
    .score-high   { color:#0F6E56; font-weight:bold; font-size:1.2em; }
    .score-medium { color:#185FA5; font-weight:bold; font-size:1.2em; }
    .score-low    { color:#854F0B; font-weight:bold; font-size:1.2em; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Sidebar — model info + Ollama status
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")

    st.markdown(f"**Model:** `{OLLAMA_MODEL}`")
    st.caption("Running locally via Ollama — no API key needed.")

    if st.button("🔄 Check Ollama Status"):
        st.session_state["ollama_status"] = check_ollama()

    if "ollama_status" not in st.session_state:
        st.session_state["ollama_status"] = check_ollama()

    status = st.session_state["ollama_status"]
    if status["ok"]:
        st.markdown(f'<div class="status-ok">✅ Ollama is running<br><small>Model ready: {OLLAMA_MODEL}</small></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-err">❌ Ollama not detected<br><small>{status.get("error","")}</small></div>', unsafe_allow_html=True)
        st.markdown("""
        **To fix:**
        ```bash
        # Install Ollama
        curl -fsSL https://ollama.com/install.sh | sh

        # Pull the model
        ollama pull qwen2.5:14b

        # Start the server
        ollama serve
        ```
        """)

    st.markdown("---")
    st.markdown("### How to use")
    st.markdown("""
    1. Start Ollama (`ollama serve`)
    2. Upload 2–10 PDF papers
    3. Click **Start Analysis**
    4. View results & download report
    """)

    st.markdown("---")
    st.markdown("### Pipeline")
    st.caption("""
    📄 PDF → chunks  
    🔢 chunks → embeddings (MiniLM)  
    🗂️ FAISS index  
    🔍 RAG retrieval  
    🤖 Qwen2.5-14B analysis  
    📊 Gap report
    """)


# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size:1.8rem;">🔍 Research Gap Finder</h1>
    <p style="margin:0.3rem 0 0; opacity:0.85;">
        Powered by local LLM + RAG — fully private, no API key required
    </p>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# File upload
# ──────────────────────────────────────────────
st.markdown("### 📂 Upload Research Papers")
uploaded_files = st.file_uploader(
    "Select 2–10 PDF files",
    type=["pdf"],
    accept_multiple_files=True,
    help="Each file should be one research paper"
)

if uploaded_files:
    if len(uploaded_files) < 2:
        st.warning("⚠️ Please upload at least 2 papers to compare.")
    elif len(uploaded_files) > 10:
        st.warning("⚠️ Maximum 10 papers allowed.")
    else:
        st.success(f"✅ {len(uploaded_files)} papers ready")
        cols = st.columns(min(len(uploaded_files), 5))
        for i, f in enumerate(uploaded_files):
            with cols[i % 5]:
                st.caption(f"📄 {f.name[:22]}...")


# ──────────────────────────────────────────────
# Analyze button
# ──────────────────────────────────────────────
st.markdown("---")

ollama_ok   = st.session_state.get("ollama_status", {}).get("ok", False)
files_ok    = bool(uploaded_files) and 2 <= len(uploaded_files) <= 10
can_analyze = ollama_ok and files_ok

if not ollama_ok:
    st.warning("⚠️ Ollama is not running. Start it with `ollama serve` then click **Check Ollama Status** in the sidebar.")

analyze_btn = st.button(
    "🚀 Start Analysis",
    type="primary",
    disabled=not can_analyze,
    use_container_width=True
)


# ──────────────────────────────────────────────
# Main analysis pipeline
# ──────────────────────────────────────────────
if analyze_btn:

    # ── Phase 1: Read & clean PDFs ──
    with st.status("📖 Reading PDFs...", expanded=True) as status:
        papers = []
        progress = st.progress(0)
        for i, f in enumerate(uploaded_files):
            paper = process_pdf(f.read(), f.name)
            if paper["status"] == "too_short":
                st.warning(f"⚠️ {f.name}: File too short or scanned image — skipped.")
            else:
                papers.append(paper)
                st.write(f"✅ {f.name} — {paper['cleaned_length']:,} chars extracted")
            progress.progress((i + 1) / len(uploaded_files))
        status.update(label=f"✅ Loaded {len(papers)} papers", state="complete")

    if len(papers) < 2:
        st.error("❌ Need at least 2 valid papers to continue.")
        st.stop()

    # ── Phase 2: Build RAG index ──
    with st.status("🔢 Building RAG index...", expanded=True) as status:
        st.write("Chunking papers and computing embeddings...")
        index: PaperIndex = build_index(papers)
        st.write(f"✅ Indexed {index.total_chunks} chunks from {len(index.papers)} papers")
        status.update(label=f"✅ RAG index ready ({index.total_chunks} chunks)", state="complete")

    # ── Phase 3: Summarize each paper ──
    with st.status("🧠 Summarizing papers with local LLM...", expanded=True) as status:
        summaries = []
        progress2 = st.progress(0)
        for i, paper in enumerate(papers):
            st.write(f"Analyzing: {paper['filename']}...")
            s = summarize_paper(index, paper["filename"])
            summaries.append(s)
            label = s.get("title", paper["filename"])[:55]
            if s["status"] == "ok":
                st.write(f"✅ {label}")
            else:
                st.warning(f"⚠️ {paper['filename']}: {s.get('error','Unknown error')}")
            progress2.progress((i + 1) / len(papers))
        status.update(label=f"✅ Summarized {len(summaries)} papers", state="complete")

    # ── Phase 4: Detect gaps ──
    with st.status("🔍 Detecting research gaps (RAG + LLM)...", expanded=True) as status:
        st.write("Retrieving cross-paper context and analyzing gaps...")
        gaps = detect_gaps(summaries, index)
        n_gaps  = len(gaps.get("research_gaps", []))
        n_ideas = len(gaps.get("suggested_ideas", []))
        if gaps["status"] == "ok":
            status.update(label=f"✅ Found {n_gaps} gaps, {n_ideas} ideas", state="complete")
        else:
            st.warning(f"Gap detection warning: {gaps.get('error','')}")
            status.update(label="⚠️ Completed with warnings", state="complete")

    # ── Phase 5: Citation graph ──
    with st.status("🌐 Building citation graph...", expanded=False) as status:
        relations = build_citation_relations(summaries)
        status.update(label=f"✅ Mapped {len(relations)} relations", state="complete")

    st.session_state["summaries"] = summaries
    st.session_state["gaps"]      = gaps
    st.session_state["relations"] = relations
    st.rerun()


# ──────────────────────────────────────────────
# Results display
# ──────────────────────────────────────────────
if "summaries" in st.session_state and "gaps" in st.session_state:
    summaries = st.session_state["summaries"]
    gaps      = st.session_state["gaps"]
    relations = st.session_state.get("relations", [])

    st.markdown("---")
    st.markdown("## 📊 Results")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Papers Analyzed", len(summaries))
    with c2: st.metric("Gaps Found",      len(gaps.get("research_gaps", [])))
    with c3: st.metric("Ideas Generated", len(gaps.get("suggested_ideas", [])))
    with c4:
        rg = gaps.get("research_gaps", [])
        avg = sum(g.get("novelty_score", 0) for g in rg) / len(rg) if rg else 0
        st.metric("Avg Novelty Score", f"{avg:.1f}/10")

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📚 Paper Summaries",
        "🔲 Comparison Matrix",
        "🕳️ Research Gaps",
        "💡 Suggested Ideas",
        "🌐 Citation Graph"
    ])

    # ── Tab 1: Summaries ──
    with tab1:
        st.markdown("### Paper Summaries")
        for i, s in enumerate(summaries, 1):
            title = s.get('title', s.get('filename', f'Paper {i}'))
            with st.expander(f"📄 {i}. {title}", expanded=(i == 1)):
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"**Problem:** {s.get('problem','—')}")
                    st.markdown(f"**Method:** {s.get('method','—')}")
                    st.markdown(f"**Dataset:** {s.get('dataset','—')}")
                with cols[1]:
                    st.markdown(f"**Result:** {s.get('main_result','—')}")
                    st.markdown(f"**Authors:** {s.get('authors','—')} ({s.get('year','—')})")
                if s.get('limitations'):
                    st.markdown("**Limitations:**")
                    for lim in s['limitations']:
                        st.markdown(f"  - {lim}")
                if s.get('keywords'):
                    kw = " ".join([
                        f'<span style="background:#E6F1FB;color:#0C447C;padding:2px 8px;border-radius:12px;font-size:0.85em;margin:2px">{k}</span>'
                        for k in s['keywords']
                    ])
                    st.markdown(kw, unsafe_allow_html=True)

    # ── Tab 2: Comparison Matrix ──
    with tab2:
        st.markdown("### Comparison Matrix")
        rows = []
        for i, s in enumerate(summaries, 1):
            rows.append({
                "#": i,
                "Paper":       s.get('title', s.get('filename', f'Paper {i}'))[:50],
                "Method":      s.get('method', '—'),
                "Dataset":     s.get('dataset', '—'),
                "Result":      s.get('main_result', '—'),
                "Limitations": " | ".join(s.get('limitations', []))[:80],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        all_kw = []
        for s in summaries:
            all_kw.extend(s.get('keywords', []))
        if all_kw:
            from collections import Counter
            kw_df = pd.DataFrame(Counter(all_kw).most_common(10), columns=["Keyword", "Count"])
            fig = px.bar(kw_df, x="Count", y="Keyword", orientation='h',
                         title="Most Frequent Keywords",
                         color="Count", color_continuous_scale="Blues")
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

    # ── Tab 3: Gaps ──
    with tab3:
        st.markdown("### 🔴 Discovered Research Gaps")
        if gaps.get("overall_summary"):
            st.info(f"**Overview:** {gaps['overall_summary']}")

        ca, cb, cc = st.columns(3)
        with ca:
            st.markdown("**Common Methods**")
            for m in gaps.get("common_methods", []): st.markdown(f"- {m}")
        with cb:
            st.markdown("**Common Datasets**")
            for d in gaps.get("common_datasets", []): st.markdown(f"- {d}")
        with cc:
            st.markdown("**Common Limitations**")
            for l in gaps.get("common_limitations", []): st.markdown(f"- {l}")

        st.markdown("---")
        rg_sorted = sorted(gaps.get("research_gaps", []),
                           key=lambda x: x.get("novelty_score", 0), reverse=True)

        for i, gap in enumerate(rg_sorted, 1):
            score = gap.get("novelty_score", 0)
            sc = "score-high" if score >= 8 else ("score-medium" if score >= 6 else "score-low")
            st.markdown(f"""
            <div class="gap-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <b>Gap #{i}</b><span class="{sc}">Novelty: {score}/10</span>
                </div>
                <p style="margin:0.5rem 0 0">{gap.get('gap','—')}</p>
                <p style="font-size:0.85em;color:#555;margin:0.3rem 0 0">📎 {gap.get('evidence','—')}</p>
            </div>""", unsafe_allow_html=True)

        if rg_sorted:
            score_df = pd.DataFrame([
                {"Gap": f"Gap #{i+1}", "Novelty Score": g.get("novelty_score", 0)}
                for i, g in enumerate(rg_sorted)
            ])
            fig2 = px.bar(score_df, x="Gap", y="Novelty Score",
                          title="Novelty Score Comparison",
                          color="Novelty Score",
                          color_continuous_scale=[[0,"#FAEEDA"],[0.5,"#185FA5"],[1,"#0F6E56"]],
                          range_y=[0, 10])
            fig2.add_hline(y=7, line_dash="dash", line_color="#854F0B",
                           annotation_text="Important gap threshold (7+)")
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

    # ── Tab 4: Ideas ──
    with tab4:
        st.markdown("### 💡 Suggested Research Ideas")
        for i, idea in enumerate(gaps.get("suggested_ideas", []), 1):
            feas = idea.get("feasibility", "—")
            fc   = "#0F6E56" if "High" in feas else ("#185FA5" if "Medium" in feas else "#854F0B")
            st.markdown(f"""
            <div class="idea-card">
                <b>💡 Idea #{i}: {idea.get('idea','—')}</b><br><br>
                <span>📌 Addresses gap: {idea.get('addresses_gap','—')}</span><br>
                <span style="color:{fc};font-weight:bold">⚡ Feasibility: {feas}</span><br>
                <span style="color:#555">🌟 {idea.get('why_promising','—')}</span>
            </div>""", unsafe_allow_html=True)
        if not gaps.get("suggested_ideas"):
            st.warning("No ideas generated.")

    # ── Tab 5: Citation Graph ──
    with tab5:
        st.markdown("### 🌐 Paper Relationship Network")
        if relations:
            G = nx.DiGraph()
            labels = {
                str(i): s.get('title', s.get('filename', f'Paper {i}'))[:25]
                for i, s in enumerate(summaries, 1)
            }
            for r in relations:
                src, tgt = str(r.get('from','')).strip(), str(r.get('to','')).strip()
                if src and tgt and src != tgt:
                    G.add_edge(src, tgt, type=r.get('type','related'))

            if G.number_of_nodes() > 0:
                pos = nx.spring_layout(G, seed=42, k=2)
                ex, ey = [], []
                for e in G.edges():
                    x0,y0 = pos[e[0]]; x1,y1 = pos[e[1]]
                    ex += [x0,x1,None]; ey += [y0,y1,None]

                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=ex, y=ey, mode='lines',
                    line=dict(width=1.5, color='#B5D4F4'), hoverinfo='none'))
                fig3.add_trace(go.Scatter(
                    x=[pos[n][0] for n in G.nodes()],
                    y=[pos[n][1] for n in G.nodes()],
                    mode='markers+text',
                    marker=dict(size=30, color='#185FA5', line=dict(width=2, color='white')),
                    text=[labels.get(n, n) for n in G.nodes()],
                    textposition="top center", textfont=dict(size=10), hoverinfo='text'
                ))
                fig3.update_layout(
                    showlegend=False, height=450,
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig3, use_container_width=True)
                st.markdown("**Relation details:**")
                st.dataframe(pd.DataFrame(relations), use_container_width=True, hide_index=True)
            else:
                st.info("Not enough nodes to draw the network.")
        else:
            st.info("No relations detected between papers.")

    # ──────────────────────────────────────────────
    # Download
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Download Report")
    _, col_dl, _ = st.columns([1, 2, 1])
    with col_dl:
        with st.spinner("Generating PDF report..."):
            try:
                pdf_bytes = generate_report(summaries, gaps)
                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=pdf_bytes,
                    file_name="research_gap_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
            except Exception as e:
                st.error(f"Error generating report: {e}")

        st.download_button(
            label="⬇️ Download JSON Data",
            data=json.dumps({"summaries": summaries, "gaps": gaps, "relations": relations},
                            ensure_ascii=False, indent=2),
            file_name="research_gap_data.json",
            mime="application/json",
            use_container_width=True
        )

    st.markdown("---")
    if st.button("🔄 New Analysis", use_container_width=True):
        for k in ["summaries", "gaps", "relations"]:
            st.session_state.pop(k, None)
        st.rerun()
