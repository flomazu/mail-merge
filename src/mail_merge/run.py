"""One complete run: read, check, compose, then dry run or send."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mail_merge.adapters.base import Mailer
from mail_merge.compose import Draft, compose_bcc, compose_individual, load_attachment
from mail_merge.config import Config, ConfigError
from mail_merge.precheck import OK, SKIPPED, RowResult, precheck
from mail_merge.reader import read_rows
from mail_merge.report import counts, report_path, write_report
from mail_merge.sendlog import SendLog, read_sent
from mail_merge.template import GREETING, load_template, placeholders

log = logging.getLogger(__name__)

WOULD_SEND = "would_send"
SENT = "sent"
FAILED = "failed"
PREVIEW_NAME = "preview.eml"
SHOW_FIRST = 5


@dataclass
class RunResult:
    summary: dict[str, Any]
    exit_code: int


def run(config: Config, execute: bool = False, mailer: Mailer | None = None) -> RunResult:
    """Run the mail merge. `mailer` is required when `execute` is True."""
    started = datetime.now()
    headers, rows = read_rows(config.input)
    body = load_template(config.mail.template)
    required = _required_columns(config, headers, body)
    attachment = load_attachment(config.mail.attachment)

    results = precheck(rows, config.email_column, required, read_sent(config.send_log))
    ready = [r for r in results if r.status == OK]
    compose = compose_bcc if config.mail.mode == "bcc" else compose_individual
    drafts = compose(config, config.mail.subject, body, ready, attachment)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    preview = None
    if execute:
        if mailer is None:
            raise ValueError("A mailer is required to send.")
        _send(drafts, mailer, SendLog(config.send_log), config.smtp.pause_seconds)
    else:
        for r in ready:
            r.status = WOULD_SEND
        if drafts:
            preview = config.output_dir / PREVIEW_NAME
            preview.write_bytes(drafts[0].message.as_bytes())

    report = report_path(config.output_dir, started, execute)
    write_report(report, results, execute, config.name, started)

    tally = counts(results)
    exit_code = 1 if tally[SKIPPED] or tally[FAILED] else 0
    _log_summary(results, tally, len(drafts), execute, config.mail.mode)
    log.info("Report: %s", report)
    if preview:
        log.info("Preview of the first email: %s", preview)

    summary = {
        "status": "completed",
        "mode": "execute" if execute else "dry_run",
        "send_mode": config.mail.mode,
        "config": config.name,
        "rows": len(results),
        "emails": len(drafts),
        "counts": tally,
        "report": str(report),
        "preview": str(preview) if preview else None,
        "send_log": str(config.send_log),
        "exit_code": exit_code,
    }
    return RunResult(summary, exit_code)


def _required_columns(config: Config, headers: list[str], body: str) -> set[str]:
    """Columns that must have a value in every row. Raises ConfigError on mismatches."""
    used = placeholders(config.mail.subject) | placeholders(body)
    columns = used - {GREETING}
    if config.email_column not in headers:
        raise ConfigError(
            f"Email column '{config.email_column}' not found. Columns: {', '.join(headers)}"
        )
    if config.mail.mode == "bcc":
        if columns:
            raise ConfigError(
                "In bcc mode all recipients get the same email, so only {greeting} can be "
                f"used. Remove these placeholders: {', '.join(sorted(columns))}"
            )
        return set()

    greeting_columns = placeholders(config.mail.greeting)
    if GREETING in greeting_columns:
        raise ConfigError("mail.greeting must not contain {greeting} itself.")
    unknown = (columns | greeting_columns) - set(headers)
    if unknown:
        raise ConfigError(
            f"Placeholders without a matching column: {', '.join(sorted(unknown))}. "
            f"Columns: {', '.join(headers)}"
        )
    return columns


def _send(drafts: list[Draft], mailer: Mailer, send_log: SendLog, pause: float) -> None:
    if not drafts:
        log.info("Nothing to send.")
        return
    mailer.connect()  # fails early (exit 2) if the server is unreachable
    try:
        for index, draft in enumerate(drafts):
            if index and pause:
                time.sleep(pause)
            try:
                refused = mailer.send(draft.message, draft.recipients)
            except Exception as exc:
                log.error("Email %d of %d failed: %s", index + 1, len(drafts), exc)
                for r in draft.rows:
                    r.status, r.reason = FAILED, f"send error: {exc}"
                continue
            for r in draft.rows:
                if r.email in refused:
                    r.status, r.reason = FAILED, f"refused by server: {refused[r.email]}"
                    log.error("Refused: %s (%s)", r.email, refused[r.email])
                else:
                    send_log.append(r.email)
                    r.status = SENT
            log.info("Sent email %d of %d (%d recipient(s))", index + 1, len(drafts),
                     len(draft.recipients))
    finally:
        mailer.close()


def _log_summary(
    results: list[RowResult], tally: dict[str, int], emails: int, execute: bool, mode: str
) -> None:
    if execute:
        log.info("Sent: %d recipient(s) in %d email(s) (%s mode).", tally[SENT], emails, mode)
    else:
        log.info("DRY RUN - nothing was sent. Use --execute to send.")
        log.info("Would send: %d recipient(s) in %d email(s) (%s mode).",
                 tally[WOULD_SEND], emails, mode)
        first = [r.email for r in results if r.status == WOULD_SEND][:SHOW_FIRST]
        if first:
            log.info("First recipients: %s", ", ".join(first))
    log.info("Skipped: %d, already sent: %d, failed: %d.",
             tally[SKIPPED], tally["already_sent"], tally[FAILED])
    for r in results:
        if r.status == SKIPPED:
            log.warning("  row %d %s: %s", r.row, r.email or "(no address)", r.reason)
