"""
mail_service.py — Envío de correos electrónicos HTML.
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL,
    MAIL_TIMEOUT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM_NAME,
)

logger = logging.getLogger(__name__)


def send_email(to_addr: str, subject: str, html_body: str):
    """Send an HTML email. Returns (ok, error_message)."""
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        msg = 'Email auth not configured. Set MAIL_USERNAME and MAIL_PASSWORD in .env'
        logger.error(msg)
        return False, msg
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'{MAIL_FROM_NAME} <{MAIL_USERNAME}>'
        msg['To']      = to_addr
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        if MAIL_USE_SSL:
            with smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=MAIL_TIMEOUT) as srv:
                srv.login(MAIL_USERNAME, MAIL_PASSWORD)
                srv.sendmail(MAIL_USERNAME, to_addr, msg.as_string())
        else:
            with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=MAIL_TIMEOUT) as srv:
                srv.ehlo()
                if MAIL_USE_TLS:
                    srv.starttls(context=ssl.create_default_context())
                    srv.ehlo()
                srv.login(MAIL_USERNAME, MAIL_PASSWORD)
                srv.sendmail(MAIL_USERNAME, to_addr, msg.as_string())

        return True, None
    except Exception as exc:
        err_msg = str(exc)
        logger.error(f'send_email failed -> {err_msg}')
        return False, err_msg
