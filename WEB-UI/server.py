#!/usr/bin/env python3
"""Sensai web UI server (feature X1): a browser front end over the same backend as the CLI.

    python WEB-UI/server.py [--host 127.0.0.1] [--port 8000] [--config config.json]

Then open http://127.0.0.1:8000 . Standard library only (no new dependency).

The UI does not change the backend: it calls the same modules as `python -m src.cli`
(ingestion, pipeline, judge, writer) and streams their progress to the browser as
Server-Sent Events. The server listens on the loopback interface only by default; it has no
login, so do not expose it to a network you do not trust.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from src import cli, ingestion, ollama_client, writer  # noqa: E402

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_QUESTIONS = 100
MAX_QUESTION_CHARS = 1000
MAX_MESSAGES = 200
MAX_MESSAGE_CHARS = 20000
SAFE_NAME = re.compile(r"^[A-Za-z0-9._ -]{1,120}$")
MODEL_NAME = re.compile(r"^[A-Za-z0-9._:/-]{1,100}$")
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png"}
# Settings the UI may change for the current server session (the host is deliberately not one).
EDITABLE = {
    "chat_model": ("str",), "judge_model": ("str",), "embed_model": ("str",),
    "top_k": ("int", 1, 20), "chunk_size": ("int", 200, 4000), "chunk_overlap": ("int", 0, 2000),
    "num_ctx": ("int", 512, 32768), "max_retries": ("int", 0, 5),
}


class RequestError(Exception):
    """A problem with the request. `status` is the HTTP code, the message is shown to the user."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class App:
    """The state shared by all requests: settings, workspace folders, and the one-job-at-a-time lock."""

    def __init__(self, config, workspace=None, data_dir=None, static_dir=None, allowed_hosts=None, index_file=None):
        self.defaults = dict(config)
        self.overrides = {}
        self.workspace = Path(workspace or HERE / "workspace")
        self.uploads = self.workspace / "uploads"
        self.outputs = self.workspace / "outputs"
        self.uploads.mkdir(parents=True, exist_ok=True)
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.data_dir = Path(data_dir or ROOT / "data")
        self.static_dir = Path(static_dir or HERE / "static")
        self.index_file = Path(index_file or HERE / "index.html")
        self.allowed_hosts = {"localhost", "127.0.0.1", "::1"} | {h.lower() for h in (allowed_hosts or ())}
        self.busy = threading.Lock()

    # ---- settings -------------------------------------------------------------------------
    def config(self):
        return {**self.defaults, **self.overrides}

    def set_overrides(self, values):
        """Validate and store session overrides; raise RequestError with a clear message."""
        if not isinstance(values, dict):
            raise RequestError("overrides must be an object")
        clean = {}
        for key, value in values.items():
            rule = EDITABLE.get(key)
            if rule is None:
                raise RequestError(f"'{key}' cannot be changed from the web UI")
            if rule[0] == "str":
                if not isinstance(value, str) or not MODEL_NAME.match(value):
                    raise RequestError(f"'{key}' must be a model name such as qwen3:4b")
                clean[key] = value
            else:
                if isinstance(value, bool) or not isinstance(value, int):
                    raise RequestError(f"'{key}' must be a whole number")
                if not rule[1] <= value <= rule[2]:
                    raise RequestError(f"'{key}' must be between {rule[1]} and {rule[2]}")
                clean[key] = value
        merged = {**self.defaults, **self.overrides, **clean}
        if merged["chunk_overlap"] >= merged["chunk_size"]:
            raise RequestError("chunk_overlap must be smaller than chunk_size")
        self.overrides.update(clean)

    def reset_overrides(self):
        self.overrides.clear()

    # ---- documents ------------------------------------------------------------------------
    def _folder(self, source):
        if source == "builtin":
            return self.data_dir
        if source == "upload":
            return self.uploads
        raise RequestError("unknown document", 404)

    def resolve_doc(self, doc_id):
        """Map 'builtin/demo.pdf' or 'upload/x.pdf' to an existing file. Never joins raw user paths."""
        if not isinstance(doc_id, str) or doc_id.count("/") != 1:
            raise RequestError("unknown document", 404)
        source, name = doc_id.split("/")
        if not SAFE_NAME.match(name) or not name.lower().endswith(".pdf"):
            raise RequestError("unknown document", 404)
        folder = self._folder(source)
        if source == "builtin" and name != "demo.pdf":
            raise RequestError("unknown document", 404)
        match = next((p for p in folder.glob("*.pdf") if p.name == name and p.is_file()), None)
        if match is None:
            raise RequestError("unknown document", 404)
        return match

    def output_path(self, doc_id):
        source, name = doc_id.split("/")
        return self.outputs / f"{source}-{name}.answers.md"

    def doc_info(self, source, path):
        from pypdf import PdfReader
        try:
            pages = len(PdfReader(str(path)).pages)
        except Exception:  # noqa: BLE001 - a broken file is listed with 0 pages, not a crash
            pages = 0
        return {"id": f"{source}/{path.name}", "name": path.name, "source": source, "pages": pages,
                "indexed": ingestion.index_path(path).exists(), "size": path.stat().st_size,
                "has_answers": self.output_path(f"{source}/{path.name}").exists()}

    def documents(self):
        docs = []
        demo = self.data_dir / "demo.pdf"
        if demo.is_file():
            docs.append(self.doc_info("builtin", demo))
        docs += [self.doc_info("upload", p) for p in sorted(self.uploads.glob("*.pdf"))]
        return docs

    def save_upload(self, name, data):
        """Validate an uploaded PDF (it must have extractable text) and store it in the workspace."""
        name = Path(str(name or "")).name
        name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)[:120]
        if not name.lower().endswith(".pdf"):
            raise RequestError("the file name must end with .pdf")
        if not data:
            raise RequestError("the file is empty")
        fd, tmp = tempfile.mkstemp(dir=self.uploads, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            ingestion.extract_pages(tmp)  # clear IngestionError for scans, non-PDFs, broken files
            os.replace(tmp, self.uploads / name)
        except ingestion.IngestionError as e:
            raise RequestError(str(e).replace(tmp, name))
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return self.doc_info("upload", self.uploads / name)

    # ---- status ---------------------------------------------------------------------------
    def status(self):
        config = self.config()
        try:
            models, error = ollama_client.list_models(host=config["host"]), None
        except ollama_client.OllamaError as e:
            models, error = [], str(e)
        installed = set(models)
        needed = {config["chat_model"], config["judge_model"], config["embed_model"]}
        missing = sorted(m for m in needed if m not in installed and f"{m}:latest" not in installed)
        return {"ollama": error is None, "error": error, "models": models,
                "missing_models": missing if error is None else [], "config": config,
                "defaults": self.defaults, "editable": EDITABLE, "busy": self.busy.locked(),
                "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024)}


def public_answer(checked):
    """The part of a checked answer the browser needs (the retrieved chunks are summarised by page)."""
    keys = ("question", "answer", "page", "quote", "status", "verdict", "reason", "disagreement")
    data = {k: checked.get(k) for k in keys}
    data["retrieved_pages"] = sorted({c.get("page") for c in checked.get("chunks", []) if c.get("page")})
    return data


def clean_questions(questions):
    if not isinstance(questions, list):
        raise RequestError("questions must be a list")
    cleaned = [q.strip() for q in questions if isinstance(q, str) and q.strip()]
    if not cleaned:
        raise RequestError("write at least one question")
    if len(cleaned) > MAX_QUESTIONS:
        raise RequestError(f"at most {MAX_QUESTIONS} questions")
    if any(len(q) > MAX_QUESTION_CHARS for q in cleaned):
        raise RequestError(f"a question is longer than {MAX_QUESTION_CHARS} characters")
    return cleaned


def prepare_run(app, doc_id, questions, only):
    """Validate a run request and return (pdf, cleaned questions, only). Raises RequestError."""
    pdf = app.resolve_doc(doc_id)
    questions = clean_questions(questions)
    if only is not None and (isinstance(only, bool) or not isinstance(only, int)
                             or not 1 <= only <= len(questions)):
        raise RequestError(f"'only' must be between 1 and {len(questions)}")
    return pdf, questions, only


def run_job(app, doc_id, questions, only, force, emit):
    """Answer questions about a document, exactly as the CLI does, reporting through emit(event, data).

    Events: start, ingest, question_start, question_done, question_failed, summary, done, error.
    Raises RequestError for a bad request before anything starts. A failing question never stops
    the run; a failed ingestion ends it with an `error` event.
    """
    pdf, questions, only = prepare_run(app, doc_id, questions, only)
    config = app.config()
    output = app.output_path(doc_id)
    selected = [(i, q) for i, q in enumerate(questions, start=1) if only in (None, i)]

    emit("start", {"doc": doc_id, "total": len(selected), "only": only, "output": output.name})
    try:
        records = ingestion.ingest(pdf, config, force=bool(force), progress=lambda ev: emit("ingest", ev))
    except (ingestion.IngestionError, ollama_client.OllamaError) as e:
        emit("error", {"message": str(e)})
        return
    except Exception as e:  # noqa: BLE001 - report anything else instead of dropping the stream
        emit("error", {"message": f"Ingestion failed: {e}"})
        return

    answered, failed = [], []
    for position, (index, question) in enumerate(selected, start=1):
        emit("question_start", {"index": index, "question": question, "position": position,
                                "total": len(selected)})
        started = time.time()
        try:
            checked = cli.answer_question(question, records, config)
            writer.upsert_section(output, index, checked)
        except (BrokenPipeError, ConnectionResetError):
            raise
        except Exception as e:  # noqa: BLE001 - one failed question must not stop the run
            failed.append((index, str(e)))
            emit("question_failed", {"index": index, "question": question, "message": str(e)})
            continue
        answered.append((index, checked))
        emit("question_done", {"index": index, "question": question, "checked": public_answer(checked),
                               "seconds": round(time.time() - started, 1)})

    review = [i for i, c in answered if c.get("disagreement")]
    emit("summary", {"text": cli.build_summary(len(selected), answered, failed, output.name),
                     "answered": len(answered), "failed": len(failed), "total": len(selected),
                     "review": review})
    emit("done", {"doc": doc_id, "output": output.name})


def prepare_chat(app, messages, model):
    """Validate a chat request and return (messages with the chat prompt, model). Raises RequestError."""
    if not isinstance(messages, list) or not messages or len(messages) > MAX_MESSAGES:
        raise RequestError("send between 1 and %d messages" % MAX_MESSAGES)
    clean = []
    for m in messages:
        if (not isinstance(m, dict) or m.get("role") not in ("user", "assistant")
                or not isinstance(m.get("content"), str) or not m["content"].strip()):
            raise RequestError("each message needs a role (user or assistant) and some text")
        if len(m["content"]) > MAX_MESSAGE_CHARS:
            raise RequestError(f"a message is longer than {MAX_MESSAGE_CHARS} characters")
        clean.append({"role": m["role"], "content": m["content"]})
    if clean[-1]["role"] != "user":
        raise RequestError("the last message must come from the user")
    config = app.config()
    model = model or config["chat_model"]
    if not isinstance(model, str) or not MODEL_NAME.match(model):
        raise RequestError("invalid model name")
    try:
        clean.insert(0, {"role": "system", "content": (ROOT / config["chat_prompt_file"]).read_text().strip()})
    except (OSError, KeyError):
        pass  # no chat prompt file: the model's own defaults apply
    try:
        from src.memory import SessionMemory
        mem = SessionMemory(base_dir=app.workspace / ".sensai", host=config["host"], embed_model=config.get("embed_model", "nomic-embed-text"))
        last_user = clean[-1]["content"]
        if mem.is_recall_query(last_user):
            matches = mem.search_memory(last_user, top_k=3)
            if matches:
                block = mem.format_memory_context(matches)
                clean.insert(1, {"role": "system", "content": block})
    except Exception:
        pass
    return clean, model


def chat_job(app, messages, model, emit):
    """Stream a plain chat reply (events: thinking, token, done with usage, error)."""
    messages, model = prepare_chat(app, messages, model)
    config = app.config()
    events = ollama_client.chat_events(messages, model, host=config["host"], num_ctx=int(config["num_ctx"]))
    try:
        for event in events:
            emit(event["type"], event)
    except ollama_client.OllamaError as e:
        emit("error", {"message": str(e)})
    finally:
        events.close()


def host_of(value):
    """'localhost:8000' -> 'localhost', '[::1]:8000' -> '::1' (lower case)."""
    value = (value or "").strip().lower()
    if value.startswith("["):
        return value[1:value.find("]")] if "]" in value else value
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


class Handler(BaseHTTPRequestHandler):
    server_version = "SensaiWebUI/1.0"

    @property
    def app(self):
        return self.server.app

    def log_message(self, fmt, *args):
        sys.stderr.write("[web] %s\n" % (fmt % args))

    # ---- helpers --------------------------------------------------------------------------
    def send_bytes(self, status, body, content_type, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, data):
        self.send_bytes(status, json.dumps(data).encode(), "application/json; charset=utf-8")

    def read_body(self, limit):
        length = self.headers.get("Content-Length")
        if length is None:
            raise RequestError("Content-Length is required", 411)
        try:
            length = int(length)
        except ValueError:
            raise RequestError("bad Content-Length")
        if length > limit:
            raise RequestError("the request is too large", 413)
        return self.rfile.read(length)

    def read_json(self):
        try:
            data = json.loads(self.read_body(MAX_JSON_BYTES) or b"{}")
        except json.JSONDecodeError:
            raise RequestError("the request body is not valid JSON")
        if not isinstance(data, dict):
            raise RequestError("the request body must be a JSON object")
        return data

    def check_origin(self):
        """Refuse requests aimed at the wrong Host, and cross-site POSTs (DNS rebinding and CSRF)."""
        if host_of(self.headers.get("Host")) not in self.app.allowed_hosts:
            raise RequestError("this server only answers requests addressed to localhost", 403)
        origin = self.headers.get("Origin")
        if origin and (urllib.parse.urlparse(origin).hostname or "").lower() not in self.app.allowed_hosts:
            raise RequestError("cross-site requests are not allowed", 403)

    def start_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def emit(event, data):
            self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())
            self.wfile.flush()
        return emit

    def stream_job(self, job):
        """Run job(emit) while holding the single-job lock, streaming events to the browser."""
        if not self.app.busy.acquire(blocking=False):
            raise RequestError("Another run or chat is in progress. Wait for it to finish.", 409)
        try:
            emit = self.start_sse()
            try:
                job(emit)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the browser left (Stop or closed tab): abandon the job
            except Exception as e:  # noqa: BLE001
                try:
                    emit("error", {"message": f"Unexpected error: {e}"})
                except (BrokenPipeError, ConnectionResetError):
                    pass
        finally:
            self.app.busy.release()

    # ---- routing --------------------------------------------------------------------------
    def dispatch(self, method):
        try:
            self.check_origin()
            url = urllib.parse.urlparse(self.path)
            path, query = url.path, urllib.parse.parse_qs(url.query)
            if method == "GET":
                self.route_get(path, query)
            else:
                self.route_post(path, query)
        except RequestError as e:
            self.send_json(e.status, {"error": str(e)})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def route_get(self, path, query):
        app = self.app
        if path in ("/", "/index.html"):
            return self.send_bytes(200, app.index_file.read_bytes(), STATIC_TYPES[".html"])
        if path.startswith("/static/"):
            return self.serve_static(path[len("/static/"):])
        if path == "/api/status":
            return self.send_json(200, app.status())
        if path == "/api/documents":
            return self.send_json(200, {"documents": app.documents()})
        if path == "/api/examples":
            def read(name):
                f = app.data_dir / name
                return [l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
            questions = read("questions.txt")
            return self.send_json(200, {"builtin/demo.pdf": {"questions": questions,
                                                            "quick": read("questions_demo.txt") or questions[:3]}})
        if path.startswith("/files/"):
            pdf = app.resolve_doc(urllib.parse.unquote(path[len("/files/"):]))
            return self.send_bytes(200, pdf.read_bytes(), "application/pdf",
                                   {"Content-Disposition": f'inline; filename="{pdf.name}"'})
        if path == "/api/answers":
            doc = (query.get("doc") or [""])[0]
            app.resolve_doc(doc)
            out = app.output_path(doc)
            if not out.is_file():
                raise RequestError("no answers file yet for this document", 404)
            extra = {"Content-Disposition": f'attachment; filename="{out.name}"'} if query.get("download") else None
            return self.send_bytes(200, out.read_bytes(), "text/markdown; charset=utf-8", extra)
        if path == "/api/memory/sessions":
            from src.memory import SessionMemory
            mem = SessionMemory(base_dir=app.workspace / ".sensai")
            return self.send_json(200, {"sessions": mem.list_sessions()})
        raise RequestError("not found", 404)

    def route_post(self, path, query):
        app = self.app
        if path == "/api/upload":
            data = self.read_body(MAX_UPLOAD_BYTES)
            return self.send_json(200, {"document": app.save_upload((query.get("name") or [""])[0], data)})
        if path == "/api/config":
            body = self.read_json()
            if body.get("reset"):
                app.reset_overrides()
            else:
                app.set_overrides(body.get("overrides"))
            return self.send_json(200, {"config": app.config()})
        if path == "/api/run":
            body = self.read_json()
            doc, questions, only = body.get("doc"), body.get("questions"), body.get("only")
            prepare_run(app, doc, questions, only)   # reject a bad request before opening the stream
            return self.stream_job(lambda emit: run_job(app, doc, questions, only, body.get("force"), emit))
        if path == "/api/chat":
            body = self.read_json()
            prepare_chat(app, body.get("messages"), body.get("model"))   # refuse a bad request before streaming
            return self.stream_job(lambda emit: chat_job(app, body.get("messages"), body.get("model"), emit))
        if path == "/api/memory/search":
            body = self.read_json()
            query_str = (body.get("query") or "").strip()
            from src.memory import SessionMemory
            mem = SessionMemory(base_dir=app.workspace / ".sensai", host=app.config()["host"], embed_model=app.config().get("embed_model", "nomic-embed-text"))
            matches = mem.search_memory(query_str, top_k=int(body.get("top_k", 3)))
            return self.send_json(200, {"query": query_str, "results": matches})
        raise RequestError("not found", 404)

    def serve_static(self, name):
        static = self.app.static_dir
        match = next((p for p in static.glob("*") if p.name == name and p.is_file()), None) \
            if "/" not in name and "\\" not in name else None
        if match is None:
            raise RequestError("not found", 404)
        self.send_bytes(200, match.read_bytes(), STATIC_TYPES.get(match.suffix, "application/octet-stream"))


def make_server(app, host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), Handler)
    server.app = app
    server.daemon_threads = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sensai web UI (feature X1).")
    parser.add_argument("--host", default="127.0.0.1", help="interface to listen on (default: loopback only)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--config", default=str(ROOT / "config.json"), help="settings file")
    args = parser.parse_args(argv)
    try:
        config = cli.load_config(args.config)
    except cli.CliError as e:
        sys.exit(f"Error: {e}")
    extra = {args.host} if args.host not in ("127.0.0.1", "localhost", "::1") else set()
    try:
        server = make_server(App(config, allowed_hosts=extra), args.host, args.port)
    except OSError as e:
        sys.exit(f"Error: cannot listen on {args.host}:{args.port} ({e}). Try another --port.")
    if extra:
        print("WARNING: listening on a non-loopback address; the web UI has no login.", file=sys.stderr)
    print(f"Sensai web UI: http://{args.host}:{args.port}   (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
