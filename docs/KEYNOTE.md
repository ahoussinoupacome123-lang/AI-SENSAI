# Keynote: Sensai Q&A

What the subject asks for: open with a concrete scenario, demonstrate the features live in that scenario (one coherent system, not disconnected demos), explain the technical choices (what we considered, what we ruled out), and close with an honest assessment. A live system that crashes is a preparation failure, so a fallback is ready for everything that depends on the model.

Suggested length: 12 to 15 minutes plus questions. The live demo is the longest part. A full run of the 9 questions takes 5 to 7 minutes, so on stage we run a short list of 3 questions chosen in advance (`data/questions_demo.txt`, about 3 minutes) and show the full 9-question result from the recorded run, **including its two errors**.

## 1. The scenario (the opening, 30 seconds)

> "Lea is a networking student. The exam is in two days and she has 24 pages of course notes: a PDF. She has nine questions to prepare. She could read everything again, or paste it into a chatbot, but the notes are private, and a chatbot that has not read them will happily invent an answer. What she wants is one file with an answer to each question, the page it came from, and a quote she can check."

That is exactly what Sensai produces, and it runs on her laptop with no cloud and no cost.

## 2. Slide outline (13 slides, SENSAI style: blue background, white text, orange accent)

| # | Slide | What to say | Key visual |
|---|---|---|---|
| 1 | **SENSAI_** Ask a PDF, get sourced answers, locally | the one-line pitch | title, banner |
| 2 | The scenario | Lea, 24 pages, 9 questions, 2 days | the question list |
| 3 | Why not just a chatbot? | it has not read your PDF, it may invent, the PDF is private; and a small model cannot hold a whole PDF (context window) | PDF vs 4096-token window |
| 4 | The system in one picture | PDF, ingestion, index, retrieval, JSON answer, quote check, judge, `answers.md` | the pipeline diagram |
| 5 | R1: Retrieval (2 stars) | chunks of 800 characters with 150 overlap and their page; embeddings; cosine top-4 | "How do plants make food?" finds "photosynthesis" |
| 6 | T5: Structured output (1 star) | the model must answer `{answer, page, quote}`; invalid output is retried twice and never written | the schema |
| 7 | M4: A living document (2 stars) | `answers.md` is the deliverable; re-run one question and only its section changes | the `diff` |
| 8 | EV1: Do we trust the answer? (3 stars) | quote check (exact, cheap) plus judge (reads the whole answer); where they disagree we flag it | two checks, one flag |
| 9 | LIVE DEMO | see section 3 | terminal |
| 10 | What we measured | 6 of 8 covered questions right (page and quote), the uncovered question refused, about 40 s per question | the results table |
| 11 | What we tried and ruled out | thinking mode, quote-first schema, reasoning-first answers, yes/no check | the table in section 5 |
| 12 | Honest assessment | what works, what does not, what we would do differently | three columns |
| 13 | Questions | | the 7 prepared questions |

The deck is [slides/keynote.html](slides/keynote.html): open it in any browser (no internet needed), move with the arrow keys or clicks, `F` for fullscreen, and print to PDF for a handout. This table is the script for it.

## 3. The live demo (4 minutes)

### Before going on stage (5 minutes, do it every time)

```bash
cd ~/EPITECH/Tek3/AI-SENSAI/AI-SENSAI && source .venv/bin/activate
ollama serve > ~/ollama.log 2>&1 &            # if it is not already running
curl http://localhost:11434                    # must print: Ollama is running
ollama run qwen3:4b "" ; ollama run nomic-embed-text ""     # warm both models (first load is slow)
rm -f data/demo.index.json data/answers.md     # start clean so the audience sees ingestion
python -m pytest -q                            # optional, 1 second, shows the tests pass
```
Close the browser and other heavy programs (the model needs about 4 GB of free RAM).

### The demo, step by step

