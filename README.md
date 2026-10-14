This is the official school README

<p align="center">
  <img src="docs/assets/sensai-banner.png" alt="SENSAI_ - WATASHI WA NIHONGO O SUKOSHI SHIKA HANASEMASEN" width="420">
</p>

---

# Sensai Q&A

A local assistant that answers a list of questions about a PDF and writes a sourced `answers.md` (answer, page, verbatim quote). Everything runs on your machine through Ollama, with no LLM framework.

## Features
- **B1** CLI chatbot (base loop): see `src/chat.py`
- **R1** Basic RAG: PDF -> chunks -> embeddings -> top-k retrieval
- **T5** Structured output: JSON `{answer, page, quote}`
- **M4** Living document: `answers.md` updated one section at a time
- Quote check: flags answers whose quote is not in the retrieved text
- **EV1** Automated evaluation: an LLM judge scores each answer against the retrieved passages

Requires Python 3.10+ and [Ollama](https://ollama.com). No LLM framework (LangChain, LlamaIndex, ...): all model calls go straight to the Ollama HTTP API with `requests`.

Status: the CLI chatbot (`src/chat.py`) works; the other `src/` modules are skeletons still to implement.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

## Usage
```bash
# CLI chatbot (streaming, history); model from config.json or as an argument
python src/chat.py                       # or: python src/chat.py qwen3:4b

# project (once implemented)
python -m src.cli data/course.pdf data/questions.txt
```

## Layout
```
README.md  requirements.txt  config.json
prompts/     system and answer prompts
src/         chat (base loop), ollama_client, ingestion, store, pipeline, judge, writer, cli
tests/       automated checks
data/        sample PDF, questions.txt, generated answers.md
docs/        EXPLANATION, USE_CASE, USER_STORIES, ARCHITECTURE(+_EXPLAINED), MODEL_SELECTION, subject/
```

## Documentation
Start with `docs/EXPLANATION.md`. User stories: `docs/USER_STORIES.md`. Architecture: `docs/ARCHITECTURE.md`.
