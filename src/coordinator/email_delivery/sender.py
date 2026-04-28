"""Email sender — provider-agnostic, picks based on settings.

Three modes via `LETHE_EMAIL_PROVIDER`:
- `resend` — uses the `resend` Python SDK + `LETHE_RESEND_API_KEY`. Free tier
  covers hackathons (3000/mo). Cleanest for demos.
- `smtp`   — `LETHE_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD` (e.g. Gmail SMTP
  with an app password). Stdlib smtplib only.
- `stub`   — default. Logs the mail but doesn't send. Demo-honest fallback so
  the rest of the pipeline (KH attestation) can still fire end-to-end.

All three return the same shape so the router can treat them uniformly:
    {sent: bool, provider: str, message_id: str | None, error: str | None}
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict

from config import settings

log = logging.getLogger("lethe.email")


def _stub(reason: str) -> Dict[str, Any]:
    return {"sent": False, "provider": f"stub ({reason})", "message_id": None, "error": None}


async def _send_resend(*, to: str, subject: str, html: str, sender: str) -> Dict[str, Any]:
    try:
        import resend  # type: ignore
    except ImportError:
        return _stub("resend SDK not installed")

    if not settings.email_resend_api_key:
        return _stub("no resend api key")

    def _do_send():
        resend.api_key = settings.email_resend_api_key
        return resend.Emails.send({
            "from": sender,
            "to": [to],
            "subject": subject,
            "html": html,
        })

    try:
        result = await asyncio.to_thread(_do_send)
        return {
            "sent": True,
            "provider": "resend",
            "message_id": (result or {}).get("id"),
            "error": None,
        }
    except Exception as e:
        log.warning("resend send failed: %s", e)
        return {"sent": False, "provider": "resend", "message_id": None, "error": str(e)[:240]}


async def _send_smtp(*, to: str, subject: str, html: str, sender: str) -> Dict[str, Any]:
    if not (settings.email_smtp_host and settings.email_smtp_user and settings.email_smtp_password):
        return _stub("incomplete smtp settings")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    # Plain-text fallback first (some clients prefer it), then HTML.
    msg.set_content("Your email client does not support HTML; please view this message in a modern client.")
    msg.add_alternative(html, subtype="html")

    def _do_send():
        ctx = ssl.create_default_context()
        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port) as smtp:
            smtp.starttls(context=ctx)
            smtp.login(settings.email_smtp_user, settings.email_smtp_password)
            smtp.send_message(msg)

    try:
        await asyncio.to_thread(_do_send)
        return {"sent": True, "provider": "smtp", "message_id": None, "error": None}
    except Exception as e:
        log.warning("smtp send failed: %s", e)
        return {"sent": False, "provider": "smtp", "message_id": None, "error": str(e)[:240]}


async def send_email(*, to: str, subject: str, html: str) -> Dict[str, Any]:
    """Dispatch to the configured provider. Always returns; never raises."""
    sender = settings.email_from or "Lethe <noreply@lethe.local>"
    provider = (settings.email_provider or "stub").strip().lower()

    if provider == "resend":
        return await _send_resend(to=to, subject=subject, html=html, sender=sender)
    if provider == "smtp":
        return await _send_smtp(to=to, subject=subject, html=html, sender=sender)

    # Stub default — log and return.
    log.info("email[stub]: would send to=%s subject=%r len(html)=%d", to, subject, len(html))
    return {
        "sent": False,
        "provider": "stub",
        "message_id": None,
        "error": None,
        "stub_note": "set LETHE_EMAIL_PROVIDER=resend|smtp to send for real",
    }
