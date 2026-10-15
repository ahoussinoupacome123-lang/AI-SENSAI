import json
import sys
from pathlib import Path
from unittest import mock

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ollama_client  # noqa: E402
from src.ollama_client import OllamaError, chat_events, list_models  # noqa: E402


def stream_response(*chunks, status=200):
    response = mock.Mock(status_code=status, text="boom")
    response.iter_lines.return_value = [json.dumps(c).encode() for c in chunks]
    return response


def test_events_are_tokens_then_done_with_usage():
    response = stream_response(
        {"message": {"content": "Hel"}},
        {"message": {"content": "lo"}},
        {"message": {"content": ""}, "done": True, "prompt_eval_count": 12, "eval_count": 5},
    )
    with mock.patch("requests.post", return_value=response):
        events = list(chat_events([{"role": "user", "content": "hi"}], "m", num_ctx=4096))
    assert events[0] == {"type": "token", "text": "Hel"}
    assert events[1] == {"type": "token", "text": "lo"}
    assert events[-1] == {"type": "done", "usage": {"prompt_tokens": 12, "reply_tokens": 5,
                                                       "total_tokens": 17, "num_ctx": 4096}}


def test_thinking_is_announced_once_and_its_text_is_not_forwarded():
    response = stream_response(
        {"message": {"thinking": "hmm", "content": ""}},
        {"message": {"thinking": " more", "content": ""}},
        {"message": {"content": "Answer"}},
        {"message": {"content": ""}, "done": True},
    )
    with mock.patch("requests.post", return_value=response):
        events = list(chat_events([], "m"))
    assert [e["type"] for e in events] == ["thinking", "token", "done"]
    assert "hmm" not in json.dumps(events)


def test_the_request_is_a_streaming_chat_with_the_history_and_context_size():
    history = [{"role": "user", "content": "hi"}]
    response = stream_response({"message": {"content": ""}, "done": True})
    with mock.patch("requests.post", return_value=response) as post:
        list(chat_events(history, "qwen", host="http://h", num_ctx=2048))
    assert post.call_args[0][0] == "http://h/api/chat"
    body = post.call_args[1]["json"]
    assert body["messages"] == history and body["stream"] is True and body["options"] == {"num_ctx": 2048}
    assert post.call_args[1]["stream"] is True


def test_closing_the_generator_early_closes_the_connection():
    response = stream_response({"message": {"content": "a"}}, {"message": {"content": "b"}})
    with mock.patch("requests.post", return_value=response):
        events = chat_events([], "m")
        next(events)
        events.close()
    response.close.assert_called()


def test_missing_model_gives_the_exact_pull_command():
    with mock.patch("requests.post", return_value=mock.Mock(status_code=404)):
        with pytest.raises(OllamaError, match="ollama pull nomodel"):
            list(chat_events([], "nomodel"))


def test_server_down_gives_a_clear_message():
    with mock.patch("requests.post", side_effect=requests.ConnectionError):
        with pytest.raises(OllamaError, match="ollama serve"):
            list(chat_events([], "m"))


def test_error_inside_the_stream_is_raised():
    with mock.patch("requests.post", return_value=stream_response({"error": "model crashed"})):
        with pytest.raises(OllamaError, match="model crashed"):
            list(chat_events([], "m"))


def test_list_models_returns_the_names():
    response = mock.Mock(status_code=200)
    response.json.return_value = {"models": [{"name": "qwen3:4b"}, {"name": "nomic-embed-text:latest"}]}
    with mock.patch("requests.get", return_value=response):
        assert list_models() == ["qwen3:4b", "nomic-embed-text:latest"]


def test_list_models_reports_a_server_that_is_down():
    with mock.patch("requests.get", side_effect=requests.ConnectionError):
        with pytest.raises(OllamaError, match="ollama serve"):
            list_models()


def test_existing_calls_still_work_without_the_streaming_flag():
    response = mock.Mock(status_code=200)
    response.json.return_value = {"message": {"content": "hello"}}
    with mock.patch("requests.post", return_value=response) as post:
        assert ollama_client.chat([{"role": "user", "content": "hi"}], "m") == "hello"
    assert post.call_args[1]["stream"] is False
