"""Pluggable mailer.

Development default is the *console* provider, which prints messages to the
terminal. Configure ``MAIL_PROVIDER=smtp`` plus the ``SMTP_*`` variables to
send real e-mail in production.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formatdate

from flask import current_app, render_template


def _console_write(text: str) -> None:
    """Write text to stdout without ever crashing on console encoding limits
    (Windows cp1252 consoles cannot encode emoji)."""
    try:
        print(text)
    except UnicodeEncodeError:
        import sys

        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(text.encode(encoding, "replace").decode(encoding, "replace"))


def _send_console(message: EmailMessage) -> None:  # pragma: no cover - dev aid
    """Print an e-mail to the terminal (development default provider)."""
    _console_write("\n" + "=" * 72)
    _console_write(f"To: {message['To']}")
    _console_write(f"Subject: {message['Subject']}")
    _console_write("-" * 72)
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.is_multipart():
            continue
        if part.get_content_maintype() != "text":
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", "replace")
        _console_write(text.strip())
    _console_write("=" * 72 + "\n")


def _send_smtp(message: EmailMessage) -> None:  # pragma: no cover - needs server
    host = current_app.config["SMTP_HOST"]
    port = current_app.config["SMTP_PORT"]
    user = current_app.config["SMTP_USER"]
    password = current_app.config["SMTP_PASSWORD"]
    use_tls = current_app.config["SMTP_USE_TLS"]
    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls()
        if user:
            server.login(user, password)
        server.send_message(message)


def send_email(to: str, subject: str, text_body: str, html_body: str = "") -> bool:
    """Send an e-mail using the configured provider. Returns success flag."""
    provider = current_app.config.get("MAIL_PROVIDER", "console")
    suppress = current_app.config.get("MAIL_SUPPRESS_SEND", True)

    message = EmailMessage()
    message["To"] = to
    message["From"] = current_app.config["MAIL_FROM"]
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    if html_body:
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")
    else:
        message.set_content(text_body)

    if suppress or provider == "console":
        _send_console(message)
        return True
    try:
        _send_smtp(message)
        return True
    except (smtplib.SMTPException, OSError) as exc:  # pragma: no cover
        current_app.logger.error("Failed to send mail to %s: %s", to, exc)
        return False


# ---------------------------------------------------------------------------
# High level helpers used by the auth blueprint
# ---------------------------------------------------------------------------
def send_verification_email(user) -> None:
    """Send the e-mail verification link."""
    link = f"{current_app.config['SITE_URL']}/verify-email?token={user.verification_token}"
    subject = "Verify your e-mail for MyDoc"
    text = (
        f"Hi {user.effective_name},\n\n"
        "Please confirm your e-mail address by opening the link below:\n"
        f"{link}\n\n"
        "If you did not create a MyDoc account, you can safely ignore this message.\n\n"
        "Developed by MTA Company"
    )
    html = render_template("auth/email/verification.html", user=user, link=link)
    send_email(user.email, subject, text, html)


def send_password_reset_email(user) -> None:
    """Send the password reset link."""
    link = f"{current_app.config['SITE_URL']}/reset-password?token={user.reset_token}"
    subject = "Reset your MyDoc password"
    text = (
        f"Hi {user.effective_name},\n\n"
        "Use the link below to choose a new password (valid for 1 hour):\n"
        f"{link}\n\n"
        "If you did not request this, ignore this message — your password stays unchanged.\n\n"
        "Developed by MTA Company"
    )
    html = render_template("auth/email/password_reset.html", user=user, link=link)
    send_email(user.email, subject, text, html)
