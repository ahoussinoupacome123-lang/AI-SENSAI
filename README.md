This is the official school README

<p align="center">
  <img src="docs/assets/sensai-banner.png" alt="SENSAI_ - WATASHI WA NIHONGO O SUKOSHI SHIKA HANASEMASEN" width="100%">
</p>

---

# Sensai Q&A

A local assistant that answers a **list of questions about a PDF** and writes a **sourced `answers.md`**: for every question, the answer, the page it comes from and a word-for-word quote. Everything runs on your own computer through [Ollama](https://ollama.com), with **no LLM framework**: the code talks to the Ollama HTTP API directly with `requests`.

It is built for a student or a researcher who has a long, private text PDF (course notes, a paper, a report) and a list of questions, and wants one file with sourced answers instead of hours of reading. Because the model is local, the document never leaves the machine.

```
report.pdf ──► ingestion ──► index ──► retrieval ──► JSON answer ──► quote check ──► judge ──► answers.md
 (pages)       (chunks +     (cosine    (top-4        {answer,        (is the quote    (is the     (one section
                vectors)      search)    chunks)       page, quote}    in the text?)    answer      per question)
                                                                                         faithful?)
```

## Features

| Feature | What it does here | Catalogue rating |
|---|---|---|
| **B1** CLI chatbot (base loop) | `src/chat.py`: streaming, in-session history, clean errors, model chosen by argument or config | mandatory |
| **R1** Basic RAG | PDF text per page, overlapping chunks, embeddings, local JSON index, cosine top-k retrieval | 2 stars |
| **T5** Structured output | the model must answer in a JSON schema `{answer, page, quote}`; invalid output is retried, never written | 1 star |
| **M4** Artifact and state document | `answers.md` is a living file: re-running one question rewrites only its section, every other byte stays identical | 2 stars |
| **EV1** Automated eval and hallucination detection | a deterministic quote check plus an LLM judge score each answer; disagreements are flagged for review | 3 stars |

Why these five: a small local model cannot read a whole PDF (context window), so we retrieve (R1); our code must use the answer, so it comes as JSON (T5); the deliverable is a file that is refined question by question (M4); and a Q&A tool is only useful if you know when not to trust it (EV1). User stories: [docs/USER_STORIES.md](docs/USER_STORIES.md).

## Requirements

- Python 3.10 or newer, and `git`.
- [Ollama](https://ollama.com) with two models: `qwen3:4b` (chat, answers, judge, about 2.5 GB) and `nomic-embed-text` (embeddings, about 0.3 GB).
- About 4 GB of free RAM. No GPU needed (CPU only works; expect roughly 40 seconds per question, between 10 and 60).
- Python packages (see `requirements.txt`): `requests`, `numpy`, `pypdf`, `pytest`.

## Setup

```bash
git clone git@github.com:ahoussinoupacome123-lang/AI-SENSAI.git
cd AI-SENSAI

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `python3 -m venv` fails with "ensurepip is not available" (some Python 3.14 installs), use:
```bash
python3 -m venv --without-pip .venv
curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
.venv/bin/python /tmp/get-pip.py
source .venv/bin/activate && pip install -r requirements.txt
```

Install Ollama, start it and pull the models:
```bash
curl -fsSL https://ollama.com/install.sh | sh        # Linux; macOS and Windows: installer on ollama.com
ollama serve > ~/ollama.log 2>&1 &                   # leave it running
ollama pull qwen3:4b
ollama pull nomic-embed-text
curl http://localhost:11434                          # must print: Ollama is running
```

Check the installation (no Ollama needed for the tests):
```bash
python -m pytest -q          # 221 tests
```

## Quick start (the demo)

The repository ships a demo document: `data/demo.pdf`, 24 pages of course notes on computer networks, with 9 questions in `data/questions.txt` (8 are covered by the PDF, 1 is not).

```bash
python -m src.cli data/demo.pdf data/questions.txt
```

It ingests the PDF once (a minute at most), then answers the questions one by one. Expect **5 to 7 minutes** on a CPU laptop (about 40 seconds per question on average). The result is `data/answers.md`; a real one is kept in [docs/examples/answers_demo.md](docs/examples/answers_demo.md). To score a run against the known answers:

```bash
python scripts/e2e_check.py data/answers.md data/expected_answers.md
```

### What you get

```markdown
<!-- sensai:section 5 -->
## Q5. What is the maximum payload size of an Ethernet frame?

**Answer:** The maximum payload of an Ethernet frame is 1500 bytes.

**Page:** 8

> The maximum payload of an Ethernet frame is 1500 bytes, a limit known as the maximum transmission unit, or MTU.

**Quote check:** supported
**Judge:** faithful - The answer matches the passage stating the 1500 byte limit.
<!-- /sensai:section 5 -->
```
(The comment lines are invisible when the Markdown is rendered; they let the writer find each section.) A question the PDF does not cover gets `The document does not cover this.` and no quote.

## Usage

```bash
python -m src.cli <pdf> <questions.txt> [--only N] [--force] [--output FILE] [--config FILE]
```

| Option | Meaning |
|---|---|
| `pdf` | the text PDF to read (scanned PDFs are refused with a clear message) |
| `questions.txt` | one question per line; blank lines are ignored |
| `--only N` | answer only question N (1-based); every other section of the file stays byte-for-byte identical |
| `--force` | rebuild the index even if one exists (**needed after changing the chunk settings**) |
| `--output FILE` | answers file (default: `answers.md` next to the PDF) |
| `--config FILE` | settings file (default: `config.json`) |

Exit code 0 when every question was answered, 1 when a question failed or an input was wrong, 130 after Ctrl+C. The index is saved next to the PDF as `<name>.index.json` and reused on the next run. A failed question never stops the run and never damages the file.

The end of a run prints a summary:
```text
Done: 9/9 questions answered, 0 failed -> data/answers.md

Quote check:
  Supported    : 7/9  (78%)
  Not supported: 2/9  (22%)
Judge verdicts:
  Faithful  : 9/9  (100%)
...
⚠ 1 answer(s) where quote check and judge disagree – review manually:
```

**Re-run one question** and see that only its section changes. Reword it first (the model is deterministic, so an unchanged question gives an identical section):
```bash
cp data/answers.md /tmp/before.md
sed 's/maximum payload size of an Ethernet frame/largest payload an Ethernet frame can carry/' data/questions.txt > /tmp/q.txt
python -m src.cli data/demo.pdf /tmp/q.txt --only 5 --output data/answers.md
diff /tmp/before.md data/answers.md        # only section 5 differs
```

**The plain chatbot** (the base loop, no PDF involved):
```bash
python src/chat.py                 # model from config.json
python src/chat.py qwen3:4b        # model as an argument; type exit, Ctrl+D or Ctrl+C to leave
```

**Inspect the ingestion** of any PDF:
```bash
python -m src.ingestion data/demo.pdf            # one line per page
python -m src.ingestion data/demo.pdf --chunks   # how it is cut into chunks
```

## Configuration (`config.json`)

| Key | Default | Meaning |
|---|---|---|
| `host` | `http://localhost:11434` | where Ollama listens |
| `chat_model` | `qwen3:4b` | model for the chatbot and the answers |
| `judge_model` | `qwen3:4b` | model for the EV1 judge |
| `embed_model` | `nomic-embed-text` | model that turns text into vectors |
| `num_ctx` | `4096` | context window, kept small to save RAM |
| `chunk_size`, `chunk_overlap` | `800`, `150` | characters per chunk and overlap between chunks |
| `top_k` | `4` | chunks given to the model for each question |
| `max_retries` | `2` | retries when the model returns invalid JSON |
| `*_prompt_file` | `prompts/...` | prompts live in files, not in the code |

Changing the chunk settings changes the index: rerun with `--force`.

## Project layout

```
src/
  chat.py           B1: the CLI chatbot
  ollama_client.py  the only module that talks HTTP to Ollama (chat, JSON schema, embeddings)
  ingestion.py      PDF -> pages -> overlapping chunks -> embeddings -> index
  store.py          save/load the index, cosine similarity search (numpy)
  pipeline.py       one question: retrieve, prompt, JSON answer, validate, retry
  quote_check.py    deterministic check that the quote is in the retrieved text
  judge.py          EV1: LLM judge of faithfulness (verdict + reason)
  eval_summary.py   run summary and quote/judge disagreement flag
  writer.py         answers.md: update exactly one section, atomically
  cli.py            wires everything: python -m src.cli
prompts/            system, answer, judge and chat prompts
data/               demo.pdf, questions.txt (9), questions_demo.txt (3, for the live demo), expected_answers.md, demo_course.txt (the source text)
scripts/            e2e_check.py (score a run), build_demo_pdf.py (rebuild and verify the demo PDF)
tests/              218 automated tests (no Ollama needed)
docs/               explanation, architecture, user stories, results, keynote, model choice
```

## How it works, in short

1. **Ingestion** reads the text page by page, cuts it into 800-character chunks that overlap by 150 and keep their page number, and asks `nomic-embed-text` for one vector per chunk. Done once per PDF.
2. **Retrieval** embeds the question and keeps the 4 chunks with the highest cosine similarity.
3. **Answer** sends those chunks to `qwen3:4b` and forces the reply into a JSON schema `{answer, page, quote}` (invalid JSON is retried twice, then the question is reported as failed).
4. **Checks.** The quote check looks for the quote word for word in the retrieved text; the judge reads the question, the passages and the answer and returns `faithful`, `partial` or `unfaithful`. Where they disagree, the section is flagged.
5. **Writer** updates only that question's section of `answers.md`.

More detail: [docs/EXPLANATION.md](docs/EXPLANATION.md) (every idea explained from zero), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ARCHITECTURE_EXPLAINED.md](docs/ARCHITECTURE_EXPLAINED.md).

## Results and honest limits

Measured on `data/demo.pdf` (24 pages, 9 questions), full details in [docs/RESULTS.md](docs/RESULTS.md):

| | |
|---|---|
| Covered questions answered with the right page and quote | **6 of 8** |
| Question not in the PDF correctly refused | **1 of 1** |
| Invented answers | none in this run |
| Time | about 40 s per question on a CPU-only laptop (5 min 31 s and 6 min 42 s for the 9 questions in two clean runs; a 3-question run takes about 30 s) |
| Automated tests | 221, none needs Ollama |

What does not work well, said honestly:
- The 4B model sometimes **refuses a question that the PDF does cover** (2 of the 8 here), even though retrieval found the right passage. It did not invent answers, but it is not complete.
- The judge is the same small model as the answerer. It caught one of the two wrong refusals; the quote-check versus judge disagreement flag lists answers worth reading, and also raises one false alarm for a correct refusal (a refusal has no quote).
- Only text PDFs (no OCR), one PDF at a time, CPU speed, and a small sample: 6 of 8 on one document is a result, not a guarantee.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Cannot reach Ollama ... Start it with: ollama serve` | the Ollama server is not running: `ollama serve > ~/ollama.log 2>&1 &` |
| `Model '...' not found. Pull it with: ollama pull ...` | run the exact `ollama pull` command shown |
| `... has no extractable text (probably scanned images)` | the PDF is a scan; only text PDFs are supported (no OCR) |
| answers ignore a changed `chunk_size` | the old index is reused: rerun with `--force` |
| the first question is slow | the model loads into memory, and `qwen3:4b` is a thinking model; later questions are faster |
| `ensurepip is not available` | see the venv workaround in Setup |
| `curl: (92) HTTP/2 stream ... PROTOCOL_ERROR` while installing Ollama | unstable connection: download with `curl -L --http1.1 -C - --retry 20 --retry-all-errors -o ollama.tar.zst https://ollama.com/download/ollama-linux-amd64.tar.zst`, then `sudo tar --zstd -C /usr/local -xf ollama.tar.zst` |
| out of memory under WSL | WSL gets half of the RAM by default; raise it with `memory=10GB` in `C:\Users\<you>\.wslconfig`, then `wsl --shutdown` |
| the chat shows nothing for about 10 s | normal: the model is thinking; the chat prints `(thinking...)` |

## Documentation

| Document | Content |
|---|---|
| [docs/EXPLANATION.md](docs/EXPLANATION.md) | every concept explained from zero (RAG, embeddings, chunking, JSON schema...) |
| [docs/USE_CASE.md](docs/USE_CASE.md) | who it is for, why these features, dependencies, plan |
| [docs/USER_STORIES.md](docs/USER_STORIES.md) | user stories with acceptance criteria, and which tests cover them |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/ARCHITECTURE_EXPLAINED.md](docs/ARCHITECTURE_EXPLAINED.md) | components, interfaces, data shapes |
| [docs/MODEL_SELECTION.md](docs/MODEL_SELECTION.md) | hardware, models and why |
| [docs/RESULTS.md](docs/RESULTS.md) | measured results, what worked and what did not |
| [docs/KEYNOTE.md](docs/KEYNOTE.md) | the keynote: slide script, live demo script, fallback, questions to prepare |
| [docs/slides/keynote.html](docs/slides/keynote.html) | the slide deck (open in a browser; arrows to move, F for fullscreen) |

## Team

Pacome, Murchid and Fati (Epitech Tek3, module G-AIA-500).
