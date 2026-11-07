"""Tests for catalogue feature X2: Branching — Resume & Interrupt.
Verifies message editing, conversation forking, history archiving, and CLI command execution.
"""
from pathlib import Path
import sys
from unittest import mock
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import chat


def test_find_user_indices_empty_and_system_only():
    assert chat.find_user_indices([]) == []
    assert chat.find_user_indices([{"role": "system", "content": "prompt"}]) == []


def test_find_user_indices_multi_turns():
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
    ]
    assert chat.find_user_indices(messages) == [1, 3]


def test_edit_and_branch_no_user_turns_raises():
    with pytest.raises(ValueError, match="No user messages"):
        chat.edit_and_branch([{"role": "system", "content": "s"}], "new")


def test_edit_and_branch_invalid_turn_index_raises():
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u1"},
    ]
    with pytest.raises(ValueError, match="Turn number must be an integer between 1 and 1"):
        chat.edit_and_branch(messages, "new", user_turn_number=2)
    with pytest.raises(ValueError, match="Turn number must be an integer between 1 and 1"):
        chat.edit_and_branch(messages, "new", user_turn_number=0)


def test_edit_and_branch_defaults_to_last_user_turn():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "question 1"},
        {"role": "assistant", "content": "answer 1"},
        {"role": "user", "content": "question 2"},
        {"role": "assistant", "content": "answer 2"},
    ]
    new_history, archived = chat.edit_and_branch(messages, "question 2 modified")

    # Archived must be untouched
    assert len(archived) == 5
    assert archived[3]["content"] == "question 2"

    # New history truncated to turn 2 without assistant 2
    assert len(new_history) == 4
    assert [m["role"] for m in new_history] == ["system", "user", "assistant", "user"]
    assert new_history[3]["content"] == "question 2 modified"


def test_edit_and_branch_intermediate_turn_truncates_future_turns():
    """Editing message 1 in a 3-turn chat regenerates from the new message and archives old branch."""
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "turn 1 original"},
        {"role": "assistant", "content": "reply 1"},
        {"role": "user", "content": "turn 2"},
        {"role": "assistant", "content": "reply 2"},
        {"role": "user", "content": "turn 3"},
        {"role": "assistant", "content": "reply 3"},
    ]
    new_history, archived = chat.edit_and_branch(messages, "turn 1 branched", user_turn_number=1)

    # Old branch intact
    assert len(archived) == 7
    assert archived[1]["content"] == "turn 1 original"

    # New branch only contains system prompt and edited turn 1
    assert len(new_history) == 2
    assert new_history[0] == {"role": "system", "content": "sys"}
    assert new_history[1] == {"role": "user", "content": "turn 1 branched"}


def test_cli_edit_command_creates_branch_and_regenerates(monkeypatch):
    """Test CLI interactive /edit command forks and re-runs generation."""
    sent = []
    inputs = [
        "What is 2+2?",
        "What is 3+3?",
        "/edit 1 What is 10+10?",
        "exit",
    ]
    replies = iter(["4", "6", "20"])
    typed = iter(inputs)

    def fake_input(prompt=""):
        try:
            return next(typed)
        except StopIteration:
            raise EOFError

    def fake_stream(host, model, messages):
        sent.append((model, [dict(m) for m in messages]))
        return next(replies)

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(chat, "stream_reply", fake_stream)
    monkeypatch.setattr(sys, "argv", ["chat.py"])

    chat.main()

    # 3 stream calls: turn 1, turn 2, then branched turn 1
    assert len(sent) == 3
    # Turn 1
    assert sent[0][1][-1]["content"] == "What is 2+2?"
    # Turn 2
    assert sent[1][1][-1]["content"] == "What is 3+3?"
    # Branched turn 1: only system prompt + edited question
    assert len(sent[2][1]) == 2
    assert sent[2][1][0]["role"] == "system"
    assert sent[2][1][1] == {"role": "user", "content": "What is 10+10?"}


def test_cli_history_and_branches_commands(monkeypatch, capsys):
    """Test CLI inspect commands (/history, /branches, /switch)."""
    inputs = [
        "hello",
        "/edit hello again",
        "/history",
        "/branches",
        "/switch 1",
        "exit",
    ]
    replies = iter(["hi", "hi again"])
    typed = iter(inputs)

    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))
    monkeypatch.setattr(chat, "stream_reply", lambda h, m, msgs: next(replies))
    monkeypatch.setattr(sys, "argv", ["chat.py"])

    chat.main()
    out = capsys.readouterr().out
    assert "[Branch created: editing turn 1]" in out
    assert "[1] hello again" in out
    assert "[Branch 1]" in out
    assert "[Switched to branch 1]" in out


