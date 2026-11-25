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
            "import sys, threading, unittest\n"
            "from src.inventory import Inventory\n"
            "class TestInventory(unittest.TestCase):\n"
            "    def test_duplicate_sku_in_batch(self):\n"
            "        inv = Inventory({'a': 3})\n"
            "        with self.assertRaises(ValueError):\n"
            "            inv.reserve_batch([('a', 2), ('a', 2)])\n"
            "    def test_split_lock_race(self):\n"
            "        sys.setswitchinterval(1e-6)\n"
            "        for _ in range(150):\n"
            "            inv = Inventory({'a': 1})\n"
            "            bar = threading.Barrier(4)\n"
            "            ok = [0]\n"
            "            def worker():\n"
            "                bar.wait()\n"
            "                try:\n"
            "                    inv.reserve_batch([('a', 1)])\n"
            "                    ok[0] += 1\n"
            "                except ValueError:\n"
            "                    pass\n"
            "            ts = [threading.Thread(target=worker) for _ in range(4)]\n"
            "            for t in ts: t.start()\n"
            "            for t in ts: t.join()\n"
            "            self.assertGreaterEqual(inv.available('a'), 0)\n"
            "            self.assertEqual(ok[0], 1)\n"
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
            "import sys, threading\n"
            "from pool import JobPool\n"
            "sys.setswitchinterval(1e-6)\n"
            "for _ in range(150):\n"
            "    p = JobPool()\n"
            "    for i in range(40): p.push(i)\n"
            "    bar = threading.Barrier(4)\n"
            "    out = []\n"
            "    lock = threading.Lock()\n"
            "    def run():\n"
            "        bar.wait()\n"
            "        b = p.drain_batch(10)\n"
            "        with lock:\n"
            "            out.extend(b)\n"
            "    ts = [threading.Thread(target=run) for _ in range(4)]\n"
            "    for t in ts: t.start()\n"
            "    for t in ts: t.join()\n"
            "    assert len(out) == len(set(out)) == 40, f'duplicate/lost items: len={len(out)} uniq={len(set(out))}'\n"
        )
        code_c, _, err_c, data_c = _run_verify("vectored-review-concurrency", ws_c)
        self.assertEqual(code_c, 0, err_c)
        self.assertEqual(data_c["detected"], ["bug1_split_lock_drain_batch"])

        # 2) vectored-review-cross-harness
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
        code_x, _, err_x, data_x = _run_verify("vectored-review-cross-harness", ws_x)
        self.assertEqual(code_x, 0, err_x)
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
        self.assertTrue(cal_out.is_file())

        # Feed that exact calibration.json directly into astack-review-ledger --calibration
        saved = json.loads(cal_out.read_text())
        saved["models"]["openai/gpt-5.4"] = {"detected": 5, "planted": 5, "source": "vectored-review-planted-bugs"}
        cal_out.write_text(json.dumps(saved))

        ledger_in = json.dumps({
            "reviewer_pool": [
                {"provider": "anthropic", "model": "sonnet", "harness": "claude"},
                {"provider": "openai", "model": "gpt-5.4", "harness": "codex"},
            ],
            "vectors": [{"name": "auth", "risk": "risky"}],
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
        # Jeffreys miss prob: (2.5/6) * (0.5/6) = 0.0347 < 0.05 -> clears cleanly at k=2!
        vec = l_data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["verdict"], "clean_calibrated")
        self.assertAlmostEqual(vec["estimate"]["zero_bug_miss_prob"], 0.0347, places=4)
        self.assertFalse(vec["landing_blocked"])


if __name__ == "__main__":
    unittest.main()
