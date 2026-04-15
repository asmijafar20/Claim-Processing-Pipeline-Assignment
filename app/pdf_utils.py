from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

from pypdf import PdfReader, PdfWriter

from app.config import settings

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency
    Image = None


@dataclass
class PDFPage:
    page_number: int
    text: str
    text_source: str = "embedded"


def _ocr_image_bytes(image_bytes: bytes) -> str:
    if not settings.enable_ocr or pytesseract is None or Image is None:
        return ""

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return pytesseract.image_to_string(image).strip()
    except Exception:  # pragma: no cover - best effort OCR fallback
        return ""


def _extract_page_ocr_text(page: Any) -> str:
    images = getattr(page, "images", None)
    if not images:
        return ""

    ocr_chunks: list[str] = []
    for image_file in images:
        image_bytes = getattr(image_file, "data", b"")
        if not image_bytes:
            continue
        text = _ocr_image_bytes(image_bytes)
        if text:
            ocr_chunks.append(text)

    return "\n".join(ocr_chunks).strip()


def load_pdf_pages(file_bytes: bytes) -> list[PDFPage]:
    reader = PdfReader(BytesIO(file_bytes))
    if reader.is_encrypted:
        if not reader.decrypt(settings.pdf_password):
            raise ValueError(
                "The PDF is encrypted and could not be opened with the configured password."
            )

    pages: list[PDFPage] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        text_source = "embedded"
        if not text:
            ocr_text = _extract_page_ocr_text(page)
            if ocr_text:
                text = ocr_text
                text_source = "ocr"
            else:
                text_source = "missing"
        pages.append(PDFPage(page_number=index, text=text, text_source=text_source))
    return pages


def extract_selected_pages(file_bytes: bytes, page_numbers: list[int]) -> bytes:
    if not page_numbers:
        return b""

    reader = PdfReader(BytesIO(file_bytes))
    if reader.is_encrypted:
        if not reader.decrypt(settings.pdf_password):
            raise ValueError(
                "The PDF is encrypted and could not be opened with the configured password."
            )

    writer = PdfWriter()
    for page_number in sorted(set(page_numbers)):
        writer.add_page(reader.pages[page_number - 1])

    output = BytesIO()
    writer.write(output)
    return output.getvalue()
