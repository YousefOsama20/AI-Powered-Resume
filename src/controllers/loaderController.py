from pathlib import Path

from pypdf import PdfReader
from docx import Document


def load_pdf(file_path: str) -> list[dict]:
    """Load a PDF page by page while preserving page numbers."""

    path = Path(file_path)

    reader = PdfReader(file_path)

    documents = []

    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text()

        if not text:
            continue

        documents.append({
            "text": text.strip(),
            "metadata": {
                "file_name": path.name,
                "file_type": "pdf",
                "page": page_number,
            }
        })

    return documents


def load_docx(file_path: str) -> list[dict]:
    """Load a DOCX file while preserving source metadata."""

    path = Path(file_path)

    document = Document(file_path)

    paragraphs = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    text = "\n\n".join(paragraphs)

    if not text:
        return []

    return [{
        "text": text,
        "metadata": {
            "file_name": path.name,
            "file_type": "docx",
        }
    }]