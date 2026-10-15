"""Build tiny PDFs for tests, with no extra dependency."""
from pathlib import Path

from pypdf import PdfWriter


def _escape(line):
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_text_pdf(path, pages):
    """Write a PDF with one text page per string in `pages` (newlines make new lines)."""
    count = len(pages)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(count))
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {count} >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, text in enumerate(pages):
        body = " ".join(f"({_escape(line)}) Tj T*" for line in text.split("\n"))
        stream = f"BT /F1 12 Tf 72 720 Td 14 TL {body} ET"
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>"
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n").encode()
    Path(path).write_bytes(bytes(out))


def make_blank_pdf(path, page_count=3):
    """Write a PDF whose pages have no text at all (like a scan without OCR)."""
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)
