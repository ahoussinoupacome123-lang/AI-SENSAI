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
| **EV1** Automated eval & hallucination detection | A second model call (the judge) scores each answer against the retrieved passages | Catches wrong readings of a real quote, which the string check cannot; gives a per-run score to compare settings |

**About EV1.** The catalogue's EV1 describes an LLM acting as judge and producing scores. The quote check alone is a plain string check, so it is not EV1. The judge is: it reads the question, the retrieved passages and the answer, and returns a verdict (`faithful`, `partial` or `unfaithful`) with a one-line reason. We keep the quote check as the cheap, deterministic anchor and present the judge as a second opinion. The two can disagree, and we say so honestly in the keynote. The judge uses the same `qwen3:4b` model (see `MODEL_SELECTION.md`). When unsure whether this counts as EV1, ask during the Follow-up.

**Ratings.** The catalogue rates features on two scales, difficulty (1-3) and pedagogical value (1-3). The icons could not be extracted as text, so only one number per feature is known so far. *Still to confirm in the PDF: which scale these numbers are, and the other scale.*

| Feature | Stars known so far | Scale |
|---|---|---|
| B1 | mandatory | - |
| R1 | 2 | to confirm |
| T5 | 1 | to confirm |
| M4 | 2 | to confirm |
| EV1 | 3 | to confirm |

### Out of scope (deliberately)
Interactive chat over the PDF, R2 reranking, export (X3), multi-agent, web UI, scheduling, code execution, web search, SQLite. They add risk and little to the demo.

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

## 5. Two-day plan

- **Day 1 morning:** `ollama_client.py`, `ingestion.py`; check a known fact retrieves the right page.
- **Day 1 afternoon:** `pipeline.py` (retrieve, prompt, JSON, retry); test on 5 questions with known answers.
- **Day 2 morning:** `writer.py` (test: other sections byte-identical) and the quote check.
- **Day 2 midday:** `judge.py` (EV1): judge prompt, verdict parsing, per-run score.
- **Day 2 afternoon:** user stories, tests, README, rehearse, record a fallback video.

Demo material: one 20-60 page text PDF, 6-8 questions, one question not covered.

## 6. Models

`qwen3:4b` for the chatbot, the answers and the EV1 judge, `nomic-embed-text` for embeddings. Nothing else. See `MODEL_SELECTION.md`.
