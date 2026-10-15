# Sensai – Architecture (simplified)

How the code is split into files, what each file does, and what goes in and out. Vocabulary is explained in `EXPLANATION.md`; a plain-language walkthrough of this document is in `ARCHITECTURE_EXPLAINED.md`. All model calls go straight to the Ollama HTTP API with `requests` (no LLM framework).

---

## 1. Overview

```
 questions.txt ──► ┌──────────────────┐ ◄── config.json, prompts/
                   │ cli.py           │
                   │ (wires, summary) │
                   └───┬─────────┬────┘
        ingest once    │         │   for each question
                       ▼         ▼
            ┌──────────────┐  ┌──────────────────────┐   ┌───────────┐
 report.pdf►│ ingestion.py │  │ pipeline.py          │──►│ writer.py │──► answers.md
            │ chunk + embed│  │ retrieve, prompt,    │   └───────────┘
            └──────┬───────┘  │ JSON, retry, quote   │
                   ▼          │ check                │
            ┌──────────────┐  └────┬─────────────────┘
            │ store.py     │◄──────┘ (search top-k)
            │ index.json   │
            └──────────────┘
         everything that calls a model goes through ollama_client.py ──► localhost:11434
```

## 2. Files and responsibilities

| File | One job | In → Out |
|---|---|---|
| `ollama_client.py` | The only place that talks HTTP to Ollama: chat (streaming or not, optional JSON schema) and embeddings. In schema mode it sends `think=false` and temperature 0. Raises `OllamaError` with clear messages (no connection, model missing, timeout). | messages/texts → text / dict / vectors |
| `ingestion.py` | Extract text per page from the PDF (`extract_pages`), cut into overlapping chunks keeping the page number (`chunk_pages`), get embeddings in batches, save the index next to the PDF (`ingest`). Detect PDFs with no text. | PDF path → chunk records |
| `store.py` | Save and load chunks + vectors in `index.json`; `search(vector, k)` with cosine similarity (numpy). | chunks ↔ top-k results |
| `pipeline.py` | For one question: embed, search the top-k chunks (`retrieve_and_answer`), build the prompt, ask for JSON (`answer`), validate, retry, run the quote check. | question → `Checked` answer (with the retrieved `chunks`) |
| `judge.py` | EV1: second model call that compares an answer with the retrieved passages and returns a verdict (`faithful` / `partial` / `unfaithful`) plus a one-line reason, using `prompts/judge_prompt.txt`. | question + answer + chunks → verdict |
| `eval_summary.py` | Run summary: quote-check and judge counts, and the answers where the two disagree. | list of `Checked` → text, disagreements |
| `writer.py` | Own `answers.md`. Update exactly one section per question (found by invisible markers), leave the rest untouched, insert in numeric order if missing, write atomically. | checked answer → file |
| `cli.py` | Read args and config, ingest once, loop over questions (`pipeline` → `judge` → `writer`), print the summary. Only wires; no logic. A failed question never stops the run. | args → calls the others |
| `WEB-UI/` | X1: a browser front end. `server.py` (standard library) calls the same modules as the CLI and streams progress as Server-Sent Events; `static/` holds the page. See `WEB-UI/README.md`. | HTTP requests → JSON / event streams |
| `scripts/` | `e2e_check.py` scores a run against an expected-answers file; `build_demo_pdf.py` builds and verifies the demo PDF. Not part of the product. | – |
| `config.json`, `prompts/` | Settings (models, host, chunk size, overlap, top-k) and prompt text, kept out of the code. | – |

## 3. Data shapes (agree on these before coding)

```
Chunk    = { id, text, page, vector }
Answer   = { question, answer, page, quote }          # exactly the JSON schema
Checked  = Answer + { status: "supported" | "not supported", chunks, verdict, reason, disagreement }

client.chat(messages, model, schema=None, stream=False, host=..., num_ctx=...) -> str | dict
client.embed(texts, model, host=...)                    -> list[list[float]]
client.chat_events(messages, model, host=..., num_ctx=...) -> generator of {thinking | token | done(usage)}   # for the web UI
client.list_models(host=...)                            -> list[str]                                       # for the web UI
ingestion.extract_pages(pdf_path)                       -> [(page, text)]
ingestion.chunk_pages(pages, size, overlap)             -> [{text, page}]
ingestion.ingest(pdf_path, config, force=False, progress=None) -> list[Chunk]   # also saves <pdf>.index.json; progress(dict) replaces print
store.save(chunks, path) ; store.load(path)             -> None ; list[Chunk]
store.search(chunks, vector, k)                         -> list[Chunk]
pipeline.retrieve_and_answer(question, index_chunks, config) -> Checked   # embeds, searches, answers
pipeline.answer(question, chunks, config)               -> Checked        # chunks already retrieved
judge.evaluate(question, answer, chunks, config)        -> { verdict, reason }
writer.upsert_section(path, index, checked)             -> None           # raises WriterError on a bad answer
eval_summary.summarize(checked_list)                    -> (text, disagreements)
```

## 4. Repository layout

```
sensai/
├── README.md
├── requirements.txt        # requests, numpy, a PDF library
├── config.json
├── prompts/                # system prompt, answer prompt
├── src/ chat.py  ollama_client.py  ingestion.py  store.py  pipeline.py  judge.py  eval_summary.py  writer.py  cli.py
├── WEB-UI/                 # X1: server.py + static/ (the web interface)
├── scripts/                # e2e_check.py, build_demo_pdf.py
├── tests/
├── docs/                   # these documents
└── data/                   # sample PDF, questions.txt, answers.md
```

## 5. Risks

| Risk | Mitigation |
|---|---|
| Scanned PDF has no text | Detect empty extraction, show a clear error; scope is text PDFs |
| Poor retrieval | Chunk size, overlap and top-k are settings; test on a PDF with known answers |
| Model returns invalid JSON | JSON-schema `format`, validation, 2 retries, never write on failure |
| Quote check proves only that the quote exists | The EV1 judge adds a second opinion; state the limits of both honestly in the keynote |
| Small judge is lenient or inconsistent | Short fixed-label output, keep the quote check as anchor, report disagreements |
| Low RAM | Small models, `num_ctx` 4096, one chat model at a time |
| Live demo crashes | Pre-warm the model, record a fallback video |

## 6. Decisions already taken

- Vector store: JSON file + numpy (simple, debuggable, easy to explain).
- Questions: plain text, one per line. Answers: Markdown.
- No interactive chat mode, no reranking, no export, no SQLite.
- PDF library: still open (`pypdf` is the simplest; try it first).
