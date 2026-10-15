"""Checks added while integrating the pieces (S1): schema mode and retrieval wiring."""
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ollama_client, pipeline  # noqa: E402


def fake_response(content='{"answer": "a", "page": 1, "quote": "q"}'):
    response = mock.Mock(status_code=200)
    response.json.return_value = {"message": {"content": content}}
    return response


def sent_payload(**kwargs):
    with mock.patch("requests.post", return_value=fake_response()) as post:
        ollama_client.chat([{"role": "user", "content": "hi"}], "m", **kwargs)
    return post.call_args[1]["json"]


def test_schema_mode_turns_thinking_off_and_uses_temperature_zero():
    payload = sent_payload(schema=pipeline.ANSWER_SCHEMA)
    assert payload["think"] is False
    assert payload["options"]["temperature"] == 0
    assert payload["format"] == pipeline.ANSWER_SCHEMA


def test_plain_chat_keeps_default_thinking():
    with mock.patch("requests.post", return_value=fake_response("hello")) as post:
        ollama_client.chat([{"role": "user", "content": "hi"}], "m")
    payload = post.call_args[1]["json"]
    assert "think" not in payload and "temperature" not in payload["options"]


def test_retrieve_and_answer_returns_the_retrieved_chunks_for_the_judge():
    index = [{"id": 0, "text": "alpha beta", "page": 1, "vector": [1.0, 0.0]},
             {"id": 1, "text": "gamma delta", "page": 2, "vector": [0.0, 1.0]}]
    config = {"top_k": 1, "embed_model": "e", "chat_model": "m", "max_retries": 0}
    with mock.patch.object(ollama_client, "chat",
                           return_value={"answer": "a", "page": 1, "quote": "alpha beta"}):
        result = pipeline.retrieve_and_answer("q?", index, config,
                                              client_embed=lambda texts, model, host=None: [[1.0, 0.0]])
    assert [c["page"] for c in result["chunks"]] == [1]
    assert result["status"] == "supported"


def test_judge_schema_asks_for_the_reason_before_the_verdict():
    from src import judge
    assert list(judge.VERDICT_SCHEMA["properties"]) == ["reason", "verdict"]
    assert set(judge.VERDICT_SCHEMA["required"]) == {"reason", "verdict"}
