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
    """Return {verdict, reason}. Thinking off, short output, same JSON-schema path as the answers."""
    raise NotImplementedError
