import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdf_factory import make_blank_pdf, make_text_pdf  # noqa: E402
from src.ingestion import IngestionError, NoTextError, extract_pages  # noqa: E402

PAGES = [
    "Chapter one. Networks connect computers together so they can share data.",
    "Chapter two. The OSI model has seven layers from physical to application.",
    "Chapter three. TCP was specified in RFC 793 in the year 1981.",
]


@pytest.fixture
def text_pdf(tmp_path):
    path = tmp_path / "course.pdf"
    make_text_pdf(path, PAGES)
    return path


def test_page_count_matches_pdf(text_pdf):
    assert len(extract_pages(text_pdf)) == 3


def test_pages_are_numbered_from_one_in_order(text_pdf):
    assert [number for number, _ in extract_pages(text_pdf)] == [1, 2, 3]


def test_known_sentence_is_on_the_right_page(text_pdf):
    pages = dict(extract_pages(text_pdf))
    assert "RFC 793" in pages[3]
    assert "RFC 793" not in pages[1]
    assert "seven layers" in pages[2]


def test_blank_page_keeps_its_number(tmp_path):
    path = tmp_path / "gap.pdf"
    make_text_pdf(path, [PAGES[0], "", PAGES[2]])
    pages = extract_pages(path)
    assert [number for number, _ in pages] == [1, 2, 3]
    assert pages[1][1] == ""


def test_scanned_pdf_raises_no_text_error(tmp_path):
    path = tmp_path / "scan.pdf"
    make_blank_pdf(path)
    with pytest.raises(NoTextError, match="no extractable text"):
        extract_pages(path)


def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(IngestionError, match="not found"):
        extract_pages(tmp_path / "nope.pdf")


def test_non_pdf_file_gives_clear_error(tmp_path):
    path = tmp_path / "notes.pdf"
    path.write_text("this is plain text, not a pdf")
    with pytest.raises(IngestionError, match="not a PDF"):
        extract_pages(path)


def test_empty_file_gives_clear_error(tmp_path):
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")
    with pytest.raises(IngestionError, match="not a PDF"):
        extract_pages(path)


def test_truncated_pdf_gives_clear_error(tmp_path):
    path = tmp_path / "cut.pdf"
    path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog")
    with pytest.raises(IngestionError):
        extract_pages(path)


def test_real_pdf_page_count_matches():
    real = ROOT / "docs" / "subject" / "features_catalog.pdf"
    if not real.exists():
        pytest.skip("features_catalog.pdf not in the repo")
    assert len(extract_pages(real)) == len(PdfReader(str(real)).pages)
