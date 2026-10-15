import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import e2e_check  # noqa: E402
from src.writer import upsert_section  # noqa: E402


def answer(n, page, quote, text="An answer.", status="supported"):
    return {"question": f"Q{n}?", "answer": text, "page": page, "quote": quote, "status": status,
            "verdict": "faithful", "reason": "ok"}


EXPECTED = "# Expected\n\n1 | page 3 | seven layers\n2 | page 5 | 32 bits long\n3 | none |\nnot a line\n"


@pytest.fixture
def files(tmp_path):
    exp = tmp_path / "expected.md"
    exp.write_text(EXPECTED)
    return tmp_path / "answers.md", exp


def test_parse_expected_reads_covered_and_uncovered_lines():
    assert e2e_check.parse_expected(EXPECTED) == {1: (3, "seven layers"), 2: (5, "32 bits long"), 3: (None, "")}


def test_parse_answers_reads_what_the_writer_wrote(tmp_path):
    out = tmp_path / "a.md"
    upsert_section(out, 2, answer(2, 5, "IPv4 addresses are 32 bits long"))
    parsed = e2e_check.parse_answers(out.read_text())
    assert parsed[2]["page"] == 5 and "32 bits" in parsed[2]["quote"] and parsed[2]["status"] == "supported"


def test_a_perfect_run_passes(files, capsys):
    out, exp = files
    upsert_section(out, 1, answer(1, 3, "The OSI model has seven layers"))
    upsert_section(out, 2, answer(2, 5, "IPv4 addresses are 32 bits long"))
    upsert_section(out, 3, answer(3, 0, "", text="The document does not cover this.", status="not supported"))
    assert e2e_check.main([str(out), str(exp)]) == 0
    assert "RESULT: PASS" in capsys.readouterr().out


def test_wrong_page_fails_when_below_the_threshold(files):
    out, exp = files
    upsert_section(out, 1, answer(1, 9, "seven layers"))
    upsert_section(out, 2, answer(2, 8, "32 bits long"))
    upsert_section(out, 3, answer(3, 0, "", text="The document does not cover this."))
    assert e2e_check.main([str(out), str(exp)]) == 1


def test_answering_an_uncovered_question_fails(files, capsys):
    out, exp = files
    upsert_section(out, 1, answer(1, 3, "seven layers"))
    upsert_section(out, 2, answer(2, 5, "32 bits long"))
    upsert_section(out, 3, answer(3, 4, "invented", text="Because of reasons."))
    assert e2e_check.main([str(out), str(exp)]) == 1
    assert "ANSWERED" in capsys.readouterr().out


def test_missing_section_counts_as_failure(files):
    out, exp = files
    upsert_section(out, 1, answer(1, 3, "seven layers"))
    assert e2e_check.main([str(out), str(exp), "--min-pages", "1"]) == 1


def test_min_pages_option_changes_the_threshold(files):
    out, exp = files
    upsert_section(out, 1, answer(1, 3, "seven layers"))
    upsert_section(out, 2, answer(2, 1, "x"))
    upsert_section(out, 3, answer(3, 0, "", text="The document does not cover this."))
    assert e2e_check.main([str(out), str(exp), "--min-pages", "1"]) == 0
    assert e2e_check.main([str(out), str(exp), "--min-pages", "2"]) == 1


def test_empty_expected_file_is_an_error(tmp_path):
    exp = tmp_path / "e.md"
    exp.write_text("nothing here\n")
    with pytest.raises(SystemExit):
        e2e_check.main([str(tmp_path / "a.md"), str(exp)])