| Step | Command | What to say | Time |
|---|---|---|---|
| 1. The input | `head -c 700 data/demo_course.txt` and `cat data/questions_demo.txt` | "24 pages of notes. Three questions today; the full set has nine. The last one, who invented the Web, is **not** in the notes: remember it." | 20 s |
| 2. Run | `python -m src.cli data/demo.pdf data/questions_demo.txt` | "Ingestion happens once: pages, chunks with their page number, one vector per chunk. Then one question at a time." While it runs, talk through slides 5 to 8. | about 3 minutes |
| 3. Read the result | `cat data/answers.md` (or open it) | "One section per question: answer, page, a quote you can check in the PDF, the quote check, the judge's verdict." | 30 s |
| 4. The refusal | point at question 3 | "It did not invent an answer. It says the document does not cover this." | 15 s |
| 5. The flag | point at a `Review needed` line (if one appears) | "Here the two checks disagree, so the tool tells us which answers to read ourselves." | 20 s |
| 6. Living document | `cp data/answers.md /tmp/before.md`, then `sed 's/maximum payload size of an Ethernet frame/largest payload an Ethernet frame can carry/' data/questions_demo.txt > /tmp/q.txt`, then `python -m src.cli data/demo.pdf /tmp/q.txt --only 2`, then `diff /tmp/before.md data/answers.md` | "I reword question 2 and re-run only that one. The diff shows that only section 2 changed; every other byte of the file is identical. That is feature M4." (The model answers deterministically, so re-running the *same* question would give an empty diff: reword it.) | 45 s |
| 7. Verify a quote | open `data/demo.pdf` at the page shown | "The page and quote are real: that is what makes the answer checkable." | 20 s |

Be open that the live questions were chosen in advance, and show the **full** 9-question result (slide 10, [RESULTS.md](RESULTS.md), `docs/examples/answers_demo.md`) with its two wrong refusals. If the live run is too slow, run only `--only 1` and show the recording for the rest.

### Fallback (use it without hesitation)

A live demo that hangs is a preparation failure, so everything that depends on the model has a fallback:
- **Recorded run:** record the terminal (or the screen) of one complete run during rehearsal. Keep the video on the laptop and on a USB stick.
- **Transcript:** `docs/examples/demo_run.txt` is the real output of a complete run, with timings.
- **Result file:** `docs/examples/answers_demo.md` is the real `answers.md` of that run.
- **If Ollama is down:** `ollama serve > ~/ollama.log 2>&1 &`, wait 5 seconds, retry. If the model hangs, press Ctrl+C (the CLI keeps what it has written) and switch to the recording.

## 4. What to demonstrate honestly

Do not hide the weak points: the evaluation asks for an honest assessment. The demo run is real and not rehearsed to be perfect: if the model refuses a question that the PDF covers, show how the flag and the judge catch it. It is a better demonstration of EV1 than a flawless run.

## 5. Technical choices: what we considered, what we ruled out

| Decision | Chosen | Considered and ruled out | Why |
|---|---|---|---|
| LLM | `qwen3:4b` | `qwen3:8b`, `llama3.2:3b`, `gemma3:4b`, `phi4-mini` | fits in about 2.5 GB, follows JSON schemas well for its size; 8B is too slow and tight on 8 GB of RAM without a GPU |
| Embeddings | `nomic-embed-text` | larger embedding models | 0.3 GB, good enough: retrieval ranked the right page first in every test |
| Vector store | JSON file + numpy | SQLite, a vector database | simple, readable, easy to explain; hundreds of chunks do not need more |
| Framework | none (`requests` to the Ollama API) | LangChain, LlamaIndex | forbidden by the subject, and it keeps every step visible |
| Chunking | 800 characters, 150 overlap, page kept | whole pages, sentence splitting | small chunks match sharper; overlap protects cut sentences; the page enables citations |
| Structured output | Ollama `format` JSON schema, validate, retry twice | asking nicely for JSON | a schema constrains the output; validation protects the file |
| Thinking mode | on in plain chat, **off in schema mode** | on everywhere | tested: with a schema the model returned empty answers or hung for minutes |
| Answer schema order | `answer, page, quote` | quote first; reasoning first | tested on the same questions: quote first scored 5/8 and 3/8, reasoning first 2/8, against 6/8 for the current order |
| Judge schema order | **reason before verdict** | verdict first | tested: verdict first called wrongly refused answers "faithful" (2 of 2 missed); reason first got 5 of 5 right |
| Checks | quote check **and** judge, flag on disagreement | judge only, quote check only | the quote check is exact but blind to misreading; the judge reads everything but is a lenient small model |

