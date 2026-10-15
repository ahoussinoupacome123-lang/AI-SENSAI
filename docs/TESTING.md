# Testing guide

Everything you can run to check Sensai, from a one-second automated check to a full scored run on the real models. Each test says what to run, what you should see, and what it proves. The expected outputs below were produced on the project machine (CPU only, `qwen3:4b`); your wording and timings may differ slightly.

| Level | What | Needs Ollama | Time |
|---|---|---|---|
| **A. Automated tests** | 329 pytest tests | no | about 1 s |
| **B. Manual checks without a model** | inspect a PDF, error messages, demo data, scoring a saved run | no | seconds |
| **C. Manual checks with Ollama** | chatbot, short demo, full run, re-running one question, settings | yes | 30 s to 7 min |
| **D. Failure tests** | server down, corrupt index, scanned PDF, wrong inputs | mostly no | seconds |
| **E. Quality evaluation** | score a run against known answers, compare settings | yes | 5 to 7 min |
| **F. Web UI** | the browser interface (feature X1) | yes, except the security checks | 5 to 10 min |

## 0. Before you start

```bash
cd AI-SENSAI
source .venv/bin/activate            # the environment from the README
```
For levels C and E, Ollama must be running with both models:
```bash
ollama serve > ~/ollama.log 2>&1 &
curl http://localhost:11434          # must print: Ollama is running
ollama list                          # must list qwen3:4b and nomic-embed-text
```
The commands below use the committed settings (`chunk_size` 800, `chunk_overlap` 150). If you changed `config.json`, some counts (such as the number of chunks) will differ.

---

## A. Automated tests (no Ollama, about 1 second)

```bash
python -m pytest -q                  # expected: 329 passed
python -m pytest -q tests/test_writer.py        # one file
python -m pytest -q -k quote                    # tests whose name contains "quote"
python -m pytest -x -q                          # stop at the first failure
python -m pytest -v tests/test_cli.py           # list every test name
```
They never call Ollama: the model client and the store are replaced by fakes, and test PDFs are built on the fly by `tests/pdf_factory.py`.

| Test file | Tests | What it covers | Feature / stories |
|---|---|---|---|
| `test_chat.py` | 23 | streaming, history sent every turn, empty input, errors (server down, missing model, timeout), Ctrl+C, model from argument or config | B1 |
| `test_extract_pages.py` | 10 | text per page, page numbers, blank pages, scanned PDF, missing file, not a PDF, truncated PDF | R1 |
| `test_chunk_pages.py` | 22 | chunk size, exact overlap, page numbers, nothing lost, invalid settings | R1 |
| `test_ingest.py` | 21 | embedding in batches, index next to the PDF, reuse, `--force`, stale index, corrupt or invalid index, no partial index on failure, progress callback | R1 |
| `test_m1_ollama_client.py` | 9 | chat, JSON schema, embeddings, clear errors | B1, T5 |
| `test_m2_store.py` | 9 | save/load, cosine ranking, empty index, zero vectors | R1 |
| `test_m3_m4_pipeline.py` | 18 | prompt building, top-k, JSON validation, retries, `AnswerError` | R1, T5 |
| `test_quote_check.py` | 22 | exact, case, spaces, curly quotes, dashes, ligatures, empty quote, stitched quote | EV1 |
| `test_m5_judge.py` | 12 | verdict parsing, `unknown` after a bad verdict, prompt content | EV1 |
| `test_m6_eval_summary.py` | 9 | counts, percentages, disagreement list, empty run | EV1 |
| `test_writer.py` | 32 | one section per question, only that section changes (hashes), order, hand-edited text kept, atomic write, file permissions, failed answers refused | M4 |
| `test_cli.py` | 32 | wiring, failed question does not stop the run, `--only`, `--force`, input errors, judge optional, disagreement flag, Ctrl+C, exit codes | all |
| `test_integration_fixes.py` | 4 | schema mode turns thinking off, retrieved chunks reach the judge, judge schema order | T5, EV1 |
| `test_ollama_events.py` | 10 | the streaming chat events with token usage, early close, model list, errors (used by the web UI) | X1 |
| `test_web_ui.py` | 85 | the web server over real HTTP with a faked model: routes, traversal, Host/Origin checks, uploads, serving PDFs, settings validation, a streamed run, `only`, errors, the one-job lock, disconnects, chat | X1 |
| `test_e2e_check.py` | 8 | the scoring script (pass, fail, missing section, thresholds) | quality |

