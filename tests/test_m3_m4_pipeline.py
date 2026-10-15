"""Tests for src/pipeline.py (M3 + M4).

Run with: .venv/bin/python -m pytest tests/test_m3_m4_pipeline.py -v
"""
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")
from src.pipeline import (
    answer,
    quote_is_supported,
    retrieve_and_answer,
    AnswerError,
    _format_passages,
    _validate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_CONFIG = {
    "host": "http://localhost:11434",
    "chat_model": "qwen3:4b",
    "embed_model": "nomic-embed-text",
    "top_k": 4,
    "max_retries": 2,
    "num_ctx": 4096,
    "system_prompt_file": "prompts/system_prompt.txt",
    "answer_prompt_file": "prompts/answer_prompt.txt",
}


def _chunk(id_, text, page, vector=None):
    return {"id": id_, "text": text, "page": page, "vector": vector or [0.0]}


def _valid_answer_json(ans="Paris", page=3, quote="the capital is Paris"):
    return {"answer": ans, "page": page, "quote": quote}


# ---------------------------------------------------------------------------
# M3 – Prompt construction
# ---------------------------------------------------------------------------

class TestFormatPassages(unittest.TestCase):

    def test_contains_page_numbers(self):
        chunks = [_chunk(1, "hello", 2), _chunk(2, "world", 5)]
        text = _format_passages(chunks)
        self.assertIn("page 2", text)
        self.assertIn("page 5", text)

    def test_contains_chunk_text(self):
        chunks = [_chunk(1, "unique-text-abc", 1)]
        text = _format_passages(chunks)
        self.assertIn("unique-text-abc", text)

    def test_top_k_passages_in_prompt(self):
        """Prompt contains exactly top_k passages when top_k < total."""
        chunks = [_chunk(i, f"text-{i}", i) for i in range(1, 6)]  # 5 chunks

        captured = {}

        def fake_chat(messages, model, schema=None, **kwargs):
            captured["prompt"] = messages[-1]["content"]
            return _valid_answer_json()

        with patch("src.pipeline.ollama_client.chat", side_effect=fake_chat):
            config = {**BASE_CONFIG, "top_k": 3}
            # We call answer() with exactly 3 pre-retrieved chunks (top_k already applied)
            answer("question?", chunks[:3], config)

        # 3 passages labelled [Passage 1], [Passage 2], [Passage 3]
        for i in range(1, 4):
            self.assertIn(f"[Passage {i}", captured["prompt"])
        self.assertNotIn("[Passage 4]", captured["prompt"])

    def test_prompt_reads_from_file(self):
        """Changing the prompt file changes the prompt text (no hard-coded strings)."""
        import tempfile, os
        chunks = [_chunk(1, "content", 1)]

        custom_marker = "CUSTOM_MARKER_XYZ"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(f"{custom_marker} {{passages}}\nQ: {{question}}")
            tmp_path = f.name

        try:
            captured = {}

            def fake_chat(messages, model, schema=None, **kwargs):
                captured["prompt"] = messages[-1]["content"]
                return _valid_answer_json()

            config = {**BASE_CONFIG, "answer_prompt_file": tmp_path}
            with patch("src.pipeline.ollama_client.chat", side_effect=fake_chat):
                answer("q", chunks, config)

            self.assertIn(custom_marker, captured["prompt"])
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# M4 – JSON validation, retries, AnswerError
# ---------------------------------------------------------------------------

class TestValidate(unittest.TestCase):

    def test_valid_dict(self):
        d = {"answer": "x", "page": 2, "quote": "y"}
        self.assertEqual(_validate(d), d)

    def test_missing_key_returns_none(self):
        self.assertIsNone(_validate({"answer": "x", "page": 2}))

    def test_invalid_json_returns_none(self):
        self.assertIsNone(_validate("not json {{{"))

    def test_page_as_string_coerced(self):
        d = {"answer": "x", "page": "5", "quote": "y"}
        result = _validate(d)
        self.assertIsNotNone(result)
        self.assertEqual(result["page"], 5)


class TestRetries(unittest.TestCase):

    def test_invalid_twice_then_valid_succeeds(self):
        """Mock returns invalid JSON twice then valid: success after 2 retries."""
        calls = [0]

        def fake_chat(messages, model, schema=None, **kwargs):
            calls[0] += 1
            if calls[0] <= 2:
                return {"answer": "x"}  # missing page and quote
            return _valid_answer_json()

        with patch("src.pipeline.ollama_client.chat", side_effect=fake_chat):
            result = answer("q", [_chunk(1, "the capital is Paris", 3)], BASE_CONFIG)

        self.assertEqual(calls[0], 3)
        self.assertIn("answer", result)

    def test_always_invalid_raises_answer_error(self):
        """Mock returns invalid JSON 3 times: AnswerError raised."""

        def fake_chat(messages, model, schema=None, **kwargs):
            return {"answer": "x"}  # always missing page and quote

        with patch("src.pipeline.ollama_client.chat", side_effect=fake_chat):
            with self.assertRaises(AnswerError):
                answer("q", [_chunk(1, "text", 1)], BASE_CONFIG)

    def test_result_has_required_keys(self):
        """A valid result has exactly the keys answer, page, quote (plus question and status)."""
        def fake_chat(messages, model, schema=None, **kwargs):
            return _valid_answer_json()

        chunks = [_chunk(1, "the capital is Paris", 3)]
        with patch("src.pipeline.ollama_client.chat", side_effect=fake_chat):
            result = answer("q", chunks, BASE_CONFIG)

        for key in ("question", "answer", "page", "quote", "status"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# M3 – top_k and retrieve integration
# ---------------------------------------------------------------------------

class TestRetrieveAndAnswer(unittest.TestCase):

    def test_top_k_larger_than_index_no_crash(self):
        """top_k larger than the index does not crash."""
        chunks = [_chunk(i, f"text-{i}", i, [float(i), 0.0]) for i in range(1, 3)]
        config = {**BASE_CONFIG, "top_k": 100}

        def fake_embed(texts, model, host=None):
            return [[1.0, 0.0]] * len(texts)

        def fake_chat(messages, model, schema=None, **kwargs):
            return _valid_answer_json()

        with patch("src.pipeline.ollama_client.chat", side_effect=fake_chat):
            result = retrieve_and_answer("q", chunks, config, client_embed=fake_embed)

        self.assertIn("answer", result)

    def test_correct_top_k_passed_to_search(self):
        """With a 5-chunk index and top_k=2, only 2 chunks are in the prompt."""
        chunks = [_chunk(i, f"text-{i}", i, [float(i), 0.0]) for i in range(1, 6)]
        config = {**BASE_CONFIG, "top_k": 2}

        captured = {}

        def fake_embed(texts, model, host=None):
            return [[1.0, 0.0]] * len(texts)

        def fake_chat(messages, model, schema=None, **kwargs):
            captured["prompt"] = messages[-1]["content"]
            return _valid_answer_json()

        with patch("src.pipeline.ollama_client.chat", side_effect=fake_chat):
            retrieve_and_answer("q", chunks, config, client_embed=fake_embed)

        # Should see Passage 1 and Passage 2 but NOT Passage 3
        self.assertIn("[Passage 1", captured["prompt"])
        self.assertIn("[Passage 2", captured["prompt"])
        self.assertNotIn("[Passage 3", captured["prompt"])


# ---------------------------------------------------------------------------
# Quote check
# ---------------------------------------------------------------------------

class TestQuoteIsSupported(unittest.TestCase):

    def test_exact_match(self):
        chunks = [_chunk(1, "The OSI model has seven layers.", 1)]
        self.assertTrue(quote_is_supported("The OSI model has seven layers.", chunks))

    def test_case_insensitive(self):
        chunks = [_chunk(1, "The OSI model has seven layers.", 1)]
        self.assertTrue(quote_is_supported("the osi MODEL has seven LAYERS.", chunks))

    def test_extra_spaces_ignored(self):
        chunks = [_chunk(1, "The OSI model has seven layers.", 1)]
        self.assertTrue(quote_is_supported("The  OSI  model  has seven layers.", chunks))

    def test_not_in_chunks(self):
        chunks = [_chunk(1, "Networks use protocols.", 1)]
        self.assertFalse(quote_is_supported("The OSI model has seven layers.", chunks))

    def test_empty_quote_is_not_supported(self):
        chunks = [_chunk(1, "text", 1)]
        self.assertFalse(quote_is_supported("", chunks))


if __name__ == "__main__":
    unittest.main(verbosity=2)
