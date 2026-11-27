---
description: "Centralize scattered os.environ reads and overloaded switches into one typed config loader with explicit CLI flags, fail-fast validation, docs, and tests."
expected_outcome: "Reads no-hidden-config/SKILL.md, centralizes all env/CLI parsing into AppConfig and load_config in src/config.py, removes direct os.environ reads from src/worker.py, separates log_level from verify_tls, validates bounds and fails fast on invalid values, documents every option in README.md and --help, and tests defaults, overrides, and invalid inputs."
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` The sync service in `./repo` (`src/worker.py`, `src/config.py`, `src/cli.py`) currently reads undocumented environment variables directly inside four helper functions with silent fallbacks and an overloaded debug switch that disables TLS verification.

Refactor `./repo` to parse all settings in one place (`AppConfig` and `load_config(argv=None, env=None)` in `src/config.py`) and wire `src/worker.py` and `src/cli.py` to use it with these exact options:
- `endpoint`: CLI `--endpoint`, env `SYNC_ENDPOINT`, default `"https://api.example.invalid"`, must start with `http://` or `https://`.
- `batch_size`: CLI `--batch-size`, env `SYNC_BATCH_SIZE`, default `50`, integer in `1..1000`.
- `output_format`: CLI `--output-format`, env `SYNC_OUTPUT_FORMAT`, default `"json"`, allowed values: `json`, `csv`, `ndjson`.
- `log_level`: CLI `--log-level`, env `SYNC_LOG_LEVEL`, default `"info"`, allowed values: `debug`, `info`, `warning`, `error`.
- `verify_tls`: CLI `--verify-tls` / `--no-verify-tls`, env `SYNC_VERIFY_TLS` (`true`/`false`/`1`/`0`), default `True`, independent of `log_level`.

CLI flags override env vars, which override defaults. Fail fast with a clear `ValueError` (and non-zero CLI exit) on invalid values. Remove all direct environment reads from `src/worker.py`, document every option (name, default, allowed values) in `./repo/README.md` and `cli.py --help`, add tests under `./repo/tests/` covering defaults, overrides, flag separation, and invalid inputs, and verify all tests pass.
