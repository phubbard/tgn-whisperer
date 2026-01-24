"""Main Prefect flow for orchestrating all podcast processing."""
from prefect import flow, tags
from loguru import logger as log

from models.podcast import get_all_podcasts
from flows.podcast import process_podcast


@flow(name="process-all-podcasts", log_prints=True)
def process_all_podcasts():
    """
    Main orchestration flow that processes all podcasts sequentially.

    Each podcast flow runs independently and handles its own site generation.
    Sequential processing ensures proper resource management (transcription service, etc).
    """
    log.info("Starting podcast processing for all feeds")

    podcasts = get_all_podcasts()

    # Process all podcasts sequentially
    results = []
    for podcast in podcasts:
        log.info(f"Processing podcast: {podcast.name}")
        # Add tags to identify the podcast in the UI
        with tags(podcast.name, "podcast"):
            result = process_podcast(podcast)
        results.append(result)

    log.info(f"Completed processing {len(podcasts)} podcasts")
    return results


if __name__ == "__main__":
    # For local testing
    process_all_podcasts()
