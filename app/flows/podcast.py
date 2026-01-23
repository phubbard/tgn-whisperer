"""Podcast processing flow for a single podcast feed."""
from pathlib import Path
from prefect import flow
from loguru import logger as log

from models.podcast import Podcast
from tasks.shownotes import (
    generate_tgn_shownotes,
    generate_wcl_shownotes,
    generate_hodinkee_shownotes
)


@flow(name="process-podcast", log_prints=True)
def process_podcast(podcast: Podcast):
    """
    Process a single podcast feed.

    Workflow:
    1. Fetch and process RSS feed
    2. Check for new episodes
    3. Send notifications
    4. Process each new episode in parallel
    5. Generate and deploy site immediately

    Args:
        podcast: Podcast configuration object

    Returns:
        List of newly processed episodes
    """
    log.info(f"Processing podcast: {podcast.name}")

    # TODO: Implement RSS fetching and processing
    # rss_content = fetch_rss_feed(podcast)
    # episodes_data = process_rss_feed(rss_content, podcast.name)

    # TODO: Check for new episodes
    # new_eps = check_new_episodes(podcast.name, episodes_data)

    # TODO: If no new episodes, return early
    # if not new_eps:
    #     log.info(f"No new episodes for {podcast.name}")
    #     return []

    # TODO: Send notifications
    # send_notification_email(podcast, new_eps)

    # TODO: Process each episode in parallel
    # episode_futures = []
    # for episode_data in new_eps:
    #     future = process_episode.submit(podcast, episode_data)
    #     episode_futures.append(future)
    # results = [f.result() for f in episode_futures]

    # TODO: Generate and deploy site immediately
    # generate_and_deploy_site(podcast)

    log.info(f"Completed processing for {podcast.name}")
    return []


@flow(name="generate-and-deploy-site", log_prints=True)
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

    # TODO: Build site with zensical
    # site_path = build_site(podcast.name)

    # TODO: Generate search index
    # generate_search_index(site_path)

    # TODO: Deploy (update static files in caddy2 directory)
    # deploy_site(podcast.name, site_path)

    log.info(f"Site generation complete for {podcast.name}")
