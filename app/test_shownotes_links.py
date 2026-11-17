"""Tests for repairing bare/broken @handle link text in shownotes.

TGN episodes 8 and 29 have Substack anchors whose visible text is just
"@" or "@ handle" (the handle half lived in a sibling anchor). The cache
stores that text verbatim; clean_handle_text() repairs it at render time.
"""

from related_links_collector.utils import clean_handle_text


def test_bare_at_derives_handle_from_url():
    assert clean_handle_text('@', 'https://soundcloud.com/Redbarcrew') == \
        '@Redbarcrew (SoundCloud)'


def test_split_handle_collapses_and_labels_platform():
    assert clean_handle_text('@ Redbarcrew', 'https://www.instagram.com/redbarcrew/') == \
        '@Redbarcrew (Instagram)'


def test_episode_8_twitter_variant():
    assert clean_handle_text('@ the_watchnerd', 'https://twitter.com/the_watchnerd') == \
        '@the_watchnerd (Twitter)'


def test_underscore_handle_from_url():
    assert clean_handle_text('@', 'https://soundcloud.com/the_watchnerd') == \
        '@the_watchnerd (SoundCloud)'


def test_ordinary_text_passes_through():
    text = 'Seiko Quartz Chrono from Harrier Pilot'
    assert clean_handle_text(text, 'https://www.instagram.com/p/BRJznvpjK1Y/') == text


def test_intact_handle_still_gets_platform_label():
    assert clean_handle_text('@jasonheaton', 'https://www.instagram.com/jasonheaton') == \
        '@jasonheaton (Instagram)'


def test_unknown_host_gets_no_platform_suffix():
    assert clean_handle_text('@', 'https://example.com/somebody') == '@somebody'


def test_text_mentioning_at_mid_sentence_unchanged():
    text = 'Dinner @ the summit'
    assert clean_handle_text(text, 'https://example.com/') == text
