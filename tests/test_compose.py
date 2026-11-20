from mail_merge.compose import compose_bcc, compose_individual, load_attachment
from mail_merge.config import load_config
from mail_merge.precheck import OK, RowResult
from mail_merge.template import load_template


def rows(*entries):
    return [
        RowResult(row=i, email=email, values={"Name": name, "Firma": firm}, status=OK)
        for i, (email, name, firm) in enumerate(entries, start=2)
    ]


def test_individual(workdir):
    config = load_config(workdir / "config.yaml")
    body = load_template(config.mail.template)
    attachment = load_attachment(config.mail.attachment)
    recipients = rows(("a@example.com", "Anna Schmidt", "Firma A"), ("b@example.com", "", "Firma B"))

    drafts = compose_individual(config, config.mail.subject, body, recipients, attachment)

    assert len(drafts) == 2
    first, second = (d.message for d in drafts)
    assert first["To"] == "a@example.com"
    assert first["Subject"] == "Einladung zum Kundentag für Firma A"
    assert first["From"] == "Beispiel GmbH <einladung@example.com>"
    assert first.get_body().get_content().startswith("Guten Tag Anna Schmidt,")
    assert "wir laden Firma A herzlich" in first.get_body().get_content()
    assert second.get_body().get_content().startswith("Sehr geehrte Damen und Herren,")
    assert [a.get_filename() for a in first.iter_attachments()] == ["agenda.pdf"]
    assert recipients[0].subject == "Einladung zum Kundentag für Firma A"
    assert recipients[0].greeting == "Guten Tag Anna Schmidt,"
    assert recipients[1].greeting == "Sehr geehrte Damen und Herren,"


def test_bcc_batches(workdir):
    config = load_config(workdir / "config_bcc.yaml")  # bcc_batch_size: 2
    body = load_template(config.mail.template)
    recipients = rows(*[(f"p{i}@example.com", "", "") for i in range(5)])

    drafts = compose_bcc(config, config.mail.subject, body, recipients, None)

    assert [d.recipients for d in drafts] == [
        ["p0@example.com", "p1@example.com"],
        ["p2@example.com", "p3@example.com"],
        ["p4@example.com"],
    ]
    message = drafts[0].message
    assert message["To"] == "info@example.com"  # default: sender's own address
    assert message["Bcc"] == "p0@example.com, p1@example.com"
    assert message.get_content().startswith("Sehr geehrte Damen und Herren,")
    assert not list(message.iter_attachments())


def test_bcc_visible_to_is_configurable(make_config):
    config = load_config(make_config("config_bcc.yaml", mail={"bcc_to": "kunden@example.com"}))
    drafts = compose_bcc(config, "Betreff", "{greeting}", rows(("a@example.com", "", "")), None)
    assert drafts[0].message["To"] == "kunden@example.com"
