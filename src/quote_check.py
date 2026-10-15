"""Deterministic quote check: is the model's quote really in the retrieved passages?

Plain string matching, no model involved. It proves the quote exists in the text we gave
the model; it does not prove that the answer is a correct reading of it.
"""
import unicodedata

_REPLACEMENTS = {
    "‘": "'", "’": "'", "‚": "'", "′": "'",   # curly single quotes, prime
    "“": '"', "”": '"', "„": '"', "″": '"',   # curly double quotes
    "‐": "-", "‑": "-", "‒": "-", "–": "-",   # hyphens and dashes
    "—": "-", "―": "-", "−": "-",
    "­": "",                                                   # soft hyphen
}


def normalize(text):
    """Lower-case, fold ligatures and look-alike characters, collapse whitespace."""
    text = unicodedata.normalize("NFKC", str(text))
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return " ".join(text.lower().split())


def quote_is_supported(quote, chunks):
    """True if `quote` appears inside one of the chunks (case, spaces and typography ignored).

    An empty quote is never supported: the caller treats a refusal ("the document does not
    cover this") separately. `chunks` are dicts with a "text" key.
    """
    needle = normalize(quote or "")
    if not needle:
        return False
    return any(needle in normalize(chunk["text"]) for chunk in chunks)
