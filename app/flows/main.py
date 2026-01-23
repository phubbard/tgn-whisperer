"""Main Prefect flow for orchestrating all podcast processing."""
from prefect import flow
from loguru import logger as log

from models.podcast import get_all_podcasts
from flows.podcast import process_podcast


@flow(name="process-all-podcasts", log_prints=True)
def process_all_podcasts():
    """
    Main orchestration flow that processes all podcasts in parallel.

    Each podcast flow runs independently and handles its own site generation.
    """
    log.info("Starting podcast processing for all feeds")

    podcasts = get_all_podcasts()

    # Submit all podcast processing flows in parallel
    futures = []
    for podcast in podcasts:
        log.info(f"Submitting flow for podcast: {podcast.name}")
        future = process_podcast.submit(podcast)
        futures.append(future)

    # Wait for all to complete (optional - could fire and forget)
    results = [f.result() for f in futures]

    log.info(f"Completed processing {len(podcasts)} podcasts")
    return results


if __name__ == "__main__":
    # For local testing
    process_all_podcasts()
