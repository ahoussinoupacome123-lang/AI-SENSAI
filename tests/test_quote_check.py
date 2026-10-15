import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import pipeline  # noqa: E402
from src.quote_check import normalize, quote_is_supported  # noqa: E402

CHUNKS = [
    {"id": 0, "page": 1, "text": "The OSI model has seven layers: physical, data link, network and more."},
    {"id": 1, "page": 2, "text": "It's a well-known rule: TCP opens a connection with a three-way handshake."},
    {"id": 2, "page": 3, "text": "Les accents é à ç sont conservés dans le texte."},
]


def test_exact_quote_is_supported():
    assert quote_is_supported("The OSI model has seven layers", CHUNKS)


def test_case_and_extra_spaces_are_ignored():
    assert quote_is_supported("  the   OSI MODEL\nhas seven   layers ", CHUNKS)


def test_invented_quote_is_not_supported():
    assert not quote_is_supported("The OSI model has eight layers", CHUNKS)


def test_curly_apostrophe_matches_a_straight_one():
    assert quote_is_supported("It’s a well-known rule", CHUNKS)


def test_straight_apostrophe_matches_a_curly_one():
    chunks = [{"text": "It’s a well-known rule"}]
    assert quote_is_supported("It's a well-known rule", chunks)


@pytest.mark.parametrize("dash", ["‐", "‑", "–", "—", "−"])
def test_dashes_match_a_plain_hyphen(dash):
    assert quote_is_supported(f"a well{dash}known rule", CHUNKS)


def test_ligatures_are_folded():
    chunks = [{"text": "Your ﬁnal presentation is a keynote"}]  # fi ligature as pypdf may return it
    assert quote_is_supported("Your final presentation", chunks)


def test_non_breaking_space_counts_as_a_space():
    assert quote_is_supported("seven layers", CHUNKS)


@pytest.mark.parametrize("empty", ["", "   ", "\n", None])
def test_empty_quote_is_never_supported(empty):
    assert not quote_is_supported(empty, CHUNKS)


def test_quote_found_in_any_chunk_not_just_the_first():
    assert quote_is_supported("three-way handshake", CHUNKS)


def test_no_chunks_means_not_supported():
    assert not quote_is_supported("anything", [])


def test_accents_are_kept():
    assert quote_is_supported("accents é à ç sont", CHUNKS)
    assert not quote_is_supported("accents e a c sont", CHUNKS)


def test_a_quote_stitched_from_two_chunks_is_not_supported():
    assert not quote_is_supported("data link, network and more. It's a well-known", CHUNKS)


def test_normalize_is_idempotent():
    once = normalize("It’s  A – test ﬁx")
    assert normalize(once) == once == "it's a - test fix"


def test_pipeline_still_exposes_the_function_with_the_same_behaviour():
    assert pipeline.quote_is_supported is quote_is_supported
