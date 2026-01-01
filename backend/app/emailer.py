ready for emailer.py content

import aiosmtplib
from email.message import EmailMessage

from .config import settings


async def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Sends an email using SMTP settings defined in config.py.
    This is used by the alert engine for notifications.
    """

    if not settings.smtp_host or not settings.smtp_user:
        # Email not configured; fail silently for now
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        start_tls=True,
        username=settings.smtp_user,
        password=settings.smtp_password,
        timeout=10,
    )
