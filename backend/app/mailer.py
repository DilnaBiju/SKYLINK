"""Sends email through SMTP when configured; otherwise saves each email as an
HTML file in backend/outbox/ (and in the email_outbox table) so you can open it."""
import re
import smtplib
import ssl
from email.message import EmailMessage

from . import config
from .db import now_iso, session


def _log(to, subject, html, mode, status, error=None, path=None):
    with session() as db:
        db.execute("INSERT INTO email_outbox(to_email,subject,body_html,mode,status,error,file_path,created_at)"
                   " VALUES (?,?,?,?,?,?,?,?)", (to, subject, html, mode, status, error, path, now_iso()))


def send_email(to: str, subject: str, html: str) -> dict:
    if not config.SMTP_HOST:
        config.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        stamp = now_iso().replace(":", "").replace("-", "")
        safe = re.sub(r"[^a-zA-Z0-9]+", "_", subject)[:50]
        path = config.OUTBOX_DIR / f"{stamp}_{safe}.html"
        path.write_text(f"<!-- To: {to} | Subject: {subject} -->\n{html}", encoding="utf-8")
        _log(to, subject, html, "file", "SAVED", path=str(path))
        print(f"[mail] SMTP not configured - saved '{subject}' for {to} -> {path}")
        return {"mode": "file", "status": "SAVED", "path": str(path)}
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.MAIL_FROM, to, subject
    msg.set_content("This email contains HTML content. Please view it in an HTML-capable mail app.")
    msg.add_alternative(html, subtype="html")
    try:
        if config.SMTP_SSL:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=20,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20)
            if config.SMTP_STARTTLS:
                server.starttls(context=ssl.create_default_context())
        with server:
            if config.SMTP_USER:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        _log(to, subject, html, "smtp", "SENT")
        return {"mode": "smtp", "status": "SENT"}
    except Exception as exc:  # never break a booking because email failed
        _log(to, subject, html, "smtp", "FAILED", error=str(exc))
        print(f"[mail] SMTP send failed: {exc}")
        return {"mode": "smtp", "status": "FAILED", "error": str(exc)}
