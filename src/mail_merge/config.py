"""Load and validate the YAML config.

Relative paths in the config are resolved against the folder that contains the
config file, so a config works the same no matter where the tool is started from.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

MODES = ("individual", "bcc")
SECURITY_OPTIONS = ("starttls", "ssl", "none")


class ConfigError(Exception):
    """Invalid or incomplete configuration. Leads to exit code 2."""


@dataclass
class InputSettings:
    file: Path
    sheet: str | None
    header_row: int
    csv_delimiter: str
    encoding: str


@dataclass
class MailSettings:
    mode: str
    subject: str
    template: Path
    greeting: str
    greeting_fallback: str
    attachment: Path | None
    bcc_to: str | None
    bcc_batch_size: int


@dataclass
class SmtpSettings:
    host: str
    port: int
    security: str
    from_address: str
    from_name: str
    pause_seconds: float


@dataclass
class Config:
    name: str
    input: InputSettings
    email_column: str
    mail: MailSettings
    smtp: SmtpSettings
    output_dir: Path
    send_log: Path


def load_config(path: str | Path, overrides: dict[str, Any] | None = None) -> Config:
    """Read the config file and apply CLI overrides (input_file, output_dir, mode).

    Override paths are taken as given (relative to the current folder),
    config paths relative to the config file.
    """
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config file is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Config file must contain a mapping at the top level.")

    overrides = {k: v for k, v in (overrides or {}).items() if v is not None}
    base = path.resolve().parent

    def resolve(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else base / p

    inp = _section(raw, "input")
    columns = _section(raw, "columns")
    mail = _section(raw, "mail")
    smtp = _section(raw, "smtp")

    input_file = (
        Path(overrides["input_file"])
        if "input_file" in overrides
        else resolve(_require(inp, "file", "input"))
    )
    input_settings = InputSettings(
        file=input_file,
        sheet=inp.get("sheet"),
        header_row=_positive_int(inp.get("header_row", 1), "input.header_row"),
        csv_delimiter=str(inp.get("csv_delimiter", ";")),
        encoding=str(inp.get("encoding", "utf-8-sig")),
    )

    mode = overrides.get("mode", mail.get("mode", "individual"))
    if mode not in MODES:
        raise ConfigError(f"mail.mode must be one of {', '.join(MODES)}, got '{mode}'.")
    attachment = mail.get("attachment")
    mail_settings = MailSettings(
        mode=mode,
        subject=str(_require(mail, "subject", "mail")),
        template=resolve(_require(mail, "template", "mail")),
        greeting=str(mail.get("greeting", "")),
        greeting_fallback=str(_require(mail, "greeting_fallback", "mail")),
        attachment=resolve(attachment) if attachment else None,
        bcc_to=mail.get("bcc_to") or None,
        bcc_batch_size=_positive_int(mail.get("bcc_batch_size", 50), "mail.bcc_batch_size"),
    )

    security = smtp.get("security", "starttls")
    if security not in SECURITY_OPTIONS:
        raise ConfigError(
            f"smtp.security must be one of {', '.join(SECURITY_OPTIONS)}, got '{security}'."
        )
    try:
        pause = float(smtp.get("pause_seconds", 1))
    except (TypeError, ValueError) as exc:
        raise ConfigError("smtp.pause_seconds must be a number.") from exc
    if pause < 0:
        raise ConfigError("smtp.pause_seconds must not be negative.")
    smtp_settings = SmtpSettings(
        host=str(_require(smtp, "host", "smtp")),
        port=_positive_int(_require(smtp, "port", "smtp"), "smtp.port"),
        security=security,
        from_address=str(_require(smtp, "from_address", "smtp")),
        from_name=str(smtp.get("from_name", "")),
        pause_seconds=pause,
    )

    output_dir = (
        Path(overrides["output_dir"])
        if "output_dir" in overrides
        else resolve(raw.get("output_dir", "output"))
    )
    send_log = resolve(_require(raw, "send_log", "top level"))

    return Config(
        name=path.stem,
        input=input_settings,
        email_column=str(_require(columns, "email", "columns")),
        mail=mail_settings,
        smtp=smtp_settings,
        output_dir=output_dir,
        send_log=send_log,
    )


def _section(raw: dict, key: str) -> dict:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"Config section '{key}' is missing or not a mapping.")
    return value


def _require(section: dict, key: str, where: str) -> Any:
    value = section.get(key)
    if value is None or value == "":
        raise ConfigError(f"Config value '{key}' in {where} is required.")
    return value


def _positive_int(value: Any, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a whole number.") from exc
    if number < 1:
        raise ConfigError(f"{name} must be at least 1.")
    return number
