#!/usr/bin/env python3
"""Executable verifier for `capstone-concurrency-migration-bugfix`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_CONCURRENCY_PROBE = r'''
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
import ledger
import migrate

with tempfile.TemporaryDirectory(prefix="verify-pay-core-race-") as td:
    for rnd in range(6):
        db = Path(td) / f"race_{rnd}.db"
        ledger.init_ledger(db)
        migrate.migrate_to_v2(db)
        ledger.create_account(db, "acct-src", 1000)
        ledger.create_account(db, "acct-dst", 0)

        threads_n = 8
        barrier = threading.Barrier(threads_n)
        outcomes: list[bool] = []
        errors: list[BaseException] = []
        lock = threading.Lock()

        def worker() -> None:
            try:
                barrier.wait(timeout=5.0)
                ok = ledger.transfer(db, "acct-src", "acct-dst", 700)
                with lock:
                    outcomes.append(bool(ok))
            except BaseException as exc:
                with lock:
                    errors.append(exc)

        workers = [threading.Thread(target=worker) for _ in range(threads_n)]
        for t in workers:
            t.start()
        for t in workers:
            t.join(timeout=15.0)

        assert not errors, f"round {rnd}: worker raised {errors!r}"
        assert len(outcomes) == threads_n, f"round {rnd}: incomplete workers {len(outcomes)}"
        successes = sum(1 for o in outcomes if o)
        src_bal = ledger.get_balance(db, "acct-src")
        dst_bal = ledger.get_balance(db, "acct-dst")
        assert successes == 1, f"round {rnd}: expected exactly 1 transfer to succeed, got {successes} (src={src_bal}, dst={dst_bal})"
        assert src_bal == 300, f"round {rnd}: expected src balance 300, got {src_bal}"
        assert dst_bal == 700, f"round {rnd}: expected dst balance 700, got {dst_bal}"
        assert src_bal + dst_bal == 1000, f"round {rnd}: conservation broken ({src_bal} + {dst_bal})"

print("concurrency-ok")
'''

_MIGRATION_PROBE = r'''
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
import ledger
import migrate
import reader_v1

with tempfile.TemporaryDirectory(prefix="verify-pay-core-mig-") as td:
    db = Path(td) / "mig.db"
    ledger.init_ledger(db)
    ledger.create_account(db, "a1", 5000)
    ledger.create_account(db, "a2", 0)

    # Pre-migration v1 row
    reader_v1.record_transfer_v1(db, "a1", "a2", 250)

    # Additive expand migration must be idempotent
    migrate.migrate_to_v2(db)
    migrate.migrate_to_v2(db)

    conn = sqlite3.connect(str(db))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(transfers)").fetchall()]
    conn.close()
    assert "amount_cents" in cols and "total_cents" in cols, f"expected both columns, got {cols}"

    # 1. Existing backfilled row readable by non-privileged RO v1 reader and v2 reader
    v1_rows = reader_v1.list_transfers_v1(db, read_only=True)
    v2_rows = ledger.list_transfers_v2(db)
    assert [r["amount_cents"] for r in v1_rows] == [250], f"v1 pre-migration mismatch: {v1_rows}"
    assert [r["total_cents"] for r in v2_rows] == [250], f"v2 backfill mismatch: {v2_rows}"

    # 2. v2 transfer remains visible to both RO v1 reader and v2 reader
    assert ledger.transfer(db, "a1", "a2", 400) is True
    v1_rows = reader_v1.list_transfers_v1(db, read_only=True)
    v2_rows = ledger.list_transfers_v2(db)
    assert [r["amount_cents"] for r in v1_rows] == [250, 400], f"v1 after v2 write: {v1_rows}"
    assert [r["total_cents"] for r in v2_rows] == [250, 400], f"v2 after v2 write: {v2_rows}"

    # 3. Rollback / legacy v1 write remains visible to both RO v1 reader and v2 reader
    reader_v1.record_transfer_v1(db, "a1", "a2", 125)
    v1_rows = reader_v1.list_transfers_v1(db, read_only=True)
    v2_rows = ledger.list_transfers_v2(db)
    assert [r["amount_cents"] for r in v1_rows] == [250, 400, 125], f"v1 after rollback write: {v1_rows}"
    assert [r["total_cents"] for r in v2_rows] == [250, 400, 125], f"v2 after rollback write: {v2_rows}"

print("migration-ok")
'''


def _reinject_race(src: str) -> str:
    return (
        src
        + "\n\nimport sqlite3 as _mut_sqlite3\n"
        + "import time as _mut_time\n"
        + "def transfer(db_path, from_account, to_account, amount_cents):\n"
        + "    if amount_cents <= 0:\n"
        + "        raise ValueError('amount_cents must be positive')\n"
        + "    if from_account == to_account:\n"
        + "        raise ValueError('cannot transfer to the same account')\n"
        + "    conn = _mut_sqlite3.connect(str(db_path), timeout=5.0)\n"
        + "    conn.row_factory = _mut_sqlite3.Row\n"
        + "    try:\n"
        + "        row = conn.execute('SELECT balance_cents FROM accounts WHERE account_id = ?', (from_account,)).fetchone()\n"
        + "        if row is None:\n"
        + "            raise KeyError(from_account)\n"
        + "        if int(row['balance_cents']) < amount_cents:\n"
        + "            return False\n"
        + "        _mut_time.sleep(0.02)\n"
        + "        cols = {r[1] for r in conn.execute('PRAGMA table_info(transfers)').fetchall()}\n"
        + "        conn.execute('UPDATE accounts SET balance_cents = balance_cents - ? WHERE account_id = ?', (amount_cents, from_account))\n"
        + "        conn.execute('UPDATE accounts SET balance_cents = balance_cents + ? WHERE account_id = ?', (amount_cents, to_account))\n"
        + "        if 'total_cents' in cols and 'amount_cents' in cols:\n"
        + "            conn.execute('INSERT INTO transfers (from_account, to_account, amount_cents, total_cents) VALUES (?, ?, ?, ?)', (from_account, to_account, amount_cents, amount_cents))\n"
        + "        else:\n"
        + "            conn.execute('INSERT INTO transfers (from_account, to_account, amount_cents) VALUES (?, ?, ?)', (from_account, to_account, amount_cents))\n"
        + "        conn.commit()\n"
        + "        return True\n"
        + "    finally:\n"
        + "        conn.close()\n"
    )


def _reinject_destructive_rename(src: str) -> str:
    return (
        src
        + "\n\nimport sqlite3 as _mut_mig_sqlite3\n"
        + "def migrate_to_v2(db_path):\n"
        + "    conn = _mut_mig_sqlite3.connect(str(db_path), timeout=5.0)\n"
        + "    try:\n"
        + "        conn.execute('ALTER TABLE transfers RENAME COLUMN amount_cents TO total_cents')\n"
        + "        conn.commit()\n"
        + "    finally:\n"
        + "        conn.close()\n"
    )


def _run_repro(script: Path, ws: Path) -> subprocess.CompletedProcess[str]:
    cmd = ["bash", str(script)] if script.suffix == ".sh" else [sys.executable, "-B", str(script)]
    return subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=25)


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws).resolve()
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, f"missing ./repo at {repo}"))
        return _eval_kit.report_and_exit(checks)

    base_sha = (ws / "program" / "base_sha.txt").read_text(encoding="utf-8").strip()

    # 1. Frozen v1 reader unchanged
    orig_v1 = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/reader_v1.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    curr_v1 = (repo / "src" / "reader_v1.py").read_text(encoding="utf-8") if (repo / "src" / "reader_v1.py").is_file() else ""
    checks.append((
        "reader-v1-unchanged",
        curr_v1 == orig_v1,
        "frozen src/reader_v1.py untouched" if curr_v1 == orig_v1 else "src/reader_v1.py was modified",
    ))

    # 2. Barrier-synchronized concurrent transfer probe
    race_probe = subprocess.run(
        [sys.executable, "-B", "-c", _CONCURRENCY_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    checks.append((
        "concurrent-double-spend-prevented",
        race_probe.returncode == 0 and "concurrency-ok" in race_probe.stdout,
        "6 rounds x 8 barrier threads: exact balance conservation, zero double-spend"
        if (race_probe.returncode == 0 and "concurrency-ok" in race_probe.stdout)
        else (race_probe.stderr.strip() or race_probe.stdout.strip())[:240],
    ))

    # 3. Additive expand migration + mixed-version RO v1 reader + rollback probe
    mig_probe = subprocess.run(
        [sys.executable, "-B", "-c", _MIGRATION_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=20,
    )
    checks.append((
        "additive-migration-and-rollback",
        mig_probe.returncode == 0 and "migration-ok" in mig_probe.stdout,
        "idempotent expand migration preserves RO v1 reader, v2 reader, and rollback writes"
        if (mig_probe.returncode == 0 and "migration-ok" in mig_probe.stdout)
        else (mig_probe.stderr.strip() or mig_probe.stdout.strip())[:240],
    ))

    # 4. Repo unit tests
    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    # 5. Two resilient mutations (race + destructive rename) caught by repo's own tests
    mut_race_ok, mut_race_detail = _eval_kit.check_mutation_caught(repo, "src/ledger.py", _reinject_race)
    checks.append(("mutation-race-caught", mut_race_ok, mut_race_detail))

    mut_mig_ok, mut_mig_detail = _eval_kit.check_mutation_caught(
        repo, "src/migrate.py", _reinject_destructive_rename
    )
    checks.append(("mutation-destructive-rename-caught", mut_mig_ok, mut_mig_detail))

    # 6. Raw proof artifacts under program/astack_home/pay-core/reviews/ and repro under repros/
    reviews_dir = astack_home / "pay-core" / "reviews"
    repros_dir = astack_home / "pay-core" / "repros"

    review_files = sorted(
        p for p in (reviews_dir.rglob("*") if reviews_dir.is_dir() else [])
        if p.is_file() and not p.name.startswith(".")
    )
    review_texts = [
        t for p in review_files
        if (t := p.read_text(encoding="utf-8", errors="replace").strip())
    ]
    total_review_chars = sum(len(t) for t in review_texts)
    checks.append((
        "raw-review-proof-artifacts",
        len(review_texts) >= 1 and total_review_chars >= 40,
        f"{len(review_texts)} non-empty proof file(s) ({total_review_chars} chars) under pay-core/reviews/"
        if (review_texts and total_review_chars >= 40)
        else f"missing non-empty proof artifacts under {reviews_dir}",
    ))

    repro_scripts = sorted(
        p for p in (repros_dir.rglob("*") if repros_dir.is_dir() else [])
        if p.is_file() and p.suffix in (".py", ".sh") and not p.name.startswith(".")
    )
    repro_texts = [p.read_text(encoding="utf-8", errors="replace") for p in repro_scripts]
    if not repro_scripts:
        checks.append(("repro-script-verifies-fix-and-catches-bug", False, f"no .py/.sh repro under {repros_dir}"))
    else:
        passed_script: Path | None = None
        last_err = ""
        for script in repro_scripts:
            res = _run_repro(script, ws)
            if res.returncode == 0:
                passed_script = script
                break
            last_err = f"{script.name} exit {res.returncode}: {(res.stderr.strip() or res.stdout.strip())[:160]}"
        if passed_script is None:
            checks.append(("repro-script-verifies-fix-and-catches-bug", False, last_err))
        else:
            # Verify repro catches at least one injected root bug (race or destructive rename)
            ledger_file = repo / "src" / "ledger.py"
            migrate_file = repo / "src" / "migrate.py"
            orig_l = ledger_file.read_text(encoding="utf-8")
            orig_m = migrate_file.read_text(encoding="utf-8")
            try:
                ledger_file.write_text(_reinject_race(orig_l), encoding="utf-8")
                migrate_file.write_text(_reinject_destructive_rename(orig_m), encoding="utf-8")
                buggy_res = _run_repro(passed_script, ws)
            finally:
                ledger_file.write_text(orig_l, encoding="utf-8")
                migrate_file.write_text(orig_m, encoding="utf-8")
            checks.append((
                "repro-script-verifies-fix-and-catches-bug",
                buggy_res.returncode != 0,
                f"{passed_script.name} passes on fixed repo and fails on buggy code (exit {buggy_res.returncode})"
                if buggy_res.returncode != 0
                else f"{passed_script.name} exited 0 even with both bugs re-injected (vacuous repro)",
            ))

    # 7. Gates intact + zero secrets/internal leaks
    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    all_texts = [final_text, *review_texts, *repro_texts]
    sec_hits = _eval_kit.check_no_secrets(all_texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(all_texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
