"""EV1: a second model call that judges an answer against the retrieved passages."""

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["faithful", "partial", "unfaithful"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
}


def evaluate(question, answer, chunks, config):
    """Return {verdict, reason}. Short output, same JSON-schema path as the answers. Do not send think=false (it breaks this qwen3:4b tag)."""
    raise NotImplementedError
