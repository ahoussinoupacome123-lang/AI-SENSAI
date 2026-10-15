"""Tests for src/ollama_client.py (M1).

Run with: .venv/bin/python -m pytest tests/test_m1_ollama_client.py -v
"""
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")
from src import ollama_client as client
from src.ollama_client import OllamaError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code=200, json_body=None, text=""):
    """Return a fake requests.Response."""
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    if json_body is not None:
        r.json.return_value = json_body
        r.text = json.dumps(json_body)
    return r


def _chat_response(content, done=True):
    return _make_response(
        json_body={"message": {"content": content}, "done": done}
    )


def _embed_response(vectors):
    return _make_response(json_body={"embeddings": vectors})


# ---------------------------------------------------------------------------
# chat() – plain text
# ---------------------------------------------------------------------------

class TestChatPlainText(unittest.TestCase):

    @patch("src.ollama_client.requests.post")
    def test_returns_string(self, mock_post):
        mock_post.return_value = _chat_response("Hello there friend")
        result = client.chat(
            [{"role": "user", "content": "Reply with exactly three words"}],
            model="qwen3:4b",
        )
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    @patch("src.ollama_client.requests.post")
    def test_schema_returns_dict(self, mock_post):
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "string"}, "page": {"type": "integer"}, "quote": {"type": "string"}},
            "required": ["answer", "page", "quote"],
        }
        mock_post.return_value = _chat_response(
            json.dumps({"answer": "Paris", "page": 3, "quote": "capital is Paris"})
        )
        result = client.chat(
            [{"role": "user", "content": "Where is Paris?"}],
            model="qwen3:4b",
            schema=schema,
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"answer", "page", "quote"})

    @patch("src.ollama_client.requests.post")
    def test_no_schema_key_forwarded(self, mock_post):
        """When schema is None, 'format' must NOT appear in the payload."""
        mock_post.return_value = _chat_response("ok")
        client.chat([{"role": "user", "content": "hi"}], model="qwen3:4b")
        payload = mock_post.call_args[1]["json"]
        self.assertNotIn("format", payload)


# ---------------------------------------------------------------------------
# chat() – error handling
# ---------------------------------------------------------------------------

class TestChatErrors(unittest.TestCase):

    @patch("src.ollama_client.requests.post",
           side_effect=__import__("requests").ConnectionError)
    def test_ollama_not_running_message(self, _):
        with self.assertRaises(OllamaError) as ctx:
            client.chat([{"role": "user", "content": "hi"}], model="qwen3:4b")
        self.assertIn("ollama serve", str(ctx.exception))

    @patch("src.ollama_client.requests.post")
    def test_unknown_model_message(self, mock_post):
        mock_post.return_value = _make_response(status_code=404, text="not found")
        with self.assertRaises(OllamaError) as ctx:
            client.chat([{"role": "user", "content": "hi"}], model="does-not-exist")
        self.assertIn("ollama pull does-not-exist", str(ctx.exception))

    @patch("src.ollama_client.requests.post",
           side_effect=__import__("requests").Timeout)
    def test_timeout_raises(self, _):
        with self.assertRaises(OllamaError):
            client.chat([{"role": "user", "content": "hi"}], model="qwen3:4b")


# ---------------------------------------------------------------------------
# embed()
# ---------------------------------------------------------------------------

class TestEmbed(unittest.TestCase):

    @patch("src.ollama_client.requests.post")
    def test_returns_two_vectors_same_length(self, mock_post):
        vec_a = [0.1, 0.2, 0.3]
        vec_b = [0.4, 0.5, 0.6]
        mock_post.return_value = _embed_response([vec_a, vec_b])
        result = client.embed(["a", "b"], model="nomic-embed-text")
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), len(result[1]))

    @patch("src.ollama_client.requests.post")
    def test_unknown_model_embed(self, mock_post):
        mock_post.return_value = _make_response(status_code=404, text="not found")
        with self.assertRaises(OllamaError) as ctx:
            client.embed(["test"], model="bad-model")
        self.assertIn("ollama pull bad-model", str(ctx.exception))

    @patch("src.ollama_client.requests.post",
           side_effect=__import__("requests").ConnectionError)
    def test_ollama_not_running_embed(self, _):
        with self.assertRaises(OllamaError) as ctx:
            client.embed(["test"], model="nomic-embed-text")
        self.assertIn("ollama serve", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
