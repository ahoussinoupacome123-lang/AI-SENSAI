"""Tests for dynamic context window handling (M8).

Run with: .venv/bin/python -m pytest tests/test_dynamic_context.py -v
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from src import ollama_client, pipeline


def test_zero_hardcoded_4096_in_src():
    """Ensure no hardcoded 4096 integer or string literals remain in src/."""
    src_dir = Path("src")
    assert src_dir.is_dir()
    for py_file in src_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "4096" not in content, f"Hardcoded 4096 found in {py_file}"


def test_get_context_limit_from_config():
    assert pipeline.get_context_limit({"num_ctx": 1024}) == 1024
    assert pipeline.get_context_limit({"num_ctx": "2048"}) == 2048
    assert pipeline.get_context_limit({"num_ctx": 8192}) == 8192


def test_get_context_limit_fallback_when_unspecified():
    with patch("src.ollama_client.get_model_context_length", return_value=None):
        limit = pipeline.get_context_limit({})
        assert limit == pipeline.DEFAULT_FALLBACK_NUM_CTX


def test_get_context_limit_queries_ollama_metadata():
    with patch("src.ollama_client.get_model_context_length", return_value=32768):
        limit = pipeline.get_context_limit({}, model="custom:latest")
        assert limit == 32768


def test_budget_chunks_trims_on_tight_context_window():
    # 5 chunks of 800 chars each = ~4000 chars
    chunks = [
        {"id": i, "page": i, "text": f"Chunk {i} " + "A" * 700}
        for i in range(1, 6)
    ]
    # Small context window: 512 tokens (~1500 chars budget)
    selected, warning = pipeline.budget_chunks_for_context(chunks, "What is this?", num_ctx=512)
    assert len(selected) < len(chunks)
    assert warning is not None
    assert "Context budget constraint" in warning

    # Large context window: 8192 tokens (~24000 chars budget)
    all_selected, no_warning = pipeline.budget_chunks_for_context(chunks, "What is this?", num_ctx=8192)
    assert len(all_selected) == len(chunks)
    assert no_warning is None


def test_budget_chunks_handles_empty_chunks():
    selected, warning = pipeline.budget_chunks_for_context([], "Empty question?", num_ctx=2048)
    assert selected == []
    assert warning is None


def test_get_model_context_length_parsing():
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"model_info": {"qwen.context_length": 32768}}

    with patch("src.ollama_client._post", return_value=FakeResponse()):
        length = ollama_client.get_model_context_length("qwen3:4b")
        assert length == 32768
