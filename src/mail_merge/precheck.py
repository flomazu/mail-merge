"""Check every row before anything is sent.

Each row ends up as `ok`, `skipped` (with a reason) or `already_sent`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mail_merge.reader import Row

OK = "ok"
SKIPPED = "skipped"
ALREADY_SENT = "already_sent"

# Deliberately simple: catches typos, does not check whether the address exists.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class RowResult:
    row: int
    email: str
    values: dict[str, str]
    status: str
    reason: str = ""
    greeting: str = ""
    subject: str = ""


def is_valid_email(address: str) -> bool:
    return bool(_EMAIL.match(address))


def precheck(
    rows: list[Row],
    email_column: str,
    required_columns: set[str],
    already_sent: set[str],
) -> list[RowResult]:
    """Classify rows. `already_sent` holds lowercase addresses from the send log."""
    results: list[RowResult] = []
    first_seen: dict[str, int] = {}
    for row in rows:
        email = row.values.get(email_column, "").strip()
        key = email.lower()
        result = RowResult(row=row.number, email=email, values=row.values, status=OK)

        if not email:
            result.status, result.reason = SKIPPED, "email address is empty"
        elif not is_valid_email(email):
            result.status, result.reason = SKIPPED, "invalid email format"
        elif key in first_seen:
            result.status = SKIPPED
            result.reason = f"duplicate address (first in row {first_seen[key]})"
        else:
            first_seen[key] = row.number
            missing = sorted(c for c in required_columns if not row.values.get(c))
            if missing:
                result.status = SKIPPED
                result.reason = "missing value for " + ", ".join(missing)
            elif key in already_sent:
                result.status, result.reason = ALREADY_SENT, "in send log"
        results.append(result)
    return results
