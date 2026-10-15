"""Tests for src/store.py (M2).

Run with: .venv/bin/python -m pytest tests/test_m2_store.py -v
"""
import json
import sys
import unittest
from pathlib import Path
import tempfile
import os

sys.path.insert(0, ".")
from src.store import save, load, search, StoreError


def _chunk(id_, vector):
    return {"id": id_, "text": f"text-{id_}", "page": id_, "vector": vector}


class TestSearch(unittest.TestCase):

    def test_order_a_b_c(self):
        """Chunks A=[0.9,0.1], B=[0,1], C=[-1,0] and query [1,0]: order is A, B, C."""
        A = _chunk("A", [0.9, 0.1])
        B = _chunk("B", [0.0, 1.0])
        C = _chunk("C", [-1.0, 0.0])
        result = search([A, B, C], [1.0, 0.0], k=3)
        self.assertEqual([r["id"] for r in result], ["A", "B", "C"])

    def test_k_larger_than_index(self):
        """k larger than the number of chunks returns all of them."""
        chunks = [_chunk(i, [float(i), 0.0]) for i in range(1, 4)]
        result = search(chunks, [1.0, 0.0], k=100)
        self.assertEqual(len(result), 3)

    def test_k_exact(self):
        chunks = [_chunk(i, [float(i), 0.0]) for i in range(1, 6)]
        result = search(chunks, [1.0, 0.0], k=2)
        self.assertEqual(len(result), 2)

    def test_empty_index_raises(self):
        """Empty index gives a clear error."""
        with self.assertRaises(StoreError):
            search([], [1.0, 0.0], k=4)

    def test_zero_vector_no_crash(self):
        """A zero query vector does not divide by zero."""
        chunks = [_chunk(1, [1.0, 0.0]), _chunk(2, [0.0, 1.0])]
        result = search(chunks, [0.0, 0.0], k=2)
        self.assertEqual(len(result), 2)  # returns chunks, no crash

    def test_chunk_with_zero_vector_no_crash(self):
        """A chunk with a zero vector is given similarity 0, no crash."""
        chunks = [_chunk(1, [1.0, 0.0]), _chunk(2, [0.0, 0.0])]
        result = search(chunks, [1.0, 0.0], k=2)
        self.assertEqual(result[0]["id"], 1)  # non-zero chunk comes first


class TestSaveLoad(unittest.TestCase):

    def test_save_then_load_identical(self):
        """save then load returns identical data."""
        original = [
            _chunk(1, [0.1, 0.2, 0.3]),
            _chunk(2, [0.4, 0.5, 0.6]),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.json"
            save(original, path)
            loaded = load(path)

        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["id"], 1)
        self.assertEqual(loaded[1]["id"], 2)
        self.assertAlmostEqual(loaded[0]["vector"][0], 0.1, places=6)
        self.assertAlmostEqual(loaded[1]["vector"][2], 0.6, places=6)

    def test_save_creates_parent_dir(self):
        """save creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "dir" / "index.json"
            save([_chunk(1, [1.0])], path)
            self.assertTrue(path.exists())

    def test_load_missing_file_raises(self):
        with self.assertRaises(StoreError):
            load("/nonexistent/path/index.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
