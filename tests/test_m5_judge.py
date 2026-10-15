"""Tests for src/judge.py (M5).

Run with: .venv/bin/python -m pytest tests/test_m5_judge.py -v
"""
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, ".")
from src.judge import evaluate, _parse_verdict


def _chunk(id_, text, page):
    return {"id": id_, "text": text, "page": page, "vector": [0.0]}


BASE_CONFIG = {
    "host": "http://localhost:11434",
    "chat_model": "qwen3:4b",
    "judge_model": "qwen3:4b",
    "num_ctx": 4096,
    "judge_prompt_file": "prompts/judge_prompt.txt",
}


# ---------------------------------------------------------------------------
# _parse_verdict unit tests
# ---------------------------------------------------------------------------

class TestParseVerdict(unittest.TestCase):

    def test_faithful(self):
        d = {"verdict": "faithful", "reason": "all claims supported"}
        self.assertEqual(_parse_verdict(d), d)

    def test_partial(self):
        d = {"verdict": "partial", "reason": "some claims missing"}
        self.assertEqual(_parse_verdict(d), d)

    def test_unfaithful(self):
        d = {"verdict": "unfaithful", "reason": "contradicts passages"}
        self.assertEqual(_parse_verdict(d), d)

    def test_invalid_verdict_label(self):
        self.assertIsNone(_parse_verdict({"verdict": "wrong", "reason": "x"}))

    def test_missing_reason(self):
        self.assertIsNone(_parse_verdict({"verdict": "faithful"}))

    def test_invalid_json_string(self):
        self.assertIsNone(_parse_verdict("not-json"))


# ---------------------------------------------------------------------------
# evaluate() integration tests (mocked)
# ---------------------------------------------------------------------------

class TestEvaluate(unittest.TestCase):

    def _run(self, verdict_str):
        verdict_dict = {"verdict": verdict_str, "reason": "test reason"}

        def fake_chat(messages, model, schema=None, **kwargs):
            return verdict_dict

        chunks = [_chunk(1, "some passage text", 1)]
        with patch("src.judge.ollama_client.chat", side_effect=fake_chat):
            result = evaluate("q?", "an answer", chunks, BASE_CONFIG)
        return result

    def test_faithful_verdict(self):
        result = self._run("faithful")
        self.assertEqual(result["verdict"], "faithful")
        self.assertIn("reason", result)

    def test_partial_verdict(self):
        result = self._run("partial")
        self.assertEqual(result["verdict"], "partial")

    def test_unfaithful_verdict(self):
        result = self._run("unfaithful")
        self.assertEqual(result["verdict"], "unfaithful")

    def test_fallback_on_always_invalid(self):
        """Invalid output after 2 tries returns 'unknown', no crash."""
        def fake_chat(messages, model, schema=None, **kwargs):
            return {"verdict": "garbage", "reason": "x"}

        chunks = [_chunk(1, "text", 1)]
        with patch("src.judge.ollama_client.chat", side_effect=fake_chat):
            result = evaluate("q?", "answer", chunks, BASE_CONFIG)

        self.assertEqual(result["verdict"], "unknown")

    def test_prompt_contains_question_answer_passages(self):
        """Judge prompt must include question, answer and passages – no extra info."""
        captured = {}

        def fake_chat(messages, model, schema=None, **kwargs):
            captured["messages"] = messages
            return {"verdict": "faithful", "reason": "ok"}

        chunks = [_chunk(1, "unique-passage-text-ABC", 7)]
        with patch("src.judge.ollama_client.chat", side_effect=fake_chat):
            evaluate("the-question-XYZ?", "the-answer-QRS", chunks, BASE_CONFIG)

        content = captured["messages"][0]["content"]
        self.assertIn("the-question-XYZ?", content)
        self.assertIn("the-answer-QRS", content)
        self.assertIn("unique-passage-text-ABC", content)

    def test_exception_during_call_returns_unknown(self):
        """OllamaError or any exception during judge call returns 'unknown' gracefully."""
        from src.ollama_client import OllamaError

        def fake_chat(messages, model, schema=None, **kwargs):
            raise OllamaError("Ollama down")

        chunks = [_chunk(1, "text", 1)]
        with patch("src.judge.ollama_client.chat", side_effect=fake_chat):
            result = evaluate("q?", "answer", chunks, BASE_CONFIG)

        self.assertEqual(result["verdict"], "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
