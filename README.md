# mail-merge

Send one prepared email text to every recipient in an Excel or CSV list, with
placeholders like `{Firma}` filled per recipient. Dry run by default; nothing is
sent without `--execute`.

One of several small, independent automation building blocks for business
processes, often built around Excel and Microsoft 365. It reads files and writes files, so it can be chained with
other tools (e.g. n8n or a script) without depending on them.

## Problem

An invitation, a price update or an office-closure notice has to go to 100
contacts from an Excel list. In practice that means copying addresses and
names by hand, one email at a time, or pasting everyone into one CC field by
mistake. It is slow, error-prone, and hard to tell afterwards who actually got
the email.

## Before / after

| | By hand | With mail-merge |
|---|---|---|
| 100 personalised emails | ~2–3 hours of copy and paste | ~10 minutes: check the dry run, then send |
| Typos in addresses, duplicates | noticed when mails bounce | listed in the report before sending |
| "Who already got it?" | search the sent folder | send log; a re-run never sends twice |

The times are rough estimates for a list of 100 contacts.

## Quickstart

Requires Python 3.11 or newer.

```bash
pip install git+https://github.com/FloMazu/mail-merge
mail-merge --config examples/config.yaml            # dry run: report + preview.eml
mail-merge --config examples/config.yaml --execute  # send
```

To try sending without a real mail account, start a local test server first.
[Mailpit](https://github.com/axllent/mailpit) accepts mails on port 1025 and
shows them in the browser at http://localhost:8025:

```bash
docker run --rm -p 1025:1025 -p 8025:8025 axllent/mailpit
```

Without Docker, `python -m aiosmtpd -n -l localhost:1025` (installed with the dev
extras) prints received mails to the terminal.

For development:

```bash
git clone https://github.com/FloMazu/mail-merge && cd mail-merge
pip install -e ".[dev]"   # editable install plus pytest and aiosmtpd
pytest
```

### CLI

| Flag | Meaning |
|---|---|
| `--config PATH` | YAML config (required) |
| `--execute` | actually send; without it, only a dry run |
| `--json` | print a JSON summary to stdout (logs go to stderr) |
| `--input PATH` | override `input.file` |
| `--output-dir PATH` | override `output_dir` |
| `--mode individual\|bcc` | override `mail.mode` |
| `--env-file PATH` | file with SMTP credentials (default `.env`) |

Exit codes: `0` success, `1` completed but rows were skipped or failed,
`2` aborted (config or technical error, e.g. SMTP server unreachable).

## Config

One YAML file per mailing type, reused across runs. See
[config.example.yaml](config.example.yaml) for every option with comments, and
[examples/](examples/) for two working setups (individual mode with Excel,
bcc mode with CSV). Relative paths are resolved against the config file's folder.

**Placeholders.** Any column name in curly braces, e.g. `{Firma}`, in subject or
body. A column is only required if its placeholder is used; rows with an empty
value for it are skipped.

**Greeting.** The list needs no salutation column. `greeting: "Guten Tag {Name},"`
builds the greeting per row; the template uses `{greeting}`. If the name is
empty, `greeting_fallback` is used and the email is still sent.

**Modes.**
- `individual`: one email per recipient, all placeholders filled.
- `bcc`: one email per batch of `bcc_batch_size` recipients, all in BCC; the
  visible To is `bcc_to` (default: the sender). Only `{greeting}` is allowed and
  always uses the fallback; any other placeholder aborts the run.

**Credentials.** Only via the environment variables `SMTP_USER` and
`SMTP_PASSWORD`, optionally from a `.env` file (copy [.env.example](.env.example)).
Both can stay empty for a local test server.

## Input / output

Input files are only read, never modified.

| File | When | Content |
|---|---|---|
| Recipient list (`.xlsx` / `.csv`) | input | one column with email addresses, any others as placeholders |
| Template (`.txt` / `.docx`) | input | body text with placeholders; from `.docx` only the plain text |
| Attachment | input, optional | one file attached to every email |
| `report_<timestamp>_dryrun.xlsx` / `_sent.xlsx` | every run, new file | every row with status, reason and final subject; mode stated at the top |
| `preview.eml` | dry run, overwritten | the first email; opens in Outlook or Thunderbird like a received mail |
| Send log (`.csv`) | `--execute`, appended | address and time of every successfully sent email; the tool's memory across runs |
| JSON summary | `--json` | counts and file paths, printed to stdout |

Statuses in the report: `would_send` (dry run), `sent`, `skipped` (invalid
format, duplicate in the list, missing placeholder value), `already_sent` (in the
send log, not an error), `failed` (send error or refused by the server).

**No double sending.** Each address is written to the send log right after the
server accepted it. A re-run skips those addresses and retries only the ones
that failed. An interrupted run can simply be started again.

## Variants

### Docker

Docker is optional; it runs the same CLI without installing Python. The image
contains only the tool. Config, list and output come from a mounted folder,
credentials from environment variables at runtime.

```bash
docker build -t mail-merge .
docker run --rm -v "$PWD/examples:/data" mail-merge --config config.yaml
docker run --rm -v "$PWD/examples:/data" --env-file .env mail-merge --config config.yaml --execute
```

`-v "$PWD/examples:/data"` makes the local `examples` folder visible inside the
container as `/data`, the container's working folder. Output is written there too.

Notes:
- Inside a container, `localhost` is the container itself. To reach Mailpit on
  your machine, set `smtp.host: host.docker.internal` (on Linux also add
  `--add-host=host.docker.internal:host-gateway`).
- The container runs as user ID 1000. On Linux, if the mounted folder belongs to
  another user, add `--user "$(id -u):$(id -g)"`.

## Limitations

- Plain-text emails only; formatting in `.docx` templates is ignored.
- The email check only catches obvious typos; it does not verify that an address exists.
- One attachment, the same for every recipient.
- Placeholders are matched by exact column name; literal curly braces in the
  text are not supported.
- If the tool stops in the split second between the server accepting an email
  and the send log entry being written, that one email may be sent again on the
  next run.
- In bcc mode the visible To address does not receive a copy.

## Possible extensions

- HTML emails
- Microsoft Graph / Outlook adapter
- Personalised attachments per recipient
- Greeting with a salutation column ("Sehr geehrter Herr Müller")
- GUI, or generating the config from a template
- Scheduling, hosting and triggering via n8n
- Publishing on PyPI

## Dependencies and licenses

| Package | Purpose | License |
|---|---|---|
| [PyYAML](https://pypi.org/project/PyYAML/) | read the config | MIT |
| [openpyxl](https://pypi.org/project/openpyxl/) (+ et-xmlfile) | read and write .xlsx | MIT |
| [python-docx](https://pypi.org/project/python-docx/) | read .docx templates | MIT |
| ↳ lxml | used by python-docx | BSD-3-Clause |
| ↳ typing_extensions | used by python-docx | PSF-2.0 |
| [setuptools](https://pypi.org/project/setuptools/) | build only | MIT |
| **Development only** | | |
| [pytest](https://pypi.org/project/pytest/) (+ pluggy, iniconfig, packaging, Pygments, colorama) | tests | MIT / Apache-2.0 / BSD |
| [aiosmtpd](https://pypi.org/project/aiosmtpd/) (+ atpublic, attrs) | SMTP test server | Apache-2.0 / MIT |
| **Optional tool, not a Python dependency** | | |
| [Mailpit](https://github.com/axllent/mailpit) | local test mail server with web UI | MIT |

CSV, email building, SMTP, `.eml` and `.env` reading use the Python standard library.

This project is licensed under the [MIT License](LICENSE).
