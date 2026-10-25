"""PDF export and page previews for the owner brief."""

from __future__ import annotations

import base64
import io


def render_pdf(html_text: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html_text).write_pdf()


def page_count(pdf: bytes) -> int:
    import pypdfium2 as pdfium

    return len(pdfium.PdfDocument(pdf))


def preview_pngs(pdf: bytes, scale: float = 1.6) -> list[str]:
    """Render each page of the real PDF to a PNG data URI, so the app shows the actual file."""
    import pypdfium2 as pdfium

    out = []
    doc = pdfium.PdfDocument(pdf)
    for page in doc:
        image = page.render(scale=scale).to_pil()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        out.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    return out
