"""Podcast processing flow for a single podcast feed."""
import os
import traceback
from pathlib import Path
from prefect import flow
from utils.logging import get_logger
from utils.email import send_failure_alert

from models.podcast import Podcast
from tasks.rss import (
    fetch_rss_feed,
    process_rss_feed,
    check_new_episodes,
    get_episode_details
)
from tasks.notifications import send_notification_email
from tasks.shownotes import (
    generate_tgn_shownotes,
    generate_wcl_shownotes,
    generate_hodinkee_shownotes
)
from tasks.build import (
    update_episodes_index,
    build_site,
    generate_search_index,
    deploy_site
)
from tasks.completion import filter_incomplete_episodes
from flows.episode import process_episode


@flow(
    name="process-podcast",
    flow_run_name="{podcast.name}",
    log_prints=True
)
def process_podcast(podcast: Podcast):
    """
    Process a single podcast feed.

    Workflow:
    1. Fetch and process RSS feed
    2. Check for new episodes
    3. Send notifications
    4. Process each incomplete episode sequentially
    5. Generate and deploy site only if episodes were processed

    Args:
        podcast: Podcast configuration object

    Returns:
        List of newly processed episode numbers
    """
    log = get_logger()
    log.info(f"Processing podcast: {podcast.name}")

    try:
        # Step 1: Fetch RSS feed
        rss_content = fetch_rss_feed(podcast)

        # Step 2: Process feed to add episode numbers and parse XML
        feed_data = process_rss_feed(rss_content, podcast.name)
        episodes = feed_data['episodes']

        # Step 3: Check for new episodes (for notifications)
        new_ep_numbers = check_new_episodes(podcast.name, episodes)

        # Step 4: Send notifications for truly new episodes
        if new_ep_numbers:
            log.info(f"Found {len(new_ep_numbers)} new episodes")
            send_notification_email(podcast, new_ep_numbers)
        else:
            log.info(f"No new episodes found")

        # Step 5: Check ALL episodes for incomplete processing
        # Get all episode numbers from the feed
        all_ep_numbers = []
        for entry in episodes:
            ep_num = entry.get('itunes:episode')
            if ep_num:
                all_ep_numbers.append(float(ep_num))

        log.info(f"Checking {len(all_ep_numbers)} total episodes for completion status")

        # Filter to find incomplete episodes (new or previously failed)
        incomplete_ep_numbers = filter_incomplete_episodes(podcast.name, all_ep_numbers)

        if not incomplete_ep_numbers:
            log.info(f"All episodes for {podcast.name} are complete - skipping site rebuild")
            return []

        log.info(f"Processing {len(incomplete_ep_numbers)} incomplete episodes")

        # Step 6: Process each incomplete episode sequentially
        # Note: For parallel processing, episodes should be submitted to a work pool
        # For now, process sequentially to ensure reliability
        results = []
        for ep_number in incomplete_ep_numbers:
            episode_entry = get_episode_details(episodes, ep_number)
            if episode_entry:
                log.info(f"Processing episode {ep_number}...")
                result = process_episode(podcast, episode_entry)
                results.append(result)
            else:
                log.warning(f"Could not find episode {ep_number} in feed")

        log.info(f"All {len(results)} episodes processed successfully")

        # Step 7: Generate and deploy site (skip for mock/testing if SKIP_SITE_DEPLOY is set)
        if os.environ.get("SKIP_SITE_DEPLOY"):
            log.info("Skipping site deployment (SKIP_SITE_DEPLOY is set)")
        else:
            generate_and_deploy_site(podcast)

        log.info(f"Completed processing {len(incomplete_ep_numbers)} episodes for {podcast.name}")
        return incomplete_ep_numbers

    except Exception as e:
        # Send email alert for individual podcast failure
        error_msg = f"""Podcast processing failed for {podcast.name}.

Error: {type(e).__name__}: {str(e)}

Traceback:
{traceback.format_exc()}

Check Prefect UI for details: http://webserver.phfactor.net:4200
"""
        log.error(f"Podcast {podcast.name} failed with error: {e}")

        try:
            send_failure_alert(error_msg)
        except Exception as email_error:
            log.error(f"Failed to send failure alert email: {email_error}")

        # Re-raise to mark flow as failed in Prefect
        raise


@flow(
    name="generate-and-deploy-site",
    flow_run_name="{podcast.name}-deploy",
    log_prints=True
)
def generate_and_deploy_site(podcast: Podcast):
    """
    Generate and deploy the static site for a podcast.

    Workflow:
    1. Generate shownotes if applicable
    2. Build site with zensical
    3. Generate search index with Pagefind
    4. Deploy to caddy2 static hosting

    Args:
        podcast: Podcast configuration object
    """
    log = get_logger()
    log.info(f"Generating and deploying site for {podcast.name}")

    # Step 1: Generate shownotes if applicable
    project_root = Path(__file__).parent.parent.parent
    rss_path = project_root / f"{podcast.name}_feed.rss"
    output_path = project_root / "sites" / podcast.name / "docs" / "shownotes.md"

    if rss_path.exists():
        if podcast.name == 'tgn':
            generate_tgn_shownotes(rss_path, output_path)
        elif podcast.name == 'wcl':
            generate_wcl_shownotes(rss_path, output_path)
        elif podcast.name == 'hodinkee':
            generate_hodinkee_shownotes(rss_path, output_path)
    else:
        log.warning(f"RSS feed not found for shownotes: {rss_path}")

    # Step 2: Build site with zensical
    site_path = build_site(podcast.name)

    # Step 3: Generate search index with Pagefind
    generate_search_index(site_path)

    # Step 4: Deploy to caddy2 static hosting
    deploy_site(podcast.name, site_path)

    log.info(f"Site deployed for {podcast.name}")