The traceability from user stories to tests is at the end of [USER_STORIES.md](USER_STORIES.md).

---

## B. Manual checks without a model

**B1. Inspect a PDF page by page**
```bash
python -m src.ingestion data/demo.pdf
```
Expect 24 lines such as `page   1:  1566 chars | Chapter 1 - Introduction to computer networks A computer network is a ...`. Words must have spaces between them (a PDF whose text comes out as `Whatisexpected` will retrieve badly).

**B2. See how it is cut into chunks**
```bash
python -m src.ingestion data/demo.pdf --chunks
```
Expect `59 chunks (size 800, overlap 150)` followed by the first few chunks, none longer than 800 characters.

**B3. Check the demo data is consistent**
```bash
python scripts/build_demo_pdf.py
```
Expect `RESULT: OK` after one `Qn: page P ... ok` line per question. It rebuilds `data/demo.pdf` and proves that every expected quote is on exactly the stated page and that the question not covered really is not covered.

**B4. Score a saved run (no Ollama needed)**
```bash
python scripts/e2e_check.py docs/examples/answers_demo.md data/expected_answers.md
```
Expect a table and `covered questions: right page 6/8 ...`, `uncovered questions: refused 1/1`, `RESULT: PASS`.

**B5. Try the answers-file writer on its own**
```bash
python - <<'PY'
from src.writer import upsert_section
make = lambda n, a: dict(question=f"Q number {n}?", answer=a, page=n + 1, quote=f"quote {n}",
                         status="supported", verdict="faithful", reason="ok")
for n in (1, 2, 3):
    upsert_section("/tmp/answers_demo.md", n, make(n, f"Answer {n}."))
PY
cp /tmp/answers_demo.md /tmp/before.md
python - <<'PY'
from src.writer import upsert_section
upsert_section("/tmp/answers_demo.md", 2, dict(question="Q number 2?", answer="A DIFFERENT answer.",
               page=9, quote="new quote", status="supported", verdict="partial", reason="half"))
PY
diff /tmp/before.md /tmp/answers_demo.md
```
Expect the diff to list only lines inside section 2.

**B6. Input errors (each must print one clear `Error:` line, no traceback)**

| Command | Expected |
|---|---|
| `python -m src.cli nope.pdf data/questions.txt` | `Error: PDF not found: nope.pdf` |
| `python -m src.cli data/demo.pdf nope.txt` | `Error: questions file not found: nope.txt` |
| `python -m src.cli data/demo.pdf <an empty file>` | `Error: no questions found in ... (write one question per line)` |
| `python -m src.cli data/demo.pdf data/questions_demo.txt --only 9` | `Error: --only 9 is out of range: the file has 3 questions` |
| `python -m src.cli data/demo.pdf data/questions_demo.txt --config nope.json` | `Error: config file not found: nope.json` |
| `python -m src.cli README.md data/questions.txt` | `Error: README.md is not a PDF file.` |
| `python -m src.cli <a scanned PDF> data/questions.txt` | `Error: ... has no extractable text (probably scanned images). Only text PDFs are supported.` |

To make a scanned-style PDF to try: `python -c "import sys; sys.path.insert(0,'tests'); from pdf_factory import make_blank_pdf; make_blank_pdf('/tmp/scan.pdf')"`.

---

## C. Manual checks with Ollama

**C1. The chatbot (feature B1)**
```bash
python src/chat.py
```

| # | Do this | Expected |
|---|---|---|
| 1 | `Explain in 4 sentences what a vector is.` | `(thinking...)` for about 10 s, then the answer appears word by word |
| 2 | `My name is Sam. Reply in one short sentence.` then `What is my name?` | the second answer says Sam (history works) |
| 3 | press Enter on an empty line | `(empty input, please type something)`, no crash |
| 4 | ask something long, press Ctrl+C after `(thinking...)` | `(reply cancelled)`, no traceback, the chat still works |
| 5 | at the empty prompt press Ctrl+C or Ctrl+D, or type `exit` | the program quits cleanly |
| 6 | `python src/chat.py nomodel-xyz`, type `hi` | `Error: Model 'nomodel-xyz' not found. Pull it with: ollama pull nomodel-xyz` |
| 7 | run `python src/chat.py qwen3:4b` | the first line says `Chatting with qwen3:4b.` |
| 8 | stop Ollama (`pkill ollama`), type `hi` | `Error: Cannot reach Ollama at http://localhost:11434. Start it with: ollama serve`; restart the server and the chat works again |

