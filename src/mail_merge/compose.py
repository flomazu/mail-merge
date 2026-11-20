"""Build the email messages for both modes."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

from mail_merge.config import Config, ConfigError
from mail_merge.precheck import RowResult
from mail_merge.template import GREETING, build_greeting, fill


@dataclass
class Attachment:
    filename: str
    data: bytes
    maintype: str
    subtype: str


@dataclass
class Draft:
    """One email to send, plus the rows (recipients) it covers."""

    message: EmailMessage
    recipients: list[str]
    rows: list[RowResult]


def load_attachment(path: Path | None) -> Attachment | None:
    if path is None:
        return None
    if not path.is_file():
        raise ConfigError(f"Attachment not found: {path}")
    mime, _ = mimetypes.guess_type(path.name)
    maintype, subtype = (mime or "application/octet-stream").split("/", 1)
    return Attachment(path.name, path.read_bytes(), maintype, subtype)


def compose_individual(
    config: Config, subject: str, body: str, rows: list[RowResult], attachment: Attachment | None
) -> list[Draft]:
    """One email per row, placeholders filled with that row's values."""
    drafts = []
    for row in rows:
        values = dict(row.values)
        row.greeting = build_greeting(
            config.mail.greeting, config.mail.greeting_fallback, row.values
        )
        values[GREETING] = row.greeting
        row.subject = fill(subject, values)
        message = _message(config, row.subject, fill(body, values), attachment)
        message["To"] = row.email
        drafts.append(Draft(message, [row.email], [row]))
    return drafts


def compose_bcc(
    config: Config, subject: str, body: str, rows: list[RowResult], attachment: Attachment | None
) -> list[Draft]:
    """One email per batch, all recipients in BCC, greeting = fallback."""
    values = {GREETING: config.mail.greeting_fallback}
    final_subject = fill(subject, values)
    final_body = fill(body, values)
    visible_to = config.mail.bcc_to or config.smtp.from_address
    size = config.mail.bcc_batch_size

    drafts = []
    for start in range(0, len(rows), size):
        batch = rows[start : start + size]
        for row in batch:
            row.greeting = config.mail.greeting_fallback
            row.subject = final_subject
        message = _message(config, final_subject, final_body, attachment)
        message["To"] = visible_to
        # Kept for the .eml preview; smtplib removes it from what is transmitted.
        message["Bcc"] = ", ".join(r.email for r in batch)
        drafts.append(Draft(message, [r.email for r in batch], batch))
    return drafts


def _message(
    config: Config, subject: str, body: str, attachment: Attachment | None
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = formataddr((config.smtp.from_name, config.smtp.from_address))
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    domain = config.smtp.from_address.rpartition("@")[2] or None
    message["Message-ID"] = make_msgid(domain=domain)
    message.set_content(body)
    if attachment:
        message.add_attachment(
            attachment.data,
            maintype=attachment.maintype,
            subtype=attachment.subtype,
            filename=attachment.filename,
        )
    return message
