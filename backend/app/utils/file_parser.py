"""
Lightweight text extraction for uploaded complaint sources.
Not production-grade OCR (per assignment scope) — just enough to get real
text out of a PDF/email/txt so the LangGraph pipeline has something to work with.
"""
import io
from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()


def extract_text_from_eml_or_txt(file_bytes: bytes) -> str:
    # .eml files are mostly readable as plain text for header/body content;
    # for a fresher-level assignment we don't need full MIME parsing.
    try:
        return file_bytes.decode("utf-8", errors="ignore").strip()
    except Exception:
        return file_bytes.decode("latin-1", errors="ignore").strip()


def extract_text(filename: str, file_bytes: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if lower.endswith((".eml", ".txt", ".msg")):
        return extract_text_from_eml_or_txt(file_bytes)
    # images: OCR intentionally out of scope — return placeholder so the
    # pipeline still runs end-to-end in the demo.
    if lower.endswith((".png", ".jpg", ".jpeg")):
        return "[Image attachment received — OCR not implemented in this demo. " \
               "Please describe the image content in the complaint notes field.]"
    return extract_text_from_eml_or_txt(file_bytes)
