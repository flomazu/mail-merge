# SPEC: mail-merge (v1)

## Goal
Send one prepared email text to all recipients in an Excel/CSV list, without
copying addresses or text by hand.

## Input
- Recipient list: .xlsx or .csv. Required: one column with email addresses.
  Any other column can be used as a placeholder in subject and body, e.g. {Company}.
- Body template: .txt or .docx with placeholders, e.g. `template.docx`.
  From .docx only the text is used in v1 (no formatting).
- Config (YAML): input file, sheet, column mapping, subject, template path,
  mode, attachment, SMTP settings (without password), path of the send log,
  output folder.
- CSV: delimiter and encoding come from the config (defaults `;` and `utf-8-sig`,
  matching a German Excel export).

## Modes
- `individual` (default): one email per recipient, placeholders filled per row.
- `bcc`: one email with all recipients in BCC. The visible To address is
  configurable (default: the sender's own address). No per-row
  placeholders; the fallback greeting is used. Split into several emails if the
  number of recipients exceeds `bcc_batch_size` (configurable).
  If subject or body contain any placeholder other than `{greeting}`, the run
  aborts before sending (exit 2) with a clear message.

## Greeting
The list needs no salutation column. The greeting is built from a pattern in the
config, e.g. `greeting: "Guten Tag {Name},"` and
`greeting_fallback: "Sehr geehrte Damen und Herren,"`. Subject and body use the
reserved placeholder `{greeting}`. If any value used in the pattern is empty,
the fallback is used and the email is still sent.

## Pre-check (before anything is sent)
Skip and report rows with: invalid email format, duplicate address within the
list, missing values for placeholders used in subject or body.
A column is only required if its placeholder appears in subject or body
(the greeting pattern is exempt, see Greeting).

## Attachment
Optional: one file attached to every email (path in config).

## Adapter (v1)
SMTP. Config: host, port, security (`starttls` | `ssl` | `none`), sender
address and name. Credentials via environment variables `SMTP_USER` and
`SMTP_PASSWORD` (both optional, e.g. for a local test server), optionally loaded
from a local `.env` file (listed in .gitignore; `.env.example` in the repo;
read without an extra dependency). Configurable pause between emails.

## Dry run and execution
- Default: dry run. Nothing is sent.
  - Terminal: short summary (counts, first few recipients, skipped rows).
  - Report: every recipient with the greeting used and the final subject
    (placeholders filled in).
    File name ends in `_dryrun` (or `_sent` with `--execute`); the mode is also
    stated at the top of the sheet.
  - Preview: the first email as an .eml file in the output folder, which opens
    in any mail program as a normal email view.
- `--execute` sends.

## No double sending
Write a send log (CSV, one per config): only successfully sent emails, with
address and timestamp. Each address is written right after the server accepted
it, so an interrupted run can be resumed. On start, skip addresses already in the
log (status `already_sent`, not an error). Failed emails, and addresses the server
refused in a BCC batch, are not logged; they appear as `failed` in the report and
are retried on the next run. Duplicates within one list are handled by the pre-check.

## Output
All files go to the configured output folder (`output_dir`, overridable with
`--output-dir`). Report (.xlsx, timestamped: sent / skipped + reason), send log,
JSON summary with `--json`, exit codes as defined in CLAUDE.md. Exit code 1 if
any row was skipped by the pre-check or failed to send; `already_sent` is not an error.

## Runtime
Python 3.11 or newer for pip installs. The Docker image uses Python 3.14.

## Done when
- Dry run and sending to a local test SMTP server work with the files in examples/.
- Both modes and the pre-check are covered by tests; tests pass in GitHub Actions.
- Dockerfile builds and runs the same CLI.
- README is complete.

## Not in v1
HTML emails, personalised attachments per recipient, Outlook or Microsoft Graph
adapter, GUI, scheduling.
