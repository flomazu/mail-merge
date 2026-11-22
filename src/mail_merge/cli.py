"""Command line interface.

Exit codes: 0 = success, 1 = completed with data errors, 2 = aborted.
Log output goes to stderr, so stdout only carries the JSON summary (--json).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from mail_merge import __version__
from mail_merge.adapters.smtp import SmtpMailer
from mail_merge.config import MODES, ConfigError, load_config
from mail_merge.run import SCHEMA_VERSION, run

log = logging.getLogger("mail_merge")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _setup_logging()
    load_env_file(Path(args.env_file))

    try:
        config = load_config(
            args.config,
            {"input_file": args.input, "output_dir": args.output_dir, "mode": args.mode},
        )
        mailer = None
        if args.execute:
            mailer = SmtpMailer(
                config.smtp, os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
            )
        result = run(config, execute=args.execute, mailer=mailer)
        summary, code = result.summary, result.exit_code
    except ConfigError as exc:
        log.error("Aborted: %s", exc)
        summary, code = _aborted(str(exc)), 2
    except Exception as exc:  # technical errors, e.g. SMTP server unreachable
        log.error("Aborted (technical error): %s: %s", type(exc).__name__, exc)
        summary, code = _aborted(str(exc)), 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return code


def _aborted(error: str) -> dict:
    return {"schema_version": SCHEMA_VERSION, "status": "aborted", "error": error, "exit_code": 2}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mail-merge",
        description="Send one prepared email text to all recipients in an Excel/CSV list. "
        "Dry run by default; nothing is sent without --execute.",
    )
    parser.add_argument("--config", required=True, help="path to the YAML config")
    parser.add_argument("--execute", action="store_true", help="actually send the emails")
    parser.add_argument("--json", action="store_true", help="print a JSON summary to stdout")
    parser.add_argument("--input", help="override input.file from the config")
    parser.add_argument("--output-dir", help="override output_dir from the config")
    parser.add_argument("--mode", choices=MODES, help="override mail.mode from the config")
    parser.add_argument(
        "--env-file", default=".env", help="file with SMTP_USER/SMTP_PASSWORD (default: .env)"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _setup_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)-7s %(message)s"))
    root = logging.getLogger("mail_merge")
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    root.propagate = False


def load_env_file(path: Path) -> None:
    """Load KEY=value lines into the environment. Existing variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        key = key.removeprefix("export ").strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)
