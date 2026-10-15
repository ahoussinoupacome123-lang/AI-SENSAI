# ARCHITECTURE.md explained from zero

Companion to `ARCHITECTURE.md`. Same structure, but every file, box and table row is explained in plain words with a small example. Unknown word? Check `EXPLANATION.md`.

Running example used everywhere: **`course.pdf`** (40 pages about networks) and **`questions.txt`** containing:
```
What are the layers of the OSI model?
Who invented TCP?
What is the capital of France?     <- not in the PDF, on purpose
```

---

## 1. The big picture (the diagram)

The program has two phases.

**Phase A – Ingestion (once per PDF).** Prepare the PDF so it can be searched. Like making the index of a book.

**Phase B – Answering (once per question).** For each question: find the relevant passages, ask the model, check the result, write it into `answers.md`.

Think of a **library assistant**:
- `ingestion.py` reads the book and files index cards (one card per paragraph, with page number).
- `store.py` is the card drawer.
- `pipeline.py` takes a question, pulls the 4 best cards, reads them, writes an answer.
- `writer.py` copies that answer onto the right page of a report.
- `ollama_client.py` is the phone the assistant uses to call the "brain" (the model).
- `cli.py` is the manager who tells everyone what to do and in what order.

The arrows in the diagram are just "who calls whom".

---

## 2. The files, one by one

### `ollama_client.py` – the phone to the model
**Job:** it is the *only* file allowed to talk to Ollama. Everyone else calls it.

**Why only one file?** If Ollama's address changes, or you want better error messages, you fix one place, not six.

**What it can do:**
1. **Chat:** send messages, get text back. Can stream (word by word) or not. Can optionally carry a *JSON schema* that forces the answer into a strict shape.
2. **Embed:** send texts, get back lists of numbers (vectors).

**Errors it must explain clearly:** Ollama not running ("run `ollama serve`"), model missing ("run `ollama pull qwen3:4b`").

**Example:**
- In: `"Reply with three words"` → Out: `"Hello there friend"`.
- In: `["The OSI model has seven layers"]` → Out: `[[0.12, -0.53, 0.08, ...]]` (768 numbers).

---

### `ingestion.py` – preparing the PDF
**Job:** turn a PDF into small searchable pieces.

**Steps:**
1. **Extract text per page.** Page 2 → `"The OSI model has seven layers..."`. Pages stay separate so we can later say "page 2".
2. **Cut into overlapping chunks, keeping the page number.** About 800 characters per chunk. Each chunk repeats the last ~150 characters of the previous one, so a sentence cut at the border is still whole somewhere. Every chunk remembers its page.
3. **Get embeddings.** Ask `ollama_client` for a vector per chunk. The vector captures meaning, so "how do plants make food" can match "photosynthesis".
4. **Hand to the store.** It does not save anything itself.
5. **Detect PDFs with no text.** A scanned PDF is just pictures; extraction returns nothing. Stop with a clear message instead of building an empty index.

**In → Out:** `course.pdf` → a list of chunk records `{id, text, page, vector}`.

---

### `store.py` – the card drawer
**Job:** save the chunks to disk and find the best ones for a question.

**Two functions:**
1. **Save / load** to `index.json`. A plain file next to the PDF. No database to install, and you can open it and look.
2. **`search(vector, k)`**: given the question's vector, compare it with every chunk vector using **cosine similarity** (a score of how much two vectors point the same way, computed with `numpy`) and return the top `k`.

**Example:** the question vector is compared with 150 chunk vectors. Scores: chunk 17 → 0.91, chunk 18 → 0.84, chunk 3 → 0.20... With k=4 it returns the 4 highest.

**In → Out:** chunks ↔ top-k results.

---

### `pipeline.py` – answering one question
**Job:** everything that happens between "question" and "checked answer".

**Steps:**
1. **Embed** the question (turn it into a vector).
2. **Search** the store for the top 4 chunks.
3. **Build the prompt:** system prompt + the 4 chunks (with their pages) + the question.
4. **Ask for JSON** using the schema `{answer, page, quote}`.
5. **Validate:** is it valid JSON with all fields? If not, **retry** (at most 2 more times).
6. **Quote check:** does the `quote` really appear, word for word (ignoring case and extra spaces), in the 4 chunks? Yes → `supported`. No → `not supported`.

**Example of output:**
```json
{ "question": "What are the layers of the OSI model?",
  "answer": "Seven layers: physical, data link, network, ...",
  "page": 2,
  "quote": "The OSI model has seven layers",
  "status": "supported" }
```
For "capital of France" the model should answer "The document does not cover this" with an empty quote.

**In → Out:** a question → a `Checked` answer.

---

### `judge.py` – the second opinion (EV1)
**Job:** after an answer exists, ask the model a different question: "Is this answer really supported by these passages?"

**How it differs from the quote check:** the quote check only proves the quoted words exist in the document. The judge reads the whole answer and catches a *real quote misread* (right sentence, wrong conclusion).

**Steps:**
1. Build a prompt with the question, the 4 retrieved passages and the answer (`prompts/judge_prompt.txt`).
2. Ask the model for a tiny JSON: `{"verdict": "faithful" | "partial" | "unfaithful", "reason": "one sentence"}`.
3. Return it; the pipeline stores it next to the quote-check status.

