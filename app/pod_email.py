from os import getenv
from pathlib import Path
from email.message import EmailMessage
import smtplib

from prefect import get_run_logger

system_admin = 'tgn-whisperer@phfactor.net'


class FastMailSMTP(smtplib.SMTP_SSL):
    """A wrapper for handling SMTP connections to FastMail.
    From https://alexwlchan.net/2016/python-smtplib-and-fastmail/
    with attachments code removed and edits for this use case.
    """

    def __init__(self):
        log = get_run_logger()
        self.no_email = True

        super().__init__('mail.messagingengine.com', port=465)
        smtp_password = getenv('FASTMAIL_PASSWORD', None)
        if Path(".no_email").exists():
            log.warning('Honoring .no_email file')
            return

        if not smtp_password:
            log.error(f'FASTMAIL_PASSWORD not found in environment, cannot email')
            return

        self.login('pfh@phfactor.net', smtp_password)
        self.no_email = False

    def send_fm_message(self, *,
                        from_addr,
                        to_addrs,
                        msg,
                        subject):
        log = get_run_logger()
        msg_root = EmailMessage()
        msg_root['Subject'] = subject
        msg_root['From'] = from_addr
        msg_root['To'] = ', '.join(to_addrs)
        msg_root.set_payload(msg)

        if self.no_email:
            log.info('Email send disabled')
            return

        self.sendmail(from_addr, to_addrs, msg_root.as_string())


def send_failure_alert(fail_message):
    # TODO replace with Prefect error management?
    with FastMailSMTP() as server:
        server.send_fm_message(from_addr=system_admin,
                               to_addrs=system_admin,
                               msg=fail_message,
                               subject='Error in podcast processing')


def send_email(email_list: list, new_ep_list: list, base_url: str) -> None:
    # TODO templates, opt-in system, web-based signup, send when done.
    log = get_run_logger()
    new_count: int = len(new_ep_list)
    subject = f'{new_count} new episodes are available' if new_count > 1 else 'New episode available'

    disclaimer = 'This email goes out just as the process begins, so transcripts may be delayed - about 90 minutes per episode.'
    payload = f'New episode' + 's' if new_count > 1 else '' + ':\n'
    for ep in new_ep_list:
        payload = payload + f"\n{base_url}/{str(ep)}/episode/"
    payload += '\n' + disclaimer

    # TODO Spawn this into a background thread/process
    log.info(f'Emailing {email_list} with {new_count} episodes...')
    with FastMailSMTP() as server:
        server.send_fm_message(from_addr=system_admin,
                               to_addrs=email_list,
                               msg=payload,
                               subject=subject)
        log.info('email sent.')

