"""EV1: a second model call that judges an answer against the retrieved passages."""
import json
from pathlib import Path

from src import ollama_client

ROOT = Path(__file__).resolve().parent.parent

# "reason" comes BEFORE "verdict" on purpose: the model writes its short justification first,
# then decides. Tested on the demo questions: with the verdict first, wrongly refused answers
# were judged "faithful" while the reason said the passages contained the answer (2 of 2 missed);
# with the reason first, 5 of 5 hand-checked cases were right.
VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "verdict": {"type": "string", "enum": ["faithful", "partial", "unfaithful"]},
    },
    "required": ["reason", "verdict"],
}

_VALID_VERDICTS = frozenset({"faithful", "partial", "unfaithful"})


def _load_prompt(path):
    """Read a prompt file. If *path* is not absolute, resolve from project root."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return p.read_text()


def _format_passages(chunks):
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Passage {i} – page {chunk['page']}]\n{chunk['text']}")
    return "\n\n".join(parts)


def _parse_verdict(raw):
    """Return a valid verdict dict or None."""
    try:
        d = raw if isinstance(raw, dict) else json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(d, dict):
        return None
    if d.get("verdict") not in _VALID_VERDICTS:
        return None
    if "reason" not in d:
        return None
    return d


def evaluate(question, answer, chunks, config):
    """Return {verdict, reason}. Falls back to 'unknown' after 1 retry.

    Uses prompts/judge_prompt.txt with {question}, {passages}, {answer} placeholders.
    Same model as chat (qwen3:4b), schema mode (thinking off), very short JSON output.
    """
    host = config.get("host", "http://localhost:11434")
    model = config.get("judge_model", config.get("chat_model", "qwen3:4b"))
    num_ctx = int(config.get("num_ctx", 4096))
    prompt_file = config.get("judge_prompt_file", "prompts/judge_prompt.txt")

    template = _load_prompt(prompt_file)
    passages_text = _format_passages(chunks)
    user_content = (
        template
        .replace("{question}", question)
        .replace("{passages}", passages_text)
        .replace("{answer}", answer)
    )

    messages = [{"role": "user", "content": user_content}]

    # 1 retry maximum; if still invalid, return 'unknown'
    for _ in range(2):
        try:
            raw = ollama_client.chat(
                messages, model, schema=VERDICT_SCHEMA,
                host=host, num_ctx=num_ctx
            )
            result = _parse_verdict(raw)
            if result is not None:
                return result
        except Exception:
            pass

    return {"verdict": "unknown", "reason": "Judge failed to produce a valid verdict."}
