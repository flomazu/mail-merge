import pytest

from mail_merge.config import ConfigError, load_config


def test_example_config_resolves_paths_relative_to_config(workdir):
    config = load_config(workdir / "config.yaml")
    assert config.input.file == workdir / "recipients.xlsx"
    assert config.mail.template == workdir / "template.txt"
    assert config.mail.attachment == workdir / "agenda.pdf"
    assert config.send_log == workdir / "output" / "send_log.csv"
    assert config.mail.mode == "individual"
    assert config.email_column == "E-Mail"


def test_cli_overrides_win(workdir, tmp_path):
    config = load_config(
        workdir / "config.yaml",
        {"mode": "bcc", "output_dir": str(tmp_path / "out"), "input_file": None},
    )
    assert config.mail.mode == "bcc"
    assert config.output_dir == tmp_path / "out"
    assert config.input.file == workdir / "recipients.xlsx"


def test_defaults(workdir):
    config = load_config(workdir / "config_bcc.yaml")
    assert config.mail.bcc_to is None
    assert config.mail.greeting == ""
    assert config.input.sheet is None


@pytest.mark.parametrize(
    "content, message",
    [
        ("input: {}\n", "columns"),
        ("not: [valid", "YAML"),
    ],
)
def test_invalid_config(tmp_path, content, message):
    path = tmp_path / "bad.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        load_config(path)


def test_invalid_mode(make_config):
    with pytest.raises(ConfigError, match="mail.mode"):
        load_config(make_config(mail={"mode": "everyone"}))


def test_config_example_is_valid():
    from conftest import EXAMPLES

    config = load_config(EXAMPLES.parent / "config.example.yaml")
    assert config.smtp.security == "starttls"
    assert config.mail.bcc_batch_size == 50


def test_missing_config_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.yaml")
