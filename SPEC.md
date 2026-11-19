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
  mode, attachment, SMTP settings (without password), path of the send log.

## Modes
- `individual` (default): one email per recipient, placeholders filled per row.
  If the salutation value is empty, use a configurable fallback
  (e.g. "Sehr geehrte Damen und Herren").
- `bcc`: one email with all recipients in BCC. The visible To address is
  configurable (default: the sender's own address). No per-row
  placeholders; the fallback salutation is used. Split into several emails if the
  number of recipients exceeds `bcc_batch_size` (configurable).

## Pre-check (before anything is sent)
Skip and report rows with: invalid email format, duplicate address within the
list, missing values for placeholders used in the template.

## Attachment
Optional: one file attached to every email (path in config).

## Adapter (v1)
SMTP. Credentials via environment variables, optionally loaded from a local
`.env` file (listed in .gitignore; `.env.example` in the repo). Configurable pause
between emails.

## Dry run and execution
- Default: dry run. Nothing is sent.
  - Terminal: short summary (counts, first few recipients, skipped rows).
  - Report: every recipient with the final subject (placeholders filled in).
  - Preview: the first email as an .eml file in the output folder, which opens
    in any mail program as a normal email view.
- `--execute` sends.

## No double sending
Write a send log (CSV, one per config): only successfully sent emails, with
address and timestamp. On start, skip addresses already in the log. Duplicates within one list are handled by the pre-check.

## Output
Report (.xlsx: sent / skipped + reason), send log, JSON summary with `--json`,
exit codes as defined in CLAUDE.md.

## Done when
- Dry run and sending to a local test SMTP server work with the files in examples/.
- Both modes and the pre-check are covered by tests; tests pass in GitHub Actions.
- Dockerfile builds and runs the same CLI.
- README is complete.

## Not in v1
HTML emails, personalised attachments per recipient, Outlook or Microsoft Graph
adapter, GUI, scheduling.
