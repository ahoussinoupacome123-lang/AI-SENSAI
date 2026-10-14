"""PDF path -> chunk records {id, text, page, vector}."""


def extract_pages(pdf_path):
    """Return a list of (page_number, text). Raise a clear error if the PDF has no text."""
    raise NotImplementedError


def chunk_pages(pages, size, overlap):
    """Cut each page into overlapping chunks that keep their page number."""
    raise NotImplementedError


def ingest(pdf_path, config):
    """Extract, chunk and embed; return chunk records for the store."""
    raise NotImplementedError
