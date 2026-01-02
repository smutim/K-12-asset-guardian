import os
from email.message import EmailMessage
from typing import Iterable, Optional, Sequence

import aiosmtplib


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return val.strip()


async def send_email(
    subject: str,
    to_addrs: Sequence[str] | str,
    body_text: str,
    *,
    from_addr: Optional[str] = None,
    body_html: Optional[str] = None,
    cc_addrs: Optional[Sequence[str]] = None,
    bcc_addrs: Optional[Sequence[str]] = None,
) -> bool:
    """
    Sends an email using SMTP settings from environment variables.

    Env vars supported:
      SMTP_HOST (required)
      SMTP_PORT (default 587)
      SMTP_USERNAME (optional)
      SMTP_PASSWORD (optional)
      SMTP_USE_TLS (default true)  -> STARTTLS
      SMTP_FROM (default SMTP_USERNAME or "noreply@localhost")
    """

    # Normalize recipients
    if isinstance(to_addrs, str):
        to_list = [to_addrs]
    else:
        to_list = list(to_addrs)

    if not to_list:
        raise ValueError("to_addrs must contain at least one recipient.")

    smtp_host = _get_env("SMTP_HOST")
    if not smtp_host:
        # In dev mode you might not want to send email; fail gracefully.
        # Raise if you want strict behavior:
        # raise RuntimeError("SMTP_HOST is not set.")
        return False

    smtp_port = int(_get_env("SMTP_PORT", "587") or "587")
    smtp_user = _get_env("SMTP_USERNAME")
    smtp_pass = _get_env("SMTP_PASSWORD")
    use_tls = (_get_env("SMTP_USE_TLS", "true") or "true").lower() in ("1", "true", "yes", "y")

    from_addr = from_addr or _get_env("SMTP_FROM") or smtp_user or "noreply@localhost"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_list)

    if cc_addrs:
        msg["Cc"] = ", ".join(list(cc_addrs))

    # Text/plain is always set
    msg.set_content(body_text)

    # Optional HTML alternative
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    # Build final RCPT list including cc/bcc
    rcpt: list[str] = []
    rcpt.extend(to_list)
    if cc_addrs:
        rcpt.extend(list(cc_addrs))
    if bcc_addrs:
        rcpt.extend(list(bcc_addrs))

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_user,
        password=smtp_pass,
        start_tls=use_tls,
        recipients=rcpt,
    )
    return True
