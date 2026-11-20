from mail_merge.template import build_greeting, fill, load_template, placeholders

FALLBACK = "Sehr geehrte Damen und Herren,"


def test_txt_and_docx_give_the_same_text(workdir):
    txt = load_template(workdir / "template.txt")
    docx = load_template(workdir / "template.docx")
    assert docx.strip() == txt.strip()


def test_placeholders(workdir):
    text = load_template(workdir / "template.txt")
    assert placeholders(text) == {"greeting", "Firma"}
    assert placeholders("{ Name } and {Firma}") == {"Name", "Firma"}


def test_fill():
    assert fill("Hallo {Name} von { Firma }", {"Name": "Anna", "Firma": "X"}) == "Hallo Anna von X"


def test_greeting_with_name():
    assert build_greeting("Guten Tag {Name},", FALLBACK, {"Name": "Anna Schmidt"}) == (
        "Guten Tag Anna Schmidt,"
    )


def test_greeting_falls_back_when_value_is_empty():
    assert build_greeting("Guten Tag {Name},", FALLBACK, {"Name": ""}) == FALLBACK


def test_greeting_falls_back_without_pattern():
    assert build_greeting("", FALLBACK, {"Name": "Anna"}) == FALLBACK
