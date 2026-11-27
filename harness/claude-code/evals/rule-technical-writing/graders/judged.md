---
type: llm
---

Evaluate the CLI change and documentation audit against `technical-writing`.

PASS if all of these hold:
- Renamed `--format` to `--output` in `./repo/src/export_cli.py`, added `jsonl` support as the new default, and updated `./repo/tests/test_export_cli.py`.
- Discovered and updated BOTH `./repo/README.md` and `./repo/docs/cli.md` in the same change.
- Zero stale `--format` references or vague marketing adjectives (`blazing fast`, `seamless`, `robust`) remain in the docs.
- Documented commands, flags, defaults, and examples match the actual CLI implementation.

FAIL otherwise.
