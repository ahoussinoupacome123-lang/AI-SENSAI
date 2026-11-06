import hashlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import writer  # noqa: E402
from src.writer import WriterError, sections, upsert_section  # noqa: E402


def checked(n, answer=None, **extra):
    data = {
        "question": f"Question number {n}?",
        "answer": answer or f"Answer {n}.",
        "page": n,
        "quote": f"exact quote {n}",
        "status": "supported",
        "verdict": "faithful",
        "reason": "matches the passage",
    }
    data.update(extra)
    return data


def digests(path):
    return {n: hashlib.sha256(block.encode()).hexdigest()
            for n, block in sections(path.read_text(encoding="utf-8")).items()}


@pytest.fixture
def out(tmp_path):
    return tmp_path / "answers.md"


def test_new_file_gets_a_header_and_the_first_section(out):
    upsert_section(out, 1, checked(1))
    text = out.read_text()
    assert text.startswith("# Answers\n")
    assert "## Q1. Question number 1?" in text
    assert "**Answer:** Answer 1." in text
    assert "**Page:** 1" in text
    assert "> exact quote 1" in text
    assert "**Quote check:** supported" in text
    assert "**Judge:** faithful - matches the passage" in text


def test_a_new_question_appends_a_new_section(out):
    upsert_section(out, 1, checked(1))
    upsert_section(out, 2, checked(2))
    assert list(sections(out.read_text())) == [1, 2]


def test_rerunning_question_2_changes_only_section_2(out):
    for n in (1, 2, 3):
        upsert_section(out, n, checked(n))
    before = digests(out)
    upsert_section(out, 2, checked(2, answer="A completely different answer."))
    after = digests(out)
    assert "completely different" in out.read_text()
    assert after[1] == before[1] and after[3] == before[3]
    assert after[2] != before[2]
    assert list(after) == [1, 2, 3]


def test_whole_file_is_identical_apart_from_the_replaced_section(out):
    for n in (1, 2, 3):
        upsert_section(out, n, checked(n))
    old = out.read_text()
    old_block = sections(old)[2]
    upsert_section(out, 2, checked(2, answer="New."))
    new = out.read_text()
    new_block = sections(new)[2]
    assert old.replace(old_block, "@@") == new.replace(new_block, "@@")


def test_rewriting_the_same_answer_changes_no_byte(out):
    for n in (1, 2):
        upsert_section(out, n, checked(n))
    before = out.read_bytes()
    upsert_section(out, 2, checked(2))
    assert out.read_bytes() == before


def test_sections_are_kept_in_numeric_order(out):
    upsert_section(out, 1, checked(1))
    upsert_section(out, 3, checked(3))
    upsert_section(out, 2, checked(2))
    assert list(sections(out.read_text())) == [1, 2, 3]


def test_index_beyond_existing_sections_appends_cleanly(out):
    upsert_section(out, 1, checked(1))
    upsert_section(out, 2, checked(2))
    upsert_section(out, 5, checked(5))
    text = out.read_text()
    assert list(sections(text)) == [1, 2, 5]
    assert "\n\n\n" not in text


def test_inserting_a_middle_section_leaves_the_others_identical(out):
    upsert_section(out, 1, checked(1))
    upsert_section(out, 3, checked(3))
    before = digests(out)
    upsert_section(out, 2, checked(2))
    after = digests(out)
    assert after[1] == before[1] and after[3] == before[3]


@pytest.mark.parametrize("bad", [
    None,
    "text",
    {"error": "model returned invalid JSON"},
    {"question": "q", "answer": "a"},
    {"question": "q", "answer": "a", "page": 1, "quote": "x", "status": "supported", "error": "boom"},
])
def test_failed_or_incomplete_answer_leaves_the_file_untouched(out, bad):
    upsert_section(out, 1, checked(1))
    before = out.read_bytes()
    with pytest.raises(WriterError):
        upsert_section(out, 2, bad)
    assert out.read_bytes() == before


