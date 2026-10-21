"""Unit tests for External Structured Memory / Second Brain (feature M3 - 2 stars).
Validates cross-session persistence, vector indexing, query detection, and recall injection.
"""
from pathlib import Path
import sys
from unittest import mock
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import chat
from src.memory import SessionMemory


def fake_embed(texts, model="nomic-embed-text"):
    """Deterministic vector generator based on keywords."""
    vectors = []
    for t in texts:
        t_low = t.lower()
        if "tcp" in t_low or "network" in t_low or "osi" in t_low:
            vectors.append([1.0, 0.0, 0.0])
        elif "biology" in t_low or "photosynthesis" in t_low or "plant" in t_low:
            vectors.append([0.0, 1.0, 0.0])
        else:
            vectors.append([0.0, 0.0, 1.0])
    return vectors


@pytest.fixture
def memory_env(tmp_path):
    mem = SessionMemory(base_dir=tmp_path / ".sensai")
    return mem


def test_session_save_and_load(memory_env):
    turns = [
        {"role": "user", "content": "My favorite programming language is Python."},
        {"role": "assistant", "content": "Understood, Python is noted."},
    ]
    path = memory_env.save_session("session_1", turns, title="User Preferences")
    assert path.exists()

    loaded = memory_env.load_session("session_1")
    assert loaded["id"] == "session_1"
    assert loaded["title"] == "User Preferences"
    assert len(loaded["turns"]) == 2
    assert loaded["turns"][0]["content"] == "My favorite programming language is Python."


def test_list_sessions_returns_metadata(memory_env):
    memory_env.save_session("s1", [{"role": "user", "content": "turn 1"}], title="First Session")
    memory_env.save_session("s2", [{"role": "user", "content": "turn 2"}], title="Second Session")

    sessions = memory_env.list_sessions()
    assert len(sessions) == 2
    titles = [s["title"] for s in sessions]
    assert "First Session" in titles and "Second Session" in titles


def test_index_sessions_and_cross_session_recall(memory_env):
    # Session A: Networking
    memory_env.save_session(
        "session_net",
        [
            {"role": "user", "content": "Explain TCP handshake protocol."},
            {"role": "assistant", "content": "TCP uses SYN, SYN-ACK, ACK to establish connection."},
        ],
        title="Network Architecture",
    )

    # Session B: Biology
    memory_env.save_session(
        "session_bio",
        [
            {"role": "user", "content": "How does photosynthesis work in green plants?"},
            {"role": "assistant", "content": "Plants convert sunlight, water, and CO2 into glucose and oxygen."},
        ],
        title="Plant Biology",
    )

    # Index both sessions
    indexed = memory_env.index_sessions(embed_fn=fake_embed)
    assert len(indexed) >= 2

    # Query from a third context inquiring about networking
    results = memory_env.search_memory("What did we say about TCP earlier?", embed_fn=fake_embed, top_k=2)
    assert len(results) > 0
    top_hit = results[0]
    assert top_hit["session_id"] == "session_net"
    assert "TCP" in top_hit["text"]
    assert top_hit["similarity"] > 0.8


def test_is_recall_query_pattern_matching(memory_env):
    # Positive signals
    assert memory_env.is_recall_query("Remember when we talked about databases?") is True
    assert memory_env.is_recall_query("As we discussed earlier in our previous conversation") is True
    assert memory_env.is_recall_query("What did we discuss about Python last time?") is True
    assert memory_env.is_recall_query("De quoi avons-nous parlé hier ?") is True
    assert memory_env.is_recall_query("Rappelle-toi notre session") is True

    # Negative signals (regular questions)
    assert memory_env.is_recall_query("What is 1 + 1?") is False
    assert memory_env.is_recall_query("Explain section 2 of the document.") is False
    assert memory_env.is_recall_query("Hello there") is False


def test_format_memory_context(memory_env):
    memories = [
        {"session_title": "Database Prep", "role": "user", "text": "PostgreSQL port is 5432."},
        {"session_title": "Database Prep", "role": "assistant", "text": "Confirmed, default port is 5432."},
    ]
    context = memory_env.format_memory_context(memories)
    assert "[Cross-Session Recall / External Memory]" in context
    assert "PostgreSQL port is 5432." in context
    assert "Database Prep" in context


def test_empty_or_missing_memory_search_graceful(memory_env):
    results = memory_env.search_memory("Anything stored?", embed_fn=fake_embed)
    assert results == []


def test_cli_recall_injection(monkeypatch, tmp_path):
    """Test CLI injects recalled facts when recall query is typed."""
    mem_dir = tmp_path / ".sensai"
    dummy_embed = lambda texts, m: [[1.0, 0.0] for _ in texts]
    mem = SessionMemory(base_dir=mem_dir, embed_fn=dummy_embed)
    mem.save_session(
        "s_prior",
        [{"role": "user", "content": "Our server IP is 192.168.1.100."}],
        title="Server Config",
    )
    mem.index_sessions()

    sent = []
    inputs = ["Remember what our server IP was?", "exit"]
    typed = iter(inputs)

    def fake_stream(host, model, messages):
        sent.append(messages)
        return "Your server IP was 192.168.1.100."

    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))
    monkeypatch.setattr(chat, "stream_reply", fake_stream)
    monkeypatch.setattr(chat, "SessionMemory", lambda **kwargs: mem)
    monkeypatch.setattr(sys, "argv", ["chat.py"])

    chat.main()

    assert len(sent) == 1
    system_messages = [m["content"] for m in sent[0] if m.get("role") == "system"]
    assert any("Cross-Session Recall" in s for s in system_messages)
    assert any("192.168.1.100" in s for s in system_messages)


def test_web_ui_memory_endpoints(tmp_path, monkeypatch):
    import importlib.util
    import threading
    import requests

    spec = importlib.util.spec_from_file_location("web_ui_server", ROOT / "WEB-UI" / "server.py")
    web = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(web)

    dummy_embed = lambda texts, model, host=None: [[1.0, 0.0] for _ in texts]
    monkeypatch.setattr("src.ollama_client.embed", dummy_embed)

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    mem = SessionMemory(base_dir=ws_dir / ".sensai", embed_fn=lambda texts, m: [[1.0, 0.0] for _ in texts])
    mem.save_session("s_web", [{"role": "user", "content": "Favorite fruit is mango."}], title="Web Session")
    mem.index_sessions()

    app = web.App({"host": "http://127.0.0.1:11434", "chat_model": "qwen3:4b", "embed_model": "nomic-embed-text"}, workspace=ws_dir, data_dir=data_dir)

    server = web.make_server(app, "127.0.0.1", 0)
    port = server.server_address[1]
    t = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    t.start()

    try:
        r = requests.get(f"http://127.0.0.1:{port}/api/memory/sessions")
        assert r.status_code == 200
        data = r.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["title"] == "Web Session"

        r_post = requests.post(f"http://127.0.0.1:{port}/api/memory/search", json={"query": "mango"})
        assert r_post.status_code == 200
        search_data = r_post.json()
        assert len(search_data["results"]) == 1
        assert "mango" in search_data["results"][0]["text"].lower()
    finally:
        server.shutdown()
        server.server_close()
