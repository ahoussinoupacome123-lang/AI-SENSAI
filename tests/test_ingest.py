import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdf_factory import make_blank_pdf, make_text_pdf  # noqa: E402
from src import ollama_client, store  # noqa: E402
from src.ingestion import IngestionError, NoTextError, index_path, ingest  # noqa: E402

CONFIG = {
    "host": "http://fake:1",
    "embed_model": "fake-embed",
    "chunk_size": 100,
    "chunk_overlap": 20,
    "embed_batch_size": 4,
}
PAGES = [
    "Networks connect computers so they can share data across a building. " * 3,
    "The OSI model has seven layers from the physical layer to the application layer. " * 3,
    "TCP was specified in RFC 793 and gives reliable ordered delivery of bytes. " * 3,
]


@pytest.fixture
def pdf(tmp_path):
    path = tmp_path / "course.pdf"
    make_text_pdf(path, PAGES)
    return path


@pytest.fixture
def fakes(monkeypatch):
    """Replace the Ollama client and the store (not written yet) with in-memory fakes."""
    calls = []

    def fake_embed(texts, model, host=None):
        calls.append({"texts": list(texts), "model": model, "host": host})
        return [[float(len(t)), 1.0] for t in texts]

    def fake_save(chunks, path):
        Path(path).write_text(json.dumps(chunks))

    def fake_load(path):
        return json.loads(Path(path).read_text())

    monkeypatch.setattr(ollama_client, "embed", fake_embed)
    monkeypatch.setattr(store, "save", fake_save)
    monkeypatch.setattr(store, "load", fake_load)
    return calls


def test_one_record_per_chunk_with_all_fields(pdf, fakes):
    records = ingest(pdf, CONFIG)
    assert len(records) == sum(len(call["texts"]) for call in fakes)
    for record in records:
        assert set(record) == {"id", "text", "page", "vector"}
        assert record["page"] in (1, 2, 3)
        assert record["vector"] == [float(len(record["text"])), 1.0]


def test_ids_are_unique_and_sequential(pdf, fakes):
    records = ingest(pdf, CONFIG)
    assert [r["id"] for r in records] == list(range(len(records)))


def test_every_page_is_represented(pdf, fakes):
    assert {r["page"] for r in ingest(pdf, CONFIG)} == {1, 2, 3}


def test_embedding_uses_config_model_host_and_batches(pdf, fakes):
    ingest(pdf, CONFIG)
    assert all(call["model"] == "fake-embed" and call["host"] == "http://fake:1" for call in fakes)
    assert all(len(call["texts"]) <= 4 for call in fakes)
    assert len(fakes) > 1  # several batches were needed


def test_index_is_saved_next_to_the_pdf(pdf, fakes):
    ingest(pdf, CONFIG)
    assert index_path(pdf) == pdf.with_name("course.index.json")
    assert index_path(pdf).exists()


def test_second_run_reuses_the_index_without_embedding(pdf, fakes):
    first = ingest(pdf, CONFIG)
    calls_after_first = len(fakes)
    second = ingest(pdf, CONFIG)
    assert len(fakes) == calls_after_first
    assert second == first


def test_force_rebuilds_the_index(pdf, fakes):
    ingest(pdf, CONFIG)
    calls_after_first = len(fakes)
    ingest(pdf, CONFIG, force=True)
    assert len(fakes) == 2 * calls_after_first


def test_index_older_than_the_pdf_is_rebuilt(pdf, fakes):
    ingest(pdf, CONFIG)
    calls_after_first = len(fakes)
    old = index_path(pdf).stat().st_mtime - 100
    os.utime(index_path(pdf), (old, old))
    ingest(pdf, CONFIG)
    assert len(fakes) == 2 * calls_after_first


def test_scanned_pdf_raises_and_embeds_nothing(tmp_path, fakes):
    path = tmp_path / "scan.pdf"
    make_blank_pdf(path)
    with pytest.raises(NoTextError):
        ingest(path, CONFIG)
    assert fakes == []
    assert not index_path(path).exists()


def test_missing_pdf_raises_ingestion_error(tmp_path, fakes):
    with pytest.raises(IngestionError, match="not found"):
        ingest(tmp_path / "nope.pdf", CONFIG)


def test_embedding_failure_leaves_no_partial_index(pdf, monkeypatch):
    def failing_embed(texts, model, host=None):
        raise RuntimeError("Cannot reach Ollama")

    monkeypatch.setattr(ollama_client, "embed", failing_embed)
    with pytest.raises(RuntimeError, match="Cannot reach Ollama"):
        ingest(pdf, CONFIG)
    assert not index_path(pdf).exists()


def test_wrong_number_of_vectors_raises(pdf, monkeypatch):
    monkeypatch.setattr(ollama_client, "embed", lambda texts, model, host=None: [[1.0]])
    monkeypatch.setattr(store, "save", lambda chunks, path: None)
    with pytest.raises(IngestionError, match="vectors"):
        ingest(pdf, CONFIG)


@pytest.mark.parametrize("content", ["{ not json", "", "{}", "[]", '[{"id": 0}]', "[1, 2]"])
def test_unreadable_or_invalid_index_gives_a_message_that_says_how_to_fix_it(pdf, fakes, content):
    ingest(pdf, CONFIG)                                  # builds a good index
    index_path(pdf).write_text(content)
    calls_before = len(fakes)
    with pytest.raises(IngestionError, match="--force"):
        ingest(pdf, CONFIG)
    assert len(fakes) == calls_before                    # nothing was embedded or overwritten
    assert index_path(pdf).read_text() == content


def test_force_replaces_a_corrupt_index(pdf, fakes):
    ingest(pdf, CONFIG)
    index_path(pdf).write_text("{ not json")
    records = ingest(pdf, CONFIG, force=True)
    assert records and json.loads(index_path(pdf).read_text())
