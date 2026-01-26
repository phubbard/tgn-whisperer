"""Email utilities for podcast notifications."""
import smtplib
from email.message import EmailMessage
from os import getenv
from pathlib import Path
from loguru import logger as log

from constants import system_admin, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME


class FastMailSMTP(smtplib.SMTP_SSL):
    """
    A wrapper for handling SMTP connections to FastMail.

    From https://alexwlchan.net/2016/python-smtplib-and-fastmail/
    with attachments code removed and edits for this use case.
    """

    def __init__(self):
        self.no_email = True

        super().__init__(SMTP_SERVER, port=SMTP_PORT)
        smtp_password = getenv('FASTMAIL_PASSWORD', None)

        if Path(".no_email").exists():
            log.warning('Honoring .no_email file - emails disabled')
            return

        if not smtp_password:
            log.error('FASTMAIL_PASSWORD not found in environment, cannot email')
            return

        self.login(SMTP_USERNAME, smtp_password)
        self.no_email = False
        log.debug('FastMail SMTP connection established')

    def send_fm_message(self, *,
                        from_addr: str,
                        to_addrs: list[str],
                        msg: str,
                        subject: str):
        """
        Send an email message via FastMail.

        Args:
            from_addr: Sender email address
            to_addrs: List of recipient email addresses
            msg: Message body (plain text)
            subject: Email subject line
        """
        if self.no_email:
            log.info('Email send disabled')
            return

        msg_root = EmailMessage()
        msg_root['Subject'] = subject
        msg_root['From'] = from_addr
        msg_root['To'] = ', '.join(to_addrs)
        msg_root.set_payload(msg)

        self.sendmail(from_addr, to_addrs, msg_root.as_string())
        log.info(f"Email sent to {', '.join(to_addrs)}")


def send_notification_email(email_list: list[str], new_ep_list: list[float], base_url: str) -> None:
    """
    Send email notification about new episodes.

    Args:
        email_list: List of email addresses to notify
        new_ep_list: List of new episode numbers
        base_url: Base URL for episode links
    """
    new_count = len(new_ep_list)
    if new_count == 0:
        log.debug("No new episodes to notify about")
        return

    subject = f'{new_count} new episodes are available' if new_count > 1 else 'New episode available'

    disclaimer = ('This email goes out just as the process begins, so transcripts may be delayed - about 90 minutes per '
                  'episode.')

    payload = f'New episode{"s" if new_count > 1 else ""}:\n'
    for ep in sorted(new_ep_list):
        payload = payload + f"\n{base_url}/{str(ep)}/episode/"
    payload += '\n' + disclaimer

    log.info(f'Emailing {email_list} with {new_count} episodes...')

    try:
        with FastMailSMTP() as server:
            server.send_fm_message(
                from_addr=system_admin,
                to_addrs=email_list,
                msg=payload,
                subject=subject
            )
        log.info('Notification email sent successfully')
    except Exception as e:
        log.error(f"Failed to send notification email: {e}")
        raise


def send_failure_alert(fail_message: str) -> None:
    """
    Send failure alert email to system admin.

    Args:
        fail_message: Error message to send
    """
    log.warning(f"Sending failure alert: {fail_message}")

    try:
        with FastMailSMTP() as server:
            server.send_fm_message(
                from_addr=system_admin,
                to_addrs=[system_admin],
                msg=fail_message,
                subject='Error in podcast processing'
            )
        log.info('Failure alert sent')
    except Exception as e:
        log.error(f"Failed to send failure alert: {e}")
        # Don't raise - we don't want email failures to crash the pipeline