Do not type while the model is answering: the input is queued and becomes the next question.

**C2. The short demo (3 questions, about 30 seconds)**
```bash
python -m src.cli data/demo.pdf data/questions_demo.txt
```
Expect the ingestion progress (`Embedded 16/59 chunks` ... `Index saved: data/demo.index.json (59 chunks)`), then for each question one line such as `supported, page 13, judge: faithful`. The third question (who invented the Web) is not in the PDF: expect `not supported, page 0` and the answer `The document does not cover this.` in `data/answers.md`. The run ends with a summary (`Done: 3/3 questions answered, 0 failed`, the quote-check and judge counts, and a `Review needed` list if the two checks disagree).

**C3. Open the result**
```bash
cat data/answers.md
```
One section per question with the answer, page, quote, quote check and judge verdict. Open `data/demo.pdf` at the stated page and find the quote: that is the point of the tool.

**C4. The index is reused**
Run C2 again. Expect `Index found: data/demo.index.json (rebuild with --force)` and no `Embedded ...` lines (no new embedding).

**C5. Rebuild the index**
```bash
python -m src.cli data/demo.pdf data/questions_demo.txt --force
```
Expect the `Embedded ...` lines again. Needed after changing `chunk_size` or `chunk_overlap`.

**C6. Re-run one question: only its section changes (feature M4)**
```bash
cp data/answers.md /tmp/before.md
sed 's/maximum payload size of an Ethernet frame/largest payload an Ethernet frame can carry/' data/questions_demo.txt > /tmp/q.txt
python -m src.cli data/demo.pdf /tmp/q.txt --only 2
diff /tmp/before.md data/answers.md
```
Expect `[1/1] Q2: ...` and a diff that touches only section 2 (measured: a single changed line, the section heading). Re-running the *same* question gives an identical section, because the model runs at temperature 0, so reword it to see a change.

**C7. Interrupt a run**
Start the full run (C8) and press Ctrl+C during a question. Expect `Interrupted: answers written so far are kept.` and exit code 130; the sections already written stay in the file. (Covered by `test_cli.py`; try it by hand.)

**C8. The full run on the demo (9 questions, 5 to 7 minutes)**
```bash
python -m src.cli data/demo.pdf data/questions.txt
```
Measured: 5 min 31 s and 6 min 42 s in two clean runs. Expect `Done: 9/9 questions answered, 0 failed` and a summary close to: quote check 6 supported and 3 not supported, judge 8 faithful and 1 unfaithful, 2 answers flagged for review. See E1 for the scoring.

**C9. Your own PDF**
```bash
printf 'What is the main topic?\nWho wrote it?\n' > /tmp/my_questions.txt
python -m src.cli path/to/your.pdf /tmp/my_questions.txt
```
Text PDFs only. Check the words have spaces with `python -m src.ingestion your.pdf`.

**C10. Check the models directly (optional)**
```bash
python - <<'PY'
import json
from src import ollama_client
cfg = json.load(open("config.json"))
print(len(ollama_client.embed(["a", "b"], cfg["embed_model"])[0]))                       # 768
print(ollama_client.chat([{"role": "user", "content": "Give a city and the number 3."}],
      cfg["chat_model"], schema={"type": "object", "properties": {"city": {"type": "string"},
      "n": {"type": "integer"}}, "required": ["city", "n"]}))                                # a dict
PY
```

---

## D. Failure tests

