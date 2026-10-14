"""PDF path -> chunk records {id, text, page, vector}."""
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

MIN_TEXT_CHARS = 50  # below this in the whole PDF, we assume it is scanned


class IngestionError(Exception):
    """The PDF cannot be ingested. The message says why and is safe to print."""


class NoTextError(IngestionError):
    """The PDF has no extractable text (probably scanned images)."""


def extract_pages(pdf_path, min_chars=MIN_TEXT_CHARS):
    """Return a list of (page_number, text), one entry per PDF page (numbers start at 1).

    Pages without text are kept with an empty string so page numbers stay correct.
    Raise IngestionError for a missing or invalid file, NoTextError for a scanned PDF.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise IngestionError(f"PDF not found: {path}")
    try:
        with path.open("rb") as f:
            header = f.read(5)
    except OSError as e:
        raise IngestionError(f"Cannot read {path}: {e}")
    if header != b"%PDF-":
        raise IngestionError(f"{path} is not a PDF file.")

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(""):
            raise IngestionError(f"{path} is password protected.")
        pages = [(number, (page.extract_text() or "").strip())
                 for number, page in enumerate(reader.pages, start=1)]
    except IngestionError:
        raise
    except (PyPdfError, ValueError, OSError) as e:
        raise IngestionError(f"Cannot read {path} as a PDF: {e}")

    if sum(len(text) for _, text in pages) < min_chars:
        raise NoTextError(
            f"{path} has no extractable text (probably scanned images). "
            "Only text PDFs are supported."
        )
    return pages


def chunk_pages(pages, size, overlap):
    """Cut each page into overlapping chunks that keep their page number."""
    raise NotImplementedError


def ingest(pdf_path, config):
    """Extract, chunk and embed; return chunk records for the store."""
    raise NotImplementedError


if __name__ == "__main__":
    # Debug helper: python -m src.ingestion some.pdf
    if len(sys.argv) != 2:
        sys.exit("usage: python -m src.ingestion <file.pdf>")
    try:
        for number, text in extract_pages(sys.argv[1]):
            preview = " ".join(text.split())[:70]
            print(f"page {number:>3}: {len(text):>5} chars | {preview}")
    except IngestionError as e:
        sys.exit(f"Error: {e}")
