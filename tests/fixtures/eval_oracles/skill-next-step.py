"""Separated offline oracle for `skill-next-step`."""
from __future__ import annotations

from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Write ranked minimal-surface next-step proposals for cli-kit."""
    doc = (
        "# Next-Step Capability Proposals — cli-kit\n\n"
        "Verified existing Tier 0 contract in `program/astack_home/cli-kit/docs/contracts/cli-contract.md` "
        "against `repo/src/cli.py` (`list`, `run <task>`, `--config <path>`, `CLI_KIT_CONFIG`, exit codes `0`/`1`/`2`).\n\n"
        "## 1. Preview Resolved Commands via `run --dry-run`\n"
        "- **Current rung -> Next rung:** Tier 0 single-task execution (`cli-kit run <task>` at `repo/src/cli.py:33`) -> Tier 1 safe pre-flight inspection before CI or release execution.\n"
        "- **Minimal contract delta:** Add one optional boolean flag `--dry-run` to `run` in `build_parser()` (`repo/src/cli.py:45`). Existing `cli-kit run <task>` callers remain completely unchanged (zero regression on Tier 0).\n"
        "- **Consumer impact:** Removes the blind-execution cliff in CI release pipelines (`repo/docs/user_feedback.md:4`) without introducing a new subcommand.\n"
        "- **Evidence & trade-offs:** `repo/src/cli.py:33-38`, `repo/docs/user_feedback.md:4`. Low maintenance cost; relies on resolved config from `load_tasks()` (`repo/src/cli.py:18`).\n\n"
        "## 2. Machine-Readable Discovery via `list --json`\n"
        "- **Current rung -> Next rung:** Tier 0 human tab-delimited output (`cmd_list` at `repo/src/cli.py:26`) -> Tier 1 structured automation input.\n"
        "- **Minimal contract delta:** Add one optional `--json` flag to `list` outputting `{name: {cmd, tag}}`. Default `cli-kit list` output format and exit code `0` stay untouched.\n"
        "- **Consumer impact:** Eliminates fragile `awk`/`cut` shell glue in CI scripts (`repo/docs/user_feedback.md:3`).\n"
        "- **Evidence & trade-offs:** `repo/src/cli.py:26-30`, `repo/docs/user_feedback.md:3`. Keeps JSON schema tied to the existing `DEFAULT_TASKS` dictionary shape (`repo/src/cli.py:11-15`).\n\n"
        "## 3. Grouped Execution via `run --tag <tag>`\n"
        "- **Current rung -> Next rung:** Tier 0 single-task invocation -> Tier 2 grouped task runs reusing existing `tag` metadata.\n"
        "- **Minimal contract delta:** Make `task` optional when `--tag <tag>` is supplied on `run` (mutually exclusive with positional `task`), running matching tasks in sorted order and failing fast on non-zero exit. Zero impact on `cli-kit run <task>`.\n"
        "- **Consumer impact:** Replaces manual `cli-kit run lint && cli-kit run test` chaining (`repo/docs/user_feedback.md:5`) by composing the `tag` field already present in `DEFAULT_TASKS` (`repo/src/cli.py:12-14`) instead of inventing a parallel workflow subsystem.\n"
        "- **Evidence & trade-offs:** `repo/src/cli.py:11-15`, `repo/docs/user_feedback.md:5`. Adds deterministic ordering semantics that must be documented in `cli-contract.md`.\n"
    )
    (ws / "program" / "NEXT_STEPS.md").write_text(doc, encoding="utf-8")
    return {
        "final_text": (
            "Wrote ranked minimal-surface next-step proposals to `program/NEXT_STEPS.md` based on "
            "`program/astack_home/cli-kit/docs/contracts/cli-contract.md`, `repo/src/cli.py`, and `repo/docs/user_feedback.md` (`./repo` untouched):\n"
            "1. `cli-kit run --dry-run` (Tier 0 -> Tier 1 safe CI pre-flight preview; zero change to existing callers).\n"
            "2. `cli-kit list --json` (Tier 0 -> Tier 1 structured output replacing `awk`/`cut` shell glue).\n"
            "3. `cli-kit run --tag <tag>` (Tier 0 -> Tier 2 grouped execution reusing existing `tag` metadata)."
        ),
    }
