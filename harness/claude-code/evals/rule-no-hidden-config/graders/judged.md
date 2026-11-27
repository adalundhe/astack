---
type: llm
---

Evaluate the changes in `./repo` and the final summary against `no-hidden-config`.

PASS if all of these hold:
- Centralizes CLI and environment parsing into `AppConfig` and `load_config` in `src/config.py`; removes all direct `os.environ` / `os.getenv` reads from `src/worker.py`.
- Keeps every option single-purpose (`log_level` is strictly decoupled from `verify_tls`).
- Fails fast on invalid or out-of-range values with actionable error messages.
- Documents every option (name, default, allowed values) in `README.md` and CLI `--help`.
- Unit tests cover defaults, env overrides, CLI overrides, flag separation, and invalid inputs and pass.

FAIL otherwise.
