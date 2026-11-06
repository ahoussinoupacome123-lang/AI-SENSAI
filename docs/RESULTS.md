# Results

Measured on 2026-10-15 with the real chain and the real models: `python -m src.cli data/demo.pdf data/questions.txt`, scored by `scripts/e2e_check.py`. The raw output of this run is in [examples/demo_run.txt](examples/demo_run.txt) and the answers file in [examples/answers_demo.md](examples/answers_demo.md).

## Setup

| | |
|---|---|
| Document | `data/demo.pdf`: 24 pages of course notes on computer networks (about 34,600 characters, 59 chunks) |
| Questions | 9 in `data/questions.txt`: 8 covered by the PDF, 1 not covered ("Who invented the World Wide Web?") |
| Chat model and judge | `qwen3:4b`, schema mode (thinking off, temperature 0) |
| Embeddings | `nomic-embed-text` |
| Settings | chunk size 800, overlap 150, top-k 4 (the committed `config.json`) |
| Machine | WSL2, CPU only, 7.6 GiB of RAM in total (about 2.6 GiB free during the run) |

## Result of the full run

| Q | Question | Expected | Answered | Quote check | Judge |
|---|---|---|---|---|---|
| 1 | bits in an IPv6 address | page 13 | page 13 | supported | faithful |
| 2 | the four steps of DHCP | page 15 | **refused (wrong)** | not supported | faithful (missed) |
| 3 | usable hosts in a /26 | page 12 | page 12 | supported | faithful |
| 4 | non-overlapping 2.4 GHz channels | page 22 | page 22 | supported | faithful |
| 5 | max payload of an Ethernet frame | page 8 | page 8 | supported | faithful |
| 6 | the port used by SSH | page 17 | **refused (wrong)** | not supported | **unfaithful (caught)** |
| 7 | what the TTL field does | page 14 | page 14 | supported | faithful |
| 8 | length of an 802.1Q VLAN tag | page 10 | page 10 | supported | faithful |
| 9 | who invented the Web (not in the PDF) | none | refused (right) | not supported | faithful |

- **Covered questions:** right page and quote **6 of 8 (75 %)**. Uncovered question: refused **1 of 1**. The checker says **PASS**.
- **No invented answer:** in this run the model never made up an answer; its two errors were refusals ("the document does not cover this") for facts that were in the retrieved passages.
- **Retrieval:** for all 8 covered questions, the right page was among the 4 retrieved chunks, including the two that the model then refused.
- **Time (CPU only):** **6 min 42 s** for the 9 questions including the ingestion of the 59 chunks, and **5 min 31 s** in a second full run from a fresh clone with the models already warm: about **40 seconds per question** on average, from about 10 s for a simple question to about 60 s when the model refuses and the judge writes a long reason. A 3-question run (`data/questions_demo.txt`) took 31 s including ingestion. A first full run while other programs were using the CPU took 11 min 16 s, so measure on a quiet machine.
- **Quote check:** 6 supported, 3 not supported (the two wrong refusals and the correct one: a refusal has no quote).
- **Judge:** 8 faithful, 1 unfaithful. It caught the SSH refusal (its reason says the passages state that SSH uses port 22) and missed the DHCP one.
- **Third full run (2026-11-06, committed config, nothing else running):** **8 min 57 s** for the 9 questions (about 1 minute per question including reading the PDF). 6 of 8 right pages, the uncovered question refused: PASS. Q2 gave the right four steps (Discover, Offer, Request, Acknowledge) but with page 0, so it fails the page check; Q6 (the SSH port) was wrongly refused and the judge flagged it. Raw files: [examples/verification/](examples/verification/). On this laptop only about 0.5 GiB of RAM stays free during a run, and speed drops when memory is tight.
- **Review list:** the disagreement flag lists Q2 (a real error) and Q9 (in this recorded run a correct refusal was flagged as a false alarm; since this run, a correct refusal is no longer flagged). Q6 is not in that list because both checks agree that it is wrong; it shows as `unfaithful` in the file and in the summary counts.

**Reproducibility:** the full run was repeated from a fresh clone of the repository (clone, install, run): the answers, the quote-check results, the judge verdicts and the review list were identical to the first run, because the model runs at temperature 0. A separate test harness also gave 6 of 8.

**Living document, measured:** rewording question 2 and re-running only that question (`--only 2`) changed exactly one line of `answers.md`, section 2's heading; every other line was identical (`diff` shows `17c17` only).

## What we tested, and what it taught us

1. **Thinking vs JSON schema.** `qwen3:4b` is a thinking model. With default thinking plus a JSON schema, the first real question ran 9 min 40 s without finishing. With `think=false` and temperature 0 in schema mode, a whole run takes minutes. In plain chat the opposite holds: without a schema, `think=false` leaks the reasoning into the text, so the chatbot keeps thinking on.
2. **The prompt matters a lot in schema mode.** A terse system prompt made the model refuse every question. An explicit prompt ("if a passage contains the answer, give its answer, its page and a word-for-word quote; only if no passage has it, say the document does not cover this") fixed that.
3. **Answer-step variants (same 9 questions, same retrieval):**

   | Variant | Pages right (of 8) | Time per question |
   |---|---|---|
   | current order (`answer`, `page`, `quote`) | **6** | 8 s |
   | `quote` first | 5 and 3 in two tests | 7 s |
   | a short "reasoning" field first | 2 | 48 s |

   So we kept the current schema.
4. **Judge schema order.** With the verdict written first, the judge called both wrongly refused answers "faithful" while its own reason said the passages contained the answer. With the **reason written first**, 5 of 5 hand-checked cases were right (both wrong refusals, the correct refusal, a correct answer, a wrong answer). In the final full run it caught one of the two wrong refusals, so it is better, not perfect.
5. **A separate yes/no "is it answerable?" check** scored 2 of 5, so we dropped it.
6. **Judge on refusals.** Without a special rule the judge called a correct refusal "unfaithful"; with the rule in the prompt it handles refusals better but is still the same small model that wrote the answer.

## Limits (to say out loud)

- 6 of 8 covered questions on one 24-page document is a small sample; the true rate could be anywhere around 60 to 90 %.
- The model sometimes refuses a question whose answer is in the passages. We did not see it invent an answer, but it is not complete.
- The judge shares the model and its weaknesses; it caught one of two wrong refusals.
- A correct refusal shows `Quote check: not supported` (there is no quote), (this was recorded before the fix: the flag then raised a false alarm). Now a refusal is flagged only when the judge says the passages do answer the question, and the run summary counts refusals apart. Showing "refused" instead of "not supported" in the file would be clearer still.
- About 1 minute per question on a CPU-only laptop with 7.6 GiB of RAM (25 to 90 s; 5 min 31 s to 8 min 57 s for the 9 questions). It is slower when RAM is nearly full, and the first question also loads the model.
- Text PDFs only, no OCR.

## How to reproduce

```bash
python scripts/build_demo_pdf.py                                   # rebuild data/demo.pdf and verify the expected answers against it
python -m src.cli data/demo.pdf data/questions.txt                 # the run
python scripts/e2e_check.py data/answers.md data/expected_answers.md
```
`e2e_check.py` exits 0 when at least 70 % of the covered questions cite the right page and every uncovered question is refused. The expected-answers format is `number | page P | key phrase` (or `number | none |`).
