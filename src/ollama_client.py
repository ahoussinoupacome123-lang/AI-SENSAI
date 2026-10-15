"""The only module that talks HTTP to Ollama: chat (optional JSON schema) and embeddings."""
import json

import requests


class OllamaError(RuntimeError):
    """Raised for any Ollama communication problem."""


def _post(url, payload, timeout=(5, 300), stream=False):
    """HTTP POST with clear error translation."""
    try:
        r = requests.post(url, json=payload, timeout=timeout, stream=stream)
    except requests.ConnectionError:
        raise OllamaError(
            "Cannot reach Ollama. Start it with: ollama serve"
        )
    except requests.Timeout:
        raise OllamaError("Ollama timed out.")
    return r


def chat(messages, model, schema=None, stream=False, host="http://localhost:11434", num_ctx=4096):
    """Return text (schema is None) or a parsed dict (schema given).

    Notes
    -----
    - With a schema we send think=False and temperature 0. Tested on qwen3:4b: a
      schema with default thinking can return EMPTY content after 40+ s or hang,
      while think=False gives clean JSON in 2-8 s.
    - Without a schema we do NOT send think=False: tested, the model then leaks
      its reasoning into message.content. Keep default thinking and read only
      message.content.
    - num_ctx is forwarded as an Ollama option so RAM stays bounded.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"num_ctx": num_ctx},
    }
    if schema is not None:
        payload["format"] = schema
        payload["think"] = False
        payload["options"]["temperature"] = 0

    r = _post(f"{host}/api/chat", payload)

    if r.status_code == 404:
        raise OllamaError(
            f"Model '{model}' not found. Pull it with: ollama pull {model}"
        )
    if r.status_code != 200:
        raise OllamaError(f"Ollama returned HTTP {r.status_code}: {r.text.strip()}")

    if stream:
        # Return a generator that yields text fragments
        def _gen():
            for line in r.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if "error" in chunk:
                    raise OllamaError(chunk["error"])
                text = chunk.get("message", {}).get("content", "")
                yield text
                if chunk.get("done"):
                    break
        return _gen()

    data = r.json()
    if "error" in data:
        raise OllamaError(data["error"])

    content = data["message"]["content"]

    if schema is not None:
        return json.loads(content)

    return content


def embed(texts, model, host="http://localhost:11434"):
    """Return one vector (list of floats) per text.

    Uses /api/embed (batch endpoint available since Ollama 0.3+).
    Falls back to /api/embeddings (single-text) when needed.
    """
    payload = {"model": model, "input": texts}
    r = _post(f"{host}/api/embed", payload)

    if r.status_code == 404:
        raise OllamaError(
            f"Model '{model}' not found. Pull it with: ollama pull {model}"
        )
    if r.status_code != 200:
        raise OllamaError(f"Ollama returned HTTP {r.status_code}: {r.text.strip()}")

    data = r.json()
    if "error" in data:
        raise OllamaError(data["error"])

    # /api/embed returns {"embeddings": [[...], [...]]}
    return data["embeddings"]


def chat_events(messages, model, host="http://localhost:11434", num_ctx=4096):
    """Stream a plain chat reply as events, for user interfaces (WEB-UI).

    Yields {"type": "thinking"} once if the model reasons first, {"type": "token", "text": ...}
    for each piece of the reply, and finally {"type": "done", "usage": {...}} with the token
    counts reported by Ollama. Closing the generator early closes the connection, which makes
    Ollama stop generating. Raises OllamaError like chat().
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"num_ctx": num_ctx},
    }
    r = _post(f"{host}/api/chat", payload, stream=True)
    try:
        if r.status_code == 404:
            raise OllamaError(f"Model '{model}' not found. Pull it with: ollama pull {model}")
        if r.status_code != 200:
            raise OllamaError(f"Ollama returned HTTP {r.status_code}: {r.text.strip()}")
        thinking_sent = False
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if "error" in chunk:
                raise OllamaError(chunk["error"])
            message = chunk.get("message", {})
            if message.get("thinking") and not thinking_sent:
                thinking_sent = True
                yield {"type": "thinking"}
            if message.get("content"):
                yield {"type": "token", "text": message["content"]}
            if chunk.get("done"):
                prompt_tokens = int(chunk.get("prompt_eval_count", 0))
                reply_tokens = int(chunk.get("eval_count", 0))
                yield {"type": "done", "usage": {
                    "prompt_tokens": prompt_tokens,
                    "reply_tokens": reply_tokens,
                    "total_tokens": prompt_tokens + reply_tokens,
                    "num_ctx": num_ctx,
                }}
                return
    finally:
        r.close()


def list_models(host="http://localhost:11434"):
    """Return the names of the models installed in Ollama. Raises OllamaError if it is down."""
    try:
        r = requests.get(f"{host}/api/tags", timeout=(3, 10))
    except requests.ConnectionError:
        raise OllamaError("Cannot reach Ollama. Start it with: ollama serve")
    except requests.Timeout:
        raise OllamaError("Ollama timed out.")
    if r.status_code != 200:
        raise OllamaError(f"Ollama returned HTTP {r.status_code}: {r.text.strip()}")
    return [m["name"] for m in r.json().get("models", [])]
