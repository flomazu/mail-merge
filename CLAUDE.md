# CLAUDE.md

Small, standalone automation building blocks for Excel-heavy business processes.
Each repo is one building block. Blocks can be chained (e.g. via n8n or a script),
but never depend on each other.

## Scope discipline
- Build only what SPEC.md describes. Ideas beyond it go into "Possible extensions"
  in the README, not into code.
- Simplest working solution first. No abstractions for hypothetical future needs.
- Ask before adding a dependency, a new config option or a new adapter.
- If something in SPEC.md is unclear, ask instead of assuming.
- Plan first, then implement after approval.

## Structure
```
README.md
SPEC.md
config.example.yaml
Dockerfile
src/<package_name>/   # core logic + CLI
examples/             # dummy input and expected output, no real data
tests/
variants/             # optional: non-Python variants (e.g. power-automate/)
```

## Core and adapters
- The core contains the business logic and makes no assumption about where it runs
  (local, server, container). No hard-coded paths, no GUI, no interactive prompts.
- Connections to external systems (mail, storage, mailbox) are adapters behind a
  small interface. SPEC.md names the adapter for v1; add others only when asked.

## Docker
- The code must work on its own without Docker (installable via pip). Docker is an
  optional wrapper around it, never a requirement.
- Every block ships a Dockerfile by default. Skip it only if SPEC.md says so
  (e.g. an adapter that needs a local desktop app).
- The container runs the same CLI as a local install. Config, input and output
  are mounted as volumes; nothing customer-specific is baked into the image.
- No secrets in the image; pass them as environment variables at runtime.
- Small official base image, no extra tooling beyond what the block needs.

## Input/output contract
- Input: Excel (.xlsx) or CSV. Sheet, header row and column names come from the
  config, never from the code.
- Output, always:
  1. the result (file, drafts, ...)
  2. a report (.xlsx): what was processed, what was skipped and why
  3. a JSON summary, printed to stdout with `--json`
- Exit codes: 0 = success, 1 = completed with data errors, 2 = aborted
  (config or technical error).

## Config
- One YAML config per setup (e.g. one per mailing type), reused across runs;
  single values can be overridden via CLI flags.
- Secrets only via environment variables. Never in config files, code or the repo.

## Safety
- Never modify input files.
- Dry run is the default. Sending or writing to external systems requires an
  explicit flag (e.g. `--execute`).
- Re-running must not create duplicates (e.g. no second mail to the same recipient
  for the same run).
- Clear, human-readable log output.

## Dependencies and licensing
- Python 3, CLI via argparse. Keep dependencies minimal.
- Only permissively licensed packages (MIT, BSD, Apache 2.0). Check before adding
  and list every dependency with its license in the README.
- This repo is MIT-licensed.

## Tests
- pytest, using the files in examples/. Tests run in GitHub Actions on every push.

## README (English)
Problem → Before/after (time saved) → Quickstart (as few commands as needed) → Config →
Input/output → Variants → Limitations → Possible extensions → Dependencies and licenses.
