import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import cli, ingestion, judge, pipeline  # noqa: E402
from src.writer import sections  # noqa: E402

CONFIG = {"host": "http://x", "chat_model": "m", "embed_model": "e",
          "chunk_size": 100, "chunk_overlap": 10, "top_k": 2}
RECORDS = [{"id": 0, "text": "t", "page": 1, "vector": [1.0]}]


class Calls:
    def __init__(self):
        self.ingest = []
        self.answer = []
        self.judge = []


@pytest.fixture
def env(tmp_path, monkeypatch):
    pdf = tmp_path / "course.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake, ingestion is mocked")
    questions = tmp_path / "questions.txt"
    questions.write_text("What is one?\nWhat is two?\nWhat is three?\n")
    config = tmp_path / "config.json"
    config.write_text(json.dumps(CONFIG))
    calls = Calls()

    def fake_ingest(pdf_path, cfg, force=False):
        calls.ingest.append({"pdf": Path(pdf_path), "cfg": cfg, "force": force})
        return RECORDS

    def fake_answer(question, records, cfg):
        calls.answer.append((question, records, cfg))
        if "FAIL" in question:
            raise RuntimeError("model returned invalid JSON")
        return {"question": question, "answer": f"answer to {question}", "page": 2,
                "quote": "a quote", "status": "supported", "chunks": records}

    def fake_judge(question, answer, chunks, cfg):
        calls.judge.append(question)
        return {"verdict": "faithful", "reason": "ok"}

    monkeypatch.setattr(ingestion, "ingest", fake_ingest)
    monkeypatch.setattr(pipeline, "answer", fake_answer)
    monkeypatch.setattr(judge, "evaluate", fake_judge)
    return {"dir": tmp_path, "pdf": pdf, "questions": questions, "config": config,
            "out": tmp_path / "answers.md", "calls": calls}


def run(env, *extra, questions=None, pdf=None):
    argv = [str(pdf or env["pdf"]), str(questions or env["questions"]),
            "--config", str(env["config"]), *extra]
    return cli.main(argv)


def digests(path):
    return {n: hashlib.sha256(b.encode()).hexdigest() for n, b in sections(path.read_text()).items()}


def test_three_questions_write_three_sections(env, capsys):
    assert run(env) == 0
    assert list(sections(env["out"].read_text())) == [1, 2, 3]
    assert "Done: 3/3 questions answered, 0 failed" in capsys.readouterr().out


def test_ingestion_gets_the_pdf_config_and_default_force(env):
    run(env)
    call = env["calls"].ingest[0]
    assert call["pdf"] == env["pdf"] and call["cfg"] == CONFIG and call["force"] is False


def test_force_is_passed_to_ingestion(env):
    run(env, "--force")
    assert env["calls"].ingest[0]["force"] is True


def test_pipeline_receives_each_question_with_the_index_records(env):
    run(env)
    assert [q for q, _, _ in env["calls"].answer] == ["What is one?", "What is two?", "What is three?"]
    assert all(records == RECORDS for _, records, _ in env["calls"].answer)


def test_one_failed_question_does_not_stop_the_run(env, capsys):
    env["questions"].write_text("What is one?\nFAIL this one\nWhat is three?\n")
    assert run(env) == 1
    assert list(sections(env["out"].read_text())) == [1, 3]
    out = capsys.readouterr().out
    assert "2/3 questions answered, 1 failed" in out
    assert "Failed: Q2 (model returned invalid JSON)" in out


def test_all_questions_failing_writes_no_file(env):
    env["questions"].write_text("FAIL a\nFAIL b\n")
    assert run(env) == 1
    assert not env["out"].exists()


def test_only_rewrites_just_that_section(env, monkeypatch):
    run(env)
    before = digests(env["out"])
    monkeypatch.setattr(pipeline, "answer", lambda q, r, c: {
        "question": q, "answer": "NEW ANSWER", "page": 7, "quote": "new", "status": "supported"})
    assert run(env, "--only", "2") == 0
    after = digests(env["out"])
    assert "NEW ANSWER" in env["out"].read_text()
    assert after[1] == before[1] and after[3] == before[3] and after[2] != before[2]


def test_only_answers_a_single_question(env):
    run(env, "--only", "3")
    assert [q for q, _, _ in env["calls"].answer] == ["What is three?"]
    assert list(sections(env["out"].read_text())) == [3]


@pytest.mark.parametrize("value", ["0", "4", "-1"])
def test_only_out_of_range_is_a_clear_error(env, capsys, value):
    assert run(env, "--only", value) == 1
    assert "out of range" in capsys.readouterr().err
    assert env["calls"].ingest == []


def test_blank_lines_are_ignored_and_numbering_follows_the_remaining_lines(env):
    env["questions"].write_text("\nFirst?\n\n   \nSecond?\n")
    run(env)
    assert list(sections(env["out"].read_text())) == [1, 2]
    assert "## Q2. Second?" in env["out"].read_text()


def test_empty_questions_file_is_a_clear_error(env, capsys):
    env["questions"].write_text("\n  \n")
    assert run(env) == 1
    assert "no questions found" in capsys.readouterr().err
    assert env["calls"].ingest == []


