import json
import sys
from pathlib import Path
from unittest import mock

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import chat  # noqa: E402


def stream_of(*chunks):
    """A fake streaming response: one JSON line per chunk, like Ollama sends."""
    response = mock.Mock(status_code=200)
    response.iter_lines.return_value = [json.dumps(c).encode() for c in chunks]
    return response


def words(*texts):
    chunks = [{"message": {"content": t}} for t in texts]
    chunks.append({"message": {"content": ""}, "done": True})
    return stream_of(*chunks)


def test_stream_reply_prints_chunks_progressively_and_returns_the_full_text(capsys):
    with mock.patch("requests.post", return_value=words("Hel", "lo", " there")) as post:
        reply = chat.stream_reply("http://h", "m", [{"role": "user", "content": "hi"}])
    assert reply == "Hello there"
    assert capsys.readouterr().out == "Hello there\n"
    assert post.call_args[1]["json"]["stream"] is True


def test_stream_reply_sends_the_whole_history():
    history = [{"role": "system", "content": "s"}, {"role": "user", "content": "hi"}]
    with mock.patch("requests.post", return_value=words("ok")) as post:
        chat.stream_reply("http://h", "m", history)
    assert post.call_args[1]["json"]["messages"] == history


def test_thinking_indicator_is_shown_once_and_thinking_text_is_not_printed(capsys):
    response = stream_of(
        {"message": {"thinking": "let me think", "content": ""}},
        {"message": {"thinking": " more", "content": ""}},
        {"message": {"content": "Answer"}},
        {"message": {"content": ""}, "done": True},
    )
    with mock.patch("requests.post", return_value=response):
        reply = chat.stream_reply("http://h", "m", [])
    out = capsys.readouterr().out
    assert reply == "Answer"
    assert out.count("(thinking...)") == 1 and "let me think" not in out


def test_unreachable_server_gives_a_clear_message():
    with mock.patch("requests.post", side_effect=requests.ConnectionError):
        with pytest.raises(RuntimeError, match="ollama serve"):
            chat.stream_reply("http://h", "m", [])


def test_missing_model_gives_the_exact_pull_command():
    with mock.patch("requests.post", return_value=mock.Mock(status_code=404)):
        with pytest.raises(RuntimeError, match="ollama pull nomodel"):
            chat.stream_reply("http://h", "nomodel", [])


def test_timeout_gives_a_clear_message():
    with mock.patch("requests.post", side_effect=requests.Timeout):
        with pytest.raises(RuntimeError, match="timed out"):
            chat.stream_reply("http://h", "m", [])


def test_error_inside_the_stream_is_raised():
    with mock.patch("requests.post", return_value=stream_of({"error": "model crashed"})):
        with pytest.raises(RuntimeError, match="model crashed"):
            chat.stream_reply("http://h", "m", [])


def test_other_http_errors_are_reported_with_the_status():
    response = mock.Mock(status_code=500, text="boom")
    with mock.patch("requests.post", return_value=response):
        with pytest.raises(RuntimeError, match="HTTP 500"):
            chat.stream_reply("http://h", "m", [])


def test_config_file_overrides_defaults(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"chat_model": "other:1b"}))
    config = chat.load_config(path)
    assert config["chat_model"] == "other:1b" and config["host"] == chat.DEFAULTS["host"]


def test_missing_config_file_falls_back_to_defaults(tmp_path):
    assert chat.load_config(tmp_path / "nope.json") == chat.DEFAULTS


def test_broken_config_file_exits_with_a_message(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{not json")
    with pytest.raises(SystemExit, match="cannot read config"):
        chat.load_config(path)


def test_system_prompt_is_read_from_a_file(tmp_path):
    path = tmp_path / "p.txt"
    path.write_text("  Be brief.\n")
    assert chat.load_system_prompt(path) == "Be brief."


def test_missing_system_prompt_exits_with_a_message(tmp_path):
    with pytest.raises(SystemExit, match="cannot read system prompt"):
        chat.load_system_prompt(tmp_path / "nope.txt")


def run_main(monkeypatch, inputs, replies, argv=("chat.py",)):
    """Drive main() with scripted user input and scripted model replies; return the messages sent."""
    sent = []
    typed = iter(inputs)

    def fake_input(prompt=""):
        try:
            value = next(typed)
        except StopIteration:
            raise EOFError
        if isinstance(value, BaseException):
            raise value
        return value

    def fake_stream(host, model, messages):
        sent.append((model, [dict(m) for m in messages]))
        reply = next(replies)
        if isinstance(reply, BaseException):
            raise reply
        return reply

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(chat, "stream_reply", fake_stream)
    monkeypatch.setattr(sys, "argv", list(argv))
    chat.main()
    return sent


def test_history_is_sent_on_every_turn(monkeypatch):
    sent = run_main(monkeypatch, ["hello", "and now?", "exit"], iter(["first", "second"]))
    _, second_turn = sent[1]
    assert [m["role"] for m in second_turn] == ["system", "user", "assistant", "user"]
    assert second_turn[2]["content"] == "first" and second_turn[3]["content"] == "and now?"


def test_empty_input_is_ignored_with_a_hint(monkeypatch, capsys):
    sent = run_main(monkeypatch, ["", "   ", "exit"], iter([]))
    assert sent == []
    assert capsys.readouterr().out.count("empty input") == 2


def test_a_failed_turn_does_not_pollute_the_history(monkeypatch, capsys):
    sent = run_main(monkeypatch, ["one", "two", "exit"], iter([RuntimeError("Cannot reach Ollama"), "fine"]))
    assert "Error: Cannot reach Ollama" in capsys.readouterr().out
    assert [m["content"] for m in sent[1][1] if m["role"] == "user"] == ["two"]


def test_ctrl_c_during_a_reply_cancels_only_that_reply(monkeypatch, capsys):
    sent = run_main(monkeypatch, ["slow question", "next", "exit"], iter([KeyboardInterrupt(), "ok"]))
    assert "(reply cancelled)" in capsys.readouterr().out
    assert [m["content"] for m in sent[1][1] if m["role"] == "user"] == ["next"]


@pytest.mark.parametrize("quit_input", [EOFError(), KeyboardInterrupt(), "exit", "QUIT"])
def test_the_chat_can_be_left_in_four_ways(monkeypatch, quit_input):
    assert run_main(monkeypatch, [quit_input], iter([])) == []


def test_model_argument_overrides_the_config(monkeypatch):
    sent = run_main(monkeypatch, ["hi", "exit"], iter(["x"]), argv=("chat.py", "other:7b"))
    assert sent[0][0] == "other:7b"


def test_model_defaults_to_the_config_file(monkeypatch):
    sent = run_main(monkeypatch, ["hi", "exit"], iter(["x"]))
    assert sent[0][0] == chat.load_config(chat.ROOT / "config.json")["chat_model"]
