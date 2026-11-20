"""SMTP adapter based on Python's built-in smtplib."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from mail_merge.config import SmtpSettings

TIMEOUT_SECONDS = 30


class SmtpMailer:
    """Keeps one connection open; reconnects on the next send after an error."""

    def __init__(self, settings: SmtpSettings, user: str | None, password: str | None):
        self.settings = settings
        self.user = user
        self.password = password
        self._connection: smtplib.SMTP | None = None

    def connect(self) -> None:
        s = self.settings
        if s.security == "ssl":
            connection = smtplib.SMTP_SSL(
                s.host, s.port, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
            )
        else:
            connection = smtplib.SMTP(s.host, s.port, timeout=TIMEOUT_SECONDS)
            if s.security == "starttls":
                connection.starttls(context=ssl.create_default_context())
        if self.user:
            connection.login(self.user, self.password or "")
        self._connection = connection

    def send(self, message: EmailMessage, recipients: list[str]) -> dict[str, str]:
        if self._connection is None:
            self.connect()
        try:
            refused = self._connection.send_message(message, to_addrs=recipients)
        except smtplib.SMTPRecipientsRefused as exc:
            # Every recipient was refused; the connection itself is still fine.
            return {addr: _reason(err) for addr, err in exc.recipients.items()}
        except Exception:
            self.close()
            raise
        return {addr: _reason(err) for addr, err in refused.items()}

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.quit()
            except Exception:
                pass
            self._connection = None


def _reason(error: tuple[int, bytes]) -> str:
    code, text = error
    return f"{code} {text.decode(errors='replace')}"
