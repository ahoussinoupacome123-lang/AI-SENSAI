"""Tests for general knowledge fallback and basic query routing (D6).

Run with: .venv/bin/python -m pytest tests/test_general_fallback.py -v
"""
import pytest

from src import judge, pipeline, routing


def test_basic_math_queries():
    cases = [
        ("1 + 1", "2"),
        ("1+1=?", "2"),
        ("1 + 1 = combien", "2"),
        ("what is 2 + 2?", "4"),
        ("how much is 5 * 10", "50"),
        ("100 - 45", "55"),
        ("12 / 4", "3"),
        ("2 ^ 3", "8"),
        ("2 ** 4", "16"),
        ("10 % 3", "1"),
    ]
    for query, expected in cases:
        assert routing.is_math_query(query), f"Failed to identify math in: {query}"
        res = routing.solve_basic_query(query)
        assert res is not None, f"Failed to solve: {query}"
        assert res["answer"] == expected
        assert res["page"] == 0
        assert res["quote"] == ""
        assert res["status"] == "supported"


def test_division_by_zero_does_not_crash():
    res = routing.solve_basic_query("10 / 0")
    assert res is not None
    assert "divide by zero" in res["answer"].lower()
    assert res["page"] == 0


def test_greetings_and_identity_queries():
    greetings = [
        "hello",
        "Hello !",
        "hi",
        "Bonjour",
        "qui es-tu ?",
        "who are you?",
        "what can you do?",
        "aide",
        "help",
    ]
    for q in greetings:
        assert routing.is_greeting_query(q), f"Failed to recognize greeting: {q}"
        assert routing.is_general_query(q)
        res = routing.solve_basic_query(q)
        assert res is not None
        assert len(res["answer"]) > 5
        assert res["page"] == 0
        assert res["quote"] == ""


def test_document_queries_are_not_routed_to_fallback():
    doc_queries = [
        "What are the layers of the OSI model?",
        "What is an IPv6 address?",
        "Who invented the World Wide Web?",
        "In a bus topology, what happens when the cable breaks?",
        "What is the maximum payload of an Ethernet frame?",
        "Explain routing tables and default gateway.",
    ]
    for q in doc_queries:
        assert not routing.is_math_query(q), f"False positive math for: {q}"
        assert not routing.is_greeting_query(q), f"False positive greeting for: {q}"
        assert not routing.is_general_query(q), f"False positive general query for: {q}"
        assert routing.solve_basic_query(q) is None


def test_pipeline_answer_with_math_query():
    res = pipeline.answer("1 + 1 = combien", chunks=[], config={})
    assert res["question"] == "1 + 1 = combien"
    assert res["answer"] == "2"
    assert res["page"] == 0
    assert res["quote"] == ""
    assert res["status"] == "supported"


def test_pipeline_retrieve_and_answer_with_math_query():
    # Should not invoke embed or search
    res = pipeline.retrieve_and_answer("1 + 1", index_chunks=[], config={})
    assert res["answer"] == "2"
    assert res["chunks"] == []
    assert res["status"] == "supported"


def test_judge_evaluates_general_query_faithfully():
    verdict = judge.evaluate("1 + 1 = combien", "2", chunks=[], config={})
    assert verdict["verdict"] == "faithful"
    assert "reason" in verdict


def test_invalid_and_empty_inputs():
    assert not routing.is_general_query("")
    assert not routing.is_general_query(None)
    assert not routing.is_general_query(123)
    assert not routing.is_general_query("   ")
    assert routing.solve_basic_query("") is None
    assert routing.solve_basic_query(None) is None
    assert routing.solve_basic_query("this is just some random text") is None
