"""Send transactional email (OTP codes) via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("qbridge.email")


def _smtp_configured() -> bool:
    return bool(os.environ.get("QBRIDGE_SMTP_HOST", "").strip())


def send_otp_email(*, to_email: str, otp_code: str, username: str) -> None:
    """
    Deliver a one-time login code. When SMTP is not configured, log the OTP
    (dev only) so local testing works without a mail server.
    """
    subject = "Your Quantum Bridge OS security code"
    body = (
        f"Hello {username},\n\n"
        f"Your login verification code is: {otp_code}\n\n"
        "This code expires in 10 minutes. If you did not attempt to sign in, "
        "ignore this message.\n\n"
        "— Quantum Bridge OS"
    )

    if not _smtp_configured():
        if os.environ.get("QBRIDGE_AUTH_DEV_LOG_OTP", "1").strip() in ("1", "true", "yes"):
            logger.warning(
                "SMTP not configured — OTP for %s: %s (set QBRIDGE_SMTP_HOST to send real email)",
                to_email,
                otp_code,
            )
            print(
                f"[qbridge-auth] OTP for {to_email}: {otp_code}",
                flush=True,
            )
        return

    host = os.environ["QBRIDGE_SMTP_HOST"]
    port = int(os.environ.get("QBRIDGE_SMTP_PORT", "587"))
    user = os.environ.get("QBRIDGE_SMTP_USER", "")
    password = os.environ.get("QBRIDGE_SMTP_PASSWORD", "")
    from_addr = os.environ.get("QBRIDGE_SMTP_FROM", user or "noreply@qbridge.local")
    use_tls = os.environ.get("QBRIDGE_SMTP_TLS", "1").strip() in ("1", "true", "yes")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)

    logger.info("OTP email sent to %s", to_email)