def test_failed_answer_does_not_create_the_file(out):
    with pytest.raises(WriterError):
        upsert_section(out, 1, None)
    assert not out.exists()


@pytest.mark.parametrize("index", [0, -1, "1", 1.5, True, None])
def test_invalid_section_number_raises(out, index):
    with pytest.raises(WriterError):
        upsert_section(out, index, checked(1))
    assert not out.exists()


def test_no_temp_file_is_left_after_a_write(out):
    upsert_section(out, 1, checked(1))
    assert [p.name for p in out.parent.iterdir()] == ["answers.md"]


def test_failure_while_writing_keeps_the_old_file_and_cleans_up(out, monkeypatch):
    upsert_section(out, 1, checked(1))
    before = out.read_bytes()

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        upsert_section(out, 2, checked(2))
    monkeypatch.undo()
    assert out.read_bytes() == before
    assert [p.name for p in out.parent.iterdir()] == ["answers.md"]


def test_text_written_by_hand_outside_sections_is_preserved(out):
    upsert_section(out, 1, checked(1))
    text = out.read_text().replace("# Answers", "# My course answers\n\nIntro written by me.")
    out.write_text(text + "\nNotes at the end.\n")
    upsert_section(out, 1, checked(1, answer="Changed."))
    result = out.read_text()
    assert "# My course answers" in result and "Intro written by me." in result
    assert "Notes at the end." in result and "Changed." in result


def test_multiline_quote_becomes_a_block_quote(out):
    upsert_section(out, 1, checked(1, quote="first line\nsecond line"))
    text = out.read_text()
    assert "> first line\n> second line" in text


def test_empty_quote_and_missing_page_render_cleanly(out):
    upsert_section(out, 1, checked(1, answer="The document does not cover this.", quote="", page=0,
                                   status="not supported"))
    text = out.read_text()
    assert "_(no quote)_" in text and "**Page:** -" in text


def test_missing_judge_verdict_says_not_evaluated(out):
    data = checked(1)
    del data["verdict"], data["reason"]
    upsert_section(out, 1, data)
    assert "**Judge:** not evaluated" in out.read_text()


def test_disputed_refusal_explains_why(out):
    upsert_section(out, 1, checked(1, answer="The document does not cover this.", quote="", page=0,
                                   status="not supported", verdict="unfaithful", disagreement=True))
    assert "the judge says the passages answer it" in out.read_text()


def test_disagreement_flag_is_shown(out):
    upsert_section(out, 1, checked(1, disagreement=True))
    assert "**Review needed:**" in out.read_text()


def test_unicode_text_roundtrips(out):
    upsert_section(out, 1, checked(1, answer="Réponse avec des accents é à ç et l’apostrophe courbe.",
                                   quote="L’OSI a sept couches"))
    text = out.read_bytes().decode("utf-8")
    assert "Réponse avec des accents é à ç" in text and "L’OSI a sept couches" in text


def test_multiline_question_stays_on_one_heading_line(out):
    upsert_section(out, 1, checked(1, question="Line one\nline two?"))
    assert "## Q1. Line one line two?" in out.read_text()


def test_section_numbers_above_ten_do_not_collide(out):
    for n in (1, 10, 11):
        upsert_section(out, n, checked(n))
    upsert_section(out, 1, checked(1, answer="Only this."))
    assert list(sections(out.read_text())) == [1, 10, 11]
    assert "Answer 10." in out.read_text() and "Answer 11." in out.read_text()


def test_new_file_gets_the_normal_default_permissions_not_private_ones(out):
    import stat
    umask = os.umask(0)
    os.umask(umask)
    upsert_section(out, 1, checked(1))
    assert stat.S_IMODE(out.stat().st_mode) == 0o666 & ~umask


def test_an_existing_files_permissions_are_kept_on_update(out):
    import stat
    upsert_section(out, 1, checked(1))
    out.chmod(0o640)
    upsert_section(out, 1, checked(1, answer="Changed."))
    assert stat.S_IMODE(out.stat().st_mode) == 0o640