**Example:** answer "TCP was invented in 1999" with the quote "TCP was specified in RFC 793 (1981)". The quote check says `supported` (the quote exists), but the judge says `unfaithful` (1999 contradicts 1981). That disagreement is flagged in the file.

**Honest limit:** it is the same small model judging, so it can be lenient. That is why the quote check stays as the independent anchor.

**In → Out:** question + answer + chunks → verdict and reason.

---

### `writer.py` – owner of `answers.md`
**Job:** put each answer in the file without damaging the rest.

**Rule:** update **exactly one section** per question. If the section exists, replace it; if not, append it. All other sections stay *byte-for-byte identical*. This is the "living document" (feature M4).

**Example:** you re-run question 2 alone. Only the "Who invented TCP?" section changes; sections 1 and 3 are untouched.

**How it finds a section:** each section has a marker in the file (for example a heading with the question number), so the code finds it by text matching, never by asking the model to rewrite the file.

**In → Out:** a checked answer → an edited file.

---

### `cli.py` – the manager
**Job:** read what the user typed, load settings, and run the others in order. **No logic of its own**, only wiring.

**Typical flow:**
```
python -m src.cli course.pdf questions.txt
 1. read config.json and prompts/
 2. ingest course.pdf (skip if index.json already exists)
 3. for each question: pipeline.retrieve_and_answer(q) -> judge.evaluate(...) -> writer.upsert_section(...)
 4. print: "2/3 supported, 1 not supported"
```
Keeping it dumb makes the other files easy to test alone.

**In → Out:** command-line arguments → calls to the other files.

---

### `config.json` and `prompts/` – settings kept out of the code
**Job:** hold everything you might want to change *without editing Python*.
- `config.json`: model names, Ollama address, chunk size (800), overlap (150), top-k (4).
- `prompts/`: the system prompt text, e.g. "Answer only from the provided passages. If they do not contain the answer, say so."

**Why:** testing a different chunk size or rewording the prompt becomes a one-line edit, and it shows in the keynote that choices are tunable and justified.

---

## 3. Data shapes (the "agreement" between files)

Files exchange data in fixed shapes, so they must agree *before* coding. Otherwise one file sends a field the next doesn't expect.

| Shape | Meaning | Example |
|---|---|---|
| `Chunk` | One piece of the PDF | `{id: 17, text: "The OSI model...", page: 2, vector: [..]}` |
| `Answer` | What the model returns (the JSON schema) | `{question, answer, page, quote}` |
| `Checked` | An answer plus the quote-check result and the judge verdict | `Answer` + `status: "supported"`, `verdict: "faithful"`, `reason` |

**The function signatures, in plain words:**

| Signature | Reads as |
|---|---|
| `client.chat(messages, model, schema=None, stream=False) -> str \| dict` | "Send these messages to this model. If a schema is given, force JSON and return a dict; otherwise return text." |
| `client.embed(texts, model) -> list[list[float]]` | "Give me one vector for each text." |
| `store.save(chunks)` / `store.search(vector, k)` | "Save these chunks." / "Give me the k chunks closest to this vector." |
| `pipeline.retrieve_and_answer(question, index_chunks, config) -> Checked` | "Find the best chunks for this question, answer it, and tell me if the quote is supported." The result also carries the retrieved `chunks`, because the judge needs them. |
| `pipeline.answer(question, chunks, config) -> Checked` | "Same, but for chunks I already retrieved." |
| `writer.upsert_section(path, index, checked)` | "Put this answer into section number `index` of the file at `path`." Returns nothing; refuses a failed answer. |

---

## 4. Repository layout

| Path | What lives there |
|---|---|
| `README.md` | Setup, features, usage (required by the subject) |
| `requirements.txt` | Python packages: `requests`, `numpy`, a PDF library |
| `config.json` | Settings |
| `prompts/` | Prompt texts |
| `src/` | The Python files above, plus `chat.py` (the base CLI chatbot) and `judge.py` |
| `tests/` | Automated checks (for example "other sections stay identical") |
| `docs/` | These documents |
| `data/` | Demo PDF, `questions.txt`, generated `answers.md` |

---

## 5. Risks (what can go wrong, and what we do about it)

| Risk | Explained | Our answer |
|---|---|---|
| Scanned PDF has no text | The PDF is images, so there is nothing to read | Detect it, show a clear error; we only support text PDFs |
| Poor retrieval | The search brings back the wrong chunks, so the model answers badly | Chunk size, overlap and top-k are settings; test on a PDF where we know the answers |
| Model returns invalid JSON | Small models sometimes break the format | Force the schema, validate, retry twice, never write a broken result into the file |
| Quote check proves only that the quote exists | The quote may be real but misread | We say this honestly in the keynote |
| Low RAM | The laptop has ~5 GB free | Small models, context window of 4096 tokens, one chat model at a time |
| Live demo crashes | Slow or failing model during the keynote | Load the model before the demo, record a fallback video |

---

## 6. Decisions already taken

| Decision | Why |
|---|---|
| JSON file + numpy as the vector store | Simple, you can open and read it, easy to explain. A database would add setup for no demo benefit. |
| Questions in plain text, answers in Markdown | Anyone can edit the first and read the second. |
| No chat mode, reranking, export or SQLite | Each adds risk and little to the demo; fewer, deeper features score better. |
| PDF library: still open | Try `pypdf` first because it is the simplest. |
