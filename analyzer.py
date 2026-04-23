"""
المرحلة الثانية والثالثة: التلخيص وكشف الـ Research Gaps باستخدام Claude API
"""

import json
import re
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"


# ──────────────────────────────────────────────
# المرحلة الثانية: تلخيص كل ورقة بحثية
# ──────────────────────────────────────────────

SUMMARY_PROMPT = """أنت محلل أبحاث علمي متخصص. حلّل هذه الورقة البحثية واستخرج المعلومات التالية بدقة.

أجب بـ JSON فقط بهذا الهيكل الدقيق، ولا تضف أي نص خارجه:

{{
  "title": "عنوان الورقة",
  "year": "سنة النشر أو unknown",
  "authors": "المؤلفون الرئيسيون",
  "problem": "المشكلة التي تحلها الورقة في جملة واحدة",
  "method": "الطريقة أو النموذج المستخدم",
  "dataset": "البيانات المستخدمة للتجربة",
  "main_result": "أهم نتيجة رقمية أو نوعية",
  "limitations": ["قيد 1", "قيد 2", "قيد 3"],
  "keywords": ["كلمة 1", "كلمة 2", "كلمة 3", "كلمة 4", "كلمة 5"]
}}

الورقة البحثية:
{paper_text}"""


def summarize_paper(paper_text: str, filename: str = "") -> dict:
    """تلخيص ورقة بحثية واحدة باستخدام Claude"""
    prompt = SUMMARY_PROMPT.format(paper_text=paper_text)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()

        # تنظيف الـ JSON إذا كان محاطاً بـ ```
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
            "problem": "تعذّر استخراج المعلومات",
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
            "problem": "خطأ في الاتصال بـ API",
            "method": "unknown",
            "dataset": "unknown",
            "main_result": "unknown",
            "limitations": [],
            "keywords": []
        }


def summarize_all_papers(papers: list[dict]) -> list[dict]:
    """تلخيص قائمة من الأوراق البحثية"""
    summaries = []
    for paper in papers:
        summary = summarize_paper(paper["text"], paper["filename"])
        summaries.append(summary)
    return summaries


# ──────────────────────────────────────────────
# المرحلة الثالثة: كشف الـ Research Gaps
# ──────────────────────────────────────────────

GAP_PROMPT = """أنت خبير في تحليل الأبحاث العلمية وتحديد الثغرات البحثية.

بناءً على ملخصات الأوراق التالية، قم بالتحليل الشامل واستخرج:

الأوراق البحثية:
{summaries_text}

أجب بـ JSON فقط بهذا الهيكل، ولا تضف أي نص خارجه:

{{
  "common_methods": ["الطريقة الأكثر استخداماً", "الثانية", "الثالثة"],
  "common_datasets": ["Dataset الأكثر استخداماً", "الثاني"],
  "common_limitations": ["القيد المشترك الأول", "الثاني", "الثالث"],
  "research_gaps": [
    {{
      "gap": "وصف الثغرة البحثية",
      "evidence": "الدليل من الأوراق على وجود هذه الثغرة",
      "novelty_score": 8.5
    }},
    {{
      "gap": "ثغرة ثانية",
      "evidence": "الدليل",
      "novelty_score": 7.0
    }},
    {{
      "gap": "ثغرة ثالثة",
      "evidence": "الدليل",
      "novelty_score": 6.5
    }}
  ],
  "suggested_ideas": [
    {{
      "idea": "فكرة بحثية مقترحة تعالج الثغرة",
      "addresses_gap": "الثغرة التي تعالجها",
      "feasibility": "عالية / متوسطة / منخفضة",
      "why_promising": "لماذا هذه الفكرة واعدة"
    }},
    {{
      "idea": "فكرة ثانية",
      "addresses_gap": "الثغرة التي تعالجها",
      "feasibility": "عالية",
      "why_promising": "السبب"
    }}
  ],
  "overall_summary": "ملخص عام للمجال وأبرز الاتجاهات في 2-3 جمل"
}}"""


def detect_gaps(summaries: list[dict]) -> dict:
    """كشف الثغرات البحثية من ملخصات الأوراق"""

    # تحويل الملخصات إلى نص منظم
    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += f"""
ورقة {i}: {s.get('title', s.get('filename', f'ورقة {i}'))}
- المشكلة: {s.get('problem', 'غير محدد')}
- الطريقة: {s.get('method', 'غير محدد')}
- البيانات: {s.get('dataset', 'غير محدد')}
- النتيجة: {s.get('main_result', 'غير محدد')}
- القيود: {', '.join(s.get('limitations', []))}
- الكلمات المفتاحية: {', '.join(s.get('keywords', []))}
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
            "overall_summary": "تعذّر تحليل البيانات"
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
            "overall_summary": "خطأ في الاتصال"
        }


# ──────────────────────────────────────────────
# Citation Graph: العلاقات بين الأوراق
# ──────────────────────────────────────────────

CITATION_PROMPT = """بناءً على ملخصات الأوراق التالية، حدد العلاقات المنطقية بينها.

{summaries_text}

أجب بـ JSON فقط:
{{
  "relations": [
    {{"from": "عنوان الورقة أو رقمها", "to": "عنوان الورقة أو رقمها", "type": "extends / compares / uses_same_dataset / contradicts"}},
    {{"from": "...", "to": "...", "type": "..."}}
  ]
}}

استخدم أرقام الأوراق (1، 2، 3...) كمعرفات."""


def build_citation_relations(summaries: list[dict]) -> list[dict]:
    """استخراج العلاقات بين الأوراق"""
    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += f"ورقة {i}: {s.get('title', f'ورقة {i}')} - الطريقة: {s.get('method', '')} - البيانات: {s.get('dataset', '')}\n"

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
    print("اختبار analyzer.py")
    test_text = """
    This paper presents a deep learning approach for car damage detection using CNNs.
    We use the CarDD dataset with 4000 images. Our model achieves 91% accuracy.
    However, the model struggles with low-light conditions and rare damage types.
    Keywords: damage detection, CNN, automotive, deep learning, insurance
    """
    result = summarize_paper(test_text, "test_paper.pdf")
    print(json.dumps(result, ensure_ascii=False, indent=2))