# ---------- Interrupt and redirect (X2) ----------

def _run_cli(monkeypatch, inputs, fake_stream):
    typed = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))
    monkeypatch.setattr(chat, "stream_reply", fake_stream)
    monkeypatch.setattr(sys, "argv", ["chat.py"])
    chat.main()


def test_stream_reply_ctrl_c_mid_reply_raises_with_the_partial_text():
    """Ctrl+C after some tokens: the text so far comes back, and the connection is closed (Ollama stops)."""
    import json

    def lines():
        yield json.dumps({"message": {"content": "Once upon "}}).encode()
        yield json.dumps({"message": {"content": "a time"}}).encode()
        raise KeyboardInterrupt

    response = mock.Mock(status_code=200)
    response.iter_lines.return_value = lines()
    with mock.patch("requests.post", return_value=response):
        with pytest.raises(chat.ReplyInterrupted) as info:
            chat.stream_reply("http://h", "m", [{"role": "user", "content": "story"}])
    assert info.value.partial == "Once upon a time"
    response.close.assert_called_once()


def test_stream_reply_ctrl_c_before_any_text_is_a_plain_cancel():
    def lines():
        raise KeyboardInterrupt
        yield b""  # pragma: no cover - makes this a generator

    response = mock.Mock(status_code=200)
    response.iter_lines.return_value = lines()
    with mock.patch("requests.post", return_value=response):
        with pytest.raises(KeyboardInterrupt):
            chat.stream_reply("http://h", "m", [{"role": "user", "content": "story"}])


def test_cli_interrupt_keeps_partial_reply_and_next_message_redirects(monkeypatch, capsys):
    sent = []

    def fake_stream(host, model, messages):
        sent.append([dict(m) for m in messages])
        if len(sent) == 1:
            raise chat.ReplyInterrupted("Once upon a time, in a far")
        return "A short one."

    _run_cli(monkeypatch, ["write a long story", "make it shorter", "exit"], fake_stream)
    redirect = sent[1]
    assert redirect[-3:] == [
        {"role": "user", "content": "write a long story"},
        {"role": "assistant", "content": "Once upon a time, in a far"},
        {"role": "user", "content": "make it shorter"},
    ]
    assert "Type your next message to redirect it" in capsys.readouterr().out


def test_cli_cancel_before_any_text_drops_the_unanswered_question(monkeypatch):
    sent = []

    def fake_stream(host, model, messages):
        sent.append([dict(m) for m in messages])
        if len(sent) == 1:
            raise KeyboardInterrupt
        return "ok"

    _run_cli(monkeypatch, ["first", "second", "exit"], fake_stream)
    assert [m["content"] for m in sent[1] if m["role"] == "user"] == ["second"]


def test_cli_interrupted_edit_keeps_partial_on_the_new_branch(monkeypatch):
    sent = []

    def fake_stream(host, model, messages):
        sent.append([dict(m) for m in messages])
        if len(sent) == 2:
            raise chat.ReplyInterrupted("Paris is")
        return "reply"

    _run_cli(monkeypatch, ["capital of Italy?", "/edit capital of France?", "in one word", "exit"], fake_stream)
    assert sent[2][-3:] == [
        {"role": "user", "content": "capital of France?"},
        {"role": "assistant", "content": "Paris is"},
        {"role": "user", "content": "in one word"},
    ]


def test_cli_switch_swaps_in_place_so_numbers_stay_stable(monkeypatch, capsys):
    replies = iter(["r1", "r2", "r3"])
    _run_cli(monkeypatch, ["v1", "/edit v2", "/edit v3", "/switch 1", "/history", "/switch 1", "/history", "exit"],
             lambda h, m, msgs: next(replies))
    out = capsys.readouterr().out
    # branch 1 = v1, branch 2 = v2, current = v3. /switch 1 -> v1 (v3 takes slot 1); /switch 1 again -> v3.
    first, second = out.split("[Switched to branch 1]")[1:3]
    assert "[1] v1" in first.split("[Switched")[0]
    assert "[1] v3" in second