| # | How to cause it | Expected | Checked |
|---|---|---|---|
| D1 | stop Ollama (`pkill ollama`), then run C2 with an existing index | every question prints `failed: Cannot reach Ollama. Start it with: ollama serve`, the run continues, summary says `0/3 questions answered, 3 failed`, **no answers file is created**, exit code 1 | run by hand |
| D2 | corrupt the index: `echo "{ not json" > data/demo.index.json`, run C2 | `Error: The saved index ... cannot be read (...). Rebuild it with --force.` Then `--force` rebuilds it | run by hand, and `test_ingest.py` |
| D3 | an index file that is valid JSON but the wrong shape (`{}`, `[]`) | `Error: The saved index ... is not a valid index. Rebuild it with --force.` | `test_ingest.py` |
| D4 | a scanned PDF | `Error: ... has no extractable text (probably scanned images)` | run by hand, and `test_extract_pages.py` |
| D5 | a model that is not pulled (set `chat_model` to `nomodel-xyz`) | each question fails with `Model 'nomodel-xyz' not found. Pull it with: ollama pull nomodel-xyz` | `test_m1_ollama_client.py`, `test_chat.py` |
| D6 | the model returns invalid JSON | retried twice, then that question fails and **its section is not written**; the other questions are written | `test_m3_m4_pipeline.py`, `test_cli.py` |
| D7 | kill the process (`kill -9`) while it writes | the old `answers.md` is intact (the writer saves to a temporary file and renames it) | `test_writer.py` (forced failure while writing) |
| D8 | the judge fails or is missing | the answers are kept; the judge line says `unknown` or `not evaluated` | `test_cli.py` |
| D9 | a question the PDF does not cover | the answer is `The document does not cover this.`, no quote | C2, C8 |

---

## E. Quality evaluation

**E1. Score a run against the known answers**
```bash
python scripts/e2e_check.py data/answers.md data/expected_answers.md
```
For each covered question it checks the page and that the key phrase is in the quote; for the uncovered question it checks that the answer is a refusal. It exits 0 (`RESULT: PASS`) when at least 70 % of the covered questions cite the right page and every uncovered question is refused. Measured on the demo: **right page 6/8, refusal 1/1, PASS**. The two misses are wrong refusals (the model said the document does not cover a fact that is in the retrieved passages); see [RESULTS.md](RESULTS.md).

**E2. Compare two settings**
```bash
cp config.json /tmp/other.json            # edit chunk_size, top_k, chat_model ... in the copy
python -m src.cli data/demo.pdf data/questions.txt --config /tmp/other.json --force --output /tmp/other_answers.md
python scripts/e2e_check.py /tmp/other_answers.md data/expected_answers.md
```
Compare the score and the summary with the baseline. Use `--force` whenever the chunk settings change, otherwise the old index is reused.

**E3. Add your own scored test set**
Write a questions file (one per line) and an expected file in the format `number | page P | key phrase` (or `number | none |` for a question the document does not cover), then run E1. Keep at least one uncovered question: it tests that the system does not invent.

**What "good" looks like:** valid output for every question, the right page in the retrieved chunks, no invented answer, and a score at or above the baseline in `RESULTS.md`. A change to a prompt or to a schema must be measured this way before it is merged.

---

## F. Web UI (feature X1)

Start it and open the page. The server tests (`tests/test_web_ui.py`) cover the server; these checks cover what you see.
```bash
python WEB-UI/server.py            # http://127.0.0.1:8000
```

