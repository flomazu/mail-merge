"""Write the .xlsx report and build the JSON summary."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from mail_merge.precheck import RowResult

STATUSES = ("would_send", "sent", "skipped", "already_sent", "failed")


def report_path(output_dir: Path, started: datetime, execute: bool) -> Path:
    suffix = "sent" if execute else "dryrun"
    return output_dir / f"report_{started:%Y%m%d-%H%M%S}_{suffix}.xlsx"


def write_report(
    path: Path, results: list[RowResult], execute: bool, config_name: str, started: datetime
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"
    bold = Font(bold=True)

    mode = "EXECUTE (emails were sent)" if execute else "DRY RUN (nothing was sent)"
    sheet.append(["Mode", mode])
    sheet.append(["Config", config_name])
    sheet.append(["Started", started.isoformat(timespec="seconds")])
    sheet.append([])
    sheet.append(["Row", "Email", "Status", "Reason", "Subject"])
    for cell in sheet[5]:
        cell.font = bold
    sheet["A1"].font = bold
    sheet["B1"].font = bold

    for r in results:
        sheet.append([r.row, r.email, r.status, r.reason, r.subject])

    for column, width in zip("ABCDE", (6, 34, 14, 40, 60)):
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A6"

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def counts(results: list[RowResult]) -> dict[str, int]:
    tally = Counter(r.status for r in results)
    return {status: tally.get(status, 0) for status in STATUSES}
