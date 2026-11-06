# Sensai – Use Case & Feature Scope

Working title: **a local assistant that answers a list of questions about a PDF and writes a sourced answers file.**

New to the vocabulary? Read `EXPLANATION.md` first.

---

## 1. Use case

**Who uses it?** A student or researcher working with a long text PDF: course notes, a paper, a report.

**What do they want?** They have one PDF and a list of questions (6 to 20). They want **one file** with a detailed answer to each question, plus the **page** and a **short quote** proving where each answer comes from.

**Why not do it without our system?**
- A generic chatbot has not read the PDF and may invent answers.
- Reading and summarising by hand takes hours.
- The document is private and stays on the machine, which is why a local Ollama model is justified.
- A small model cannot fit a whole PDF in its context window, so the relevant passages must be searched and selected (RAG).

**Keynote scenario.** A student opens a 20-60 page course PDF and supplies 6-8 exam questions. The answers file fills in one section at a time with pages and quotes. One question is **not covered** by the PDF: the tool says so instead of inventing. One answer is flagged "not supported" by the quote check; the student rewords the question and re-runs only that one, and only that section changes.

**How long does it take, and is that realistic?** On a CPU-only laptop with 7.6 GiB of RAM we measured **5.5 to 9 minutes for the 9 questions** (about 1 minute each, longer when memory is tight; raw results in `docs/examples/verification/`). That is why the scenario is *not* "wait at the screen": Lea starts the run for her 9 questions before dinner and reads `answers.md` afterwards, then re-runs the one question she rewords (about a minute). A cloud model would answer faster, but her notes would leave her computer; for a batch of 9 questions the wait costs her nothing.

---

## 2. Feature scope (kept small on purpose)

The catalogue says a few well-integrated features beat many shallow ones. We keep four catalogue features (plus the mandatory base) and one small safeguard.

| Feature | Role | Why |
|---|---|---|
| **B1** CLI chatbot (base) | Streaming, history, errors, model by argument/config | Mandatory; its Ollama code is reused |
| **R1** Basic RAG | Extract, chunk, embed, store, retrieve top-k | The heart: lets a small model use a big PDF |
| **T5** Structured output | Model answers in JSON `{answer, page, quote}` | Makes the answer usable by code |
| **M4** Artifact document | `answers.md` updated section by section | The deliverable |
| Quote check (safeguard) | Verify the quote exists in the retrieved text | Cheap, deterministic hallucination flag |
| **X1** Web UI (added last) | `WEB-UI/`: a browser front end over the same backend: upload a PDF, write questions, watch answers stream in with page links, re-run one question, chat with a token meter, change settings | the same work without a terminal; the backend stays unchanged (catalogue: 1 star) |
| **EV1** Automated eval & hallucination detection | A second model call (the judge) scores each answer against the retrieved passages | Catches wrong readings of a real quote, which the string check cannot; gives a per-run score to compare settings |

**About EV1.** The catalogue's EV1 describes an LLM acting as judge and producing scores. The quote check alone is a plain string check, so it is not EV1. The judge is: it reads the question, the retrieved passages and the answer, and returns a verdict (`faithful`, `partial` or `unfaithful`) with a one-line reason. We keep the quote check as the cheap, deterministic anchor and present the judge as a second opinion. The two can disagree, and we say so honestly in the keynote. The judge uses the same `qwen3:4b` model (see `MODEL_SELECTION.md`). When unsure whether this counts as EV1, ask during the Follow-up.

**Ratings.** Read from `docs/subject/features_catalog.pdf` (the catalogue shows one star rating per feature, next to its title; the subject text mentions difficulty and pedagogical value, but the catalogue itself gives a single rating):