| # | Do this | Expected |
|---|---|---|
| F1 | open the page | a ChatGPT-style screen: sidebar (New chat, history, Settings), the greeting `What can I help with?`, the composer mid-screen, suggestion pills below it; the top shows `Ollama ready qwen3:4b` |
| F2 | stop Ollama (`pkill ollama`), reload | the dot turns red (`Ollama not reachable`) and a banner shows `Start it with: ollama serve`; restart Ollama and reload |
| F3 | `+` then *Upload a PDF*: a scanned PDF (see B6 to make one) | `Upload failed: ... has no extractable text (probably scanned images)` |
| F4 | upload a valid text PDF (or drag one onto the page) | `<name> is ready (N pages)`; a chip with the name and page count appears in the composer; the x removes it |
| F5 | click *Try the demo PDF* (or attach `demo.pdf` and type questions, one per line) | your message appears on the right; the reply shows a live status and one block per question that fills in: answer, `page N` button, quote, quote-check and judge badges; then a summary with *Download answers.md* and *View answers.md* |
| F6 | click a `page 13` button | a side panel opens with the PDF at that page (Escape closes it and focus returns to the button; *Open in a new tab* is offered) |
| F7 | *Edit and re-run* on question 2, change the text, *Re-run this question* | only block 2 changes; in *View answers.md* only section 2 changes |
| F8 | press the square *Stop* button during a run | `Stopped. Answers already written are kept.`; Send is back at once |
| F9 | *New chat*, send `Reply with exactly three words.` | `Thinking...`, then the reply streams; under the composer the meter shows `N / 4,096 tokens` (the count includes the model's hidden thinking tokens) |
| F10 | send a second message that refers to the first; press *Stop* during another reply | the history is used; Stop keeps the partial text; the chat still works |
| F11 | *Settings* (sidebar or the model button): set `top_k` to 99 | `'top_k' must be between 1 and 20`; set it to 3 and *Apply*, then *Reset*; Escape closes the dialog |
| F12 | start a run, then send a message from a second browser tab | `Another run or chat is in progress. Wait for it to finish.` |
| F13 | *Theme* in the sidebar, reload | light and dark both stay readable; the choice is remembered |
| F14 | after a run, click the *Needs review* tile (if any) | only the blocks that need review stay visible; click again to show all |
| F15 | narrow the window to phone width | the sidebar hides behind a menu button (it slides over a dimmed page); nothing scrolls sideways |
| F16 | reload the page; open an older chat in the sidebar; delete one with the bin icon | chats are kept in this browser (not on the server); an old PDF chat shows its answers again |

Security checks (no model needed; the port is 8000 by default):
```bash
curl -s -o /dev/null -w "%{http_code}
" -H "Host: evil.example.com" http://127.0.0.1:8000/api/status   # 403
curl -s -o /dev/null -w "%{http_code}
" "http://127.0.0.1:8000/static/..%2Fserver.py"                     # 404
curl -s -o /dev/null -w "%{http_code}
" "http://127.0.0.1:8000/files/upload/..%2Fserver.py"               # 404
curl -s -o /dev/null -w "%{http_code}
" -X POST -H "Origin: http://evil.example.com" -H "Content-Type: application/json" -d '{"reset":true}' http://127.0.0.1:8000/api/config   # 403
```
The page is also checked automatically in a real browser (headless Chromium) with `WEB-UI/e2e/ui_check.py`: 61 checks covering F1 to F16, accessibility basics, reduced motion and the phone layout, plus a real demo run and a real chat reply (about 5 minutes with the models; `--quick` skips those). It needs Playwright, which is not in `requirements.txt`:
```bash
pip install playwright && playwright install chromium
python WEB-UI/server.py &
python WEB-UI/e2e/ui_check.py --shots /tmp/shots       # 61/61 expected
```
F1 to F16 are still worth repeating by eye once.

---

## Test data

| File | Content |
|---|---|
| `data/demo.pdf` | 24-page demo course on networks (built from `data/demo_course.txt` by `scripts/build_demo_pdf.py`) |
| `data/questions.txt` | 9 questions (8 covered, 1 not) |
| `data/questions_demo.txt` | 3 questions for the short demo |
| `data/expected_answers.md` | expected page and key phrase per question |
| `docs/examples/answers_demo.md` | the real result of a full run |
| `docs/examples/demo_run.txt` | the real terminal output of that run, with timings |

Generated files (`data/answers.md`, `data/*.index.json`) are git-ignored.

## When something fails

| Symptom | Likely cause |
|---|---|
| tests fail with `ModuleNotFoundError` | the environment is not activated, or `pip install -r requirements.txt` was not run |
| a manual check hangs for a long time | Ollama is overloaded or swapping: close other programs, check `free -h`; the first question also loads the model |
| `Cannot reach Ollama` | `ollama serve > ~/ollama.log 2>&1 &`, then `curl http://localhost:11434` |
| `answers.md` was not updated | the answers file is written **next to the PDF** unless you pass `--output`: the first line of a run says `Answers will be written to ...`. Running on `Sensai_project.pdf` in the repo root writes `./answers.md`, not `data/answers.md` |
| the score differs from the documented one | different `config.json` (check `chunk_size`), a different model, or a stale index: run with `--force` |
| answers differ between two runs | they should not (temperature 0); a changed prompt, setting or model is the usual reason |

Adding a test: see [CONTRIBUTING.md](../CONTRIBUTING.md).
