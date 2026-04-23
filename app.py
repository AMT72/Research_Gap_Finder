"""
المرحلة الخامسة: واجهة Streamlit الرئيسية
تشغيل: streamlit run app.py
"""

import os
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx

from pdf_reader import process_pdf
from analyzer import summarize_all_papers, detect_gaps, build_citation_relations
from report import generate_report

# ──────────────────────────────────────────────
# إعداد الصفحة
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Research Gap Finder",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS مخصص
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0C447C, #185FA5);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #E6F1FB;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .gap-card {
        background: #EAF3DE;
        border: 1px solid #C0DD97;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .idea-card {
        background: #EEEDFE;
        border: 1px solid #CECBF6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .score-high   { color: #0F6E56; font-weight: bold; font-size: 1.2em; }
    .score-medium { color: #185FA5; font-weight: bold; font-size: 1.2em; }
    .score-low    { color: #854F0B; font-weight: bold; font-size: 1.2em; }
    .stProgress > div > div { background-color: #185FA5; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ الإعدادات")
    
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="احصل على مفتاحك من console.anthropic.com"
    )
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    st.markdown("---")
    st.markdown("### كيفية الاستخدام")
    st.markdown("""
    1. أدخل الـ API Key
    2. ارفع 2-10 ملفات PDF
    3. اضغط **تحليل**
    4. شاهد النتائج وحمّل التقرير
    """)
    
    st.markdown("---")
    st.markdown("### عن المشروع")
    st.caption("Research Gap Finder يساعدك على اكتشاف الثغرات البحثية في أي مجال علمي باستخدام الذكاء الاصطناعي.")


# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size:1.8rem;">🔍 Research Gap Finder</h1>
    <p style="margin:0.3rem 0 0; opacity:0.85;">اكتشف الثغرات البحثية في الأوراق العلمية تلقائياً</p>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# رفع الملفات
# ──────────────────────────────────────────────
st.markdown("### 📂 ارفع الأوراق البحثية")
uploaded_files = st.file_uploader(
    "اختر 2-10 ملفات PDF",
    type=["pdf"],
    accept_multiple_files=True,
    help="كل ملف يمثل ورقة بحثية واحدة"
)

if uploaded_files:
    if len(uploaded_files) < 2:
        st.warning("⚠️ ارفع على الأقل ورقتين للمقارنة.")
    elif len(uploaded_files) > 10:
        st.warning("⚠️ الحد الأقصى 10 أوراق.")
    else:
        st.success(f"✅ تم رفع {len(uploaded_files)} ورقة بحثية")
        
        cols = st.columns(min(len(uploaded_files), 5))
        for i, f in enumerate(uploaded_files):
            with cols[i % 5]:
                st.caption(f"📄 {f.name[:25]}...")


# ──────────────────────────────────────────────
# زر التحليل
# ──────────────────────────────────────────────
st.markdown("---")
can_analyze = (
    uploaded_files and
    2 <= len(uploaded_files) <= 10 and
    bool(os.environ.get("ANTHROPIC_API_KEY", ""))
)

if not os.environ.get("ANTHROPIC_API_KEY", ""):
    st.info("💡 أدخل الـ API Key في الشريط الجانبي للبدء.")

analyze_btn = st.button(
    "🚀 ابدأ التحليل",
    type="primary",
    disabled=not can_analyze,
    use_container_width=True
)

# ──────────────────────────────────────────────
# منطق التحليل الرئيسي
# ──────────────────────────────────────────────
if analyze_btn:
    
    # ─── المرحلة 1: قراءة الـ PDFs ───
    with st.status("📖 قراءة الملفات...", expanded=True) as status:
        st.write("جاري استخراج النصوص من الـ PDFs...")
        papers = []
        progress = st.progress(0)
        
        for i, f in enumerate(uploaded_files):
            paper = process_pdf(f.read(), f.name)
            if paper["status"] == "too_short":
                st.warning(f"⚠️ {f.name}: النص قصير جداً، قد تكون الورقة محمية أو ممسوحة ضوئياً.")
            else:
                papers.append(paper)
                st.write(f"✅ {f.name} — {paper['cleaned_length']:,} حرف")
            progress.progress((i + 1) / len(uploaded_files))
        
        status.update(label=f"✅ تم قراءة {len(papers)} ورقة", state="complete")

    if len(papers) < 2:
        st.error("❌ لا يمكن المتابعة: أقل من ورقتين صالحتين.")
        st.stop()

    # ─── المرحلة 2: التلخيص ───
    with st.status("🧠 تلخيص الأوراق بـ Claude...", expanded=True) as status:
        summaries = []
        progress2 = st.progress(0)
        
        for i, paper in enumerate(papers):
            st.write(f"جاري تحليل: {paper['filename']}...")
            from analyzer import summarize_paper
            s = summarize_paper(paper["text"], paper["filename"])
            summaries.append(s)
            
            if s["status"] == "ok":
                st.write(f"✅ {s.get('title', paper['filename'])[:60]}")
            else:
                st.warning(f"⚠️ {paper['filename']}: {s.get('error', 'خطأ غير معروف')}")
            
            progress2.progress((i + 1) / len(papers))
        
        status.update(label=f"✅ تم تلخيص {len(summaries)} ورقة", state="complete")

    # ─── المرحلة 3: كشف الـ Gaps ───
    with st.status("🔍 كشف الثغرات البحثية...", expanded=True) as status:
        st.write("جاري تحليل الأنماط واكتشاف الثغرات...")
        gaps = detect_gaps(summaries)
        
        if gaps["status"] == "ok":
            n_gaps = len(gaps.get("research_gaps", []))
            n_ideas = len(gaps.get("suggested_ideas", []))
            status.update(label=f"✅ تم اكتشاف {n_gaps} ثغرة و{n_ideas} فكرة", state="complete")
        else:
            st.warning(f"تحذير في تحليل الثغرات: {gaps.get('error', '')}")
            status.update(label="⚠️ اكتمل مع تحذيرات", state="complete")

    # ─── المرحلة 4: Citation Graph ───
    with st.status("🌐 بناء Citation Graph...", expanded=False) as status:
        relations = build_citation_relations(summaries)
        status.update(label=f"✅ تم رسم {len(relations)} علاقة", state="complete")

    # حفظ في session state
    st.session_state["summaries"] = summaries
    st.session_state["gaps"] = gaps
    st.session_state["relations"] = relations
    st.rerun()


# ──────────────────────────────────────────────
# عرض النتائج
# ──────────────────────────────────────────────
if "summaries" in st.session_state and "gaps" in st.session_state:
    summaries = st.session_state["summaries"]
    gaps      = st.session_state["gaps"]
    relations = st.session_state.get("relations", [])

    st.markdown("---")
    st.markdown("## 📊 النتائج")

    # ── بطاقات الإحصاءات ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("عدد الأوراق", len(summaries))
    with c2:
        st.metric("ثغرات مكتشفة", len(gaps.get("research_gaps", [])))
    with c3:
        st.metric("أفكار مقترحة", len(gaps.get("suggested_ideas", [])))
    with c4:
        avg_score = 0
        rg = gaps.get("research_gaps", [])
        if rg:
            avg_score = sum(g.get("novelty_score", 0) for g in rg) / len(rg)
        st.metric("متوسط Novelty", f"{avg_score:.1f}/10")

    st.markdown("---")

    # ── Tabs ──
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📚 ملخصات الأوراق",
        "🔲 Comparison Matrix",
        "🕳️ Research Gaps",
        "💡 الأفكار المقترحة",
        "🌐 Citation Graph"
    ])

    # ─── Tab 1: ملخصات ───
    with tab1:
        st.markdown("### ملخصات الأوراق البحثية")
        for i, s in enumerate(summaries, 1):
            with st.expander(f"📄 {i}. {s.get('title', s.get('filename', f'ورقة {i}'))}", expanded=(i == 1)):
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"**المشكلة:** {s.get('problem', '—')}")
                    st.markdown(f"**الطريقة:** {s.get('method', '—')}")
                    st.markdown(f"**البيانات:** {s.get('dataset', '—')}")
                with cols[1]:
                    st.markdown(f"**النتيجة:** {s.get('main_result', '—')}")
                    st.markdown(f"**المؤلفون:** {s.get('authors', '—')} ({s.get('year', '—')})")
                
                if s.get('limitations'):
                    st.markdown("**القيود:**")
                    for lim in s['limitations']:
                        st.markdown(f"  - {lim}")
                
                if s.get('keywords'):
                    kw_html = " ".join([
                        f'<span style="background:#E6F1FB;color:#0C447C;padding:2px 8px;border-radius:12px;font-size:0.85em;margin:2px">{k}</span>'
                        for k in s['keywords']
                    ])
                    st.markdown(kw_html, unsafe_allow_html=True)

    # ─── Tab 2: Comparison Matrix ───
    with tab2:
        st.markdown("### Comparison Matrix")
        matrix_data = []
        for i, s in enumerate(summaries, 1):
            matrix_data.append({
                "#": i,
                "الورقة": s.get('title', s.get('filename', f'ورقة {i}'))[:50],
                "الطريقة": s.get('method', '—'),
                "البيانات": s.get('dataset', '—'),
                "النتيجة": s.get('main_result', '—'),
                "القيود": " | ".join(s.get('limitations', []))[:80],
            })
        
        df = pd.DataFrame(matrix_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Keyword frequency chart
        all_keywords = []
        for s in summaries:
            all_keywords.extend(s.get('keywords', []))
        
        if all_keywords:
            from collections import Counter
            kw_counts = Counter(all_keywords).most_common(10)
            kw_df = pd.DataFrame(kw_counts, columns=["الكلمة", "التكرار"])
            fig = px.bar(
                kw_df, x="التكرار", y="الكلمة",
                orientation='h',
                title="أكثر الكلمات المفتاحية تكراراً",
                color="التكرار",
                color_continuous_scale="Blues"
            )
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

    # ─── Tab 3: Research Gaps ───
    with tab3:
        st.markdown("### 🔴 الثغرات البحثية المكتشفة")
        
        if gaps.get("overall_summary"):
            st.info(f"**الملخص العام:** {gaps['overall_summary']}")

        # Patterns
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("**الطرق الشائعة**")
            for m in gaps.get("common_methods", []):
                st.markdown(f"- {m}")
        with col_b:
            st.markdown("**البيانات الشائعة**")
            for d in gaps.get("common_datasets", []):
                st.markdown(f"- {d}")
        with col_c:
            st.markdown("**القيود الشائعة**")
            for l in gaps.get("common_limitations", []):
                st.markdown(f"- {l}")

        st.markdown("---")
        
        research_gaps = gaps.get("research_gaps", [])
        if research_gaps:
            # ترتيب حسب الـ Novelty Score
            research_gaps_sorted = sorted(research_gaps, key=lambda x: x.get("novelty_score", 0), reverse=True)
            
            for i, gap in enumerate(research_gaps_sorted, 1):
                score = gap.get("novelty_score", 0)
                score_class = "score-high" if score >= 8 else ("score-medium" if score >= 6 else "score-low")
                
                with st.container():
                    st.markdown(f"""
                    <div class="gap-card">
                        <div style="display:flex; justify-content:space-between; align-items:center">
                            <b>ثغرة #{i}</b>
                            <span class="{score_class}">Novelty: {score}/10</span>
                        </div>
                        <p style="margin:0.5rem 0 0">{gap.get('gap', '—')}</p>
                        <p style="font-size:0.85em; color:#666; margin:0.3rem 0 0">📎 {gap.get('evidence', '—')}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # رسم بياني للـ Novelty Scores
            scores_df = pd.DataFrame([
                {"الثغرة": f"ثغرة #{i+1}", "Novelty Score": g.get("novelty_score", 0)}
                for i, g in enumerate(research_gaps_sorted)
            ])
            fig2 = px.bar(
                scores_df, x="الثغرة", y="Novelty Score",
                title="مقارنة Novelty Score للثغرات",
                color="Novelty Score",
                color_continuous_scale=[[0,"#FAEEDA"],[0.5,"#185FA5"],[1,"#0F6E56"]],
                range_y=[0, 10]
            )
            fig2.add_hline(y=7, line_dash="dash", line_color="#854F0B",
                           annotation_text="حد الثغرة المهمة (7+)")
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("لم يتم اكتشاف ثغرات بحثية.")

    # ─── Tab 4: أفكار مقترحة ───
    with tab4:
        st.markdown("### 💡 الأفكار البحثية المقترحة")
        
        for i, idea in enumerate(gaps.get("suggested_ideas", []), 1):
            feasibility = idea.get("feasibility", "—")
            f_color = "#0F6E56" if "عالية" in feasibility else ("#185FA5" if "متوسطة" in feasibility else "#854F0B")
            
            st.markdown(f"""
            <div class="idea-card">
                <b>💡 فكرة #{i}: {idea.get('idea', '—')}</b>
                <br><br>
                <span>📌 تعالج ثغرة: {idea.get('addresses_gap', '—')}</span><br>
                <span style="color:{f_color}; font-weight:bold">⚡ الجدوى: {feasibility}</span><br>
                <span style="color:#555">🌟 {idea.get('why_promising', '—')}</span>
            </div>
            """, unsafe_allow_html=True)

        if not gaps.get("suggested_ideas"):
            st.warning("لم يتم توليد أفكار.")

    # ─── Tab 5: Citation Graph ───
    with tab5:
        st.markdown("### 🌐 شبكة العلاقات بين الأوراق")
        
        if relations:
            # بناء الـ Graph
            G = nx.DiGraph()
            
            paper_labels = {
                str(i): s.get('title', s.get('filename', f'ورقة {i}'))[:25]
                for i, s in enumerate(summaries, 1)
            }
            
            for r in relations:
                src = str(r.get('from', '')).strip()
                tgt = str(r.get('to', '')).strip()
                rtype = r.get('type', 'related')
                if src and tgt and src != tgt:
                    G.add_edge(src, tgt, type=rtype)

            if G.number_of_nodes() > 0:
                pos = nx.spring_layout(G, seed=42, k=2)
                
                edge_x, edge_y = [], []
                for e in G.edges():
                    x0, y0 = pos[e[0]]
                    x1, y1 = pos[e[1]]
                    edge_x += [x0, x1, None]
                    edge_y += [y0, y1, None]

                node_x = [pos[n][0] for n in G.nodes()]
                node_y = [pos[n][1] for n in G.nodes()]
                node_labels = [paper_labels.get(n, n) for n in G.nodes()]

                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=edge_x, y=edge_y, mode='lines',
                    line=dict(width=1.5, color='#B5D4F4'),
                    hoverinfo='none'
                ))
                fig3.add_trace(go.Scatter(
                    x=node_x, y=node_y, mode='markers+text',
                    marker=dict(size=30, color='#185FA5', line=dict(width=2, color='white')),
                    text=node_labels,
                    textposition="top center",
                    textfont=dict(size=10),
                    hoverinfo='text'
                ))
                fig3.update_layout(
                    showlegend=False,
                    height=450,
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig3, use_container_width=True)

                # جدول العلاقات
                if relations:
                    st.markdown("**تفاصيل العلاقات:**")
                    rel_df = pd.DataFrame(relations)
                    st.dataframe(rel_df, use_container_width=True, hide_index=True)
            else:
                st.info("لم يتم إنشاء علاقات كافية لرسم الشبكة.")
        else:
            st.info("لم يتم اكتشاف علاقات بين الأوراق.")

    # ──────────────────────────────────────────────
    # تحميل التقرير
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 تحميل التقرير الكامل")
    
    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
    with col_dl2:
        with st.spinner("جاري إنشاء التقرير PDF..."):
            try:
                pdf_bytes = generate_report(summaries, gaps)
                st.download_button(
                    label="⬇️ تحميل التقرير PDF",
                    data=pdf_bytes,
                    file_name="research_gap_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
            except Exception as e:
                st.error(f"خطأ في إنشاء التقرير: {e}")

        # تحميل JSON
        json_data = json.dumps({
            "summaries": summaries,
            "gaps": gaps,
            "relations": relations
        }, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="⬇️ تحميل البيانات JSON",
            data=json_data,
            file_name="research_gap_data.json",
            mime="application/json",
            use_container_width=True
        )

    # زر إعادة التحليل
    st.markdown("---")
    if st.button("🔄 تحليل جديد", use_container_width=True):
        for key in ["summaries", "gaps", "relations"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
