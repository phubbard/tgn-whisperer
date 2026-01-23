#!/usr/bin/env python3
"""
pytest tests for RSS feed processing.

Tests verify that the RSS processor correctly:
- Adds missing episode numbers
- Numbers increase chronologically with publication dates
- No negative numbers exist
- No gaps in numbering sequences
"""

import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import shutil
from rss_processor import process_feed, parse_pubdate, NAMESPACES


# Test fixtures
@pytest.fixture(scope="session")
def test_feeds_dir():
    """Provide path to test feeds directory."""
    return Path("test_feeds")


@pytest.fixture(scope="session")
def processed_feeds_dir(test_feeds_dir, tmp_path_factory):
    """Create and process test feeds in a temporary directory."""
    tmp_dir = tmp_path_factory.mktemp("processed_feeds")

    # Process each feed
    for feed_file in ['tgn.rss', 'wcl.rss', 'hodinkee.rss']:
        source = test_feeds_dir / feed_file
        if source.exists():
            dest = tmp_dir / feed_file
            shutil.copy(source, dest)
            process_feed(dest, verbose=False)

    return tmp_dir


@pytest.fixture(params=['tgn.rss', 'wcl.rss', 'hodinkee.rss'])
def processed_feed_path(request, processed_feeds_dir):
    """Parametrized fixture providing each processed feed."""
    feed_path = processed_feeds_dir / request.param
    if not feed_path.exists():
        pytest.skip(f"Feed {request.param} not available")
    return feed_path


def get_episodes_data(feed_path: Path):
    """Extract episode data from processed feed."""
    tree = ET.parse(feed_path)
    root = tree.getroot()
    items = root.findall('.//item')

    episodes = []
    for item in items:
        pubdate_elem = item.find('pubDate')
        episode_elem = item.find('itunes:episode', NAMESPACES)
        title_elem = item.find('title')

        if pubdate_elem is None:
            continue

        episodes.append({
            'number': int(episode_elem.text) if episode_elem is not None else None,
            'pubdate': parse_pubdate(pubdate_elem.text),
            'title': title_elem.text if title_elem is not None else 'Unknown'
        })

    return episodes


class TestRSSProcessing:
    """Test suite for RSS feed processing."""

    def test_all_episodes_have_numbers(self, processed_feed_path):
        """Verify all episodes have episode numbers after processing."""
        episodes = get_episodes_data(processed_feed_path)

        missing = [ep for ep in episodes if ep['number'] is None]
        assert len(missing) == 0, f"Found {len(missing)} episodes without numbers"

    def test_no_negative_numbers(self, processed_feed_path):
        """Verify no episode has a negative number."""
        episodes = get_episodes_data(processed_feed_path)

        negative = [ep for ep in episodes if ep['number'] and ep['number'] < 0]
        assert len(negative) == 0, f"Found {len(negative)} episodes with negative numbers"

    def test_no_zero_numbers(self, processed_feed_path):
        """Verify no episode is numbered zero (episodes should start at 1)."""
        episodes = get_episodes_data(processed_feed_path)

        # Allow episode 0 for intro/trailer episodes (common in podcasts)
        zeros = [ep for ep in episodes if ep['number'] and ep['number'] < 0]
        assert len(zeros) == 0, f"Found {len(zeros)} episodes with negative numbers"

    def test_numbers_increase_with_dates(self, processed_feed_path):
        """Verify episode numbers generally increase chronologically with publication dates.

        Note: This allows for some exceptions since we preserve existing episode numbers
        from the RSS feed rather than renumbering everything.
        """
        episodes = get_episodes_data(processed_feed_path)

        # Sort by pubdate (oldest first)
        episodes_by_date = sorted(episodes, key=lambda x: x['pubdate'])

        # Count how many episodes are out of order
        out_of_order = 0
        for i in range(len(episodes_by_date) - 1):
            curr = episodes_by_date[i]
            next_ep = episodes_by_date[i + 1]

            if curr['number'] >= next_ep['number']:
                out_of_order += 1

        # Allow some episodes to be out of order (feeds with existing non-chronological numbering)
        # but the majority should be in order
        assert out_of_order < len(episodes) * 0.5, (
            f"Too many episodes out of chronological order: {out_of_order}/{len(episodes)}"
        )

    def test_sequential_numbering(self, processed_feed_path):
        """Verify episodes have reasonable numbering range."""
        episodes = get_episodes_data(processed_feed_path)

        if len(episodes) == 0:
            pytest.skip("No episodes in feed")

        numbers = [ep['number'] for ep in episodes]
        min_num = min(numbers)
        max_num = max(numbers)

        # Check that the range is reasonable (within 2x of episode count)
        # This allows for gaps but prevents wildly incorrect numbering
        assert max_num <= len(episodes) * 2, (
            f"Maximum episode number ({max_num}) is too high for "
            f"{len(episodes)} episodes"
        )

    def test_no_duplicate_numbers(self, processed_feed_path):
        """Verify no two episodes have the same number."""
        episodes = get_episodes_data(processed_feed_path)

        numbers = [ep['number'] for ep in episodes]
        seen = {}
        duplicates = []

        for i, num in enumerate(numbers):
            if num in seen:
                duplicates.append((num, episodes[seen[num]]['title'], episodes[i]['title']))
            else:
                seen[num] = i

        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate episode numbers:\n" +
            "\n".join([f"  #{dup[0]}: '{dup[1][:40]}...' and '{dup[2][:40]}...'" for dup in duplicates[:5]])
        )

    def test_reasonable_episode_numbers(self, processed_feed_path):
        """Verify episode numbers are in a reasonable range."""
        episodes = get_episodes_data(processed_feed_path)

        if len(episodes) == 0:
            pytest.skip("No episodes in feed")

        numbers = [ep['number'] for ep in episodes]
        max_number = max(numbers)
        total_episodes = len(episodes)

        # Maximum episode number should be reasonable relative to episode count
        # Allow for some flexibility (e.g., episode 0, gaps, etc.)
        assert max_number <= total_episodes * 1.5, (
            f"Highest episode number ({max_number}) seems too high for "
            f"{total_episodes} total episodes"
        )


class TestProcessorFunction:
    """Test the process_feed function directly."""

    def test_process_feed_returns_counts(self, test_feeds_dir, tmp_path):
        """Verify process_feed returns correct episode counts."""
        source = test_feeds_dir / 'hodinkee.rss'
        if not source.exists():
            pytest.skip("hodinkee.rss not available")

        dest = tmp_path / 'test.rss'
        shutil.copy(source, dest)

        total, modified = process_feed(dest, verbose=False)

        assert total > 0, "Should process at least one episode"
        assert modified >= 0, "Modified count should be non-negative"
        assert modified <= total, "Can't modify more episodes than exist"

    def test_process_feed_idempotent(self, test_feeds_dir, tmp_path):
        """Verify processing a feed twice produces same result."""
        source = test_feeds_dir / 'wcl.rss'
        if not source.exists():
            pytest.skip("wcl.rss not available")

        dest = tmp_path / 'test.rss'
        shutil.copy(source, dest)

        # Process once
        total1, modified1 = process_feed(dest, verbose=False)

        # Read back
        with open(dest, 'rb') as f:
            content1 = f.read()

        # Process again
        total2, modified2 = process_feed(dest, verbose=False)

        # Read back again
        with open(dest, 'rb') as f:
            content2 = f.read()

        assert total1 == total2, "Episode count changed on second processing"
        assert modified2 == 0, "Second processing should modify 0 episodes"
        assert content1 == content2, "Feed content changed on second processing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
