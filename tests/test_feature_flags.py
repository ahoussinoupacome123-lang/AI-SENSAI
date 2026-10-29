"""Unit tests for Feature Flags system (task P9).
Verifies component enabling/disabling via config file, CLI arguments, and Web UI overrides.
"""
from pathlib import Path
import json
import sys
from unittest.mock import Mock, patch
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import cli, judge, pipeline

CONFIG_TEMPLATE = {
    "host": "http://localhost:11434",
    "chat_model": "qwen3:4b",
    "judge_model": "qwen3:4b",
    "embed_model": "nomic-embed-text",
    "chunk_size": 100,
    "chunk_overlap": 10,
    "top_k": 2,
    "feature_flags": {
        "rag": True,
        "judge": True,
        "quote_check": True,
        "cache": True
    }
}


def test_load_config_defaults_all_feature_flags(tmp_path):
    cfg_file = tmp_path / "cfg.json"
    raw_cfg = {**CONFIG_TEMPLATE, "feature_flags": {}}
    cfg_file.write_text(json.dumps(raw_cfg))

    loaded = cli.load_config(cfg_file)
    assert "feature_flags" in loaded
    assert loaded["feature_flags"]["rag"] is True
    assert loaded["feature_flags"]["judge"] is True
    assert loaded["feature_flags"]["quote_check"] is True


def test_disable_judge_via_config_skips_judge_call():
    cfg = dict(CONFIG_TEMPLATE)
    cfg["feature_flags"] = {"judge": False, "rag": True, "quote_check": True}

    fake_retrieval = {
        "question": "What is Python?",
        "answer": "A programming language",
        "page": 1,
        "quote": "A programming language",
        "status": "supported",
        "chunks": [{"page": 1, "text": "A programming language"}]
    }

    with patch.object(pipeline, "retrieve_and_answer", return_value=fake_retrieval), \
         patch.object(judge, "evaluate") as mock_judge:
        checked = cli.answer_question("What is Python?", [], cfg)

    assert mock_judge.call_count == 0
    assert checked["verdict"] == "disabled"
    assert "disabled by feature flag" in checked["reason"]


def test_cli_no_judge_flag_disables_judge(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")
    qfile = tmp_path / "q.txt"
    qfile.write_text("What is AI?\n")
    cfg_file = tmp_path / "cfg.json"
    cfg_file.write_text(json.dumps(CONFIG_TEMPLATE))

    fake_retrieval = {
        "question": "What is AI?",
        "answer": "Artificial intelligence",
        "page": 1,
        "quote": "Artificial intelligence",
        "status": "supported",
        "chunks": []
    }

    with patch("src.cli.ingestion.ingest", return_value=[]), \
         patch("src.cli.pipeline.retrieve_and_answer", return_value=fake_retrieval), \
         patch("src.cli.judge.evaluate") as mock_judge, \
         patch("src.cli.writer.upsert_section"):
        exit_code = cli.main([str(pdf), str(qfile), "--config", str(cfg_file), "--no-judge"])

    assert exit_code == 0
    assert mock_judge.call_count == 0


def test_cli_no_rag_flag_answers_without_retrieval():
    cfg = dict(CONFIG_TEMPLATE)
    cfg["feature_flags"] = {"rag": False, "judge": True, "quote_check": True}

    fake_answer = {
        "question": "What is math?",
        "answer": "A science of numbers",
        "page": 0,
        "quote": "",
        "status": "no-rag"
    }

    with patch.object(pipeline, "retrieve_and_answer") as mock_rag, \
         patch.object(pipeline, "answer", return_value=fake_answer), \
         patch.object(judge, "evaluate", return_value={"verdict": "faithful", "reason": "ok"}):
        checked = cli.answer_question("What is math?", [], cfg)

    assert mock_rag.call_count == 0
    assert checked["status"] == "no-rag"
    assert checked["page"] == 0


def test_cli_no_quote_check_flag_skips_quote_validation():
    cfg = dict(CONFIG_TEMPLATE)
    cfg["feature_flags"] = {"rag": True, "judge": False, "quote_check": False}

    fake_retrieval = {
        "question": "Question?",
        "answer": "Answer",
        "page": 1,
        "quote": "Quote",
        "status": "supported",
        "chunks": []
    }

    with patch.object(pipeline, "retrieve_and_answer", return_value=fake_retrieval):
        checked = cli.answer_question("Question?", [], cfg)

    assert checked["status"] == "skipped"


def test_web_ui_feature_flags_override_endpoint(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("web_ui_server", ROOT / "WEB-UI" / "server.py")
    web = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(web)

    app = web.App(CONFIG_TEMPLATE, workspace=tmp_path / "ws", data_dir=tmp_path / "data")
    assert app.config()["feature_flags"]["judge"] is True

    # Override judge to False
    app.set_overrides({"feature_flags": {"judge": False}})
    assert app.config()["feature_flags"]["judge"] is False
    assert app.config()["feature_flags"]["rag"] is True

    # Reset overrides
    app.reset_overrides()
    assert app.config()["feature_flags"]["judge"] is True
