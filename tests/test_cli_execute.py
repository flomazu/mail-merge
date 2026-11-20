"""End-to-end sending to a local SMTP test server."""

import socket
from email import message_from_bytes, policy

from mail_merge.sendlog import read_sent


def received(server):
    return [
        (env.rcpt_tos, message_from_bytes(env.content, policy=policy.default))
        for env in server.handler.envelopes
    ]


def test_individual_send_and_no_duplicates_on_rerun(workdir, cli, make_config, smtp_server):
    config = make_config(smtp={"port": smtp_server.port, "host": "127.0.0.1"})

    code, summary = cli("--config", str(config), "--execute")

    assert code == 1  # skipped rows in the example list
    assert summary["counts"]["sent"] == 4
    assert summary["report"].endswith("_sent.xlsx")
    mails = received(smtp_server)
    assert [rcpt for rcpt, _ in mails] == [
        ["anna.schmidt@example.com"],
        ["andreas.mueller@example.com"],
        ["info@beispiel-handel.example"],
        ["tom.becker@example.org"],
    ]
    _, fallback_mail = mails[2]
    assert fallback_mail.get_body().get_content().startswith("Sehr geehrte Damen und Herren,")
    assert fallback_mail["Subject"] == "Einladung zum Kundentag für Beispiel Handel KG"
    assert [a.get_filename() for a in fallback_mail.iter_attachments()] == ["agenda.pdf"]
    assert len(read_sent(workdir / "output" / "send_log.csv")) == 4

    # Second run: nothing new is sent.
    code, summary = cli("--config", str(config), "--execute")
    assert summary["counts"]["sent"] == 0
    assert summary["counts"]["already_sent"] == 4
    assert len(smtp_server.handler.envelopes) == 4


def test_bcc_send(workdir, cli, make_config, smtp_server):
    config = make_config("config_bcc.yaml", smtp={"port": smtp_server.port, "host": "127.0.0.1"})

    code, summary = cli("--config", str(config), "--execute")

    assert summary["counts"]["sent"] == 5
    mails = received(smtp_server)
    assert [rcpt for rcpt, _ in mails] == [
        ["anna.schmidt@example.com", "andreas.mueller@example.com"],
        ["info@beispiel-handel.example", "lisa.weber@example.com"],
        ["tom.becker@example.org"],
    ]
    for _, message in mails:
        assert message["To"] == "info@example.com"
        assert message["Bcc"] is None  # BCC addresses are not visible to recipients


def test_refused_address_is_retried_on_next_run(workdir, cli, make_config, smtp_server):
    config = make_config(smtp={"port": smtp_server.port, "host": "127.0.0.1"})
    smtp_server.handler.refuse = {"tom.becker@example.org"}

    code, summary = cli("--config", str(config), "--execute")
    assert summary["counts"]["sent"] == 3
    assert summary["counts"]["failed"] == 1
    assert "tom.becker@example.org" not in read_sent(workdir / "output" / "send_log.csv")

    smtp_server.handler.refuse = set()
    code, summary = cli("--config", str(config), "--execute")
    assert summary["counts"]["sent"] == 1
    assert summary["counts"]["already_sent"] == 3
    assert smtp_server.handler.envelopes[-1].rcpt_tos == ["tom.becker@example.org"]


def test_refused_address_in_bcc_batch(workdir, cli, make_config, smtp_server):
    config = make_config("config_bcc.yaml", smtp={"port": smtp_server.port, "host": "127.0.0.1"})
    smtp_server.handler.refuse = {"andreas.mueller@example.com"}

    _, summary = cli("--config", str(config), "--execute")

    assert summary["counts"]["sent"] == 4
    assert summary["counts"]["failed"] == 1
    assert read_sent(workdir / "output_bcc" / "send_log.csv") == {
        "anna.schmidt@example.com", "info@beispiel-handel.example",
        "lisa.weber@example.com", "tom.becker@example.org",
    }


def test_unreachable_server_aborts(workdir, cli, make_config):
    with socket.socket() as sock:  # a free port with no server behind it
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = make_config(smtp={"port": port, "host": "127.0.0.1"})

    code, summary = cli("--config", str(config), "--execute")

    assert code == 2
    assert summary["status"] == "aborted"
    assert not (workdir / "output" / "send_log.csv").exists()
