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
    """Cut each page into overlapping chunks that keep their page number.

    pages: [(page_number, text), ...] as returned by extract_pages.
    Returns [{"text": ..., "page": ...}, ...] in page order.

    - Whitespace is collapsed to single spaces so chunks are clean text.
    - A chunk never mixes pages, so its page number is always exact.
    - Chunks are at most `size` characters; consecutive chunks of a page share
      exactly `overlap` characters, so a sentence cut at a border stays whole
      in one of them.
    - Pages with no text are skipped.
    """
    if size <= 0:
        raise ValueError(f"chunk size must be positive, got {size}")
    if overlap < 0:
        raise ValueError(f"overlap cannot be negative, got {overlap}")
    if overlap >= size:
        raise ValueError(f"overlap ({overlap}) must be smaller than chunk size ({size})")

    step = size - overlap
    chunks = []
    for page, raw in pages:
        text = " ".join(raw.split())
        if not text:
            continue
        start = 0
        while True:
            chunks.append({"text": text[start:start + size], "page": page})
            if start + size >= len(text):
                break
            start += step
    return chunks


def ingest(pdf_path, config):
    """Extract, chunk and embed; return chunk records for the store."""
    raise NotImplementedError


if __name__ == "__main__":
    # Debug helper: python -m src.ingestion some.pdf [--chunks]
    args = [a for a in sys.argv[1:] if a != "--chunks"]
    if len(args) != 1:
        sys.exit("usage: python -m src.ingestion <file.pdf> [--chunks]")
    try:
        pages = extract_pages(args[0])
        if "--chunks" in sys.argv:
            import json
            config = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text())
            size, overlap = config["chunk_size"], config["chunk_overlap"]
            chunks = chunk_pages(pages, size, overlap)
            print(f"{len(chunks)} chunks (size {size}, overlap {overlap})")
            for chunk in chunks[:6]:
                print(f"page {chunk['page']:>3}, {len(chunk['text']):>4} chars | {chunk['text'][:60]}")
        else:
            for number, text in pages:
                preview = " ".join(text.split())[:70]
                print(f"page {number:>3}: {len(text):>5} chars | {preview}")
    except IngestionError as e:
        sys.exit(f"Error: {e}")
