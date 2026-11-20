import pytest

from mail_merge.config import ConfigError, InputSettings
from mail_merge.reader import read_rows


def settings(path, sheet=None, header_row=1):
    return InputSettings(
        file=path, sheet=sheet, header_row=header_row, csv_delimiter=";", encoding="utf-8-sig"
    )


def test_xlsx_and_csv_give_the_same_rows(workdir):
    headers_x, rows_x = read_rows(settings(workdir / "recipients.xlsx", "Recipients"))
    headers_c, rows_c = read_rows(settings(workdir / "recipients.csv"))
    assert headers_x == headers_c == ["E-Mail", "Name", "Firma"]
    assert [(r.number, r.values) for r in rows_x] == [(r.number, r.values) for r in rows_c]
    assert len(rows_x) == 7
    assert rows_x[0].number == 2
    assert rows_x[1].values["Name"] == "Andreas Müller"
    assert rows_x[2].values["Name"] == ""


def test_empty_rows_are_ignored(tmp_path):
    path = tmp_path / "list.csv"
    path.write_text("E-Mail;Name\na@example.com;A\n;\nb@example.com;B\n", encoding="utf-8")
    _, rows = read_rows(settings(path))
    assert [r.number for r in rows] == [2, 4]


def test_header_row_from_config(tmp_path):
    path = tmp_path / "list.csv"
    path.write_text("Export vom 1.1.\n\nE-Mail;Name\na@example.com;A\n", encoding="utf-8")
    headers, rows = read_rows(settings(path, header_row=3))
    assert headers == ["E-Mail", "Name"]
    assert rows[0].number == 4


def test_unknown_sheet(workdir):
    with pytest.raises(ConfigError, match="Sheet 'Nope' not found"):
        read_rows(settings(workdir / "recipients.xlsx", "Nope"))


def test_unsupported_file_type(workdir):
    with pytest.raises(ConfigError, match="Unsupported"):
        read_rows(settings(workdir / "template.txt"))
