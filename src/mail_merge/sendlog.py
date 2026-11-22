"""Send log: one CSV per config, listing every successfully sent address.

It is the tool's memory across runs and prevents sending twice. Each address is
written right after the server accepted it, so an interrupted run can resume.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

HEADER = ["email", "sent_at"]


def read_sent(path: Path) -> set[str]:
    """Lowercase addresses already in the log (empty set if there is no log yet)."""
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            row["email"].strip().lower()
            for row in csv.DictReader(handle)
            if row.get("email")
        }


class SendLog:
    def __init__(self, path: Path):
        self.path = path

    def append(self, email: str) -> None:
        new_file = not self.path.is_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if new_file:
                writer.writerow(HEADER)
            writer.writerow([email, datetime.now().astimezone().isoformat(timespec="seconds")])
