"""One question -> Checked answer: embed, search, prompt, JSON, validate, retry, quote check."""
import json
from pathlib import Path

from src import ollama_client, store
from src.quote_check import quote_is_supported  # noqa: F401  (re-exported for callers and tests)

ROOT = Path(__file__).resolve().parent.parent

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "page": {"type": "integer"},
        "quote": {"type": "string"},
    },
    "required": ["answer", "page", "quote"],
}


class AnswerError(RuntimeError):
    """Raised when the model fails to produce a valid answer after all retries."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_prompt(path):
    """Read a prompt file. If *path* is not absolute, resolve from project root."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return p.read_text()


def _format_passages(chunks):
    """Format retrieved chunks as a numbered list with page annotations."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Passage {i} – page {chunk['page']}]\n{chunk['text']}")
    return "\n\n".join(parts)


def _build_messages(system_prompt, user_prompt):
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _validate(raw):
    """Return a dict if *raw* is valid JSON with the required keys, else None."""
    try:
        d = raw if isinstance(raw, dict) else json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(d, dict):
        return None
    if not all(k in d for k in ("answer", "page", "quote")):
        return None
    if not isinstance(d["page"], int):
        try:
            d["page"] = int(d["page"])
        except (ValueError, TypeError):
            return None
    return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def answer(question, chunks, config):
    """Return a Checked answer dict for *question* using the already-retrieved *chunks*.

    The returned dict has keys: question, answer, page, quote, status.
    *chunks* is a list of dicts {id, text, page, vector}.
    *config* is the project config dict (host, chat_model, system_prompt_file,
    answer_prompt_file, max_retries, num_ctx).
    """
    host = config.get("host", "http://localhost:11434")
    model = config.get("chat_model", "qwen3:4b")
    max_retries = int(config.get("max_retries", 2))
    num_ctx = int(config.get("num_ctx", 4096))

    system_prompt = _load_prompt(config.get("system_prompt_file", "prompts/system_prompt.txt"))
    answer_template = _load_prompt(config.get("answer_prompt_file", "prompts/answer_prompt.txt"))

    passages_text = _format_passages(chunks)
    user_prompt = answer_template.format(passages=passages_text, question=question)
    messages = _build_messages(system_prompt, user_prompt)

    result = None
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = ollama_client.chat(
                messages, model, schema=ANSWER_SCHEMA,
                host=host, num_ctx=num_ctx
            )
            result = _validate(raw)
            if result is not None:
                break
        except Exception as exc:
            last_error = exc

    if result is None:
        raise AnswerError(
            f"Model failed to produce valid JSON after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    status = "supported" if quote_is_supported(result["quote"], chunks) else "not supported"

    return {
        "question": question,
        "answer": result["answer"],
        "page": result["page"],
        "quote": result["quote"],
        "status": status,
    }


def retrieve_and_answer(question, index_chunks, config, client_embed=None):
    """Embed *question*, retrieve top-k chunks from *index_chunks*, then call answer().

    *client_embed* can be a replacement for ollama_client.embed (for testing).
    """
    host = config.get("host", "http://localhost:11434")
    embed_model = config.get("embed_model", "nomic-embed-text")
    top_k = int(config.get("top_k", 4))

    embed_fn = client_embed or ollama_client.embed
    vectors = embed_fn([question], embed_model, host=host)
    question_vector = vectors[0]

    top_chunks = store.search(index_chunks, question_vector, k=top_k)
    result = answer(question, top_chunks, config)
    result["chunks"] = top_chunks  # the judge (EV1) must see the same passages
    return result
