"""Read the recipient list from .xlsx or .csv.

Input files are only opened for reading and never modified.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from mail_merge.config import ConfigError, InputSettings


@dataclass
class Row:
    number: int  # row number as shown in Excel / line number in the CSV
    values: dict[str, str]


def read_rows(settings: InputSettings) -> tuple[list[str], list[Row]]:
    """Return the column headers and all non-empty data rows."""
    path = settings.file
    if not path.is_file():
        raise ConfigError(f"Input file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        raw_rows = _read_xlsx(path, settings.sheet)
    elif suffix == ".csv":
        raw_rows = _read_csv(path, settings.csv_delimiter, settings.encoding)
    else:
        raise ConfigError(f"Unsupported input file type '{suffix}'. Use .xlsx or .csv.")

    if len(raw_rows) < settings.header_row:
        raise ConfigError(f"Input file has no header row {settings.header_row}.")
    headers = [_to_text(h) for h in raw_rows[settings.header_row - 1]]
    named = [h for h in headers if h]
    if len(named) != len(set(named)):
        raise ConfigError("Input file has duplicate column names in the header row.")

    rows: list[Row] = []
    for offset, raw in enumerate(raw_rows[settings.header_row :], start=1):
        values = {
            header: _to_text(raw[i]) if i < len(raw) else ""
            for i, header in enumerate(headers)
            if header
        }
        if any(values.values()):
            rows.append(Row(number=settings.header_row + offset, values=values))
    return named, rows


def _read_xlsx(path: Path, sheet: str | None) -> list[tuple]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet:
            if sheet not in workbook.sheetnames:
                raise ConfigError(
                    f"Sheet '{sheet}' not found. Available: {', '.join(workbook.sheetnames)}"
                )
            worksheet = workbook[sheet]
        else:
            worksheet = workbook.worksheets[0]
        return list(worksheet.iter_rows(values_only=True))
    finally:
        workbook.close()


def _read_csv(path: Path, delimiter: str, encoding: str) -> list[list[str]]:
    try:
        with path.open(encoding=encoding, newline="") as handle:
            return list(csv.reader(handle, delimiter=delimiter))
    except UnicodeDecodeError as exc:
        raise ConfigError(
            f"Could not read {path.name} with encoding '{encoding}'. "
            "Set input.encoding in the config (e.g. cp1252)."
        ) from exc


def _to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dt.datetime) and value.time() == dt.time(0, 0):
        return value.date().isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
