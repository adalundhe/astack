#!/usr/bin/env python3
"""Executable verifier for `skill-full-spectrum-testing`."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _mut_accept_negative_amount(src: str) -> str:
    target = "amount <= 0"
    if target not in src:
        return src
    return src.replace(target, "amount == 0", 1)


def _mut_skip_insufficient_funds(src: str) -> str:
    target = "if self._balances[src] < amount:"
    if target not in src:
        return src
    return src.replace(target, "if False:", 1)


def _mut_break_concurrency_lock(src: str) -> str:
    old_block = (
        "        with self._lock:\n"
        "            if src not in self._balances or dst not in self._balances:\n"
        '                raise KeyError("unknown account")\n'
        "            if self._balances[src] < amount:\n"
        '                raise ValueError("insufficient funds")\n'
        "            src_bal = self._balances[src]\n"
        "            dst_bal = self._balances[dst]\n"
        "            self._balances[src] = src_bal - amount\n"
        "            self._balances[dst] = dst_bal + amount"
    )
    new_block = (
        "        if True:\n"
        "            if src not in self._balances or dst not in self._balances:\n"
        '                raise KeyError("unknown account")\n'
        "            if self._balances[src] < amount:\n"
        '                raise ValueError("insufficient funds")\n'
        "            src_bal = self._balances[src]\n"
        "            dst_bal = self._balances[dst]\n"
        "            import time as _mut_time\n"
        "            _mut_time.sleep(0.001)\n"
        "            self._balances[src] = src_bal - amount\n"
        "            self._balances[dst] = dst_bal + amount"
    )
    if old_block not in src:
        return src
    return src.replace(old_block, new_block, 1)


def _mut_corrupt_persistence_reload(src: str) -> str:
    target = 'return cls(raw["balances"])'
    if target not in src:
        return src
    replacement = (
        'return cls({k: (v + 1 if isinstance(v, int) and not isinstance(v, bool) else v) '
        'for k, v in raw["balances"].items()})'
    )
    return src.replace(target, replacement, 1)


def _inspect_tests(tests_dir: Path) -> tuple[int, bool, bool]:
    count = 0
    has_barrier = False
    has_seeded_fuzz = False
    for tf in sorted(tests_dir.glob("test_*.py")):
        text = tf.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                count += 1
        if "Barrier" in text and "Thread" in text:
            has_barrier = True
        if ("Random(" in text or "random.seed" in text) and "seed" in text.lower():
            has_seeded_fuzz = True
    return count, has_barrier, has_seeded_fuzz


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, "missing ./repo"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)

    scope_ok, scope_detail = _eval_kit.check_scoped_writes(repo, ["tests/*"], base_ref=base_sha)
    checks.append(("ledger-source-unmodified", scope_ok, scope_detail))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    test_count, has_barrier, has_seeded_fuzz = _inspect_tests(repo / "tests")
    checks.append((
        "spectrum-structure",
        test_count >= 5 and has_barrier and has_seeded_fuzz,
        f"test_methods={test_count} (>=5), barrier_concurrency={has_barrier}, seeded_fuzz={has_seeded_fuzz}",
    ))

    mutations = (
        ("mutation-1-accept-negative-amount", _mut_accept_negative_amount),
        ("mutation-2-skip-insufficient-funds", _mut_skip_insufficient_funds),
        ("mutation-3-break-concurrency-lock", _mut_break_concurrency_lock),
        ("mutation-4-corrupt-persistence-reload", _mut_corrupt_persistence_reload),
    )
    for label, mutator in mutations:
        m_ok, m_detail = _eval_kit.check_mutation_caught(repo, "src/ledger.py", mutator)
        checks.append((label, m_ok, m_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    texts = [final_text]
    for tf in sorted((repo / "tests").glob("test_*.py")):
        texts.append(tf.read_text(encoding="utf-8", errors="replace"))
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
