"""End-to-end dry runs through the CLI. Nothing is sent."""

import json
from email import policy
from email.parser import BytesParser

from openpyxl import load_workbook

from conftest import EXAMPLES


def test_dry_run_matches_expected_summary(workdir, cli):
    code, summary = cli("--config", str(workdir / "config.yaml"))

    expected = json.loads((EXAMPLES / "expected" / "summary.json").read_text(encoding="utf-8"))
    for key in ("schema_version", "mode", "rows", "emails", "counts", "exit_code"):
        assert summary[key] == expected[key], key
    assert code == 0  # CI DEMO: deliberately wrong, the example list has skipped rows
    assert not (workdir / "output" / "send_log.csv").exists()


def test_dry_run_report(workdir, cli):
    _, summary = cli("--config", str(workdir / "config.yaml"))

    assert summary["report"].endswith("_dryrun.xlsx")
    sheet = load_workbook(summary["report"]).active
    assert sheet["B1"].value == "DRY RUN (nothing was sent)"
    rows = {r[0]: r for r in sheet.iter_rows(min_row=6, values_only=True)}
    assert sheet["E5"].value == "Greeting"
    assert rows[2][2:] == (
        "would_send", None, "Guten Tag Anna Schmidt,",
        "Einladung zum Kundentag für Schmidt Logistik GmbH",
    )
    assert rows[4][4] == "Sehr geehrte Damen und Herren,"  # no name -> fallback
    assert rows[5][2:5] == ("skipped", "invalid email format", None)
    assert len(rows) == 7


def test_dry_run_preview_eml(workdir, cli):
    _, summary = cli("--config", str(workdir / "config.yaml"))

    with open(summary["preview"], "rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)
    assert message["To"] == "anna.schmidt@example.com"
    assert message.get_body().get_content().startswith("Guten Tag Anna Schmidt,")
    assert [a.get_filename() for a in message.iter_attachments()] == ["agenda.pdf"]


def test_docx_template_gives_same_result(workdir, cli, make_config):
    code, summary = cli("--config", str(make_config(mail={"template": "template.docx"})))
    assert code == 1
    assert summary["counts"]["would_send"] == 4


def test_bcc_dry_run_with_csv(workdir, cli):
    code, summary = cli("--config", str(workdir / "config_bcc.yaml"))

    assert summary["send_mode"] == "bcc"
    # No placeholders in bcc mode -> the row without Firma is sent too.
    assert summary["counts"]["would_send"] == 5
    assert summary["emails"] == 3  # batch size 2
    with open(summary["preview"], "rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)
    assert message["Bcc"] == "anna.schmidt@example.com, andreas.mueller@example.com"
    # Only the invalid address and the duplicate are skipped.
    assert summary["counts"]["skipped"] == 2
    assert code == 1


def test_mode_override_to_bcc_rejects_row_placeholders(workdir, cli):
    code, summary = cli("--config", str(workdir / "config.yaml"), "--mode", "bcc")
    assert code == 2
    assert summary["status"] == "aborted"
    assert "Firma" in summary["error"]


def test_unknown_placeholder_aborts(cli, make_config):
    code, summary = cli("--config", str(make_config(mail={"subject": "Hallo {Ort}"})))
    assert code == 2
    assert "Ort" in summary["error"]


def test_clean_list_exits_zero(workdir, cli, tmp_path):
    clean = tmp_path / "clean.csv"
    clean.write_text("E-Mail;Name;Firma\na@example.com;A;X\n", encoding="utf-8")
    code, summary = cli("--config", str(workdir / "config.yaml"), "--input", str(clean))
    assert code == 0
    assert summary["counts"]["would_send"] == 1


def test_missing_config_exits_two(cli, tmp_path):
    code, summary = cli("--config", str(tmp_path / "missing.yaml"))
    assert code == 2
    assert summary["status"] == "aborted"
    assert summary["schema_version"] == 1