| Feature | Catalogue rating | Why we chose it |
|---|---|---|
| B1 CLI chatbot | mandatory base (thumbs-up) | required by the subject; its Ollama code is reused |
| R1 Basic RAG | 2 stars | the heart of the project: a small model can use a long PDF |
| T5 Structured output | 1 star | cheap, and it is what makes the answers usable by code |
| M4 Artifact and state document | 2 stars | the deliverable is a living file, not a chat transcript |
| EV1 Automated eval and hallucination detection | 3 stars | highest value for a document Q&A tool: we measure when the answer is not backed by the document |
| X1 Web UI (added after the first delivery plan) | 1 star | an interface for people who prefer a page to a terminal; reuses the backend, so it adds little risk |
| M3 External structured memory (added later) | 2 stars | Lea studies over several evenings: she can ask "what did we discuss about subnets?" and get it back. Implemented as JSON sessions plus an embedding index, not a database |
| X2 Branching, resume (added later) | 2 stars | she can edit a question and explore a variant without losing the first conversation |
| Feature flags, basic-question shortcut, context budget (extras) | not rated | control and safety for a small local model: switch parts off, answer sums without the model, never overflow the context |

The four first features add up to 8 stars; X1, M3 and X2 added later bring the total to 13. The catalogue says a few well-integrated, well-justified features beat many shallow ones, so the later additions all reuse the same backend and each has user stories and tests (`USER_STORIES.md`); the effort went into testing and honest limits (see `RESULTS.md`).

### Out of scope (deliberately)
Interactive chat over the PDF, R2 reranking, export (X3), multi-agent, scheduling, code execution, web search, SQLite. They add risk and little to the demo.

---

## 3. How the pieces connect

```
PDF ──R1──► relevant chunks ──► model ──T5──► JSON answer ──M4──► answers.md
                  └────────── quote check: is the quote in the chunks? ──┘
                  └────────── EV1 judge: is the answer faithful to the chunks? ──┘
```

### Feature dependencies

Which feature needs which. Build order follows the arrows.

```
B1  Ollama client + chat          foundation: every other feature calls it
 └─► R1  Basic RAG                needs embeddings from the client
      └─► T5  Structured output   needs the retrieved chunks to build the prompt
           ├─► Quote check        needs the JSON `quote` + the retrieved chunks
           ├─► EV1 judge          needs question + answer + the retrieved chunks
           └─► M4  answers.md     needs the validated JSON answer to write
```

| Feature | Depends on | Needed by | Why the dependency exists |
|---|---|---|---|
| B1 | – | R1, T5, M4, quote check | All model calls (chat, embeddings) go through its client |
| R1 | B1 | T5 | The JSON answer is built from the chunks R1 retrieves |
| T5 | B1, R1 | M4, quote check | M4 and the check need labelled fields (`answer`, `page`, `quote`), not prose |
| Quote check | T5, R1 | M4 (status shown in file), EV1 summary | Compares the `quote` field with the retrieved chunk text |
| EV1 judge | T5, R1, B1 | M4 (verdict shown in file) | Needs the answer, the chunks and one more model call through the client |
| M4 | T5 (and the check's status) | – | Writes the validated answer into one section of the file |

**Consequence for the plan.** Nothing can be tested end to end until R1 and T5 both work, so we finish the whole chain thin first (one PDF, one question, one section written), then improve each part. If time runs out, cut from the end of the chain: the quote check goes first, then M4 polish. R1 and T5 stay. EV1 is built last, after the quote check, so it can be cut without breaking the chain.

---

## 4. Stress tests

- **Demo test:** one scenario shows all features in order.
- **Time test:** two days (see plan below), finish the full chain first, polish after.
- **Depth test:** everyone must explain embeddings, cosine similarity, chunking and why retrieval works.
- **Cut test:** if time runs out, EV1 goes first, then the quote check; R1 + T5 + M4 stay.

## 5. Plan and status

- **Day 1 morning** (done): `ollama_client.py`, `ingestion.py`; a known fact retrieves the right page.
- **Day 1 afternoon** (done): `pipeline.py` (retrieve, prompt, JSON, retry), tested on questions with known answers.
- **Day 2 morning** (done): `writer.py` (test: other sections byte-identical) and the quote check.
- **Day 2 midday** (done): `judge.py` (EV1): judge prompt, verdict parsing, per-run score.
- **Day 2 afternoon** (docs done, rehearsal and video still to do by the group): user stories, tests, README, `KEYNOTE.md`; rehearse and record a fallback video.

Demo material: one 20-60 page text PDF, 6-8 questions, one question not covered.

## 6. Models

`qwen3:4b` for the chatbot, the answers and the EV1 judge, `nomic-embed-text` for embeddings. Nothing else. See `MODEL_SELECTION.md`.
