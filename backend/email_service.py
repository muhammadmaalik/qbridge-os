"""Send transactional email (OTP codes) via SMTP or Brevo API."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("qbridge.email")


class EmailDeliveryError(RuntimeError):
    """Raised when an OTP email cannot be delivered."""


def _smtp_host_configured() -> bool:
    return bool(os.environ.get("QBRIDGE_SMTP_HOST", "").strip())


def _brevo_configured() -> bool:
    return bool(os.environ.get("QBRIDGE_BREVO_API_KEY", "").strip())


def _smtp_configured() -> bool:
    """True when any production email backend is available (SMTP or Brevo API)."""
    return _smtp_host_configured() or _brevo_configured()


def _dev_log_otp_enabled() -> bool:
    return os.environ.get("QBRIDGE_AUTH_DEV_LOG_OTP", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def smtp_setup_hint() -> str:
    return (
        "Email delivery is not configured on the server.\n"
        "Render: Dashboard → qbridge-os → Environment → add either:\n"
        "  (A) Brevo — QBRIDGE_BREVO_API_KEY + QBRIDGE_BREVO_SENDER_EMAIL\n"
        "  (B) Gmail — QBRIDGE_SMTP_HOST=smtp.gmail.com, PORT=587, USER, PASSWORD, FROM\n"
        "See docs/DEPLOY_RENDER.md or .env.example for full steps."
    )


def email_backend_label() -> str:
    if _smtp_host_configured():
        return "smtp"
    if _brevo_configured():
        return "brevo"
    return "none"


def _send_via_brevo(*, to_email: str, subject: str, body: str) -> None:
    import httpx

    api_key = os.environ["QBRIDGE_BREVO_API_KEY"].strip()
    sender = (
        os.environ.get("QBRIDGE_BREVO_SENDER_EMAIL", "").strip()
        or os.environ.get("QBRIDGE_SMTP_FROM", "").strip()
        or os.environ.get("QBRIDGE_SMTP_USER", "").strip()
    )
    if not sender:
        raise EmailDeliveryError(
            "Brevo is configured but no sender email is set. "
            "Add QBRIDGE_BREVO_SENDER_EMAIL (your verified Brevo address)."
        )

    payload = {
        "sender": {"name": "Quantum Bridge OS", "email": sender},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            res = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key,
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json=payload,
            )
            res.raise_for_status()
    except Exception as exc:
        raise EmailDeliveryError(
            f"Failed to send verification email via Brevo to {to_email}: {exc}"
        ) from exc


def _send_via_smtp(*, to_email: str, msg: EmailMessage) -> None:
    host = os.environ["QBRIDGE_SMTP_HOST"]
    port = int(os.environ.get("QBRIDGE_SMTP_PORT", "587"))
    user = os.environ.get("QBRIDGE_SMTP_USER", "")
    password = os.environ.get("QBRIDGE_SMTP_PASSWORD", "")
    use_tls = os.environ.get("QBRIDGE_SMTP_TLS", "1").strip() in ("1", "true", "yes")

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

    if _brevo_configured() and not _smtp_host_configured():
        _send_via_brevo(to_email=to_email, subject=subject, body=body)
        logger.info("OTP email sent to %s via Brevo", to_email)
        return

    from_addr = os.environ.get(
        "QBRIDGE_SMTP_FROM",
        os.environ.get("QBRIDGE_SMTP_USER", "noreply@qbridge.local"),
    )
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body)
    _send_via_smtp(to_email=to_email, msg=msg)
    logger.info("OTP email sent to %s via SMTP", to_email)
