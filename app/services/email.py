"""Transactional email service.

Sends plain-text + simple HTML email over SMTP using environment config. Email
is a best-effort side channel: when SMTP is not configured, sending degrades to
a no-op that never crashes a request. The in-app notification (see
``app/services/notifications.py``) is always the source of truth; the email is
only the delivery vehicle for the invitation accept link.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(current_app.config.get("SMTP_HOST") and current_app.config.get("SMTP_PORT"))


def send_email(to: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    """Send an email; return ``True`` on success and ``False`` otherwise.

    Never raises: mail failures are logged and swallowed so requests always
    succeed even when the mail server is down.
    """
    sender = current_app.config.get("MAIL_DEFAULT_SENDER") or "noreply@localhost"
    if not _smtp_configured():
        logger.debug("SMTP not configured; skipping email to %s", to)
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        host = current_app.config["SMTP_HOST"]
        port = current_app.config["SMTP_PORT"]
        username = current_app.config.get("SMTP_USER") or ""
        password = current_app.config.get("SMTP_PASSWORD") or ""
        use_tls = current_app.config.get("MAIL_USE_TLS", True)

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            if username:
                server.login(username, password)
            server.sendmail(sender, [to], message.as_string())
        return True
    except Exception as exc:
        logger.warning("Failed to send email to %s: %s", to, exc)
        return False


def _accept_url(raw_token: str) -> str:
    from flask import url_for

    return url_for("collaboration.invitation_landing", token=raw_token, _external=True)


def send_invitation_email(invitation, raw_token: str) -> bool:
    """Send the invitation email containing the one-time accept link."""
    url = _accept_url(raw_token)
    workspace_name = invitation.workspace.name if invitation.workspace else "workspace"
    text = (
        f'You\'ve been invited to join the workspace "{workspace_name}" '
        f"on {current_app.config['APP_NAME']} as a {invitation.role}.\n\n"
        f"Accept the invitation:\n{url}\n\n"
        f"This invitation expires at {invitation.expires_at.isoformat()}.\n"
        "If you didn't expect this invitation, you can ignore this email."
    )
    html = (
        "<p>You've been invited to join the workspace "
        f"<strong>{workspace_name}</strong> on {current_app.config['APP_NAME']} "
        f"as a <strong>{invitation.role}</strong>.</p>"
        f'<p><a href="{url}">Accept the invitation</a></p>'
        f"<p>This invitation expires at {invitation.expires_at.isoformat()}.</p>"
        "<p>If you didn't expect this invitation, you can ignore this email.</p>"
    )
    return send_email(invitation.email, f"Invitation to {workspace_name}", text, html)
