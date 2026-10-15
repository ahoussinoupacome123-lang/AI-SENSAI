import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion import chunk_pages  # noqa: E402

TEXT = " ".join(f"word{i:03d}" for i in range(300))  # 2399 chars, no double spaces


def chunks_of(text, size=800, overlap=150, page=1):
    return chunk_pages([(page, text)], size, overlap)


def test_no_chunk_is_longer_than_size():
    assert all(len(c["text"]) <= 800 for c in chunks_of(TEXT))


def test_default_settings_give_expected_count():
    # 2000 chars, step 800-150=650: starts 0, 650, 1300 -> third chunk reaches the end
    assert len(chunks_of("x" * 2000)) == 3
    # 2399 chars: starts 0, 650, 1300, 1950 -> four chunks
    assert len(TEXT) == 2399 and len(chunks_of(TEXT)) == 4


def test_consecutive_chunks_overlap_by_exactly_overlap_chars():
    chunks = chunks_of(TEXT)
    for before, after in zip(chunks, chunks[1:]):
        assert before["text"][-150:] == after["text"][:150]


def test_chunks_together_rebuild_the_whole_page_text():
    chunks = chunks_of(TEXT)
    rebuilt = chunks[0]["text"] + "".join(c["text"][150:] for c in chunks[1:])
    assert rebuilt == TEXT


def test_every_chunk_has_the_right_page_number():
    pages = [(2, "a" * 1000), (5, "b" * 900)]
    for chunk in chunk_pages(pages, 400, 50):
        assert chunk["text"][0] == ("a" if chunk["page"] == 2 else "b")
        assert chunk["page"] in (2, 5)


def test_chunks_follow_page_order_and_never_mix_pages():
    chunks = chunk_pages([(1, "a" * 500), (2, "b" * 500)], 300, 50)
    assert [c["page"] for c in chunks] == sorted(c["page"] for c in chunks)
    assert all(set(c["text"]) <= {"a"} or set(c["text"]) <= {"b"} for c in chunks)


def test_short_page_gives_a_single_chunk():
    assert chunks_of("short text") == [{"text": "short text", "page": 1}]


def test_text_exactly_size_gives_a_single_chunk():
    assert len(chunks_of("x" * 800)) == 1


def test_text_one_char_over_size_gives_two_chunks():
    chunks = chunks_of("x" * 801)
    assert len(chunks) == 2
    assert len(chunks[1]["text"]) > 150  # never a tiny leftover inside the overlap


def test_empty_and_blank_pages_are_skipped_but_numbers_are_kept():
    chunks = chunk_pages([(1, "text one"), (2, ""), (3, "  \n \t "), (4, "text four")], 800, 150)
    assert [c["page"] for c in chunks] == [1, 4]


def test_whitespace_is_collapsed():
    assert chunks_of("a\n\nb   c\td")[0]["text"] == "a b c d"


def test_no_pages_gives_no_chunks():
    assert chunk_pages([], 800, 150) == []


@pytest.mark.parametrize("size, overlap", [(100, 100), (100, 150), (0, 0), (-5, 0), (100, -1)])
def test_invalid_settings_raise_value_error(size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([(1, "text")], size, overlap)


@pytest.mark.parametrize("size, overlap", [(50, 0), (50, 10), (123, 45), (800, 150), (10, 9)])
def test_invariants_hold_for_many_settings(size, overlap):
    chunks = chunk_pages([(1, TEXT)], size, overlap)
    assert all(len(c["text"]) <= size for c in chunks)
    rebuilt = chunks[0]["text"] + "".join(c["text"][overlap:] for c in chunks[1:])
    assert rebuilt == TEXT
