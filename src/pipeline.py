"""One question -> Checked answer: embed, search, prompt, JSON, validate, retry, quote check."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "page": {"type": "integer"},
        "quote": {"type": "string"},
    },
    "required": ["answer", "page", "quote"],
}


def quote_is_supported(quote, chunks):
    """True if quote appears in the retrieved chunks (case and extra spaces ignored)."""
    raise NotImplementedError


def answer(question, chunks, config):
    """Return {question, answer, page, quote, status} where status is 'supported' or 'not supported'."""
    raise NotImplementedError
