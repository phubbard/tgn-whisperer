"""Tests for transcription vocabulary corrections."""
import pytest

from text_corrections import normalize_transcript_text


@pytest.mark.parametrize("raw,expected", [
    # Grey NATO — "nado" family, various casings/spacings
    ("welcome to another episode of The Graynado", "welcome to another episode of The Grey NATO"),
    ("The Grey Nado is a podcast", "The Grey NATO is a podcast"),
    ("greynado", "Grey NATO"),
    ("gray nado", "Grey NATO"),
    ("GreyNado", "Grey NATO"),
    ("the gray-nado show", "the Grey NATO show"),
    ("Graynado's crew", "Grey NATO's crew"),
])
def test_grey_nato_nado_family(raw, expected):
    assert normalize_transcript_text(raw) == expected


@pytest.mark.parametrize("text", [
    # "nato" spelled forms and URLs must be left alone (URL-safe / strap-safe)
    "please visit thegreynato.com for details",
    "https://thegreynato.substack.com/p/episode",
    "I put it on a gray NATO strap",
    "The Grey NATO",
])
def test_grey_nato_leaves_urls_and_straps_untouched(text):
    assert normalize_transcript_text(text) == text


@pytest.mark.parametrize("raw,expected", [
    ("I read it on Hodinky", "I read it on Hodinkee"),
    ("over at Hodinki radio", "over at Hodinkee radio"),
    ("the Hodinke shop", "the Hodinkee shop"),
    ("Hodinkey", "Hodinkee"),
    ("Hodinkie", "Hodinkee"),
    ("works at Hoding", "works at Hodinkee"),
    ("Hodingki", "Hodinkee"),
])
def test_hodinkee_misspellings(raw, expected):
    assert normalize_transcript_text(raw) == expected


@pytest.mark.parametrize("text", [
    # correct spelling and its real domain must not be altered
    "Hodinkee published a review",
    "see hodinkee.com/shop for more",
])
def test_hodinkee_correct_form_untouched(text):
    assert normalize_transcript_text(text) == text


@pytest.mark.parametrize("raw,expected", [
    ("the Blompa Fifty Fathoms", "the Blancpain Fifty Fathoms"),
    ("a Blancpan diver", "a Blancpain diver"),
    ("two Blancpans", "two Blancpains"),
    ("the Aqua star Deepstar", "the Aquastar Deepstar"),
    ("my Pelegos 39", "my Pelagos 39"),
    ("a Vasheron Constantin", "a Vacheron Constantin"),
    ("the Odemar Piguet", "the Audemars Piguet"),
    ("a Tuder Black Bay", "a Tudor Black Bay"),
    ("the Omega Speed master", "the Omega Speedmaster"),
    ("a Longine watch", "a Longines watch"),
])
def test_watch_brand_corrections(raw, expected):
    assert normalize_transcript_text(raw) == expected


def test_correct_brand_names_untouched():
    text = "the Blancpain, Aquastar, Pelagos, Tudor and Longines are all correct"
    assert normalize_transcript_text(text) == text


def test_empty_and_none_safe():
    assert normalize_transcript_text("") == ""
    assert normalize_transcript_text(None) is None
