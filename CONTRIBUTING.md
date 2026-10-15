# Contributing to Sensai Q&A

Thank you for helping. This guide explains the rules of the project, how the code is organised, how to work on it, and what a good contribution looks like. For how to run things, see the [README](README.md); for every test you can run, see [docs/TESTING.md](docs/TESTING.md).

## Ground rules

These come from the project subject and from what we learned building it:

1. **Python 3.10 or newer.** Standard library plus small utility packages (`requests`, `numpy`, `pypdf`, `pytest`).
2. **No LLM framework** (no LangChain, LlamaIndex, Haystack or equivalent). Every model call goes through the Ollama HTTP API directly.
3. **Everything that talks to Ollama goes through `src/ollama_client.py`.** No other module sends HTTP requests to the model.
4. **Prompts live in `prompts/`, settings live in `config.json`.** Do not hard-code prompt text, model names, paths or sizes in the code.
5. **Keep it local.** Documents and questions must never be sent to an outside service.
6. **No secrets, tokens, personal paths or personal data** in the repository (nor in its history).
7. **Be honest in numbers.** Any figure in the docs (accuracy, speed, test counts) must come from a real run. Say what does not work.

## Set up

```bash
git clone git@github.com:ahoussinoupacome123-lang/AI-SENSAI.git
cd AI-SENSAI
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # all tests must pass before you start
```
Ollama with `qwen3:4b` and `nomic-embed-text` is only needed to try the real chain (see the README). The automated tests never need it.

## How the code is organised

One file, one job. Put new code where its job belongs, and keep `cli.py` free of logic: it only wires the others.

| File | Job |
|---|---|
| `src/ollama_client.py` | the only module that calls Ollama (chat, JSON schema, embeddings) |
| `src/ingestion.py` | PDF to pages to chunks to embeddings to index |
| `src/store.py` | save/load the index, cosine search |
| `src/pipeline.py` | one question: retrieve, prompt, JSON answer, validate, retry |
| `src/quote_check.py` | deterministic check that the quote is in the passages |
| `src/judge.py` | LLM judge of faithfulness |
| `src/eval_summary.py` | run summary and quote/judge disagreement flag |
| `src/writer.py` | `answers.md`: update exactly one section, atomically |
| `src/cli.py` | `python -m src.cli`: wiring only |
| `src/chat.py` | the plain CLI chatbot (base loop) |

The interfaces between them are listed in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Change an interface only together with its callers, its tests and that document.

## Workflow

1. **Pick or open a task.** One task per branch and per pull request.
2. **Branch from the latest `main`:** `git checkout -b feat/<short-name>` (also `fix/...`, `docs/...`, `test/...`). If your work depends on an unmerged branch, start from that branch and say so in the pull request.
3. **Set your identity before your first commit** (inside the project folder, without `--global`), with the exact school email, so the work is credited to you:
   ```bash
   git config user.name "First LAST"
   git config user.email "first.last@epitech.eu"
   ```
4. **Write the code and its tests together** (see Tests below).
5. **Run the whole suite:** `python -m pytest -q`. Everything must pass.
6. **Commit with a clear message** (see below).
7. **Pull before you push, never force-push** shared history, then open a pull request into `main`.
8. **Use plain merges, not squash merges,** so each person's commits stay separate and credited. The school repository is fed from this one by a partner who pulls and pushes it; unrelated or rewritten histories make that painful.

### Commit messages

