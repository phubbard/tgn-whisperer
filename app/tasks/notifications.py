"""Prefect tasks for sending notifications."""
from prefect import task
from utils.logging import get_logger

from models.podcast import Podcast
from utils.email import send_notification_email as send_email_util


@task(
    name="send-notification-email",
    retries=3,
    retry_delay_seconds=60,
    log_prints=True
)
def send_notification_email(podcast: Podcast, new_episodes: list[float], episodes: list[dict] = None) -> bool:
    """
    Send email notification about new podcast episodes.

    Args:
        podcast: Podcast configuration object
        new_episodes: List of new episode numbers
        episodes: Optional list of all episode dicts from RSS feed (for titles)

    Returns:
        True if email was sent successfully, False otherwise
    """
    log = get_logger()
    if not new_episodes:
        log.debug(f"No new episodes to notify about for {podcast.name}")
        return False

    log.info(f"Sending notification for {len(new_episodes)} new episodes of {podcast.name}")

    # Build episode number → title map from feed data
    ep_titles = {}
    if episodes:
        for entry in episodes:
            ep_num = entry.get('itunes:episode')
            title = entry.get('title', '')
            if ep_num:
                ep_titles[float(ep_num)] = title

    try:
        send_email_util(
            email_list=podcast.emails,
            new_ep_list=new_episodes,
            base_url=podcast.doc_base_url,
            ep_titles=ep_titles
        )
        return True
    except Exception as e:
        log.error(f"Failed to send notification email for {podcast.name}: {e}")
        raise
