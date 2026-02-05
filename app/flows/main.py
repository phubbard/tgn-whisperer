"""Main Prefect flow for orchestrating all podcast processing."""
import traceback
from prefect import flow, tags
from utils.logging import get_logger
from utils.email import send_failure_alert

from models.podcast import get_all_podcasts
from flows.podcast import process_podcast


@flow(name="process-all-podcasts", log_prints=True)
def process_all_podcasts():
    """
    Main orchestration flow that processes all podcasts sequentially.

    Each podcast flow runs independently and handles its own site generation.
    Sequential processing ensures proper resource management (transcription service, etc).

    Sends email alert on failure for monitoring.
    """
    log = get_logger()
    log.info("Starting podcast processing for all feeds")

    try:
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

    except Exception as e:
        # Send email alert on failure
        error_msg = f"""TGN Whisperer podcast processing flow failed.

Error: {type(e).__name__}: {str(e)}

Traceback:
{traceback.format_exc()}

Check Prefect UI for details: http://webserver.phfactor.net:4200
"""
        log.error(f"Flow failed with error: {e}")

        try:
            send_failure_alert(error_msg)
        except Exception as email_error:
            log.error(f"Failed to send failure alert email: {email_error}")

        # Re-raise to mark flow as failed in Prefect
        raise


if __name__ == "__main__":
    # For local testing
    process_all_podcasts()