[Conventional Commits](https://www.conventionalcommits.org): `type(scope): what changed`, in the imperative, about 70 characters.

| Type | Use for | Example from this repository |
|---|---|---|
| `feat` | new behaviour | `feat(ingestion): chunk pages with overlap and page numbers` |
| `fix` | a bug | `fix(writer): keep normal file permissions on answers.md` |
| `docs` | documentation only | `docs(readme): final setup, usage, results and limits` |
| `test` | tests only | `test(chat): cover streaming, history, errors and Ctrl+C` |
| `refactor` | no behaviour change | `refactor(cli): print the M6 run summary instead of a duplicate` |
| `chore` | tooling, setup | `chore(chat): verify base loop with qwen3:4b` |

## Tests

- **Every change to behaviour comes with tests**, in `tests/test_<topic>.py`, written with `pytest`.
- **Automated tests must not need Ollama.** Replace the model client and the store with fakes (see `tests/test_ingest.py` and `tests/test_cli.py` for the pattern) and build PDFs with `tests/pdf_factory.py`. A test that calls the real model is a manual check, and belongs in [docs/TESTING.md](docs/TESTING.md).
- **Test the error paths,** not only the happy path: missing file, bad input, server down, invalid model output. Every error shown to a user must say what went wrong and how to fix it (for example `Start it with: ollama serve`), never a raw traceback.
- Keep tests fast (the whole suite runs in about a second) and independent of each other and of your machine.
- Never edit a test just to make it pass. If a test is wrong, say why in the commit message.

## Changing a prompt, a schema or a model setting

This area cost us the most time, so it has its own rule: **measure before and after.**

1. Run the demo before your change and save the result: `python -m src.cli data/demo.pdf data/questions.txt`, then `python scripts/e2e_check.py data/answers.md data/expected_answers.md`.
2. Make the change, run it again, compare (use `--force` if you touched the chunk settings).
3. Keep the change only if it is better, and record both numbers in [docs/RESULTS.md](docs/RESULTS.md), also when it did not help.

Things already learned, so you do not repeat them:
- With a JSON schema, `qwen3:4b` must run with thinking off (`think=false`) and temperature 0; with default thinking it returned empty answers or hung. In plain chat it is the opposite.
- A terse system prompt made the model refuse every question; the explicit prompt works.
- In the answer schema, `quote` first and a "reasoning" field first both scored worse than the current order. In the judge schema, `reason` before `verdict` is better.

## Code style

- Match the surrounding code: naming, comment density, idiom. Small functions with one purpose.
- Comments explain **why**, not what. Docstrings say what a function takes and returns.
- Prefer clear errors raised as exceptions with a helpful message over silent fallbacks.
- Do not add a dependency without a good reason; if you do, add it to `requirements.txt`.

## Documentation

Update the docs in the same pull request as the behaviour: the README (usage, options), [docs/USER_STORIES.md](docs/USER_STORIES.md) (every feature needs at least two user stories with acceptance criteria), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (interfaces), and [docs/TESTING.md](docs/TESTING.md) (new tests or checks).

## Adding a feature

1. Write the user stories first (who, what, why, and how we will observe it).
2. Check the dependencies on existing components.
3. Implement it in the file where its job belongs, with tests.
4. Run it on the real models and record what happened, including what failed.
5. Document it.

## Pull request checklist

- [ ] One task, a clear title in Conventional Commits style
- [ ] `python -m pytest -q` passes
- [ ] New or changed behaviour has tests, including error cases
- [ ] No secrets, personal paths or generated files (`answers.md`, `*.index.json`, `.venv`)
- [ ] Prompts, settings and model changes were measured before and after
- [ ] Docs, user stories and the README are updated
- [ ] Your commits use your school email

## Ideas for contributors

- A dedicated status for refusals: today a correct refusal shows `Quote check: not supported` and can raise a false review flag.
- Retry with more chunks, or rerank them, when the model refuses although the answer is in the document (feature R2).
- Count how often the first try returns valid JSON (a useful figure, not measured yet).
- Several PDFs at once, or OCR for scanned PDFs.
- A bigger test set than the 24-page demo, with more question types.

## Reporting a problem

Open an issue with: the exact command you ran, the full output, your Python version (`python3 --version`), your Ollama version (`ollama --version`), your RAM, and whether `python -m pytest -q` passes. Say which `config.json` values you changed.
