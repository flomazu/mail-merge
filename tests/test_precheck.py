import pytest

from mail_merge.config import InputSettings
from mail_merge.precheck import ALREADY_SENT, OK, SKIPPED, is_valid_email, precheck
from mail_merge.reader import read_rows


@pytest.fixture
def rows(workdir):
    settings = InputSettings(workdir / "recipients.xlsx", "Recipients", 1, ";", "utf-8-sig")
    return read_rows(settings)[1]


def by_row(results):
    return {r.row: r for r in results}


def test_example_rows(rows):
    results = by_row(precheck(rows, "E-Mail", {"Firma"}, set()))
    assert [results[n].status for n in range(2, 9)] == [OK, OK, OK, SKIPPED, SKIPPED, SKIPPED, OK]
    assert results[5].reason == "invalid email format"
    assert results[6].reason == "duplicate address (first in row 2)"
    assert results[7].reason == "missing value for Firma"


def test_empty_name_is_not_a_missing_value(rows):
    # Name is only used in the greeting pattern, so it is not required.
    results = by_row(precheck(rows, "E-Mail", {"Firma"}, set()))
    assert results[4].status == OK


def test_column_not_used_in_template_is_not_required(rows):
    results = by_row(precheck(rows, "E-Mail", set(), set()))
    assert results[7].status == OK


def test_already_sent_is_case_insensitive(rows):
    results = by_row(precheck(rows, "E-Mail", {"Firma"}, {"tom.becker@example.org"}))
    assert results[8].status == ALREADY_SENT


@pytest.mark.parametrize(
    "address, valid",
    [
        ("anna@example.com", True),
        ("a.b+tag@sub.example.de", True),
        ("max@firma", False),
        ("max@@firma.de", False),
        ("max firma@example.com", False),
        ("", False),
    ],
)
def test_email_format(address, valid):
    assert is_valid_email(address) is valid