## 6. Honest assessment (slide 12)

**What works well**
- The whole chain runs locally and fully automatically: PDF in, sourced `answers.md` out.
- Retrieval is reliable: in every test the right page was ranked first.
- The file is never corrupted: a failed question is reported and skipped, re-running one question changes only its section (tested byte for byte), and the write is atomic.
- Two independent checks on every answer, and the disagreement flag points at the answers worth reading.
- 229 automated tests, none of which needs Ollama; a scoring script compares a run with known answers.

**Current limits**
- 6 of 8 covered questions answered correctly on the demo PDF (75 %), the same in two runs and in a separate harness; a small sample
- The 4B model sometimes refuses a question that the PDF does cover, even though retrieval found the right passage. It did not invent answers in our runs, but it is not complete.
- The judge is the same small model as the answerer: lenient on some cases. It helps, it is not proof.
- Speed: about 40 seconds per question on average on a CPU-only laptop (10 to 60 s).
- Only text PDFs (no OCR), one PDF at a time, and quotes are checked per chunk.
- A correct refusal shows "Quote check: not supported" because it has no quote, which looks like a failure.

**What we would do differently**
- Measure the model choice earlier with a fixed question set instead of discovering the thinking-mode problem in the first full run.
- Give a refusal its own status instead of reusing "not supported".
- Add a second retrieval pass (reranking, feature R2) or a retry with more chunks when the model refuses.
- Use a larger or non-thinking-tuned model if a GPU is available.

## 7. Questions to prepare

The seven classic questions have written answers in [EXPLANATION.md](EXPLANATION.md), section 6. Others likely to come:

| Question | Short answer |
|---|---|
| Why no LangChain? | forbidden by the subject; also we wanted to understand each step. About 600 lines of plain Python. |
| Why is the judge the same model? | RAM: two chat models do not fit; we keep the independent quote check as an anchor and report disagreements. |
| Why a JSON file and not a vector database? | a few hundred chunks; readable and testable; a database adds setup for no benefit here. |
| What if the PDF is scanned? | detected and refused with a clear message; OCR is out of scope. |
| How do you know retrieval works? | known-fact tests: in every run the right page was ranked first; `scripts/e2e_check.py` scores page accuracy. |
| What happens when the model returns bad JSON? | validated, retried twice, then the question is reported as failed and the file is not touched. |
| How does EV1 count as evaluation? | an LLM judge scores each answer for faithfulness to the sources, the run is summarised, and the answers where the judge and the quote check disagree are flagged. |
| Why is it slow? | CPU only, a 4B model, and two model calls per question (answer and judge). |
| What would a bigger model change? | fewer false refusals; we did not test models above 4B because of the RAM limit. |

## 8. Rehearsal checklist

- [ ] Run the whole demo twice, timed, on the machine that will be used.
- [ ] Record one complete run as a video; keep a copy on a USB stick.
- [ ] Models warmed up; Ollama running; other programs closed.
- [ ] `data/` is clean (`rm -f data/demo.index.json data/answers.md`) before the live run.
- [ ] Each team member can answer the seven questions in EXPLANATION.md without notes.
- [ ] Everything works without the internet.
- [ ] Phone silent, laptop charged and plugged in.
