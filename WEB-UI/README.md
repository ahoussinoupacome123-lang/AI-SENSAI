# WEB-UI: the Sensai web interface (feature X1)

A browser front end for Sensai. It does the same work as `python -m src.cli` (answer a list of questions about a PDF and write a sourced `answers.md`) and as `python src/chat.py` (the plain chatbot), with a page instead of a terminal. Everything still runs on your computer through Ollama.

```bash
python WEB-UI/server.py            # then open http://127.0.0.1:8000
```

The catalogue describes X1 as "a decoupled web frontend over the CLI backend: message input, streaming conversation display, live token/context usage, basic agent switching, configuration... The backend logic stays unchanged." Here is how each part is met:

| X1 requirement | In this UI |
|---|---|
| Message input | one composer: a message to the model, or questions about an attached PDF |
| Streaming conversation display | chat replies and PDF answers appear as they are produced; a "Thinking..." indicator shows while the model reasons |
| Live token / context usage | a meter under the composer: tokens used out of the context size (prompt + reply), and a live count while a reply streams |
| Basic agent switching | attaching a PDF switches the conversation from plain chat to document answers; change the chat and judge model in Settings. There are no personas (that is a different catalogue feature, A5), so we do not claim them |
| Configuration | a Settings dialog: models, top-k, chunk size and overlap, context size, retries, and three **feature switches** (Retrieval, Judge, Quote check) to turn a part of the pipeline off, for the current server session |
| Backend logic unchanged | the UI calls the same modules as the CLI. Two small additive hooks were added (see "Relation to the backend"); no existing behaviour changed and all earlier tests still pass |

## What you can do

The interface follows the layout people know from ChatGPT: a sidebar (New chat, your chats, Settings), a single conversation column, and a rounded composer at the bottom. Your chats are kept in this browser only; the server stores nothing about them.

**Chat**: type in the composer and press Enter (Shift+Enter for a new line). The reply streams with a "Thinking..." indicator while the model reasons, and Markdown (lists, tables, code) is rendered safely. **Stop** (the square button) ends the reply and keeps the text so far. **Interrupt and redirect (X2):** while a reply streams you can simply type a new message and press Enter: the reply stops, its text so far is kept (marked "Stopped"), and your message is sent straight after, so it steers the model. **Edit and branch (X2):** the pencil under one of your messages lets you rewrite it; the conversation forks from there, and `‹ 1 / 2 ›` switches between the versions. The context meter under the composer shows tokens used out of the window.

**Ask a PDF**: press **+** and upload a PDF (or drop one on the page), or choose the demo document. A chip in the composer shows what is attached. Then write one question per line and send. The reply is one block per question as it arrives: the answer, a **page** button that opens the PDF at that page in a side panel, the word-for-word **quote**, the quote-check badge, the judge's verdict, and a **Review needed** note only when something really needs a second look (a correct "not in the document" answer stays calm). A summary follows, with **Download answers.md** and **View answers.md**; the *Needs review* tile filters the blocks. **Edit and re-run** on a block changes only that question and only that section of `answers.md` (the living-document feature, M4). *Try the demo PDF* on the start screen does all this in one click.

**Settings** (sidebar or the model button at the top): change models or numbers for this server session; **Reset** returns to `config.json`. Changing the chunk settings or the embedding model turns on "Rebuild the PDF index". The Ollama address cannot be changed from the browser.

**Look and feel**: light and dark themes (Theme in the sidebar, remembered), subtle motion that switches off for `prefers-reduced-motion`, and on a phone the sidebar slides over the page.

## Running it

Same environment as the rest of the project (see the main README): Python 3.10+, the packages in `requirements.txt`, Ollama running with `qwen3:4b` and `nomic-embed-text`. No extra dependency: the server uses only the Python standard library, and the page is plain HTML, CSS and JavaScript with no build step.

