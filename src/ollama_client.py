"""The only module that talks HTTP to Ollama: chat (optional JSON schema) and embeddings."""


def chat(messages, model, schema=None, stream=False, host="http://localhost:11434"):
    """Return text (schema is None) or a parsed dict (schema given)."""
    raise NotImplementedError


def embed(texts, model, host="http://localhost:11434"):
    """Return one vector (list of floats) per text."""
    raise NotImplementedError
