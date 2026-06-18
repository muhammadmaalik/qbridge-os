"""Send transactional email (OTP codes) via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("qbridge.email")


class EmailDeliveryError(RuntimeError):
    """Raised when an OTP email cannot be delivered."""


def _smtp_configured() -> bool:
    return bool(os.environ.get("QBRIDGE_SMTP_HOST", "").strip())


def _dev_log_otp_enabled() -> bool:
    return os.environ.get("QBRIDGE_AUTH_DEV_LOG_OTP", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def smtp_setup_hint() -> str:
    return (
        "Email delivery is not configured. Add SMTP settings to your .env file:\n"
        "  QBRIDGE_SMTP_HOST=smtp.gmail.com\n"
        "  QBRIDGE_SMTP_PORT=587\n"
        "  QBRIDGE_SMTP_USER=your@gmail.com\n"
        "  QBRIDGE_SMTP_PASSWORD=your-app-password\n"
        "  QBRIDGE_SMTP_FROM=your@gmail.com\n"
        "For Gmail, create an App Password at https://myaccount.google.com/apppasswords"
    )


def send_otp_email(*, to_email: str, otp_code: str, username: str) -> None:
    """Deliver a one-time login code to the user's inbox."""
    subject = "Your Quantum Bridge OS security code"
    body = (
        f"Hello {username},\n\n"
        f"Your login verification code is: {otp_code}\n\n"
        "This code expires in 10 minutes. If you did not attempt to sign in, "
        "ignore this message.\n\n"
        "— Quantum Bridge OS"
    )

    if not _smtp_configured():
        if _dev_log_otp_enabled():
            logger.warning(
                "SMTP not configured — OTP for %s logged to console (dev only)",
                to_email,
            )
            print(f"[qbridge-auth] DEV OTP for {to_email}: {otp_code}", flush=True)
            return
        raise EmailDeliveryError(smtp_setup_hint())

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

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if use_tls:
                smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    except Exception as exc:
        raise EmailDeliveryError(
            f"Failed to send verification email to {to_email}: {exc}"
        ) from exc

    logger.info("OTP email sent to %s", to_email)
