# Sensai – User Stories

Format: *As a type of user, I want to action, so that outcome*, followed by observable acceptance criteria. At least two stories per feature.

Users: **Student** (prepares exams from course PDFs), **Researcher** (extracts answers from reports and papers).

---

## B1 – CLI chatbot (base)

**US-B1.1** As a student, I want to start the tool with a model name, so that I can use the model that fits my computer.
- `python src/chat.py qwen3:4b` uses that model; with no argument the model in `config.json` is used.
- Switching models needs no code change.

**US-B1.2** As a student, I want clear messages when something is wrong, so that I know how to fix it.
- Empty input is ignored with a hint.
- Ctrl+C during a reply cancels that reply and returns to the prompt; Ctrl+C or Ctrl+D at the prompt quits.
- Ollama not running: message says to run `ollama serve`.
- Model not pulled: message gives the exact `ollama pull <model>` command.
- No traceback in any of these cases.

## R1 – Basic RAG

**US-R1.1** As a student, I want to give the tool a PDF, so that its content becomes searchable.
- Text is extracted per page, chunked with overlap, embedded and stored in a local file.
- Progress is printed while chunks are embedded, then the index location and the number of chunks.
- A second run on the same PDF reuses the saved index (no new embedding) unless `--force` is given.
- A scanned/image-only or unreadable PDF gives a clear error, not a crash.

**US-R1.2** As a student, I want each question answered from the most relevant passages, so that answers are about my document and not general knowledge.
- For each question the top-k chunks by cosine similarity go into the prompt.
- Each chunk keeps its page number.
- A question the PDF does not cover gets an answer saying the document does not cover it.

## T5 – Structured output

**US-T5.1** As a developer, I want the model to answer in a fixed JSON schema (`answer`, `page`, `quote`), so that code can place content reliably.
- The schema is defined in one place in the code.
- A response that violates the schema is rejected and retried (at most 2 retries).

**US-T5.2** As a researcher, I want a failure on one question not to ruin the run, so that I still get the other answers.
- After the retries fail, that question is reported as failed and the file is not modified for it.
- The run continues with the next question.

## M4 – Answers file as a living document

**US-M4.1** As a researcher, I want my questions answered into one Markdown file, so that I get a deliverable and not a chat transcript.
- `answers.md` has one section per question.
- Each section shows the answer, the page number and a short quote.
- The file is readable in any text editor.

**US-M4.2** As a researcher, I want to re-run or add one question without losing the rest, so that I can refine incrementally.
- Re-running question 3 changes only section 3; other sections are byte-for-byte identical (tested).
- A new question appends a new section; `--only N` re-runs just question N.

## Quote check (safeguard)

**US-Q.1** As a student, I want to know which answers are not backed by my document, so that I do not study wrong information.
- The quote must appear in the retrieved text (case and extra spaces ignored).
- If it does not, the section is marked "not supported".
- At the end of the run the tool prints the share of supported answers.

**US-Q.2** As a researcher, I want that summary score, so that I can compare two models or settings.
- The same question list run with two settings (`--config other.json`) gives two comparable scores.

## EV1 – Automated evaluation and hallucination detection

**US-EV1.1** As a student, I want each answer judged against the passages it was built from, so that I can tell which answers I can trust.
- Each section of `answers.md` shows a verdict (`faithful`, `partial` or `unfaithful`) and a one-line reason.
- An answer that says something the passages do not support is marked `unfaithful`.
- The judge sees only the question, the answer and the retrieved passages.

**US-EV1.2** As a researcher, I want a score for the whole run, so that I can compare two settings (chunk size, top-k, model).
- At the end of the run the tool prints the share of `faithful`, `partial` and `unfaithful` answers.
- Running the same questions with two configurations gives two comparable scores.

**US-EV1.3** As a student, I want to see where the quote check and the judge disagree, so that I know which answers to read myself.
- When the quote check says `supported` but the judge says `unfaithful` (or the reverse), the section is flagged for review.

## X1 – Web UI

**US-X1.1** As a student who prefers a browser to a terminal, I want to upload a PDF, write my questions and watch the answers arrive, so that I get a sourced answers file without typing commands.
- I can upload a PDF or choose the demo; a scanned or invalid PDF is refused with a clear message.
- Pressing "Answer all questions" shows indexing progress, then one card per question filling in as its answer arrives.
- Each card shows the answer, the page (a link that opens the PDF at that page), the word-for-word quote, the quote-check badge, the judge's verdict and a "review needed" badge when the checks disagree.
- The answers file is shown on the page and can be downloaded.

**US-X1.2** As a researcher, I want to edit one question and re-run only it, and to stop a long run, so that I can refine incrementally without waiting for everything.
- "Re-run this question" changes only that card and only that section of the answers file; the other sections stay byte-for-byte identical.
- "Stop" cancels the run; answers already written are kept and the interface is usable again at once.
- A failing question is reported on its card and does not stop the others.

**US-X1.3** As a user of the chatbot, I want to see the reply stream and how much of the model's context is used, so that I know when a conversation is getting too long.
- The reply appears word by word, with a thinking indicator while the model reasons.
- A meter shows the tokens used out of the context size (prompt plus reply), and a live count while the reply streams.
- "Stop" cancels the reply cleanly; "New chat" clears the history.

