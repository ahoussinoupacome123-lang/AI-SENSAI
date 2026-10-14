"""Save/load chunks + vectors in index.json and search by cosine similarity."""


def save(chunks, path):
    raise NotImplementedError


def load(path):
    raise NotImplementedError


def search(chunks, vector, k):
    """Return the k chunks closest to vector (cosine similarity, numpy)."""
    raise NotImplementedError