def test_missing_questions_file_is_a_clear_error(env, capsys):
    assert run(env, questions=env["dir"] / "nope.txt") == 1
    assert "questions file not found" in capsys.readouterr().err


def test_missing_pdf_is_a_clear_error(env, capsys):
    assert run(env, pdf=env["dir"] / "nope.pdf") == 1
    assert "PDF not found" in capsys.readouterr().err
    assert env["calls"].ingest == []


def test_missing_config_file_is_a_clear_error(env, capsys):
    env["config"].unlink()
    assert run(env) == 1
    assert "config file not found" in capsys.readouterr().err


def test_config_missing_keys_is_a_clear_error(env, capsys):
    env["config"].write_text(json.dumps({"host": "http://x"}))
    assert run(env) == 1
    err = capsys.readouterr().err
    assert "is missing" in err and "chunk_size" in err


def test_ingestion_error_is_printed_without_traceback(env, monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise ingestion.NoTextError("course.pdf has no extractable text (probably scanned images).")
    monkeypatch.setattr(ingestion, "ingest", boom)
    assert run(env) == 1
    assert "Error: course.pdf has no extractable text" in capsys.readouterr().err
    assert not env["out"].exists()


def test_ollama_error_during_ingestion_is_printed(env, monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise RuntimeError("Cannot reach Ollama at http://x. Start it with: ollama serve")
    monkeypatch.setattr(ingestion, "ingest", boom)
    assert run(env) == 1
    assert "ollama serve" in capsys.readouterr().err


def test_unimplemented_pipeline_names_the_unfinished_function(env, monkeypatch, capsys):
    def todo(*args):
        raise NotImplementedError
    monkeypatch.setattr(pipeline, "answer", todo)
    assert run(env) == 1
    err = capsys.readouterr().err
    assert "todo is not implemented yet" in err and "()" not in err
    assert not env["out"].exists()


def test_unimplemented_ingestion_stops_with_a_clear_message(env, monkeypatch, capsys):
    def todo(*args, **kwargs):
        raise NotImplementedError
    monkeypatch.setattr(ingestion, "ingest", todo)
    assert run(env) == 1
    assert "todo is not implemented yet" in capsys.readouterr().err


def test_unimplemented_judge_keeps_the_answers(env, monkeypatch):
    def todo(*args):
        raise NotImplementedError
    monkeypatch.setattr(judge, "evaluate", todo)
    assert run(env) == 0
    assert "**Judge:** not evaluated" in env["out"].read_text()


def test_judge_failure_marks_unknown_and_keeps_the_answer(env, monkeypatch):
    def bad(*args):
        raise ValueError("bad verdict")
    monkeypatch.setattr(judge, "evaluate", bad)
    assert run(env) == 0
    text = env["out"].read_text()
    assert "**Judge:** unknown - judge failed: bad verdict" in text and "answer to What is one?" in text


def test_judge_is_skipped_when_the_pipeline_already_judged(env, monkeypatch):
    monkeypatch.setattr(pipeline, "answer", lambda q, r, c: {
        "question": q, "answer": "a", "page": 1, "quote": "q", "status": "supported",
        "verdict": "partial", "reason": "r"})
    run(env)
    assert env["calls"].judge == []
    assert "**Judge:** partial - r" in env["out"].read_text()


def test_disagreement_is_flagged_in_file_and_summary(env, monkeypatch, capsys):
    monkeypatch.setattr(judge, "evaluate", lambda *a: {"verdict": "unfaithful", "reason": "wrong"})
    run(env)
    assert "**Review needed:**" in env["out"].read_text()
    assert "Review needed (quote check and judge disagree): Q1, Q2, Q3" in capsys.readouterr().out


def test_summary_counts_quote_check_and_judge(env, monkeypatch, capsys):
    verdicts = iter(["faithful", "partial", "unfaithful"])
    monkeypatch.setattr(judge, "evaluate", lambda *a: {"verdict": next(verdicts), "reason": "r"})
    run(env)
    out = capsys.readouterr().out
    assert "Quote check: 3 supported, 0 not supported" in out
    assert "Judge: 1 faithful, 1 partial, 1 unfaithful, 0 unknown" in out


def test_progress_lines_are_printed(env, capsys):
    run(env)
    out = capsys.readouterr().out
    assert "[1/3] Q1: What is one?" in out and "[3/3] Q3: What is three?" in out
    assert "supported, page 2, judge: faithful" in out


def test_default_output_is_next_to_the_pdf(env):
    run(env)
    assert env["out"].exists() and env["out"].parent == env["pdf"].parent


def test_output_option_is_respected(env):
    target = env["dir"] / "mine" / "result.md"
    target.parent.mkdir()
    run(env, "--output", str(target))
    assert target.exists() and not env["out"].exists()


def test_ctrl_c_keeps_what_was_written_and_exits_130(env, monkeypatch, capsys):
    def interrupt_on_two(question, records, cfg):
        if "two" in question:
            raise KeyboardInterrupt
        return {"question": question, "answer": "a", "page": 1, "quote": "q", "status": "supported"}
    monkeypatch.setattr(pipeline, "answer", interrupt_on_two)
    assert run(env) == 130
    assert list(sections(env["out"].read_text())) == [1]
    assert "Interrupted" in capsys.readouterr().out
