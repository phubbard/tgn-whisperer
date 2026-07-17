"""Tests for the home-page 'last updated' timestamp insertion."""
from tasks.build import apply_home_timestamp

STAMP = "_last updated July 17, 2026 at 9:13AM PDT_"
STAMP2 = "_last updated July 18, 2026 at 4:05PM PDT_"

PAGE = """## Welcome!

## What is TGN?

Some intro text.

## What is this site?
_This_ site is a side project.

## Contact me
"""


def test_inserts_above_what_is_this_site():
    out = apply_home_timestamp(PAGE, STAMP)
    assert STAMP in out
    # timestamp appears immediately before the anchor
    assert f"{STAMP}\n\n## What is this site?" in out
    # inserted before, not after, the anchor
    assert out.index(STAMP) < out.index("## What is this site?")
    # original content preserved
    assert "## What is TGN?" in out and "## Contact me" in out


def test_idempotent_replaces_existing():
    once = apply_home_timestamp(PAGE, STAMP)
    twice = apply_home_timestamp(once, STAMP2)
    assert twice.count("_last updated ") == 1  # no duplication
    assert STAMP2 in twice and STAMP not in twice


def test_fallback_appends_when_anchor_missing():
    text = "## Welcome!\n\nNo standard sections here.\n"
    out = apply_home_timestamp(text, STAMP)
    assert STAMP in out
    assert out.count("_last updated ") == 1


def test_only_one_anchor_replaced_ever():
    # running the full build many times must never accumulate timestamps
    text = PAGE
    for stamp in (STAMP, STAMP2, STAMP, STAMP2):
        text = apply_home_timestamp(text, stamp)
    assert text.count("_last updated ") == 1
