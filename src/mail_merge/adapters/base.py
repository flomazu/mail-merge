"""The small interface every mail adapter implements."""

from __future__ import annotations

from email.message import EmailMessage
from typing import Protocol


class Mailer(Protocol):
    def connect(self) -> None:
        """Open the connection. Raises if the server is unreachable or login fails."""
        ...

    def send(self, message: EmailMessage, recipients: list[str]) -> dict[str, str]:
        """Send one message.

        Returns the recipients the server refused, mapped to the reason.
        Raises an exception if the message was not sent at all.
        """
        ...

    def close(self) -> None:
        """Release the connection."""
        ...
