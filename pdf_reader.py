"""
المرحلة الأولى: قراءة وتنظيف ملفات PDF
"""

import re
import pdfplumber


def extract_text_from_pdf(file_path: str) -> str:
    """استخراج النص الكامل من ملف PDF"""
    full_text = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)

    return "\n\n".join(full_text)


def extract_text_from_bytes(file_bytes: bytes) -> str:
    """استخراج النص من bytes (للاستخدام مع Streamlit uploader)"""
    import io
    full_text = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)

    return "\n\n".join(full_text)


def clean_text(raw_text: str) -> str:
    """تنظيف النص من الضوضاء"""
    # إزالة أسطر فارغة متعددة
    text = re.sub(r'\n{3,}', '\n\n', raw_text)
    # إزالة مسافات زائدة
    text = re.sub(r' {2,}', ' ', text)
    # إزالة أرقام الصفحات المنفردة
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    # إزالة headers/footers المتكررة (أسطر قصيرة جداً)
    lines = text.split('\n')
    cleaned_lines = [l for l in lines if len(l.strip()) > 3 or l.strip() == '']
    return '\n'.join(cleaned_lines).strip()


def truncate_for_api(text: str, max_chars: int = 12000) -> str:
    """تقليص النص إذا كان طويلاً جداً للـ API"""
    if len(text) <= max_chars:
        return text
    # خذ أول 8000 حرف + آخر 4000 حرف (البداية والخاتمة أهم أجزاء الورقة)
    return text[:8000] + "\n\n[...نص محذوف للاختصار...]\n\n" + text[-4000:]


def process_pdf(file_input, filename: str = "paper") -> dict:
    """
    معالجة ملف PDF كامل وإرجاع بيانات نظيفة
    file_input: إما مسار str أو bytes
    """
    if isinstance(file_input, bytes):
        raw_text = extract_text_from_bytes(file_input)
    else:
        raw_text = extract_text_from_pdf(file_input)

    cleaned = clean_text(raw_text)
    truncated = truncate_for_api(cleaned)

    return {
        "filename": filename,
        "raw_length": len(raw_text),
        "cleaned_length": len(cleaned),
        "text": truncated,
        "status": "ok" if len(cleaned) > 200 else "too_short"
    }


if __name__ == "__main__":
    # اختبار سريع
    import sys
    if len(sys.argv) > 1:
        result = process_pdf(sys.argv[1], sys.argv[1])
        print(f"الملف: {result['filename']}")
        print(f"الطول الأصلي: {result['raw_length']} حرف")
        print(f"بعد التنظيف: {result['cleaned_length']} حرف")
        print(f"الحالة: {result['status']}")
        print("\nأول 500 حرف:")
        print(result['text'][:500])