**US-X1.4** As a user, I want to change the models and numbers and to be told clearly when Ollama or a model is missing, so that I can fix a problem without reading logs.
- A status indicator shows whether Ollama is reachable; a banner gives the exact `ollama pull ...` command for a missing model.
- Settings are validated (types and ranges) and apply to the current server session; "Reset" restores `config.json`; the Ollama address cannot be changed from the browser.
- The page and the server answer only on the local machine by default, and refuse requests from other sites.

## General Fallback – Basic Calculations and Inquiries (D6)

**US-GEN.1** As a student or researcher, I want to ask basic math calculations (such as `1 + 1 = 2`), so that the assistant computes the answer directly instead of returning an inappropriate "The document does not cover this." refusal.
- Arithmetic expressions (addition, subtraction, multiplication, division, powers) are detected and evaluated accurately.
- The reply follows the JSON schema with `page: 0` and `quote: ""` without hallucinating passage quotes.
- Mathematical errors such as division by zero are caught and returned with a clear explanation without crashing.

**US-GEN.2** As a user, I want basic conversational greetings and identity queries answered courteously, so that interacting feels natural while keeping document-specific Q&A strictly grounded.
- Common greetings ("hello", "bonjour") and identity inquiries ("who are you?") receive concise, polite responses.
- Document-specific questions continue to be strictly searched in the PDF and backed by page quotes.

## X2 – Branching: Resume & Interrupt (2 ⭐)

**US-X2.1** As a user, I want to edit a previously submitted message in the CLI or Web UI, so that the assistant forks a new branch and generates a fresh answer from that point without corrupting previous history.
- Editing turn 1 in a multi-turn chat truncates subsequent messages and re-runs generation from the edited prompt.
- The previous conversation branch is preserved in an archive without data loss.
- CLI provides `/edit <turn> <text>`, `/history`, `/branches`, and `/switch <branch_id>` commands.

**US-X2.2** As a Web UI user, I want an edit icon on my messages and branch switcher controls, so that I can explore alternative dialogue branches and seamlessly switch back and forth.
- Hovering/focusing a user bubble reveals an edit button.
- Saving updates the conversation state, forks the branch, streams the new response, and displays branch counter navigation (`< N / total >`).
- Clicking branch navigation toggles between branches without page reload.

## M3 – External Structured Memory / Second Brain (2 ⭐)

**US-M3.1** As a student or researcher, I want the assistant to recall facts exchanged in prior conversation sessions, so that I can ask questions referring to earlier discussions without re-entering the entire background.
- Prior conversation sessions are persisted as JSON files in `.sensai/sessions/` and vector-indexed.
- Cross-session recall inquiries ("as we discussed earlier...", "remember when...", "what did we talk about?") trigger semantic retrieval across historical sessions.
- Relevant memories are injected into the context as a formatted prompt block before generation.

**US-M3.2** As a developer or user, I want tools to inspect and search the external memory, so that I can verify stored facts and audit what the assistant remembers.
- CLI commands `/memory` lists archived sessions and `/recall <query>` performs semantic search with similarity scores.
- Server exposes `GET /api/memory/sessions` and `POST /api/memory/search` for web integration.

## Traceability: which tests cover which stories

| Feature | Stories | Automated tests | Manual check |
|---|---|---|---|
| B1 | US-B1.1, US-B1.2 | `tests/test_chat.py` (streaming, history, errors, Ctrl+C, model by argument or config) | `python src/chat.py` |
| R1 | US-R1.1, US-R1.2 | `tests/test_extract_pages.py`, `tests/test_chunk_pages.py`, `tests/test_ingest.py`, `tests/test_m2_store.py`, `tests/test_m3_m4_pipeline.py` | `python -m src.ingestion data/demo.pdf --chunks`; run on `data/demo.pdf` |
| T5 | US-T5.1, US-T5.2 | `tests/test_m3_m4_pipeline.py`, `tests/test_cli.py` | a run where one question fails (see `tests/test_cli.py`) |
| M4 | US-M4.1, US-M4.2 | `tests/test_writer.py`, `tests/test_cli.py` | re-run with `--only N` and `diff` the file |
| Quote check | US-Q.1, US-Q.2 | `tests/test_quote_check.py`, `tests/test_m6_eval_summary.py` | summary printed at the end of a run |
| X1 | US-X1.1, US-X1.2, US-X1.3, US-X1.4 | `tests/test_web_ui.py` (85 tests of the server), `tests/test_ollama_events.py`, `tests/test_ingest.py` (progress callback) | `python WEB-UI/server.py` and the checklist in `docs/TESTING.md`, level F |
| EV1 | US-EV1.1, US-EV1.2, US-EV1.3 | `tests/test_m5_judge.py`, `tests/test_m6_eval_summary.py`, `tests/test_cli.py` | `Judge:` and `Review needed` lines in `answers.md` |
| Fallback (D6) | US-GEN.1, US-GEN.2 | `tests/test_general_fallback.py` (8 unit tests for math, greetings, judge, and pipeline integration) | ask `1 + 1 = combien` or `hello` |
| Branching (X2) | US-X2.1, US-X2.2 | `tests/test_branching.py` (8 unit tests for history truncation, branching, CLI commands, and state preservation) | `/edit` in CLI or edit icon in Web UI |
| Memory (M3) | US-M3.1, US-M3.2 | `tests/test_cross_session_memory.py` (8 unit tests for persistence, indexing, cosine recall, CLI injection, and API endpoints) | `/memory` and `/recall` in CLI or query cross-session facts |



