# AI Agent Reference for ha-rewe

---

## Token Efficiency Rules (CRITICAL — Read First)

These rules apply to **every response** without exception:

1. **Output minimal prose.** Bullet points only. No introductory sentences, no filler, no "Great question!", no "As requested".
2. **No walkthrough unless explicitly asked.** Never create or update `walkthrough.md` unless the user writes "walkthrough" or "summary" in their request.
3. **No implementation plan unless complex.** Skip planning artifacts for simple tweaks, single-file edits, bug fixes, or minor features. Plan only for major architectural changes.
4. **Short change summaries only.** After making changes, output ≤5 bullet points describing *what* changed and *why* — never a line-by-line description.
5. **No repeating file content.** Never echo back code you just wrote or edited. Reference filenames with links instead.
6. **No tool-call narration.** Do not describe what tool you are about to call. Just call it.
7. **Targeted file reads only.** Use `grep_search` or `view_file` with `StartLine`/`EndLine` to read only the relevant section.
8. **Skip trivial confirmations.** Do not ask "Would you like me to proceed?" for obvious next steps. Just do them.
9. **No closing pleasantries.** End your response after the change summary.
10. **Suppress test output noise.** When running pytest, only report failures. Do not paste successful test output unless the user asks.

---

## Codebase Architecture

| Area | Path |
|---|---|
| Integration Entry | `custom_components/rewe/__init__.py` |
| Coordinator | `custom_components/rewe/coordinator.py` |
| Config Flow | `custom_components/rewe/config_flow.py` |
| Sensor platform | `custom_components/rewe/sensor.py` |
| Workflows | `.github/workflows/` |
| Scripts | `.github/scripts/` |

---

## CLI Commands

| Task | Command | Dir |
|---|---|---|
| Ruff linter | `ruff check . --fix` | Root |
| mypy linter | `mypy .` | Root |

---

## Coding Rules

- **Traceback Preservation**: NEVER use `raise e`. ALWAYS use `raise ... from e` or a naked `raise` to prevent stack trace destruction.
- **Silent Failure Prohibition**: `except: pass` is FORBIDDEN. All exceptions must be wrapped and propagated, or logged with context.
- **Async HA Patterns**: Ensure all Home Assistant async updates are correctly handled.
