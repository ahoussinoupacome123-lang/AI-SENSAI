"""Tests of the WEB-UI server (feature X1): real HTTP on a random port, the model client faked."""
import hashlib
import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdf_factory import make_blank_pdf, make_text_pdf  # noqa: E402
from src import judge, ollama_client, pipeline  # noqa: E402
from src.ollama_client import OllamaError  # noqa: E402
from src.writer import sections  # noqa: E402

spec = importlib.util.spec_from_file_location("web_ui_server", ROOT / "WEB-UI" / "server.py")
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)

CONFIG = {"host": "http://ollama.invalid:1", "chat_model": "qwen3:4b", "judge_model": "qwen3:4b",
          "embed_model": "nomic-embed-text", "num_ctx": 4096, "chunk_size": 100, "chunk_overlap": 20,
          "top_k": 2, "max_retries": 2, "chat_prompt_file": "prompts/chat_prompt.txt"}
PAGES = ["Networks connect computers so they can share data across a building. " * 2,
         "The OSI model has seven layers from the physical layer to the application layer. " * 2]


@pytest.fixture
def app(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    make_text_pdf(data / "demo.pdf", PAGES)
    (data / "questions.txt").write_text("What is one?\nWhat is two?\nWhat is three?\n")
    return web.App(CONFIG, workspace=tmp_path / "ws", data_dir=data)


@pytest.fixture
def base(app):
    server = web.make_server(app, "127.0.0.1", 0)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def fakes(monkeypatch):
    """Fake the model: embeddings, the pipeline, the judge and the chat stream."""
    log = {"answers": [], "chat": []}

    def embed(texts, model, host=None):
        return [[float(len(t)), 1.0] for t in texts]

    def retrieve_and_answer(question, records, config):
        log["answers"].append(question)
        time.sleep(log.get("delay", 0))
        if "FAIL" in question:
            raise RuntimeError("model returned invalid JSON")
        return {"question": question, "answer": f"answer to {question}", "page": 2, "quote": "a quote",
                "status": "supported", "chunks": [{"page": 2, "text": "t"}, {"page": 1, "text": "u"}]}

    def evaluate(question, answer, chunks, config):
        return {"verdict": "faithful", "reason": "ok"}

    def chat_events(messages, model, host=None, num_ctx=4096):
        log["chat"].append({"messages": messages, "model": model, "num_ctx": num_ctx})
        try:
            yield {"type": "thinking"}
            pieces = ["x"] * log["tokens"] if "tokens" in log else ["Hel", "lo"]
            for piece in pieces:
                time.sleep(log.get("chat_delay", 0))
                log["chat_yielded"] = log.get("chat_yielded", 0) + 1
                yield {"type": "token", "text": piece}
            yield {"type": "done", "usage": {"prompt_tokens": 10, "reply_tokens": 2, "total_tokens": 12,
                                              "num_ctx": num_ctx}}
        finally:
            log["chat_closed"] = True

    monkeypatch.setattr(ollama_client, "embed", embed)
    monkeypatch.setattr(ollama_client, "list_models", lambda host=None: ["qwen3:4b", "nomic-embed-text:latest"])
    monkeypatch.setattr(ollama_client, "chat_events", chat_events)
    monkeypatch.setattr(pipeline, "retrieve_and_answer", retrieve_and_answer)
    monkeypatch.setattr(judge, "evaluate", evaluate)
    return log


def lines(response):
    """Read a streaming response line by line, as soon as each line arrives (not in 512-byte blocks)."""
    return response.iter_lines(chunk_size=1, decode_unicode=True)


def events_of(response):
    """Parse a Server-Sent Events response into [(event, data)]."""
    out, name, data = [], None, ""
    for line in lines(response):
        if line is None:
            continue
        if line.startswith("event: "):
            name = line[7:]
        elif line.startswith("data: "):
            data = line[6:]
        elif line == "" and name:
            out.append((name, json.loads(data)))
            name, data = None, ""
    return out


def run(base, **body):
    body.setdefault("doc", "builtin/demo.pdf")
    body.setdefault("questions", ["What is one?", "What is two?", "What is three?"])
    return requests.post(f"{base}/api/run", json=body, stream=True, timeout=30)


def digests(text):
    return {n: hashlib.sha256(b.encode()).hexdigest() for n, b in sections(text).items()}


# ---------- pages and routing ----------
def test_the_page_and_its_assets_are_served(base):
    page = requests.get(base + "/")
    assert page.status_code == 200 and "SENSAI" in page.text and "text/html" in page.headers["Content-Type"]
    assert "javascript" in requests.get(base + "/static/app.js").headers["Content-Type"]
    assert "text/css" in requests.get(base + "/static/style.css").headers["Content-Type"]


@pytest.mark.parametrize("path", ["/static/../server.py", "/static/%2e%2e%2fserver.py", "/static/nope.js",
                                  "/static/..%5Cserver.py", "/nope", "/api/nope"])
def test_unknown_or_escaping_paths_are_404(base, path):
    response = requests.get(base + path)
    assert response.status_code == 404 and "error" in response.json()


def test_the_page_uses_relative_asset_links_so_it_is_not_broken_when_opened_from_disk():
    html = (ROOT / "WEB-UI" / "index.html").read_text()
    assert 'href="static/style.css"' in html and 'src="static/app.js"' in html
    assert 'href="/static' not in html and 'src="/static' not in html
    assert "file:" in (ROOT / "WEB-UI" / "static" / "app.js").read_text()     # the friendly "needs its server" screen


def test_the_script_never_builds_html_from_text():
    source = (ROOT / "WEB-UI" / "static" / "app.js").read_text()
    for forbidden in ("innerHTML", "insertAdjacentHTML", "document.write", "outerHTML"):
        assert forbidden not in source
    assert "eval(" not in source


def test_every_element_the_script_looks_up_exists_in_the_page():
    import re
    html = (ROOT / "WEB-UI" / "index.html").read_text()
    script = (ROOT / "WEB-UI" / "static" / "app.js").read_text()
    ids_in_page = set(re.findall(r'\bid="([^"]+)"', html))
    looked_up = set(re.findall(r'\$\("([a-z0-9-]+)"\)', script))
    assert looked_up - ids_in_page == set()


# ---------- security ----------
def test_a_request_addressed_to_another_host_is_refused(base):
    assert requests.get(base + "/api/status", headers={"Host": "evil.example.com"}).status_code == 403


def test_a_cross_site_post_is_refused(base, fakes):
    response = requests.post(base + "/api/config", json={"reset": True}, headers={"Origin": "http://evil.example.com"})
    assert response.status_code == 403


def test_a_same_site_origin_is_accepted(base, fakes):
    response = requests.post(base + "/api/config", json={"reset": True}, headers={"Origin": base})
    assert response.status_code == 200


@pytest.mark.parametrize("value, expected", [("localhost:8000", "localhost"), ("127.0.0.1", "127.0.0.1"),
                                             ("[::1]:8000", "::1"), ("LocalHost", "localhost"), (None, "")])
def test_host_of(value, expected):
    assert web.host_of(value) == expected


# ---------- status ----------
def test_status_reports_ollama_down_with_the_fix(base, monkeypatch):
    def down(host=None):
        raise OllamaError("Cannot reach Ollama. Start it with: ollama serve")
    monkeypatch.setattr(ollama_client, "list_models", down)
    status = requests.get(base + "/api/status").json()
    assert status["ollama"] is False and "ollama serve" in status["error"] and status["models"] == []


def test_status_lists_models_and_missing_ones(base, fakes, monkeypatch):
    monkeypatch.setattr(ollama_client, "list_models", lambda host=None: ["qwen3:4b"])
    status = requests.get(base + "/api/status").json()
    assert status["ollama"] is True and status["missing_models"] == ["nomic-embed-text"]
    monkeypatch.setattr(ollama_client, "list_models", lambda host=None: ["qwen3:4b", "nomic-embed-text:latest"])
    assert requests.get(base + "/api/status").json()["missing_models"] == []


# ---------- documents ----------
def test_documents_lists_the_builtin_demo(base):
    docs = requests.get(base + "/api/documents").json()["documents"]
    assert [d["id"] for d in docs] == ["builtin/demo.pdf"]
    assert docs[0]["pages"] == 2 and docs[0]["indexed"] is False and docs[0]["has_answers"] is False


def test_upload_a_valid_pdf(base, tmp_path):
    make_text_pdf(tmp_path / "mine.pdf", PAGES)
    response = requests.post(base + "/api/upload?name=mine.pdf", data=(tmp_path / "mine.pdf").read_bytes())
    assert response.status_code == 200 and response.json()["document"]["id"] == "upload/mine.pdf"
    ids = [d["id"] for d in requests.get(base + "/api/documents").json()["documents"]]
    assert ids == ["builtin/demo.pdf", "upload/mine.pdf"]


def test_upload_rejects_a_scanned_pdf_with_a_clear_message(base, tmp_path):
    make_blank_pdf(tmp_path / "scan.pdf")
    response = requests.post(base + "/api/upload?name=scan.pdf", data=(tmp_path / "scan.pdf").read_bytes())
    assert response.status_code == 400 and "no extractable text" in response.json()["error"]
    assert requests.get(base + "/api/documents").json()["documents"][0]["id"] == "builtin/demo.pdf"


@pytest.mark.parametrize("name, data, message", [
    ("notes.txt", b"%PDF-1.4", "must end with .pdf"),
    ("x.pdf", b"", "empty"),
    ("x.pdf", b"this is not a pdf", "not a PDF"),
    ("", b"%PDF-1.4", "must end with .pdf"),
])
def test_upload_rejects_bad_input(base, name, data, message):
    response = requests.post(base + "/api/upload?name=" + name, data=data)
    assert response.status_code == 400 and message in response.json()["error"]


def test_upload_that_is_too_large_is_refused(base, monkeypatch):
    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 100)
    assert requests.post(base + "/api/upload?name=big.pdf", data=b"x" * 500).status_code == 413


