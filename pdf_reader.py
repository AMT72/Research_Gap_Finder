"""
Phase 1: PDF reading and text extraction
"""

import re
import pdfplumber


def extract_text_from_pdf(file_path: str) -> str:
    """Extract full text from a PDF file path"""
    full_text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
    return "\n\n".join(full_text)


def extract_text_from_bytes(file_bytes: bytes) -> str:
    """Extract text from bytes (for use with Streamlit uploader)"""
    import io
    full_text = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
    return "\n\n".join(full_text)


def clean_text(raw_text: str) -> str:
    """Clean noise from extracted text"""
    text = re.sub(r'\n{3,}', '\n\n', raw_text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    lines = text.split('\n')
    cleaned_lines = [l for l in lines if len(l.strip()) > 3 or l.strip() == '']
    return '\n'.join(cleaned_lines).strip()


def truncate_for_api(text: str, max_chars: int = 12000) -> str:
    """Truncate text if too long for the API"""
    if len(text) <= max_chars:
        return text
    return text[:8000] + "\n\n[...content truncated...]\n\n" + text[-4000:]


def process_pdf(file_input, filename: str = "paper") -> dict:
    """
    Process a full PDF file and return cleaned data.
    file_input: either a str path or bytes
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
    import sys
    if len(sys.argv) > 1:
        result = process_pdf(sys.argv[1], sys.argv[1])
        print(f"File:           {result['filename']}")
        print(f"Raw length:     {result['raw_length']} chars")
        print(f"Cleaned length: {result['cleaned_length']} chars")
        print(f"Status:         {result['status']}")
        print("\nFirst 500 chars:")
        print(result['text'][:500])
