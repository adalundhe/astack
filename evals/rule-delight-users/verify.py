#!/usr/bin/env python3
"""Verifier for rule-delight-users."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit as kit


def _base_ref(ws: Path, repo: Path) -> str:
    sha_file = ws / "program" / "base_sha.txt"
    if not sha_file.is_file():
        return "HEAD"
    base = sha_file.read_text(encoding="utf-8").strip()
    cur = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    if cur.returncode == 0 and cur.stdout.strip() != base:
        return base
    return "HEAD"


def _run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(repo / "src" / "taskcli.py"), *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def _inject_destructive_clean(src: str) -> str:
    marker = 'if __name__ == "__main__":'
    alt_marker = "if __name__ == '__main__':"
    hook = (
        "\n_orig_main_mut = main\n"
        "def main(argv=None):\n"
        "    import sys as _s\n"
        "    from pathlib import Path as _P\n"
        "    _a = list(_s.argv[1:] if argv is None else argv)\n"
        "    _rc = _orig_main_mut(argv)\n"
        "    if 'clean' in _a:\n"
        "        _store = _P('.tasks.json')\n"
        "        for _i, _tok in enumerate(_a):\n"
        "            if _tok == '--store' and _i + 1 < len(_a):\n"
        "                _store = _P(_a[_i + 1])\n"
        "            elif _tok.startswith('--store='):\n"
        "                _store = _P(_tok.split('=', 1)[1])\n"
        "        _store.write_text('[]\\n', encoding='utf-8')\n"
        "    return _rc\n\n"
    )
    if marker in src:
        return src.replace(marker, hook + marker, 1)
    if alt_marker in src:
        return src.replace(alt_marker, hook + alt_marker, 1)
    return src + hook


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    with tempfile.TemporaryDirectory(prefix="astack-delight-") as td:
        store = Path(td) / "tasks.json"

        # 1. Empty state on missing store: no traceback, helpful message with next step
        p_empty = _run_cli(repo, "--store", str(store), "list")
        empty_out = (p_empty.stdout + "\n" + p_empty.stderr).strip()
        empty_ok = (
            p_empty.returncode == 0
            and "Traceback" not in empty_out
            and bool(empty_out)
            and ("no task" in empty_out.lower() or "empty" in empty_out.lower())
            and "add" in empty_out.lower()
        )
        checks.append(("empty_state", empty_ok, f"rc={p_empty.returncode} out={empty_out[:140]!r}"))

        # 2. Visible feedback on add & done
        p_add1 = _run_cli(repo, "--store", str(store), "add", "Ship release")
        p_add2 = _run_cli(repo, "--store", str(store), "add", "Write notes")
        add_ok = p_add1.returncode == 0 and "Ship release" in p_add1.stdout and p_add2.returncode == 0
        checks.append(("add_feedback", add_ok, f"rc={p_add1.returncode} out={p_add1.stdout.strip()!r}"))

        p_done1 = _run_cli(repo, "--store", str(store), "done", "1")
        done_ok = p_done1.returncode == 0 and bool(p_done1.stdout.strip())
        checks.append(("done_feedback", done_ok, f"rc={p_done1.returncode} out={p_done1.stdout.strip()!r}"))

        # 3. Actionable error on unknown task ID (no "Error 42", no traceback, states what failed + next step)
        p_miss = _run_cli(repo, "--store", str(store), "done", "999")
        miss_out = (p_miss.stdout + "\n" + p_miss.stderr).strip()
        miss_ok = (
            p_miss.returncode != 0
            and "Traceback" not in miss_out
            and "Error 42" not in miss_out
            and "999" in miss_out
            and ("list" in miss_out.lower() or "run " in miss_out.lower() or "check" in miss_out.lower())
        )
        checks.append(("actionable_missing_id_error", miss_ok, f"rc={p_miss.returncode} out={miss_out[:140]!r}"))

        # 4. No raw tracebacks on missing title or non-integer task ID
        p_notitle = _run_cli(repo, "--store", str(store), "add")
        p_badid = _run_cli(repo, "--store", str(store), "done", "abc")
        notitle_out = (p_notitle.stdout + "\n" + p_notitle.stderr).strip()
        badid_out = (p_badid.stdout + "\n" + p_badid.stderr).strip()
        bad_input_ok = (
            p_notitle.returncode != 0
            and p_badid.returncode != 0
            and "Traceback" not in notitle_out
            and "Traceback" not in badid_out
            and bool(notitle_out)
            and bool(badid_out)
        )
        checks.append((
            "no_tracebacks_on_bad_input",
            bad_input_ok,
            f"add_rc={p_notitle.returncode} done_rc={p_badid.returncode}",
        ))

        # 5. Safe default on clean: removes completed task 1, keeps open task 2
        p_clean = _run_cli(repo, "--store", str(store), "clean")
        remaining = json.loads(store.read_text(encoding="utf-8")) if store.is_file() else []
        remaining_titles = [t.get("title") for t in remaining]
        clean_ok = (
            p_clean.returncode == 0
            and remaining_titles == ["Write notes"]
            and bool((p_clean.stdout or "").strip())
        )
        checks.append((
            "safe_clean_default",
            clean_ok,
            f"rc={p_clean.returncode} remaining={remaining_titles} out={p_clean.stdout.strip()!r}",
        ))

    ok_ut, msg_ut = kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    ok_mut, msg_mut = kit.check_mutation_caught(repo, "src/taskcli.py", _inject_destructive_clean)
    checks.append(("mutation_caught", ok_mut, msg_mut))

    ok_gates, msg_gates = kit.check_gates_intact(repo, base_ref=_base_ref(ws, repo))
    checks.append(("gates_intact", ok_gates, msg_gates))

    final_text = kit.final_text_from_env()
    sec = kit.check_no_secrets([final_text])
    checks.append(("no_secrets", not sec, "; ".join(sec) if sec else "ok"))
    leaks = kit.check_no_internal_leaks([final_text])
    checks.append(("no_internal_leaks", not leaks, "; ".join(leaks) if leaks else "ok"))

    return kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
