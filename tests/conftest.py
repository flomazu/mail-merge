"""Shared fixtures: a temporary copy of examples/ and a local SMTP test server."""

from __future__ import annotations

import hashlib
import json
import shutil
import socket
from pathlib import Path

import pytest
import yaml
from aiosmtpd.controller import Controller

from mail_merge.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
INPUT_FILES = (
    "recipients.xlsx", "recipients.csv", "template.txt", "template.docx",
    "template_bcc.txt", "agenda.pdf", "config.yaml", "config_bcc.yaml",
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Copy of examples/ in a temp folder. Afterwards: input files must be unchanged."""
    target = tmp_path / "examples"
    shutil.copytree(EXAMPLES, target, ignore=shutil.ignore_patterns("output*"))
    before = {name: _digest(target / name) for name in INPUT_FILES}
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    yield target
    after = {name: _digest(target / name) for name in INPUT_FILES}
    assert after == before, "input files were modified"


@pytest.fixture
def make_config(workdir):
    """Write a variant of an example config. `smtp` / `mail` dicts are merged in."""

    def _make(base: str = "config.yaml", name: str = "test.yaml", **sections) -> Path:
        data = yaml.safe_load((workdir / base).read_text(encoding="utf-8"))
        data["smtp"]["pause_seconds"] = 0
        for key, value in sections.items():
            if isinstance(value, dict):
                data.setdefault(key, {}).update(value)
            else:
                data[key] = value
        path = workdir / name
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        return path

    return _make


@pytest.fixture
def cli(workdir, capsys):
    """Run the CLI with --json; returns (exit_code, summary)."""

    def _run(*args: str) -> tuple[int, dict]:
        code = main([*args, "--json", "--env-file", str(workdir / "no.env")])
        summary = json.loads(capsys.readouterr().out)
        return code, summary

    return _run


class _Collector:
    def __init__(self):
        self.envelopes = []
        self.refuse: set[str] = set()

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if address.lower() in self.refuse:
            return "550 mailbox unavailable"
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        self.envelopes.append(envelope)
        return "250 Message accepted"


@pytest.fixture
def smtp_server():
    """Local SMTP server on a free port. `.handler.envelopes` holds received mails."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    handler = _Collector()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()
    controller.handler = handler
    yield controller
    controller.stop()