def test_upload_name_cannot_escape_the_workspace(base, app, tmp_path):
    make_text_pdf(tmp_path / "p.pdf", PAGES)
    response = requests.post(base + "/api/upload?name=../../evil.pdf", data=(tmp_path / "p.pdf").read_bytes())
    assert response.status_code == 200 and response.json()["document"]["name"] == "evil.pdf"
    assert (app.uploads / "evil.pdf").is_file()
    assert not (tmp_path / "evil.pdf").exists() and not (app.workspace.parent / "evil.pdf").exists()


def test_pdf_files_are_served_inline(base, tmp_path):
    response = requests.get(base + "/files/builtin/demo.pdf")
    assert response.status_code == 200 and response.headers["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


@pytest.mark.parametrize("path", ["/files/builtin/other.pdf", "/files/upload/nope.pdf", "/files/upload/..%2Fserver.py",
                                  "/files/upload/%2e%2e/%2e%2e/etc/passwd", "/files/etc/passwd", "/files/builtin",
                                  "/files/upload/a.txt", "/files/other/demo.pdf"])
def test_other_files_are_never_served(base, path):
    assert requests.get(base + path).status_code == 404


def test_example_questions_come_from_the_data_folder(base, app):
    three = ["What is one?", "What is two?", "What is three?"]
    assert requests.get(base + "/api/examples").json() == {"builtin/demo.pdf": {"questions": three, "quick": three}}
    (app.data_dir / "questions_demo.txt").write_text("Only the quick one?\n")
    assert requests.get(base + "/api/examples").json()["builtin/demo.pdf"]["quick"] == ["Only the quick one?"]


# ---------- settings ----------
def test_settings_can_be_changed_for_the_session_and_reset(base, app):
    response = requests.post(base + "/api/config", json={"overrides": {"top_k": 5, "chat_model": "other:1b"}})
    assert response.status_code == 200 and response.json()["config"]["top_k"] == 5
    assert app.defaults["top_k"] == 2 and app.config()["chat_model"] == "other:1b"
    assert requests.post(base + "/api/config", json={"reset": True}).json()["config"]["top_k"] == 2


@pytest.mark.parametrize("overrides, message", [
    ({"host": "http://evil:1"}, "cannot be changed"),
    ({"top_k": 0}, "between 1 and 20"), ({"top_k": 99}, "between 1 and 20"), ({"top_k": "5"}, "whole number"),
    ({"top_k": True}, "whole number"), ({"chunk_overlap": 100}, "smaller than chunk_size"),
    ({"chat_model": "bad name!"}, "model name"), ({"chat_model": 5}, "model name"), ("oops", "object"),
])
def test_invalid_settings_are_refused_and_nothing_is_stored(base, app, overrides, message):
    response = requests.post(base + "/api/config", json={"overrides": overrides})
    assert response.status_code == 400 and message in response.json()["error"]
    assert app.overrides == {}


def test_a_request_body_that_is_not_json_is_a_400(base):
    assert requests.post(base + "/api/config", data=b"{nope", headers={"Content-Type": "application/json"}).status_code == 400


# ---------- run (ask a PDF) ----------
def test_a_run_streams_progress_then_answers_then_a_summary(base, app, fakes):
    events = events_of(run(base))
    names = [n for n, _ in events]
    assert names[0] == "start" and names[-2:] == ["summary", "done"]
    assert names.count("question_start") == 3 and names.count("question_done") == 3
    assert "ingest" in names and names.index("ingest") < names.index("question_start")
    done = [d for n, d in events if n == "question_done"]
    assert [d["index"] for d in done] == [1, 2, 3]
    assert done[0]["checked"]["retrieved_pages"] == [1, 2] and "chunks" not in done[0]["checked"]
    assert done[0]["checked"]["verdict"] == "faithful" and done[0]["seconds"] >= 0
    summary = dict(events)["summary"]
    assert summary["answered"] == 3 and summary["failed"] == 0 and "3/3 questions answered" in summary["text"]
    assert list(sections(app.output_path("builtin/demo.pdf").read_text())) == [1, 2, 3]


def test_a_failing_question_does_not_stop_the_run(base, app, fakes):
    events = events_of(run(base, questions=["What is one?", "FAIL this", "What is three?"]))
    names = [n for n, _ in events]
    assert names.count("question_done") == 2 and names.count("question_failed") == 1
    assert dict(events)["question_failed"]["message"] == "model returned invalid JSON"
    assert dict(events)["summary"]["failed"] == 1
    assert list(sections(app.output_path("builtin/demo.pdf").read_text())) == [1, 3]


def test_rerunning_one_question_changes_only_its_section(base, app, fakes):
    events_of(run(base))
    before = digests(app.output_path("builtin/demo.pdf").read_text())
    fakes["answers"].clear()
    events = events_of(run(base, only=2, questions=["What is one?", "A reworded second question?", "What is three?"]))
    assert fakes["answers"] == ["A reworded second question?"]
    assert [n for n, _ in events].count("question_start") == 1
    after = digests(app.output_path("builtin/demo.pdf").read_text())
    assert after[1] == before[1] and after[3] == before[3] and after[2] != before[2]


def test_the_index_is_built_once_and_reused(base, app, fakes):
    first = events_of(run(base))
    second = events_of(run(base))
    assert any(d["stage"] == "embedding" for n, d in first if n == "ingest")
    assert [d["stage"] for n, d in second if n == "ingest"] == ["reuse"]
    forced = events_of(run(base, force=True))
    assert any(d["stage"] == "embedding" for n, d in forced if n == "ingest")


def test_an_ingestion_error_ends_the_run_with_an_error_event(base, app, fakes, monkeypatch):
    def broken(*args, **kwargs):
        raise web.ingestion.IngestionError("The saved index is not a valid index. Rebuild it with --force.")
    monkeypatch.setattr(web.ingestion, "ingest", broken)
    events = events_of(run(base))
    assert [n for n, _ in events] == ["start", "error"] and "--force" in events[-1][1]["message"]
    assert fakes["answers"] == []


@pytest.mark.parametrize("body, status, message", [
    ({"doc": "builtin/nope.pdf"}, 404, "unknown document"),
    ({"doc": "upload/../../etc/passwd"}, 404, "unknown document"),
    ({"doc": "nonsense"}, 404, "unknown document"),
    ({"questions": []}, 400, "at least one question"),
    ({"questions": ["  ", ""]}, 400, "at least one question"),
    ({"questions": "one"}, 400, "must be a list"),
    ({"only": 9}, 400, "between 1 and 3"),
    ({"only": 0}, 400, "between 1 and 3"),
    ({"only": "2"}, 400, "between 1 and 3"),
    ({"questions": ["x" * 2000]}, 400, "longer than"),
    ({"questions": ["q"] * 101}, 400, "at most"),
])
def test_a_bad_run_request_is_refused_before_streaming(base, fakes, body, status, message):
    response = run(base, **body)
    assert response.status_code == status and message in response.json()["error"]


def test_the_answers_file_can_be_read_and_downloaded(base, fakes):
    assert requests.get(base + "/api/answers?doc=builtin/demo.pdf").status_code == 404
    events_of(run(base))
    text = requests.get(base + "/api/answers?doc=builtin/demo.pdf")
    assert text.status_code == 200 and "## Q1. What is one?" in text.text
    download = requests.get(base + "/api/answers?doc=builtin/demo.pdf&download=1")
    assert "attachment" in download.headers["Content-Disposition"]
    assert requests.get(base + "/api/documents").json()["documents"][0]["has_answers"] is True


def test_only_one_job_runs_at_a_time(base, fakes):
    fakes["delay"] = 0.4
    first = run(base)
    assert next(lines(first)) == "event: start"            # the first run has started
    second = run(base)
    assert second.status_code == 409 and "in progress" in second.json()["error"]
    first.close()


def test_leaving_the_page_stops_the_run_and_frees_the_lock(base, app, fakes):
    fakes["delay"] = 0.3
    response = run(base, questions=[f"Question {i}?" for i in range(8)])
    for line in lines(response):
        if line == "event: question_done":
            break
    response.close()                                       # the user pressed Stop / closed the tab
    deadline = time.time() + 6
    while app.busy.locked() and time.time() < deadline:
        time.sleep(0.05)
    assert not app.busy.locked()
    assert len(fakes["answers"]) < 8
    assert len(events_of(run(base, questions=["After the stop?"]))) > 0   # a new run is accepted


# ---------- chat ----------
def chat(base, messages, **extra):
    return requests.post(base + "/api/chat", json={"messages": messages, **extra}, stream=True, timeout=30)


def test_a_chat_reply_streams_tokens_and_reports_usage(base, fakes):
    events = events_of(chat(base, [{"role": "user", "content": "hi"}]))
    assert [n for n, _ in events] == ["thinking", "token", "token", "done"]
    assert "".join(d["text"] for n, d in events if n == "token") == "Hello"
    assert events[-1][1]["usage"] == {"prompt_tokens": 10, "reply_tokens": 2, "total_tokens": 12, "num_ctx": 4096}


def test_the_chat_prompt_and_the_history_are_sent_with_the_configured_model(base, fakes):
    history = [{"role": "user", "content": "My name is Sam."}, {"role": "assistant", "content": "Hi Sam."},
               {"role": "user", "content": "What is my name?"}]
    events_of(chat(base, history))
    sent = fakes["chat"][0]
    assert sent["messages"][0]["role"] == "system" and sent["messages"][1:] == history
    assert sent["model"] == "qwen3:4b" and sent["num_ctx"] == 4096


def test_a_model_chosen_in_the_ui_and_session_settings_are_used(base, app, fakes):
    requests.post(base + "/api/config", json={"overrides": {"num_ctx": 2048}})
    events_of(chat(base, [{"role": "user", "content": "hi"}], model="other:1b"))
    assert fakes["chat"][0]["model"] == "other:1b" and fakes["chat"][0]["num_ctx"] == 2048


def test_a_model_error_becomes_an_error_event(base, fakes, monkeypatch):
    def broken(*args, **kwargs):
        raise OllamaError("Model 'x' not found. Pull it with: ollama pull x")
        yield
    monkeypatch.setattr(ollama_client, "chat_events", broken)
    events = events_of(chat(base, [{"role": "user", "content": "hi"}]))
    assert events == [("error", {"message": "Model 'x' not found. Pull it with: ollama pull x"})]


@pytest.mark.parametrize("messages, message", [
    ([], "between 1 and"), ("hi", "between 1 and"),
    ([{"role": "assistant", "content": "x"}], "last message must come from the user"),
    ([{"role": "system", "content": "x"}], "role"), ([{"role": "user", "content": "  "}], "role"),
    ([{"role": "user"}], "role"), (["text"], "role"),
    ([{"role": "user", "content": "x" * 30000}], "longer than"),
    ([{"role": "user", "content": "x"}] * 300, "between 1 and"),
])
def test_bad_chat_requests_are_refused(base, fakes, messages, message):
    response = chat(base, messages)
    assert response.status_code == 400 and message in response.json()["error"]


def test_a_bad_model_name_is_refused(base, fakes):
    response = chat(base, [{"role": "user", "content": "hi"}], model="bad name; rm -rf")
    assert response.status_code == 400 and "model" in response.json()["error"]


def test_pressing_stop_in_the_chat_closes_the_model_stream(base, fakes):
    fakes["chat_delay"] = 0.1
    fakes["tokens"] = 40
    response = chat(base, [{"role": "user", "content": "hi"}])
    for line in lines(response):
        if line == "event: token":
            break
    response.close()
    deadline = time.time() + 8
    while "chat_closed" not in fakes and time.time() < deadline:
        time.sleep(0.05)
    assert fakes.get("chat_closed") is True
    assert fakes["chat_yielded"] < 40                       # the stream was stopped, not read to the end


def test_a_chat_and_a_run_cannot_overlap(base, fakes):
    fakes["chat_delay"] = 0.4
    first = chat(base, [{"role": "user", "content": "hi"}])
    assert next(lines(first)) == "event: thinking"
    assert run(base).status_code == 409
    first.close()


# ---------- helpers and startup ----------
def test_public_answer_drops_the_chunks_and_lists_their_pages():
    data = web.public_answer({"question": "q", "answer": "a", "page": 3, "quote": "x", "status": "supported",
                              "chunks": [{"page": 3}, {"page": 1}, {"page": 3}], "secret": "no"})
    assert data["retrieved_pages"] == [1, 3] and "chunks" not in data and "secret" not in data


def test_main_reports_a_missing_config_file(tmp_path):
    with pytest.raises(SystemExit, match="config file not found"):
        web.main(["--config", str(tmp_path / "nope.json")])


def test_main_reports_a_port_that_is_in_use(app):
    server = web.make_server(app, "127.0.0.1", 0)
    try:
        with pytest.raises(SystemExit, match="cannot listen"):
            web.main(["--port", str(server.server_address[1])])
    finally:
        server.server_close()