```bash
source .venv/bin/activate
ollama serve > ~/ollama.log 2>&1 &
python WEB-UI/server.py                       # http://127.0.0.1:8000
python WEB-UI/server.py --port 9000           # another port
python WEB-UI/server.py --config /tmp/my.json # another settings file
```
The coloured pill at the top shows whether Ollama is reachable; a banner tells you the exact `ollama pull ...` command if a model is missing. Only one job (a run or a chat) can be active at a time, because Ollama processes one request at a time on a laptop; a second request gets a clear "in progress" message.

## Sharing your running page with a partner

By default the server answers only to `localhost`. To let someone else use **your** running instance (they use your computer's Ollama), start it with a key and give the tunnel's hostname:

```bash
python WEB-UI/server.py --key auto --allow-host <hostname-the-tunnel-gives-you>
```
`--key auto` prints a random access key. Send your partner `https://<tunnel-hostname>/?key=<key>`: opening it once sets a cookie, then the page works as normal. Without the key every request gets `401`.

A tunnel needs no router changes. Two options without any account:
```bash
ssh -R 80:localhost:8000 nokey@localhost.run          # prints an https://....lhr.life address
cloudflared tunnel --url http://localhost:8000        # prints an https://....trycloudflare.com address (needs cloudflared installed)
```
Restart the server with the printed hostname in `--allow-host` (the address only exists once the tunnel is up).

What to expect: one job at a time (if you ask a question while your partner's run is going, you get "Another run or chat is in progress"); chats are kept in each person's own browser; settings changes are shared; uploaded PDFs are stored on your computer. Stop the tunnel and the server when you are done. Never share the link without `--key`: the page has no login of its own.

## UX principles applied
Visible system status (the Ollama pill, progress with elapsed time, a live token meter); user control (Stop, edit and re-run one question); error prevention and recovery (validation before a run starts, clear messages, retry); recognition over recall (examples, suggestion chips, labelled settings with units); accessibility (labels, roles, keyboard focus, `aria-live`, contrast, 44 px touch targets on phones, reduced motion); and an explicit message when the HTML file is opened directly instead of through the server.

## Testing
`pytest tests/test_web_ui.py` (88 tests, real HTTP, faked model) covers the server. `WEB-UI/e2e/ui_check.py` drives the page in a real browser (see `docs/TESTING.md`, section F).

## How it works

```
 browser (WEB-UI/index.html, WEB-UI/static: style.css, app.js)
      |  JSON requests, and Server-Sent Events for anything that streams
      v
 WEB-UI/server.py  (standard library http.server)
      |  calls, in the same process
      v
 src/ingestion, pipeline, judge, writer, cli.answer_question, ollama_client
      |
      v
 Ollama (localhost:11434)
```
`run_job` and `chat_job` in `server.py` are plain functions that report through an `emit(event, data)` callback, so they are tested without HTTP. They follow the same steps as the CLI loop: ingest, then for each question `cli.answer_question` (retrieve, answer, quote check, judge) and `writer.upsert_section`. A failing question never stops the run.

### Relation to the backend (what was added to `src/`)
- `ollama_client.chat_events(...)`: a generator for streaming chat that also returns the token counts Ollama reports (`prompt_eval_count`, `eval_count`). It closes the connection when the generator is closed, so Stop really stops generation. The reply count includes the model's hidden thinking tokens.
- `ollama_client.list_models(...)`: lists installed models for the status pill.
- `ingestion.ingest(..., progress=callback)`: an optional callback instead of `print`, for the progress bar. Without it, the CLI output is unchanged.

### API

| Request | Purpose |
|---|---|
| `GET /` and `/static/<file>` | the page and its assets (a fixed list; no path traversal) |
| `GET /api/status` | Ollama reachable, installed and missing models, effective and default settings, whether a job is running |
| `GET /api/documents` | the demo and uploaded PDFs: pages, indexed, has an answers file |
| `GET /api/examples` | example questions per built-in document: `{questions: [...9], quick: [...3]}` |
| `POST /api/upload?name=x.pdf` | raw PDF body (up to 50 MB); checked for extractable text before it is stored |
| `GET /files/<builtin\|upload>/<name>` | a PDF, inline (the page links use `#page=N`) |
| `POST /api/run` | `{doc, questions, only?, force?}`; streams events `start`, `ingest`, `question_start`, `question_done`, `question_failed`, `summary`, `done`, `error` |
| `POST /api/chat` | `{messages, model?}`; streams `thinking`, `token`, `done` (with usage), `error` |
| `GET /api/answers?doc=...[&download=1]` | the Markdown answers file |
| `POST /api/config` | `{overrides}` or `{reset: true}`; validated; session only |

Bad requests are refused with a JSON `{"error": ...}` and the right status code before any stream opens (400 invalid, 404 unknown, 409 busy, 413 too large). A browser that leaves or presses Stop closes the connection, which stops the job and frees the lock.

## Security

It is a local tool and it has no login, so:
- It listens on `127.0.0.1` only by default; `--host` with another address prints a warning.
- It refuses requests addressed to another `Host` (DNS rebinding) and cross-site `Origin`s on POST (CSRF).
- Uploads: PDF only, 50 MB maximum, the name is reduced to safe characters and stays inside `WEB-UI/workspace/uploads/`. Documents are referenced by an id (`builtin/demo.pdf`, `upload/<name>`), never by a path.
- Text from a document or from the model is inserted with `textContent`, never as HTML, so a hostile PDF cannot inject script into the page.
- Settings are validated (types, ranges, model-name characters) and cannot change the Ollama address.
- Nothing leaves the machine: the only outgoing connection is to your local Ollama.

## Files

| Path | Content |
|---|---|
| `server.py` | the server, the two jobs, validation |
| `static/index.html`, `style.css`, `app.js` | the interface |
| `workspace/` | created on first run: `uploads/`, `outputs/` (answers files), git-ignored. Indexes sit next to their PDF. |
| `../tests/test_web_ui.py` | 85 automated tests of the server (real HTTP, faked model) |

## Tests and how the page was checked

```bash
python -m pytest -q tests/test_web_ui.py      # 85 tests, about 3 s, no Ollama needed
```
They cover: the routes and static files (including traversal attempts), the Host and Origin checks, status with Ollama up and down, uploads (valid, scanned, not a PDF, too large, hostile names), serving PDFs, settings validation, a full run (event order, failures, `only`, index reuse, errors, bad requests), the single-job lock, closing the connection mid-run and mid-chat, and chat (events, history, model and context size, errors, bad input).

The JavaScript was run against the live server in a simulated DOM (jsdom) with the real models: boot, settings, chat with the token meter, a PDF run with cards, page links and the answers file, editing and re-running one question, uploads, and Stop. **It has not been opened in a real browser**, so check the layout visually once and report anything odd. See [../docs/TESTING.md](../docs/TESTING.md) for the manual checklist.

## Limits

- One job at a time; no login (do not expose it to a network); one PDF at a time.
- Chats are kept in this browser (localStorage, up to 40) and never sent to a server; clearing site data removes them.
- A single model call (a question's answer, a judge verdict) shows no sub-progress: expect 25 to 90 seconds per question on a CPU.
- Text PDFs only. Two people using the same server share its settings and its workspace.
- No automatic reload of a changed `config.json`: restart the server.

## Troubleshooting

| Symptom | Fix |
|---|---|
| the pill says "Ollama not reachable" | `ollama serve > ~/ollama.log 2>&1 &`, then reload the page |
| a banner lists missing models | run the `ollama pull ...` command it shows |
| `Error: cannot listen on 127.0.0.1:8000` | the port is taken: use `--port 8001` |
| "Another run or chat is in progress" | wait for it, or press Stop in the other tab |
| answers look old after changing chunk settings | tick "Rebuild the index" (Settings does it for you) |
| a changed `config.json` is ignored | restart the server |
