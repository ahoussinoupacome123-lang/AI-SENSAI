"""Save/load chunks + vectors in index.json and search by cosine similarity."""
import json
from pathlib import Path

import numpy as np


class StoreError(ValueError):
    """Raised when the index is in an unusable state."""


def save(chunks, path):
    """Persist chunks (list of dicts with a 'vector' key) to *path* as JSON.

    Each chunk must be a dict with at least: id, text, page, vector.
    The vector (list of floats) is stored as-is; JSON handles it fine.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {**{k: v for k, v in c.items() if k != "vector"}, "vector": list(c["vector"])}
        for c in chunks
    ]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def load(path):
    """Load chunks from *path*. Returns a list of dicts (same shape as save input)."""
    path = Path(path)
    if not path.exists():
        raise StoreError(f"Index file not found: {path}")
    data = json.loads(path.read_text())
    return data


def search(chunks, vector, k):
    """Return the *k* chunks closest to *vector* by cosine similarity, best first.

    Parameters
    ----------
    chunks : list of dicts, each with a ``vector`` key (list of floats).
    vector : list or array of floats (the query vector).
    k      : int – number of results to return.

    Raises
    ------
    StoreError  – if chunks is empty.
    """
    if not chunks:
        raise StoreError("The index is empty. Run ingestion first.")

    q = np.array(vector, dtype=float)
    q_norm = np.linalg.norm(q)
    if q_norm == 0.0:
        # Zero vector: all similarities are 0; return first k chunks in order.
        return chunks[:k]

    scores = []
    for chunk in chunks:
        v = np.array(chunk["vector"], dtype=float)
        v_norm = np.linalg.norm(v)
        if v_norm == 0.0:
            sim = 0.0
        else:
            sim = float(np.dot(q, v) / (q_norm * v_norm))
        scores.append((sim, chunk))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scores[:k]]
