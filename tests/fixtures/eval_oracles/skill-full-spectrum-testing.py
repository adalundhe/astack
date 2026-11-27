"""Separated offline oracle for `skill-full-spectrum-testing`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_EXPANDED_TEST_LEDGER = '''import json
import random
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ledger import AccountLedger


class LedgerTest(unittest.TestCase):
    def test_basic_transfer(self):
        ledger = AccountLedger({"alice": 100, "bob": 50})
        ledger.transfer("alice", "bob", 40)
        self.assertEqual(ledger.balance("alice"), 60)
        self.assertEqual(ledger.balance("bob"), 90)
        self.assertEqual(ledger.total_balance(), 150)

    def test_rejects_negative_zero_and_bool_amounts(self):
        ledger = AccountLedger({"alice": 100, "bob": 50})
        for bad in (-10, -1, 0, True, False):
            with self.assertRaises(ValueError, msg=f"expected ValueError for amount={bad!r}"):
                ledger.transfer("alice", "bob", bad)
        self.assertEqual(ledger.snapshot(), {"alice": 100, "bob": 50})

    def test_rejects_insufficient_funds_without_mutating_state(self):
        ledger = AccountLedger({"alice": 25, "bob": 10})
        with self.assertRaises(ValueError):
            ledger.transfer("alice", "bob", 26)
        self.assertEqual(ledger.balance("alice"), 25)
        self.assertEqual(ledger.balance("bob"), 10)
        self.assertEqual(ledger.total_balance(), 35)

    def test_rejects_same_account_unknown_account_and_negative_initial_balance(self):
        with self.assertRaises(ValueError):
            AccountLedger({"alice": -1})
        ledger = AccountLedger({"alice": 50, "bob": 50})
        with self.assertRaises(ValueError):
            ledger.transfer("alice", "alice", 10)
        with self.assertRaises(KeyError):
            ledger.transfer("alice", "missing", 10)
        with self.assertRaises(KeyError):
            ledger.transfer("missing", "alice", 10)

    def test_boundary_exact_drain_and_empty_ledger(self):
        empty = AccountLedger()
        self.assertEqual(empty.total_balance(), 0)
        ledger = AccountLedger({"alice": 1, "bob": 0})
        ledger.transfer("alice", "bob", 1)
        self.assertEqual(ledger.balance("alice"), 0)
        self.assertEqual(ledger.balance("bob"), 1)
        with self.assertRaises(ValueError):
            ledger.transfer("alice", "bob", 1)

    def test_barrier_synchronized_concurrent_transfers_preserve_conservation(self):
        workers = 4
        iters = 12
        ledger = AccountLedger({"alice": 1000, "bob": 1000})
        barrier = threading.Barrier(workers)
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                barrier.wait(timeout=5)
                for _ in range(iters):
                    if idx % 2 == 0:
                        ledger.transfer("alice", "bob", 5)
                    else:
                        ledger.transfer("bob", "alice", 5)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertEqual(ledger.total_balance(), 2000)
        self.assertEqual(ledger.balance("alice"), 1000)
        self.assertEqual(ledger.balance("bob"), 1000)

    def test_seeded_property_fuzzing_preserves_conservation_and_non_negativity(self):
        seed = 20261126
        rng = random.Random(seed)
        accounts = ["a", "b", "c", "d"]
        initial = {acct: rng.randint(50, 500) for acct in accounts}
        ledger = AccountLedger(initial)
        expected_total = sum(initial.values())

        for step in range(150):
            src, dst = rng.sample(accounts, 2)
            amt = rng.randint(-5, 250)
            src_before = ledger.balance(src)
            if amt <= 0 or amt > src_before:
                with self.assertRaises(ValueError, msg=f"seed={seed} step={step} amt={amt}"):
                    ledger.transfer(src, dst, amt)
            else:
                ledger.transfer(src, dst, amt)
            self.assertEqual(
                ledger.total_balance(),
                expected_total,
                f"conservation broken at seed={seed} step={step}",
            )
            for acct in accounts:
                self.assertGreaterEqual(
                    ledger.balance(acct),
                    0,
                    f"negative balance for {acct} at seed={seed} step={step}",
                )

    def test_persistence_roundtrip_and_corrupt_file_rejection(self):
        with tempfile.TemporaryDirectory(prefix="astack-ledger-test-") as td:
            path = Path(td) / "ledger.json"
            ledger = AccountLedger({"alice": 325, "bob": 675, "carol": 0})
            ledger.transfer("alice", "carol", 125)
            ledger.save(path)

            self.assertTrue(path.is_file())
            self.assertFalse(path.with_suffix(".json.tmp").exists())

            reloaded = AccountLedger.load(path)
            self.assertEqual(reloaded.snapshot(), {"alice": 200, "bob": 675, "carol": 125})
            self.assertEqual(reloaded.total_balance(), 1000)

            bad_json = Path(td) / "bad.json"
            bad_json.write_text("{not valid json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                AccountLedger.load(bad_json)

            bad_schema = Path(td) / "bad_schema.json"
            bad_schema.write_text(json.dumps({"balances": ["wrong"]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                AccountLedger.load(bad_schema)
'''


def apply(ws: Path) -> dict[str, object]:
    """Expand repo/tests/test_ledger.py without modifying repo/src/ledger.py."""
    test_file = ws / "repo" / "tests" / "test_ledger.py"
    test_file.write_text(_EXPANDED_TEST_LEDGER, encoding="utf-8")
    subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
        cwd=ws / "repo",
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "final_text": (
            "Expanded `./repo/tests/test_ledger.py` without modifying `./repo/src/ledger.py` to cover "
            "negative inputs, insufficient-funds state preservation, exact-drain and empty boundaries, "
            "barrier-synchronized concurrency conservation, seeded property fuzzing (reporting seed on failure), "
            "and isolated JSON persistence round-trip plus corrupt-file rejection. All tests pass."
        ),
    }
