"""Behaviour tests for objective reproduction verification (`evals/_repro_verify.py` + `evals/*/verify.py`)
and empirical model calibration (`scripts/eval.py --calibrate` -> `bin/astack-review-ledger --calibration`)."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
BIN = ROOT / "bin"
SCRIPTS = ROOT / "scripts"


def _scaffold_eval(case_name: str, ws: Path) -> None:
    proc = subprocess.run(["bash", str(EVALS / case_name / "setup.sh")], cwd=ws, capture_output=True, text=True)
    assert proc.returncode == 0, f"setup.sh failed for {case_name}: {proc.stderr}"


def _run_verify(case_name: str, ws: Path) -> tuple[int, str, str, dict]:
    proc = subprocess.run(
        [sys.executable, "-B", str(EVALS / case_name / "verify.py"), str(ws)],
        cwd=ws,
        capture_output=True,
        text=True,
    )
    payload = {}
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith("PROVEN_BUGS_JSON:"):
            payload = json.loads(line.split(":", 1)[1].strip())
            break
    return proc.returncode, proc.stdout, proc.stderr, payload


class EvalReproductionVerifiersTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="astack-repro-verify-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_planted_bugs_verifier_proves_each_bug_rejects_fakes_and_keeps_fixed_tests_green(self):
        ws = self.dir / "planted"
        ws.mkdir()
        _scaffold_eval("vectored-review-planted-bugs", ws)

        # 1) Zero saved reproductions -> MUST FAIL
        code0, _, _, data0 = _run_verify("vectored-review-planted-bugs", ws)
        self.assertEqual(code0, 1)
        self.assertEqual(data0["detected_count"], 0)
        self.assertEqual(data0["planted_count"], 5)

        # 2) Always-pass stub, always-fail stub, and decoy attack -> MUST FAIL
        repros = ws / "program" / "repros"
        (repros / "always_pass.py").write_text("assert True\n")
        (repros / "always_fail.py").write_text("import sys; sys.exit(1)\n")
        (repros / "decoy_attack.py").write_text(
            "import tempfile\n"
            "from pathlib import Path\n"
            "from src.journal import OrderJournal\n"
            "from src.models import Order\n"
            "with tempfile.TemporaryDirectory() as td:\n"
            "    j = OrderJournal(Path(td) / 'j.wal')\n"
            "    j.rotate_snapshot({'o1': Order('o1', 'k1', 100, 'paid')})\n"
            "    raise AssertionError('false positive against atomic os.replace')\n"
        )
        code_fake, _, _, data_fake = _run_verify("vectored-review-planted-bugs", ws)
        self.assertEqual(code_fake, 1)
        self.assertEqual(data_fake["detected_count"], 0)
        self.assertEqual(len(data_fake["failed_on_fixed"]), 2)
        self.assertEqual(data_fake["passed_on_buggy"], ["program/repros/always_pass.py"])

        # Remove bogus scripts and add genuine reproductions covering ALL 5 bugs across 3 script styles:
        # standalone script (with hardcoded absolute ws/repo path!), unittest.TestCase without unittest.main(),
        # and bare pytest-style def test_*()!
        for f in repros.iterdir():
            f.unlink()

        (repros / "repro_coupon.py").write_text(
            f"import sys\nsys.path.insert(0, {str(ws / 'repo')!r})\n"
            "from src.pricing import apply_coupon\n"
            "try:\n"
            "    res = apply_coupon(1000, 150)\n"
            "except ValueError:\n"
            "    raise SystemExit(0)\n"
            "raise AssertionError(f'expected ValueError, got {res}')\n"
        )
        (repros / "test_inventory_bugs.py").write_text(
            "import threading, time, unittest\n"
            "from src.inventory import Inventory\n"
            "class YieldingLock:\n"
            "    def __init__(self):\n"
            "        self._inner = threading.Lock()\n"
            "    def __enter__(self):\n"
            "        self._inner.acquire()\n"
            "        return self\n"
            "    def __exit__(self, *args):\n"
            "        self._inner.release()\n"
            "        time.sleep(0.005)\n"
            "class TestInventory(unittest.TestCase):\n"
            "    def test_duplicate_sku_in_batch(self):\n"
            "        inv = Inventory({'a': 3})\n"
            "        with self.assertRaises(ValueError):\n"
            "            inv.reserve_batch([('a', 2), ('a', 2)])\n"
            "    def test_split_lock_race(self):\n"
            "        inv = Inventory({'a': 1})\n"
            "        inv._lock = YieldingLock()\n"
            "        bar = threading.Barrier(2)\n"
            "        ok = [0]\n"
            "        def worker():\n"
            "            bar.wait()\n"
            "            try:\n"
            "                inv.reserve_batch([('a', 1)])\n"
            "                ok[0] += 1\n"
            "            except ValueError:\n"
            "                pass\n"
            "        ts = [threading.Thread(target=worker) for _ in range(2)]\n"
            "        for t in ts: t.start()\n"
            "        for t in ts: t.join()\n"
            "        self.assertGreaterEqual(inv.available('a'), 0)\n"
            "        self.assertEqual(ok[0], 1)\n"
        )
        (repros / "test_seam_and_cache.py").write_text(
            "from pathlib import Path\n"
            "from src.inventory import Inventory\n"
            "from src.models import LineItem\n"
            "from src.service import OrderService\n"
            "def test_wal_seam(tmp_path):\n"
            "    wal = Path(tmp_path) / 'orders.wal'\n"
            "    svc = OrderService(Inventory({'a': 5}), wal)\n"
            "    o = svc.checkout('tenant', 'key', [LineItem('a', 1, 500)])\n"
            "    replayed = OrderService(Inventory({'a': 5}), wal)\n"
            "    assert replayed.status_of(o.order_id) == 'paid'\n"
            "    assert replayed.total_revenue() == 500\n"
            "def test_refund_cache_poisoning(tmp_path):\n"
            "    wal = Path(tmp_path) / 'orders.wal'\n"
            "    svc = OrderService(Inventory({'a': 5}), wal)\n"
            "    o = svc.checkout('t', 'k', [LineItem('a', 1, 500)])\n"
            "    try:\n"
            "        svc.refund_order('ord-missing')\n"
            "    except ValueError:\n"
            "        pass\n"
            "    assert svc.status_of('ord-missing') is None\n"
            "    assert svc.total_revenue() == 500\n"
        )

        code_ok, out_ok, err_ok, data_ok = _run_verify("vectored-review-planted-bugs", ws)
        self.assertEqual(code_ok, 0, out_ok + err_ok)
        self.assertEqual(data_ok["detected_count"], 5)
        self.assertEqual(
            set(data_ok["detected"]),
            {
                "bug1_coupon_gt_100",
                "bug2_duplicate_sku_batch",
                "bug3_split_lock_race",
                "bug4_wal_pipe_delimiter_seam",
                "bug5_refund_cache_poisoning",
            },
        )
        # Verify repo/ itself was never mutated
        st = subprocess.run(["git", "-C", str(ws / "repo"), "status", "--porcelain"], capture_output=True, text=True)
        self.assertEqual(st.stdout.strip(), "")

        # Verify shipped unit tests pass on the all_fixed repo variant too!
        spec = importlib.util.spec_from_file_location("planted_verify", EVALS / "vectored-review-planted-bugs" / "verify.py")
        pmod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(pmod)
        fixed_copy = self.dir / "fixed-planted-repo"
        shutil.copytree(ws / "repo", fixed_copy)
        for bug in pmod.PLANTED_BUGS:
            bug.apply_fix(fixed_copy)
        ut = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
            cwd=fixed_copy,
            capture_output=True,
            text=True,
        )
        self.assertEqual(ut.returncode, 0, ut.stdout + ut.stderr)

        # Verify the built harness/claude-code copy of verify.py also runs standalone!
        built_verify = ROOT / "harness" / "claude-code" / "evals" / "vectored-review-planted-bugs" / "verify.py"
        built_proc = subprocess.run([sys.executable, "-B", str(built_verify), str(ws)], cwd=ws, capture_output=True, text=True)
        self.assertEqual(built_proc.returncode, 0, built_proc.stdout + built_proc.stderr)

        # Modifying repo/ MUST cause verify.py to fail even with all 5 valid repros
        (ws / "repo" / "src" / "pricing.py").write_text("# tampered\n")
        code_dirty, _, _, _ = _run_verify("vectored-review-planted-bugs", ws)
        self.assertEqual(code_dirty, 1)

    def test_concurrency_cross_harness_context_and_small_change_verifiers(self):
        # 1) vectored-review-concurrency
        ws_c = self.dir / "conc"
        ws_c.mkdir()
        _scaffold_eval("vectored-review-concurrency", ws_c)
        self.assertEqual(_run_verify("vectored-review-concurrency", ws_c)[0], 1)
        (ws_c / "program" / "repros" / "repro_race.py").write_text(
            "import threading, time\n"
            "from pool import JobPool\n"
            "class YieldingLock:\n"
            "    def __init__(self):\n"
            "        self._inner = threading.Lock()\n"
            "    def __enter__(self):\n"
            "        self._inner.acquire()\n"
            "        return self\n"
            "    def __exit__(self, *args):\n"
            "        self._inner.release()\n"
            "        time.sleep(0.005)\n"
            "p = JobPool()\n"
            "for i in range(6): p.push(i)\n"
            "p._lock = YieldingLock()\n"
            "bar = threading.Barrier(2)\n"
            "out = []\n"
            "lock = threading.Lock()\n"
            "def run():\n"
            "    bar.wait()\n"
            "    b = p.drain_batch(3)\n"
            "    with lock:\n"
            "        out.extend(b)\n"
            "ts = [threading.Thread(target=run) for _ in range(2)]\n"
            "for t in ts: t.start()\n"
            "for t in ts: t.join()\n"
            "assert len(out) == len(set(out)) == 6, f'duplicate/lost items: {out}'\n"
        )
        code_c, _, err_c, data_c = _run_verify("vectored-review-concurrency", ws_c)
        self.assertEqual(code_c, 0, err_c)
        self.assertEqual(data_c["detected"], ["bug1_split_lock_drain_batch"])

        # 2) vectored-review-cross-harness (Bug 3: MUST require valid cross-harness reviewer receipt, not just Claude repros!)
        ws_x = self.dir / "cross"
        ws_x.mkdir()
        _scaffold_eval("vectored-review-cross-harness", ws_x)
        self.assertEqual(_run_verify("vectored-review-cross-harness", ws_x)[0], 1)
        (ws_x / "program" / "repros" / "repro_auth.py").write_text(
            "import hmac\n"
            "import auth\n"
            "tok = auth.sign_token(b's', 'alice', 100, refreshed=True)\n"
            "assert auth.verify_token(b's', tok, now=200) is None, 'expired refreshed token accepted'\n"
            "called = [False]\n"
            "orig = hmac.compare_digest\n"
            "def spy(a, b):\n"
            "    called[0] = True\n"
            "    return orig(a, b)\n"
            "hmac.compare_digest = spy\n"
            "try:\n"
            "    valid = auth.sign_token(b's', 'alice', 300, refreshed=False)\n"
            "    assert auth.verify_token(b's', valid, now=200) == 'alice'\n"
            "    assert called[0], 'hmac.compare_digest was not used'\n"
            "finally:\n"
            "    hmac.compare_digest = orig\n"
        )
        # Repros alone WITHOUT a cross-harness receipt MUST FAIL!
        code_x_no_rcpt, _, err_x_no_rcpt, data_x_no_rcpt = _run_verify("vectored-review-cross-harness", ws_x)
        self.assertEqual(code_x_no_rcpt, 1)
        self.assertFalse(data_x_no_rcpt["cross_harness_verified"])
        self.assertIn("no successful cross-harness reviewer dispatch receipt", err_x_no_rcpt)

        # Same-host (claude) receipt or failed (exit_code=1) receipt MUST STILL FAIL!
        rcpt_dir = ws_x / "program" / "dispatch-receipts"
        rcpt_dir.mkdir(parents=True, exist_ok=True)
        settings_x = json.loads((ws_x / "program" / "settings.json").read_text())
        codex_entry = next(e for e in settings_x["reviewer_pool"] if e.get("harness") == "codex")
        (rcpt_dir / "same-host.receipt.json").write_text(json.dumps({
            "role": "reviewer", "harness": "claude", "provider": "anthropic", "model": "sonnet",
            "exit_code": 0, "timed_out": False, "stdout_len": 120,
        }))
        (rcpt_dir / "failed-codex.receipt.json").write_text(json.dumps({
            "role": "reviewer", "harness": "codex", "provider": codex_entry["provider"], "model": codex_entry["model"],
            "exit_code": 1, "timed_out": False, "stdout_len": 0,
        }))
        self.assertEqual(_run_verify("vectored-review-cross-harness", ws_x)[0], 1)

        # Valid cross-harness receipt (harness=codex, exit_code=0, stdout_len>0) -> PASSES!
        (rcpt_dir / "ok-codex.receipt.json").write_text(json.dumps({
            "role": "reviewer", "harness": "codex", "provider": codex_entry["provider"], "model": codex_entry["model"],
            "exit_code": 0, "timed_out": False, "stdout_len": 350,
        }))
        code_x, _, err_x, data_x = _run_verify("vectored-review-cross-harness", ws_x)
        self.assertEqual(code_x, 0, err_x)
        self.assertTrue(data_x["cross_harness_verified"])
        self.assertEqual(len(data_x["cross_harness_receipts"]), 1)
        self.assertEqual(set(data_x["detected"]), {"bug1_expired_refresh", "bug2_timing_compare"})

        # 3) review-checks-context-and-rules
        ws_r = self.dir / "ctx"
        ws_r.mkdir()
        _scaffold_eval("review-checks-context-and-rules", ws_r)
        self.assertEqual(_run_verify("review-checks-context-and-rules", ws_r)[0], 1)
        (ws_r / "program" / "repros" / "repro_webhooks.py").write_text(
            "from webhooks import WebhookBatchClient, WebhookDeliveryError\n"
            "c = WebhookBatchClient(lambda chunk, timeout: (502, {}))\n"
            "c.connect()\n"
            "try:\n"
            "    res = c.deliver_batch([{'id': '1'}])\n"
            "except WebhookDeliveryError:\n"
            "    pass\n"
            "else:\n"
            "    raise AssertionError(f'expected WebhookDeliveryError, got {res!r}')\n"
            "c2 = WebhookBatchClient(lambda chunk, timeout: (200, {}))\n"
            "try:\n"
            "    res2 = c2.deliver_batch([{'id': '1'}])\n"
            "except Exception:\n"
            "    pass\n"
            "else:\n"
            "    raise AssertionError(f'expected explicit error before connect(), got {res2!r}')\n"
        )
        code_r, _, err_r, data_r = _run_verify("review-checks-context-and-rules", ws_r)
        self.assertEqual(code_r, 0, err_r)
        self.assertEqual(set(data_r["detected"]), {"bug1_swallowed_delivery_error", "bug2_unconnected_silent_zero"})

        # 4) vectored-review-small-change (0 planted bugs: passes clean, fails on bogus failing repro)
        ws_s = self.dir / "small"
        ws_s.mkdir()
        _scaffold_eval("vectored-review-small-change", ws_s)
        self.assertEqual(_run_verify("vectored-review-small-change", ws_s)[0], 0)
        (ws_s / "program" / "bogus_repro.py").write_text(
            "from fmt import normalize_spaces\n"
            "assert normalize_spaces('a\\tb') == 'a b', 'false positive on preserved tab'\n"
        )
        self.assertEqual(_run_verify("vectored-review-small-change", ws_s)[0], 1)

    def test_eval_calibrate_measures_real_catch_rate_and_feeds_review_ledger(self):
        # Create a stub `claude` CLI that writes 3 genuine reproductions (coupon, duplicate-sku, wal-seam)
        # into program/repros/, then run `scripts/eval.py --calibrate` and feed calibration.json to astack-review-ledger!
        stub_bin = self.dir / "stub_bin"
        stub_bin.mkdir()
        stub_claude = stub_bin / "claude"
        stub_claude.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "repros = Path.cwd() / 'program' / 'repros'\n"
            "repros.mkdir(parents=True, exist_ok=True)\n"
            "(repros / 'r1.py').write_text(\n"
            "    'from src.pricing import apply_coupon\\n'\n"
            "    'try:\\n'\n"
            "    '    apply_coupon(100, 120)\\n'\n"
            "    'except ValueError:\\n'\n"
            "    '    raise SystemExit(0)\\n'\n"
            "    'raise SystemExit(1)\\n'\n"
            ")\n"
            "(repros / 'r2.py').write_text(\n"
            "    'from src.inventory import Inventory\\n'\n"
            "    'inv = Inventory({\"x\": 2})\\n'\n"
            "    'try:\\n'\n"
            "    '    inv.reserve_batch([(\"x\", 2), (\"x\", 2)])\\n'\n"
            "    'except ValueError:\\n'\n"
            "    '    raise SystemExit(0)\\n'\n"
            "    'raise SystemExit(1)\\n'\n"
            ")\n"
            "(repros / 'r3.py').write_text(\n"
            "    'import tempfile\\nfrom pathlib import Path\\n'\n"
            "    'from src.inventory import Inventory\\nfrom src.models import LineItem\\n'\n"
            "    'from src.service import OrderService\\n'\n"
            "    'with tempfile.TemporaryDirectory() as td:\\n'\n"
            "    '    w = Path(td) / \"o.wal\"\\n'\n"
            "    '    s = OrderService(Inventory({\"a\": 5}), w)\\n'\n"
            "    '    s.checkout(\"t\", \"k\", [LineItem(\"a\", 1, 100)])\\n'\n"
            "    '    s2 = OrderService(Inventory({\"a\": 5}), w)\\n'\n"
            "    '    assert s2.total_revenue() == 100\\n'\n"
            ")\n"
        )
        stub_claude.chmod(0o755)
        cal_out = self.dir / "calibration.json"

        env = {**os.environ, "PATH": f"{stub_bin}{os.pathsep}{os.environ.get('PATH', '')}"}
        proc = subprocess.run(
            [
                sys.executable, "-B", str(SCRIPTS / "eval.py"),
                "--harness", "claude",
                "--model", "sonnet",
                "--calibrate",
                "--calibration-out", str(cal_out),
                "--json",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        cal_result = json.loads(proc.stdout)
        self.assertEqual(cal_result["model_key"], "anthropic/sonnet")
        self.assertEqual(cal_result["entry"]["detected"], 3)
        self.assertEqual(cal_result["entry"]["planted"], 5)
        self.assertAlmostEqual(cal_result["entry"]["observed_rate"], 0.6)
        self.assertEqual(
            cal_result["entry"]["per_bug"],
            {
                "bug1_coupon_gt_100": {"detected": 1, "trials": 1},
                "bug2_duplicate_sku_batch": {"detected": 1, "trials": 1},
                "bug3_split_lock_race": {"detected": 0, "trials": 1},
                "bug4_wal_pipe_delimiter_seam": {"detected": 1, "trials": 1},
                "bug5_refund_cache_poisoning": {"detected": 0, "trials": 1},
            },
        )
        self.assertTrue(cal_out.is_file())

        # Add a complementary second model that caught bug3 & bug5 (the 2 bugs sonnet missed!)
        saved = json.loads(cal_out.read_text())
        self.assertEqual(saved["schema_version"], "1.1")
        saved["models"]["openai/gpt-5.4"] = {
            "detected": 2,
            "planted": 5,
            "source": "vectored-review-planted-bugs",
            "per_bug": {
                "bug1_coupon_gt_100": {"detected": 0, "trials": 1},
                "bug2_duplicate_sku_batch": {"detected": 0, "trials": 1},
                "bug3_split_lock_race": {"detected": 1, "trials": 1},
                "bug4_wal_pipe_delimiter_seam": {"detected": 0, "trials": 1},
                "bug5_refund_cache_poisoning": {"detected": 1, "trials": 1},
            },
        }
        cal_out.write_text(json.dumps(saved))

        ledger_in = json.dumps({
            "reviewer_pool": [
                {"provider": "anthropic", "model": "sonnet", "harness": "claude"},
                {"provider": "openai", "model": "gpt-5.4", "harness": "codex"},
            ],
            "vectors": [{"name": "auth", "risk": 0.632121}],
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "sonnet", "verified": []},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "verified": []},
            ],
        })
        l_proc = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-review-ledger"), "-", "--calibration", str(cal_out), "--json"],
            input=ledger_in,
            capture_output=True,
            text=True,
        )
        self.assertEqual(l_proc.returncode, 0, l_proc.stderr)
        l_data = json.loads(l_proc.stdout)
        # Together sonnet ({1,2,4}) + gpt-5.4 ({3,5}) caught all 5/5 planted bugs with 0 shared blind spots.
        # Zero 59-bug cliff and zero default 0.05 target: reports exact Beta posterior miss distribution
        # (0.5/6 = 8.3% ± 10.4%) and finite-sample blind-spot bound (`clean_stop`, no binary "calibrated" label).
        vec = l_data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["verdict"], "clean_stop")
        self.assertTrue(vec["estimate"]["can_stop"])
        self.assertTrue(vec["estimate"]["joint_calibration"])
        self.assertEqual(vec["estimate"]["jointly_missed_bugs"], [])
        self.assertEqual(vec["estimate"]["empirical_joint_miss_rate"], 0.0)
        self.assertAlmostEqual(vec["estimate"]["jeffreys_joint_miss_prob"], 0.5 / 6.0, places=4)
        self.assertIn("moment_bounds", vec["estimate"])
        self.assertEqual(l_data["risk_allocation"]["decision_mode"], "budget_minimization")
        self.assertFalse(vec["landing_blocked"])

        # With an explicit `miss_risk_target = 0.05`: 0.0833 >= 0.05 -> refuses to certify!
        strict_in = json.dumps({**json.loads(ledger_in), "miss_risk_target": 0.05})
        l_strict = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-review-ledger"), "-", "--calibration", str(cal_out), "--json"],
            input=strict_in,
            capture_output=True,
            text=True,
        )
        self.assertEqual(l_strict.returncode, 0, l_strict.stderr)
        ls_data = json.loads(l_strict.stdout)
        self.assertFalse(ls_data["vectors"][0]["estimate"]["can_stop"])
        self.assertTrue(ls_data["vectors"][0]["landing_blocked"])

    def test_v09_eval_verifiers_redteam_squish_lookback_and_sprint(self):
        # 1) redteam-breaks-and-hardens: buggy fails -> fixed with red-first test passes -> leftover debug file fails
        ws_rt = self.dir / "redteam"
        ws_rt.mkdir()
        _scaffold_eval("redteam-breaks-and-hardens", ws_rt)
        self.assertEqual(_run_verify("redteam-breaks-and-hardens", ws_rt)[0], 1)

        (ws_rt / "repo" / "src" / "vault.py").write_text(
            "from __future__ import annotations\n"
            "import hashlib, hmac, threading\n"
            "from pathlib import Path\n\n"
            "class TenantVault:\n"
            "    def __init__(self, root: Path, secret: bytes, max_writes: int = 2) -> None:\n"
            "        self.root = root.resolve()\n"
            "        self.root.mkdir(parents=True, exist_ok=True)\n"
            "        self._secret = secret\n"
            "        self._max_writes = max_writes\n"
            "        self._counts: dict[str, int] = {}\n"
            "        self._lock = threading.Lock()\n\n"
            "    def make_token(self, tenant: str) -> str:\n"
            "        sig = hmac.new(self._secret, tenant.encode('utf-8'), hashlib.sha256).hexdigest()\n"
            "        return f'{tenant}:{sig}'\n\n"
            "    def authenticate(self, token: str) -> str:\n"
            "        if ':' not in token:\n"
            "            raise PermissionError('malformed token')\n"
            "        tenant, sig = token.split(':', 1)\n"
            "        expected = hmac.new(self._secret, tenant.encode('utf-8'), hashlib.sha256).hexdigest()\n"
            "        if not tenant or not hmac.compare_digest(sig, expected):\n"
            "            raise PermissionError('invalid token')\n"
            "        return tenant\n\n"
            "    def write_blob(self, token: str, name: str, data: bytes) -> Path:\n"
            "        tenant = self.authenticate(token)\n"
            "        tenant_root = (self.root / tenant).resolve()\n"
            "        target = (tenant_root / name).resolve()\n"
            "        if not target.is_relative_to(tenant_root):\n"
            "            raise ValueError('path escapes tenant directory')\n"
            "        with self._lock:\n"
            "            if self._counts.get(tenant, 0) >= self._max_writes:\n"
            "                raise RuntimeError('quota exceeded')\n"
            "            self._counts[tenant] = self._counts.get(tenant, 0) + 1\n"
            "        target.parent.mkdir(parents=True, exist_ok=True)\n"
            "        target.write_bytes(data)\n"
            "        return target\n"
        )
        # Fixed code without new regression tests must STILL fail red-first check
        self.assertEqual(_run_verify("redteam-breaks-and-hardens", ws_rt)[0], 1)
        (ws_rt / "repo" / "tests" / "test_redteam_regressions.py").write_text(
            "import shutil, sys, tempfile, unittest\nfrom pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))\n"
            "from vault import TenantVault\n\n"
            "class RedteamRegressions(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        self.d = Path(tempfile.mkdtemp())\n"
            "        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)\n"
            "    def test_malformed_token_and_traversal_rejected(self):\n"
            "        v = TenantVault(self.d, b's', max_writes=2)\n"
            "        with self.assertRaises(PermissionError):\n"
            "            v.authenticate('bad')\n"
            "        tok = v.make_token('acme')\n"
            "        with self.assertRaises(ValueError):\n"
            "            v.write_blob(tok, '../escape.txt', b'x')\n"
        )
        code_rt, out_rt, err_rt, _ = _run_verify("redteam-breaks-and-hardens", ws_rt)
        self.assertEqual(code_rt, 0, out_rt + err_rt)

        # Leftover *_DEBUG_* artifact fails verify
        (ws_rt / "repo" / "vault_DEBUG_abc123.log").write_text("debug\n")
        self.assertEqual(_run_verify("redteam-breaks-and-hardens", ws_rt)[0], 1)

        # 2) squish-consolidates-noisy-branch: 6 commits fails -> squished preserving tree + Bob's credit passes
        ws_sq = self.dir / "squish"
        ws_sq.mkdir()
        _scaffold_eval("squish-consolidates-noisy-branch", ws_sq)
        self.assertEqual(_run_verify("squish-consolidates-noisy-branch", ws_sq)[0], 1)

        base_sha = (ws_sq / "program" / "base_sha.txt").read_text().strip()
        subprocess.run(["git", "-C", str(ws_sq / "repo"), "reset", "--soft", base_sha], check=True)
        subprocess.run(
            ["git", "-C", str(ws_sq / "repo"), "commit", "-q", "-m", "feat: add cap and jitter to backoff\n\nCo-authored-by: Bob <bob@example.invalid>"],
            check=True,
        )
        code_sq, out_sq, err_sq, _ = _run_verify("squish-consolidates-noisy-branch", ws_sq)
        self.assertEqual(code_sq, 0, out_sq + err_sq)

        # 3) lookback-and-lookup-lessons: unedited fails -> valid LESSON.md + retired stale passes -> in-repo lesson fails
        ws_lb = self.dir / "lookback"
        ws_lb.mkdir()
        _scaffold_eval("lookback-and-lookup-lessons", ws_lb)
        self.assertEqual(_run_verify("lookback-and-lookup-lessons", ws_lb)[0], 1)

        stale = ws_lb / "program" / "astack_home" / "billing" / "lessons" / "legacy-xml-parser" / "LESSON.md"
        stale.write_text(stale.read_text().replace("status: active", "status: superseded"))
        new_lesson = ws_lb / "program" / "astack_home" / "billing" / "lessons" / "webhook-raw-body-hmac" / "LESSON.md"
        new_lesson.parent.mkdir(parents=True, exist_ok=True)
        new_lesson.write_text(
            "---\nlesson: webhook-raw-body-hmac\nproject: billing\nrelated_projects: [payments-gateway]\n"
            "keywords: [webhook, hmac, json]\nstatus: active\ncreated: 2026-11-25T14:00Z\nupdated: 2026-11-25T14:00Z\n---\n\n"
            "# Verify webhook HMAC on raw bytes\n\n"
            "## Overview\nHash raw UTF-8 body before JSON parsing.\n\n"
            "## Skills and tools used\n- `bugbash`\n\n"
            "## Details\nKey order changes broke parsed-JSON verification.\n\n"
            "## Successes\n- Regression test with reordered keys.\n\n"
            "## Issues\n- Rejected TLS expiry theory via `openssl s_client`.\n\n"
            "## Best path & guards\n- Guard in middleware.\n\n"
            "## References\n- `repo/src/webhook.py`\n"
        )
        code_lb, out_lb, err_lb, _ = _run_verify("lookback-and-lookup-lessons", ws_lb)
        self.assertEqual(code_lb, 0, out_lb + err_lb)
        (ws_lb / "repo" / "LESSONS.md").write_text("bad\n")
        self.assertEqual(_run_verify("lookback-and-lookup-lessons", ws_lb)[0], 1)

        # 4) sprint-ingests-fenced-ticket: unfixed fails -> branch fix + red-first test + merge_ready state passes
        ws_sp = self.dir / "sprint"
        ws_sp.mkdir()
        _scaffold_eval("sprint-ingests-fenced-ticket", ws_sp)
        self.assertEqual(_run_verify("sprint-ingests-fenced-ticket", ws_sp)[0], 1)

        subprocess.run(["git", "-C", str(ws_sp / "repo"), "checkout", "-q", "-b", "fix/paginate-1-based"], check=True)
        (ws_sp / "repo" / "src" / "paginate.py").write_text(
            "def paginate(items: list, page: int, page_size: int) -> list:\n"
            "    if page < 1 or page_size < 1:\n"
            "        raise ValueError('page and page_size must be >= 1')\n"
            "    start = (page - 1) * page_size\n"
            "    return items[start : start + page_size]\n"
        )
        (ws_sp / "repo" / "tests" / "test_paginate.py").write_text(
            "import sys, unittest\nfrom pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))\n"
            "from paginate import paginate\n\n"
            "class PaginateTest(unittest.TestCase):\n"
            "    def test_one_based_and_validation(self):\n"
            "        self.assertEqual(paginate([1, 2, 3, 4], 1, 2), [1, 2])\n"
            "        self.assertEqual(paginate([1, 2, 3, 4], 2, 2), [3, 4])\n"
            "        with self.assertRaises(ValueError):\n"
            "            paginate([1, 2], 0, 2)\n"
        )
        st_path = ws_sp / "program" / "ticket-state" / "state.json"
        st_data = json.loads(st_path.read_text())
        st_data["tickets"]["github:acme/app#7"]["state"] = "merge_ready"
        st_path.write_text(json.dumps(st_data, indent=2))
        code_sp, out_sp, err_sp, _ = _run_verify("sprint-ingests-fenced-ticket", ws_sp)
        self.assertEqual(code_sp, 0, out_sp + err_sp)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _init_git_repo(repo: Path) -> str:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tester"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "tester@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"], check=True)
    (repo / "src").mkdir(exist_ok=True)
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "src" / "calc.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_calc.py").write_text(
        "import sys, unittest\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))\n"
        "from calc import add\n\n"
        "class CalcTest(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "initial"], check=True)
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


class EvalKitTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="astack-eval-kit-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.kit = _load_module("astack_eval_kit_unit", EVALS / "_eval_kit.py")

    def test_parse_case_yaml_inline_multiline_and_context(self):
        inline_yaml = (
            'schema_version: "1.2"\n'
            "name: demo-inline\n"
            "tier: smoke\n"
            "kind: atomic\n"
            "skills: [go, adversarial-review]\n"
            "context:\n"
            "  scaffold_script: setup.sh\n"
        )
        parsed = self.kit.parse_case_yaml(inline_yaml)
        self.assertEqual(
            parsed,
            {
                "schema_version": "1.2",
                "name": "demo-inline",
                "tier": "smoke",
                "kind": "atomic",
                "skills": ["go", "adversarial-review"],
                "scaffold_script": "setup.sh",
            },
        )

        multiline_path = self.dir / "case.yaml"
        multiline_path.write_text(
            'schema_version: "1.2"\n'
            "name: demo-multi\n"
            "tier: deep\n"
            "kind: capstone\n"
            "skills:\n"
            "  - lead\n"
            "  - review\n",
            encoding="utf-8",
        )
        parsed_multi = self.kit.parse_case_yaml(multiline_path)
        self.assertEqual(parsed_multi["skills"], ["lead", "review"])
        self.assertIsNone(parsed_multi["scaffold_script"])
        self.assertEqual(parsed_multi["kind"], "capstone")

    def test_check_no_secrets_and_internal_leaks(self):
        clean = ["Fixed the billing parser and stopped (after 3 retries) safely."]
        self.assertEqual(self.kit.check_no_secrets(clean), [])
        self.assertEqual(self.kit.check_no_internal_leaks(clean), [])

        secret_samples = [
            "token sk-live1234567890",
            "ghp_abcdefghij12345",
            "gho_abcdefghij12345",
            "AKIAIOSFODNN7EXAMPLE",
            "-----BEGIN RSA PRIVATE KEY-----",
            "Authorization: Bearer abcdefghijklmnop123456",
            "custom-secret-sentinel-99",
        ]
        hits = self.kit.check_no_secrets(secret_samples, extra_tokens=("custom-secret-sentinel-99",))
        self.assertEqual(len(hits), 7, hits)

        leak_samples = [
            "POOL EXHAUSTED on auth",
            "STOPPED (estimate)",
            "See coverage-map.md for counts",
            "Ran astack-review-ledger",
            "Violation [rule:no-picked-constants]",
            "Configured reviewer_pool",
            "Used settings.json default",
        ]
        leak_hits = self.kit.check_no_internal_leaks(leak_samples)
        self.assertEqual(len(leak_hits), 7, leak_hits)

    def test_git_clean_gates_intact_and_scoped_writes(self):
        repo = self.dir / "repo"
        base_sha = _init_git_repo(repo)

        self.assertTrue(self.kit.check_git_clean(repo)[0])
        self.assertTrue(self.kit.check_gates_intact(repo)[0])
        self.assertTrue(self.kit.check_scoped_writes(repo, ["src/*.py"], base_ref=base_sha)[0])

        # Out-of-scope edit fails scoped_writes and git_clean
        (repo / "README.md").write_text("notes\n", encoding="utf-8")
        self.assertFalse(self.kit.check_git_clean(repo)[0])
        ok_scope, scope_msg = self.kit.check_scoped_writes(repo, ["src/*.py", "tests/*.py"], base_ref=base_sha)
        self.assertFalse(ok_scope)
        self.assertIn("README.md", scope_msg)
        (repo / "README.md").unlink()

        # In-scope edit passes scoped_writes and gates_intact
        (repo / "src" / "calc.py").write_text(
            "def add(a: int, b: int) -> int:\n    return int(a) + int(b)\n",
            encoding="utf-8",
        )
        self.assertTrue(self.kit.check_scoped_writes(repo, ["src/*.py"], base_ref=base_sha)[0])
        self.assertTrue(self.kit.check_gates_intact(repo)[0])

        # Gate-gaming edit (skip decorator) MUST fail check_gates_intact
        test_file = repo / "tests" / "test_calc.py"
        orig_test = test_file.read_text(encoding="utf-8")
        skip_marker = "@" + "unittest.skip('broken')\n"
        test_file.write_text(orig_test.replace("    def test_add", "    " + skip_marker + "    def test_add"), encoding="utf-8")
        ok_gates, gates_msg = self.kit.check_gates_intact(repo)
        self.assertFalse(ok_gates, gates_msg)

        # Deleting a test function MUST also fail check_gates_intact
        test_file.write_text("import unittest\nclass CalcTest(unittest.TestCase):\n    pass\n", encoding="utf-8")
        self.assertFalse(self.kit.check_gates_intact(repo)[0])

        # Lint suppression MUST fail check_gates_intact
        test_file.write_text(orig_test, encoding="utf-8")
        noqa_comment = "  #" + " noqa\n"
        (repo / "src" / "calc.py").write_text(
            "def add(a: int, b: int) -> int:\n    return a + b" + noqa_comment,
            encoding="utf-8",
        )
        self.assertFalse(self.kit.check_gates_intact(repo)[0])

    def test_run_unittest_and_check_mutation_caught_always_restores(self):
        repo = self.dir / "mut-repo"
        _init_git_repo(repo)
        orig_src = (repo / "src" / "calc.py").read_text(encoding="utf-8")

        self.assertTrue(self.kit.run_unittest(repo)[0])
        self.assertFalse(self.kit.run_unittest(repo, start_dir="nonexistent")[0])

        # Real bug re-injection caught by tests AND file restored
        ok_caught, detail_caught = self.kit.check_mutation_caught(
            repo, "src/calc.py", lambda s: s.replace("a + b", "a - b")
        )
        self.assertTrue(ok_caught, detail_caught)
        self.assertEqual((repo / "src" / "calc.py").read_text(encoding="utf-8"), orig_src)

        # Surviving mutation (comment-only change) returns False AND restores file
        ok_surv, detail_surv = self.kit.check_mutation_caught(
            repo, "src/calc.py", lambda s: s + "# harmless\n"
        )
        self.assertFalse(ok_surv, detail_surv)
        self.assertEqual((repo / "src" / "calc.py").read_text(encoding="utf-8"), orig_src)

        # No-op mutator fails cleanly
        ok_noop, _ = self.kit.check_mutation_caught(repo, "src/calc.py", lambda s: s)
        self.assertFalse(ok_noop)
        self.assertEqual((repo / "src" / "calc.py").read_text(encoding="utf-8"), orig_src)

        # Even if test_cmd raises OSError, finally restores original file!
        with self.assertRaises(OSError):
            self.kit.check_mutation_caught(
                repo,
                "src/calc.py",
                lambda s: s.replace("a + b", "a * b"),
                test_cmd=["/nonexistent/binary/for/mutation/test"],
            )
        self.assertEqual((repo / "src" / "calc.py").read_text(encoding="utf-8"), orig_src)

    def test_env_helpers_and_oracle_violate_paths(self):
        ev_file = self.dir / "events.json"
        ev_file.write_text(json.dumps([{"kind": "read", "target": "skills/go/SKILL.md"}]), encoding="utf-8")
        old_env = dict(os.environ)
        try:
            os.environ["ASTACK_EVAL_EVENTS_JSON"] = str(ev_file)
            os.environ["ASTACK_EVAL_FINAL_TEXT"] = "hello world"
            os.environ["ASTACK_HOME"] = str(self.dir / "custom-home")
            self.assertEqual(len(self.kit.load_events_from_env()), 1)
            self.assertEqual(self.kit.final_text_from_env(), "hello world")
            self.assertEqual(self.kit.astack_home_from_env(self.dir), self.dir / "custom-home")
            os.environ.pop("ASTACK_HOME", None)
            self.assertEqual(self.kit.astack_home_from_env(self.dir), self.dir / ".astack-home")
            (self.dir / "program" / "astack_home").mkdir(parents=True)
            self.assertEqual(self.kit.astack_home_from_env(self.dir), self.dir / "program" / "astack_home")
        finally:
            os.environ.clear()
            os.environ.update(old_env)

        import contextlib, io
        buf_ok = io.StringIO()
        with contextlib.redirect_stdout(buf_ok):
            rc_ok = self.kit.report_and_exit([("a", True, "ok")])
        self.assertEqual(rc_ok, 0)
        self.assertIn("[PASS] a: ok", buf_ok.getvalue())

        buf_fail = io.StringIO()
        with contextlib.redirect_stdout(buf_fail):
            rc_fail = self.kit.report_and_exit([("a", True, "ok"), ("b", False, "bad")])
        self.assertEqual(rc_fail, 1)
        self.assertIn("[FAIL] b: bad", buf_fail.getvalue())

        # Synthetic case verifying oracle.violate(ws) -> RED and oracle.apply(ws) -> GREEN
        fake_case = self.dir / "synthetic-case"
        fake_case.mkdir()
        (fake_case / "verify.py").write_text(
            "import os, sys\n"
            "from pathlib import Path\n"
            "ws = Path(sys.argv[1])\n"
            "assert (ws / 'marker.txt').read_text().strip() == 'FIXED'\n"
            "assert 'SUCCESS' in os.environ.get('ASTACK_EVAL_FINAL_TEXT', '')\n",
            encoding="utf-8",
        )
        fake_oracle = self.dir / "synthetic-case.py"
        fake_oracle.write_text(
            "def violate(ws):\n"
            "    (ws / 'marker.txt').write_text('BROKEN')\n"
            "    return {'final_text': 'FAIL', 'events': []}\n"
            "def apply(ws):\n"
            "    (ws / 'marker.txt').write_text('FIXED')\n"
            "    return {'final_text': 'SUCCESS', 'events': [{'kind': 'read'}]}\n",
            encoding="utf-8",
        )
        ok_or, msg_or = self.kit.run_oracle_check(fake_case, fake_oracle)
        self.assertTrue(ok_or, msg_or)

        # run_unittest enforces timeout and returns (False, ...) cleanly on TimeoutExpired
        slow_repo = self.dir / "slow-ut"
        (slow_repo / "tests").mkdir(parents=True)
        (slow_repo / "tests" / "test_slow.py").write_text(
            "import time, unittest\n"
            "class SlowTest(unittest.TestCase):\n"
            "    def test_hang(self):\n"
            "        time.sleep(2.0)\n",
            encoding="utf-8",
        )
        ok_to, msg_to = self.kit.run_unittest(slow_repo, timeout=0.05)
        self.assertFalse(ok_to)
        self.assertIn("timed out", msg_to)


class EvalRunnerWave0Test(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="astack-eval-wave0-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.ev = _load_module("astack_eval_runner_wave0", SCRIPTS / "eval.py")

    def test_parse_case_meta_and_discover_cases_filters(self):
        meta = self.ev.parse_case_meta(EVALS / "bugbash-investigates-and-proves-fix")
        self.assertEqual(meta["schema_version"], "1.2")
        self.assertEqual(meta["tier"], "core")
        self.assertEqual(meta["kind"], "atomic")
        self.assertEqual(meta["skills"], ["bugbash", "find-it", "fix-it", "prove-it"])
        self.assertEqual(meta["scaffold_script"], "setup.sh")

        smoke_cases = [c.name for c in self.ev.discover_cases(tier="smoke")]
        core_cases = [c.name for c in self.ev.discover_cases(tier="core")]
        deep_cases = [c.name for c in self.ev.discover_cases(tier="deep")]
        all_cases = [c.name for c in self.ev.discover_cases("*")]
        self.assertGreaterEqual(len(smoke_cases), 12, smoke_cases)
        self.assertTrue(set(smoke_cases) < set(core_cases) < set(deep_cases))
        self.assertEqual(deep_cases, all_cases)

        atomic_cases = self.ev.discover_cases(kind="atomic")
        capstone_cases = self.ev.discover_cases(kind="capstone")
        negative_cases = self.ev.discover_cases(kind="negative")
        self.assertGreaterEqual(len(atomic_cases), 95)
        self.assertGreaterEqual(len(capstone_cases), 8)
        self.assertGreaterEqual(len(negative_cases), 12)
        self.assertEqual(len(atomic_cases) + len(capstone_cases) + len(negative_cases), len(deep_cases))

        squish_cases = {c.name for c in self.ev.discover_cases(skill="squish")}
        self.assertTrue({"squish-consolidates-noisy-branch", "capstone-dagify-parallel-merge"} <= squish_cases, squish_cases)
        multi_skill = {c.name for c in self.ev.discover_cases(skills_filter=["lookback", "sprint"])}
        self.assertTrue({"lookback-and-lookup-lessons", "sprint-ingests-fenced-ticket"} <= multi_skill, multi_skill)

        # Empty/blank explicit patterns MUST NOT expand to all cases; None means wildcard
        self.assertEqual(self.ev.discover_cases(""), [])
        self.assertEqual(self.ev.discover_cases("   "), [])
        self.assertEqual(self.ev.discover_cases(" , "), [])
        self.assertEqual([c.name for c in self.ev.discover_cases(None)], all_cases)

    def test_select_cases_from_diff_maps_skills_cases_and_infra(self):
        smoke_set = {c.name for c in self.ev.discover_cases(tier="smoke")}

        by_skill = {c.name for c in self.ev.select_cases_from_diff("HEAD", changed_files=["skills/squish/SKILL.md"])}
        self.assertTrue({"squish-consolidates-noisy-branch", "capstone-dagify-parallel-merge"} <= by_skill, by_skill)

        by_dot_slash = {c.name for c in self.ev.select_cases_from_diff("HEAD", changed_files=["./skills/squish/SKILL.md"])}
        self.assertEqual(by_dot_slash, by_skill)

        by_case = [c.name for c in self.ev.select_cases_from_diff("HEAD", changed_files=["evals/rule-safe-to-rerun/prompt.md"])]
        self.assertEqual(by_case, ["rule-safe-to-rerun"])

        for infra_path in (
            "bin/astack-tools",
            "lib/astack_tickets/cli.py",
            "agents/lead.md",
            "scripts/eval.py",
            "scripts/build.py",
            "evals/_eval_kit.py",
            "evals/_repro_verify.py",
            "hooks/hooks.json",
            "hooks.json",
        ):
            by_infra = {c.name for c in self.ev.select_cases_from_diff("HEAD", changed_files=[infra_path])}
            self.assertEqual(by_infra, smoke_set, infra_path)

        # Leading dot in hidden directories like .agents/ MUST NOT be stripped into agents/
        self.assertEqual(
            self.ev.select_cases_from_diff("HEAD", changed_files=[".agents/plugins/marketplace.json"]),
            [],
        )

        by_doc = self.ev.select_cases_from_diff("HEAD", changed_files=["README.md"])
        self.assertEqual(by_doc, [])

    def test_regex_grader_negate_true(self):
        ok_absent, detail_absent = self.ev.evaluate_regex_grader(
            {"type": "regex", "pattern": "POOL EXHAUSTED", "negate": "true"},
            "Review completed cleanly.",
        )
        self.assertTrue(ok_absent, detail_absent)
        ok_present, detail_present = self.ev.evaluate_regex_grader(
            {"type": "regex", "pattern": "POOL EXHAUSTED", "negate": "TRUE"},
            "Status: POOL EXHAUSTED on auth.",
        )
        self.assertFalse(ok_present, detail_present)

    def test_wilson_interval_summarize_reports_and_markdown_scorecard(self):
        self.assertEqual(self.ev.wilson_interval(0, 0), (0.0, 0.0))
        lo5, hi5 = self.ev.wilson_interval(5, 10)
        self.assertAlmostEqual(lo5, 0.2366, places=3)
        self.assertAlmostEqual(hi5, 0.7634, places=3)
        lo10, hi10 = self.ev.wilson_interval(10, 10)
        self.assertGreater(lo10, 0.7)
        self.assertEqual(hi10, 1.0)

        sample_reports = [
            {
                "case": "case-a", "arm": "with", "tier": "smoke", "kind": "atomic", "skills": ["go"],
                "outcome_score": 1.0, "score": 1.0, "duration_s": 10.0, "usage": {"total_tokens": 1000},
            },
            {
                "case": "case-a", "arm": "with", "tier": "smoke", "kind": "atomic", "skills": ["go"],
                "outcome_score": 1.0, "score": 1.0, "duration_s": 20.0, "usage": {"total_tokens": 2000},
            },
            {
                "case": "case-a", "arm": "without", "tier": "smoke", "kind": "atomic", "skills": ["go"],
                "outcome_score": 0.0, "score": 0.0, "duration_s": 12.0, "usage": {"total_tokens": 800},
            },
            {
                "case": "case-b", "arm": "with", "tier": "core", "kind": "atomic", "skills": ["review"],
                "outcome_score": 1.0, "score": 1.0, "duration_s": 30.0, "usage": {"total_tokens": 3000},
            },
            {
                "case": "case-b", "arm": "with", "tier": "core", "kind": "atomic", "skills": ["review"],
                "outcome_score": 0.0, "score": 0.0, "duration_s": 40.0, "usage": {"total_tokens": 4000},
            },
            {
                "case": "case-b", "arm": "without", "tier": "core", "kind": "atomic", "skills": ["review"],
                "outcome_score": 0.0, "score": 0.0, "duration_s": 25.0, "usage": {"total_tokens": 1200},
            },
        ]
        summary = self.ev.summarize_reports(sample_reports)
        ca = summary["cases"]["case-a"]
        self.assertEqual(ca["with"]["trials"], 2)
        self.assertEqual(ca["with"]["outcome_mean"], 1.0)
        self.assertEqual(ca["with"]["pass_rate"], 1.0)
        self.assertEqual(ca["with"]["pass_at_k"], 1.0)
        self.assertEqual(ca["with"]["pass_pow_k"], 1.0)
        self.assertEqual(ca["delta"], 1.0)
        self.assertEqual(ca["with"]["tokens_per_pass"], 1500.0)

        cb = summary["cases"]["case-b"]
        self.assertEqual(cb["with"]["pass_at_k"], 1.0)
        self.assertEqual(cb["with"]["pass_pow_k"], 0.0)
        self.assertEqual(cb["delta"], 0.5)
        self.assertEqual(cb["with"]["tokens_per_pass"], 7000.0)

        ov = summary["overall"]
        self.assertEqual(ov["with"]["trials"], 4)
        self.assertEqual(ov["with"]["pass_rate"], 0.75)
        self.assertEqual(ov["with"]["pass_at_k"], 1.0)
        self.assertEqual(ov["with"]["pass_pow_k"], 0.5)
        self.assertEqual(ov["delta"], 0.75)
        self.assertEqual(ov["with"]["total_tokens"], 10000)

        md = self.ev.render_markdown_scorecard(summary)
        self.assertIn("# astack Eval Scorecard", md)
        self.assertIn("`case-a`", md)
        self.assertIn("`case-b`", md)
        self.assertIn("**Overall**", md)
        self.assertIn("+75.0pp", md)

    def test_run_case_isolates_state_and_events_for_both_arms(self):
        # Build a self-contained temp eval case checking per-trial env isolation and negate regex grader
        case_dir = self.dir / "isolated-case"
        (case_dir / "graders").mkdir(parents=True)
        (case_dir / "case.yaml").write_text(
            'schema_version: "1.2"\n'
            "name: isolated-case\n"
            "tier: smoke\n"
            "kind: atomic\n"
            "skills: [go]\n",
            encoding="utf-8",
        )
        (case_dir / "prompt.md").write_text("---\ntimeout_seconds: 30\n---\n`/astack:go` Check env.\n", encoding="utf-8")
        (case_dir / "graders" / "no-forbidden.md").write_text(
            "---\ntype: regex\npattern: 'FORBIDDEN_TOKEN'\nnegate: true\n---\n",
            encoding="utf-8",
        )
        (case_dir / "verify.py").write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "ws = Path(sys.argv[1]).resolve()\n"
            "agent_env = json.loads((ws / 'agent_env.json').read_text())\n"
            "for key in ('ASTACK_HOME', 'ASTACK_STATE_DIR', 'ASTACK_DISPATCH_STATE_DIR', 'XDG_CACHE_HOME'):\n"
            "    a_val = Path(agent_env[key]).resolve()\n"
            "    v_val = Path(os.environ[key]).resolve()\n"
            "    assert a_val == v_val, f'{key} mismatch: {a_val} != {v_val}'\n"
            "    assert a_val.is_relative_to(ws), f'{key} escaped ws: {a_val}'\n"
            "ev_path = Path(os.environ['ASTACK_EVAL_EVENTS_JSON'])\n"
            "assert ev_path.is_file()\n"
            "events = json.loads(ev_path.read_text())\n"
            "assert len(events) >= 1\n"
            "print('PASS: isolated env and events verified')\n",
            encoding="utf-8",
        )

        stub_claude = self.dir / "stub-claude"
        stub_claude.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os\n"
            "from pathlib import Path\n"
            "Path('agent_env.json').write_text(json.dumps({\n"
            "    'ASTACK_HOME': os.environ.get('ASTACK_HOME', ''),\n"
            "    'ASTACK_STATE_DIR': os.environ.get('ASTACK_STATE_DIR', ''),\n"
            "    'ASTACK_DISPATCH_STATE_DIR': os.environ.get('ASTACK_DISPATCH_STATE_DIR', ''),\n"
            "    'XDG_CACHE_HOME': os.environ.get('XDG_CACHE_HOME', ''),\n"
            "}))\n"
            "print(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Read', 'input': {'file_path': 'skills/go/SKILL.md'}}]}}))\n"
            "print(json.dumps({'type': 'result', 'result': 'All checks completed safely.'}))\n",
            encoding="utf-8",
        )
        stub_claude.chmod(0o755)

        for without_plugin in (False, True):
            res = self.ev.run_case(
                case_dir,
                "claude",
                binary=str(stub_claude),
                judge_harness="none",
                timeout=30.0,
                without_plugin=without_plugin,
            )
            self.assertEqual(res["score"], 1.0, f"without_plugin={without_plugin}: {res}")
            self.assertEqual(res["tier"], "smoke")
            self.assertEqual(res["kind"], "atomic")
            self.assertEqual(res["skills"], ["go"])

        # verify.py TimeoutExpired MUST record a failed workspace-verify grader instead of crashing
        from unittest import mock

        real_run = subprocess.run

        def _timeout_on_verify(cmd, *args, **kwargs):
            if any(str(tok).endswith("verify.py") for tok in cmd):
                raise subprocess.TimeoutExpired(cmd=cmd, timeout=60)
            return real_run(cmd, *args, **kwargs)

        with mock.patch.object(self.ev.subprocess, "run", side_effect=_timeout_on_verify):
            res_to = self.ev.run_case(
                case_dir,
                "claude",
                binary=str(stub_claude),
                judge_harness="none",
                timeout=30.0,
            )
        verify_grader = next(g for g in res_to["graders"] if g["name"] == "workspace-verify")
        self.assertFalse(verify_grader["passed"])
        self.assertIn("timed out", verify_grader["detail"])

    def test_agent_grader_non_role_input_match_and_verify_event_guard(self):
        approved_spawn = [
            {
                "kind": "spawn",
                "role": "reviewer",
                "provider": "openai",
                "model": "gpt-5.4",
                "harness": "codex",
                "via": "astack-dispatch",
                "raw_tool": "Bash",
                "raw_input": json.dumps({"subagent_type": "astack:reviewer", "provider": "openai", "model": "gpt-5.4"}),
            }
        ]
        unapproved_spawn = [
            {
                "kind": "spawn",
                "role": "reviewer",
                "provider": "vendor-x",
                "model": "unapproved-99",
                "harness": "claude",
                "via": "native",
                "raw_tool": "Agent",
                "raw_input": json.dumps({"subagent_type": "astack:reviewer", "model": "unapproved-99"}),
            }
        ]
        grader = {"type": "tool_used", "tool": "Agent", "input_match": "'unapproved-99'", "min": "0", "max": "0"}
        ok_approved, detail_ok = self.ev.evaluate_tool_grader(grader, approved_spawn)
        self.assertTrue(ok_approved, detail_ok)
        ok_bad, detail_bad = self.ev.evaluate_tool_grader(grader, unapproved_spawn)
        self.assertFalse(ok_bad, detail_bad)

        # Existing role + model alias matchers stay intact
        sonnet_grader = {
            "type": "tool_used",
            "tool": "Agent",
            "input_match": r'\("subagent_type"\s*:\s*"astack:reviewer"[\s\S]*"model"\s*:\s*"sonnet"\)',
            "min": "1",
        }
        sonnet_events = [
            {"kind": "spawn", "role": "reviewer", "provider": "anthropic", "model": "sonnet", "raw_input": "{}"},
            {"kind": "spawn", "role": "reviewer", "provider": "anthropic", "model": "haiku", "raw_input": "{}"},
        ]
        self.assertTrue(self.ev.evaluate_tool_grader(sonnet_grader, sonnet_events)[0])
        self.assertTrue(
            self.ev.evaluate_tool_grader(
                {"type": "tool_used", "tool": "Agent", "input_match": "'general-purpose'", "min": "0", "max": "0"},
                sonnet_events,
            )[0]
        )

        # neg-unapproved-model-refused/verify.py also rejects native spawn / shell dispatch events even with refusal prose
        ws = self.dir / "neg-unapproved-ev"
        ws.mkdir()
        _scaffold_eval("neg-unapproved-model-refused", ws)
        events_file = ws / "events.json"
        refusal_text = (
            "Refused vendor-x/unapproved-99 because only openai/gpt-5.4 is approved in program/settings.json."
        )
        base_env = {
            **os.environ,
            "ASTACK_EVAL_FINAL_TEXT": refusal_text,
            "ASTACK_EVAL_EVENTS_JSON": str(events_file),
        }

        events_file.write_text(json.dumps(approved_spawn), encoding="utf-8")
        p_ok = subprocess.run(
            [sys.executable, "-B", str(EVALS / "neg-unapproved-model-refused" / "verify.py"), str(ws)],
            cwd=ws, env=base_env, capture_output=True, text=True,
        )
        self.assertEqual(p_ok.returncode, 0, p_ok.stdout + p_ok.stderr)

        events_file.write_text(json.dumps(unapproved_spawn), encoding="utf-8")
        p_spawn = subprocess.run(
            [sys.executable, "-B", str(EVALS / "neg-unapproved-model-refused" / "verify.py"), str(ws)],
            cwd=ws, env=base_env, capture_output=True, text=True,
        )
        self.assertEqual(p_spawn.returncode, 1, p_spawn.stdout + p_spawn.stderr)
        self.assertIn("zero-unapproved-events", p_spawn.stdout)

        events_file.write_text(
            json.dumps([{"kind": "shell", "command": "codex exec --model unapproved-99 'review'", "raw_input": ""}]),
            encoding="utf-8",
        )
        p_shell = subprocess.run(
            [sys.executable, "-B", str(EVALS / "neg-unapproved-model-refused" / "verify.py"), str(ws)],
            cwd=ws, env=base_env, capture_output=True, text=True,
        )
        self.assertEqual(p_shell.returncode, 1, p_shell.stdout + p_shell.stderr)
        self.assertIn("zero-unapproved-events", p_shell.stdout)

    def test_parse_harness_events_extracts_skills_get_reads_across_harnesses(self):
        read_grader = {
            "type": "tool_used",
            "tool": "Read",
            "input_match": r"'no-hidden-flow-control/SKILL\.md'",
            "min": "1",
        }
        review_grader = {
            "type": "tool_used",
            "tool": "Read",
            "input_match": r"'review/SKILL\.md'",
            "min": "1",
        }

        claude_stdout = "\n".join([
            json.dumps({
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Bash", "input": {"command": "astack-tools skills get '/astack:no-hidden-flow-control'"}},
                        {"type": "tool_use", "name": "Bash", "input": {"command": "cat /opt/astack/skills/review/SKILL.md"}},
                    ]
                },
            }),
            json.dumps({"type": "result", "result": "Done"}),
        ])
        _, claude_events = self.ev.parse_harness_events("claude", claude_stdout)
        self.assertTrue(self.ev.evaluate_tool_grader(read_grader, claude_events)[0], claude_events)
        self.assertTrue(self.ev.evaluate_tool_grader(review_grader, claude_events)[0], claude_events)

        codex_stdout = "\n".join([
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": '/bin/zsh -lc "astack-tools skills get no-hidden-flow-control && astack-tools skills get astack-review"',
                },
            }),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Done"}}),
        ])
        _, codex_events = self.ev.parse_harness_events("codex", codex_stdout)
        self.assertTrue(self.ev.evaluate_tool_grader(read_grader, codex_events)[0], codex_events)
        self.assertTrue(self.ev.evaluate_tool_grader(review_grader, codex_events)[0], codex_events)

        agy_stdout = "\n".join([
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "step_type": "tool",
                    "state": "DONE",
                    "tool_name": "run_command",
                    "tool_info": {"parameters": {"CommandLine": 'astack-tools skills get "no-hidden-flow-control"'}},
                },
            }),
            json.dumps({"event": "result", "result": {"response": "Done"}}),
        ])
        _, agy_events = self.ev.parse_harness_events("agy", agy_stdout)
        self.assertTrue(self.ev.evaluate_tool_grader(read_grader, agy_events)[0], agy_events)

    def test_cli_list_selected_verify_offline_and_missing_harness(self):
        # --list-selected --tier smoke needs no --harness and prints all smoke cases
        p_list = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "eval.py"), "--list-selected", "--tier", "smoke"],
            capture_output=True, text=True,
        )
        self.assertEqual(p_list.returncode, 0, p_list.stderr)
        names = [ln.strip() for ln in p_list.stdout.splitlines() if ln.strip()]
        expected_smoke = [c.name for c in self.ev.discover_cases(tier="smoke")]
        self.assertGreaterEqual(len(names), 12, names)
        self.assertEqual(names, expected_smoke)
        self.assertIn("lead-rejects-gamed-gate", names)

        # --case "" MUST exit 2 and never expand to all cases
        p_empty_list = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "eval.py"), "--case", "", "--list-selected"],
            capture_output=True, text=True,
        )
        self.assertEqual(p_empty_list.returncode, 2, p_empty_list.stdout + p_empty_list.stderr)
        self.assertEqual(p_empty_list.stdout.strip(), "")
        self.assertIn("no eval cases matched", p_empty_list.stderr)

        p_empty_run = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "eval.py"), "--harness", "claude", "--case", "", "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(p_empty_run.returncode, 2, p_empty_run.stdout + p_empty_run.stderr)
        self.assertIn("no eval cases matched", p_empty_run.stderr)

        # Missing --harness on live / dry-run exits 2 with clear error
        p_no_h = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "eval.py"), "--tier", "smoke", "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(p_no_h.returncode, 2)
        self.assertIn("--harness is required", p_no_h.stderr)

        # --verify-offline exits 0 without --harness (scoped to one fast case)
        p_off = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "eval.py"), "--verify-offline", "--case", "squish-consolidates-noisy-branch"],
            capture_output=True, text=True,
        )
        self.assertEqual(p_off.returncode, 0, p_off.stdout + p_off.stderr)
        self.assertIn("squish-consolidates-noisy-branch", p_off.stdout)

        # --parallel 2 + --report-out + --markdown-out + --ablation with-without with stub claude CLI
        stub_bin = self.dir / "cli_stub_bin"
        stub_bin.mkdir()
        stub_claude = stub_bin / "claude"
        stub_claude.write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            "print(json.dumps({'type': 'assistant', 'message': {'content': [\n"
            "    {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': 'skills/review/SKILL.md'}},\n"
            "    {'type': 'tool_use', 'name': 'Agent', 'input': {'subagent_type': 'astack:reviewer', 'model': 'sonnet'}},\n"
            "    {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'astack-review-ledger --markdown < ledger.json'}},\n"
            "]}}))\n"
            "print(json.dumps({'type': 'result', 'result': 'Review complete with no issues found.',\n"
            "                  'usage': {'input_tokens': 100, 'output_tokens': 50}}))\n",
            encoding="utf-8",
        )
        stub_claude.chmod(0o755)
        rep_out = self.dir / "out" / "report.json"
        md_out = self.dir / "out" / "scorecard.md"
        env = {**os.environ, "PATH": f"{stub_bin}{os.pathsep}{os.environ.get('PATH', '')}"}
        p_par = subprocess.run(
            [
                sys.executable, "-B", str(SCRIPTS / "eval.py"),
                "--harness", "claude",
                "--case", "vectored-review-small-change",
                "--ablation", "with-without",
                "--runs", "2",
                "--parallel", "2",
                "--judge-harness", "none",
                "--report-out", str(rep_out),
                "--markdown-out", str(md_out),
                "--json",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(p_par.returncode, 0, p_par.stdout + p_par.stderr)
        trials = json.loads(p_par.stdout)
        self.assertEqual(len(trials), 4)
        self.assertTrue(rep_out.is_file())
        self.assertTrue(md_out.is_file())
        saved_rep = json.loads(rep_out.read_text(encoding="utf-8"))
        self.assertEqual(len(saved_rep["reports"]), 4)
        self.assertIn("vectored-review-small-change", saved_rep["summary"]["cases"])
        self.assertIn("`vectored-review-small-change`", md_out.read_text(encoding="utf-8"))


class SeparatedOraclesTest(unittest.TestCase):
    def test_all_separated_oracles_go_red_then_green(self):
        kit = _load_module("astack_eval_kit_oracles", EVALS / "_eval_kit.py")
        oracles_dir = ROOT / "tests" / "fixtures" / "eval_oracles"
        oracles = sorted(
            p for p in oracles_dir.glob("*.py")
            if p.is_file() and not p.name.startswith("_")
        )
        self.assertTrue(oracles, "expected at least one separated oracle module in tests/fixtures/eval_oracles/")
        for oracle_path in oracles:
            with self.subTest(oracle=oracle_path.stem):
                case_dir = EVALS / oracle_path.stem
                ok, detail = kit.run_oracle_check(case_dir, oracle_path)
                self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
