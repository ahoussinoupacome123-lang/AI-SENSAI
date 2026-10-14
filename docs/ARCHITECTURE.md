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
| `ollama_client.py` | The only place that talks HTTP to Ollama: chat (streaming or not, optional JSON schema) and embeddings. Raises clear errors (no connection, model missing). | messages/texts → text / dict / vectors |
| `ingestion.py` | Extract text per page from the PDF, cut into overlapping chunks keeping the page number, get embeddings, hand to the store. Detect PDFs with no text. | PDF path → chunk records |
| `store.py` | Save and load chunks + vectors in `index.json`; `search(vector, k)` with cosine similarity (numpy). | chunks ↔ top-k results |
| `pipeline.py` | For one question: embed, search, build prompt, ask for JSON, validate, retry, run the quote check. | question → `Checked` answer |
| `judge.py` | EV1: second model call that compares an answer with the retrieved passages and returns a verdict (`faithful` / `partial` / `unfaithful`) plus a one-line reason, using `prompts/judge_prompt.txt`. | question + answer + chunks → verdict |
| `writer.py` | Own `answers.md`. Update exactly one section per question, leave the rest untouched, append if missing. | checked answer → file |
| `cli.py` | Read args and config, load prompts, loop over questions, print the summary. Only wires; no logic. | args → calls the others |
| `config.json`, `prompts/` | Settings (models, host, chunk size, overlap, top-k) and prompt text, kept out of the code. | – |

## 3. Data shapes (agree on these before coding)

```
Chunk    = { id, text, page, vector }
Answer   = { question, answer, page, quote }          # exactly the JSON schema
Checked  = Answer + { status: "supported" | "not supported", verdict, reason }

client.chat(messages, model, schema=None, stream=False) -> str | dict
client.embed(texts, model)                              -> list[list[float]]
store.save(chunks) ; store.search(vector, k)            -> list[Chunk]
pipeline.answer(question)                               -> Checked
judge.evaluate(question, answer, chunks)                -> { verdict, reason }
writer.upsert_section(index, checked)                   -> None
```

## 4. Repository layout

```
sensai/
├── README.md
├── requirements.txt        # requests, numpy, a PDF library
├── config.json
├── prompts/                # system prompt, answer prompt
├── src/ chat.py  ollama_client.py  ingestion.py  store.py  pipeline.py  judge.py  writer.py  cli.py
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
| Small judge is lenient or inconsistent | Short fixed-label output, thinking off, keep the quote check as anchor, report disagreements |
| Low RAM | Small models, `num_ctx` 4096, one chat model at a time |
| Live demo crashes | Pre-warm the model, record a fallback video |

## 6. Decisions already taken

- Vector store: JSON file + numpy (simple, debuggable, easy to explain).
- Questions: plain text, one per line. Answers: Markdown.
- No interactive chat mode, no reranking, no export, no SQLite.
- PDF library: still open (`pypdf` is the simplest; try it first).
