#!/usr/bin/env python3
"""Executable verifier for `skill-baseline`."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _valid_side_stats(side: Any, label: str) -> tuple[bool, str, int | None]:
    if not isinstance(side, dict):
        return False, f"{label} section missing or not an object", None
    med = side.get("median_ms", side.get("p50_ms"))
    mean = side.get("mean_ms")
    if not isinstance(med, (int, float)) or isinstance(med, bool) or med <= 0:
        return False, f"{label}.median_ms invalid: {med!r}", None
    if not isinstance(mean, (int, float)) or isinstance(mean, bool) or mean <= 0:
        return False, f"{label}.mean_ms invalid: {mean!r}", None
    size = side.get("dataset_lines", side.get("dataset_size", side.get("input_size")))
    size_int = size if isinstance(size, int) and not isinstance(size, bool) else None
    return True, f"{label} median={med:.3f}ms mean={mean:.3f}ms", size_int


def _validate_report(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "baseline_report.json is not a JSON object"
    if data.get("parity_verified") is not True:
        return False, f"parity_verified must be true, got {data.get('parity_verified')!r}"

    warmup = data.get("warmup_runs", data.get("warmup"))
    if not isinstance(warmup, int) or isinstance(warmup, bool) or warmup < 1:
        return False, f"warmup_runs must be int >= 1, got {warmup!r}"

    trials = data.get("trials", data.get("num_trials"))
    if not isinstance(trials, int) or isinstance(trials, bool) or trials < 5:
        return False, f"trials must be int >= 5, got {trials!r}"

    ok_a, msg_a, size_a = _valid_side_stats(data.get("candidate"), "candidate")
    if not ok_a:
        return False, msg_a
    ok_b, msg_b, size_b = _valid_side_stats(data.get("competitor"), "competitor")
    if not ok_b:
        return False, msg_b

    top_size = data.get("dataset_lines", data.get("dataset_size", data.get("input_size")))
    eff_a = size_a if size_a is not None else top_size
    eff_b = size_b if size_b is not None else top_size
    if not isinstance(eff_a, int) or not isinstance(eff_b, int) or eff_a < 100 or eff_a != eff_b:
        return False, f"input sizes must match and be >= 100 (candidate={eff_a!r}, competitor={eff_b!r})"

    plat = data.get("platform") or data.get("environment")
    if not isinstance(plat, dict) or len(plat) < 2:
        return False, f"missing platform metadata dict (got {plat!r})"

    return True, f"parity_verified=True, size={eff_a}, warmup={warmup}, trials={trials}; {msg_a}; {msg_b}"


def _verify_runtime_fairness(ws: Path) -> tuple[bool, str]:
    """Instrument both implementations in scratch copies to verify equal inputs, alternation, and parity enforcement."""
    with tempfile.TemporaryDirectory(prefix="astack-baseline-verify-") as td:
        scratch = Path(td) / "ws"
        shutil.copytree(ws / "repo", scratch / "repo")
        shutil.copytree(ws / "program", scratch / "program")
        report_file = scratch / "program" / "baseline_report.json"
        if report_file.exists():
            report_file.unlink()

        call_log = Path(td) / "calls.log"
        for side in ("candidate", "competitor"):
            mod_path = scratch / "repo" / "src" / f"{side}.py"
            orig = mod_path.read_text(encoding="utf-8")
            hook = (
                "\n\nimport os as _v_os\n"
                "_orig_compute_word_freq = compute_word_freq\n"
                "def compute_word_freq(lines):\n"
                "    lp = _v_os.environ.get('ASTACK_BASELINE_LOG')\n"
                "    if lp:\n"
                "        with open(lp, 'a', encoding='utf-8') as fh:\n"
                f"            fh.write(f'{side}:{{len(lines)}}\\n')\n"
                f"    if _v_os.environ.get('ASTACK_BREAK_PARITY') == '{side}':\n"
                "        return {'corrupted': 1}\n"
                "    return _orig_compute_word_freq(lines)\n"
            )
            mod_path.write_text(orig + hook, encoding="utf-8")

        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "ASTACK_BASELINE_LOG": str(call_log),
        }
        proc = subprocess.run(
            [sys.executable, "-B", str(scratch / "program" / "baseline_bench.py")],
            cwd=scratch,
            env=env,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if proc.returncode != 0:
            err = (proc.stderr.strip() or proc.stdout.strip())[:240]
            return False, f"baseline_bench.py failed (exit {proc.returncode}): {err}"
        if not report_file.is_file():
            return False, "baseline_bench.py did not write program/baseline_report.json"

        fresh_report = json.loads(report_file.read_text(encoding="utf-8"))
        ok_rep, rep_msg = _validate_report(fresh_report)
        if not ok_rep:
            return False, f"regenerated report invalid: {rep_msg}"

        if not call_log.is_file():
            return False, "neither implementation was called"
        entries = [line.split(":") for line in call_log.read_text(encoding="utf-8").splitlines() if ":" in line]
        cand_sizes = [int(sz) for side, sz in entries if side == "candidate"]
        comp_sizes = [int(sz) for side, sz in entries if side == "competitor"]
        if len(cand_sizes) < 6 or len(comp_sizes) < 6:
            return False, f"expected >= 6 calls each (warmup + >=5 trials), got cand={len(cand_sizes)}, comp={len(comp_sizes)}"
        if set(cand_sizes) != set(comp_sizes) or min(cand_sizes) < 100:
            return False, f"unequal or tiny input sizes: cand={set(cand_sizes)}, comp={set(comp_sizes)}"

        sides_seq = [side for side, _ in entries]
        transitions = sum(1 for i in range(1, len(sides_seq)) if sides_seq[i] != sides_seq[i - 1])
        if transitions < 4:
            return False, f"runs did not alternate between implementations (only {transitions} side switches)"

        # Verify parity check is real (not hardcoded parity_verified: true).
        if report_file.exists():
            report_file.unlink()
        env_bad = {**env, "ASTACK_BREAK_PARITY": "competitor"}
        bad_proc = subprocess.run(
            [sys.executable, "-B", str(scratch / "program" / "baseline_bench.py")],
            cwd=scratch,
            env=env_bad,
            capture_output=True,
            text=True,
            timeout=25,
        )
        parity_caught = bad_proc.returncode != 0
        if not parity_caught and report_file.is_file():
            try:
                bad_rep = json.loads(report_file.read_text(encoding="utf-8"))
                parity_caught = bad_rep.get("parity_verified") is False
            except json.JSONDecodeError:
                parity_caught = True
        if not parity_caught:
            return False, "baseline_bench.py silently reported parity_verified=true when competitor output was corrupted"

        return True, (
            f"equal sizes ({cand_sizes[0]} lines, cand={len(cand_sizes)}x, comp={len(comp_sizes)}x), "
            f"alternating ({transitions} switches), parity violation caught"
        )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    bench_py = ws / "program" / "baseline_bench.py"
    report_json = ws / "program" / "baseline_report.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, "missing ./repo"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", clean_ok, clean_detail))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("repo-unittest", ut_ok, ut_detail))

    checks.append(("baseline-bench-exists", bench_py.is_file(), str(bench_py.name)))
    checks.append(("baseline-report-exists", report_json.is_file(), str(report_json.name)))

    raw_report = ""
    report_ok = False
    if report_json.is_file():
        raw_report = report_json.read_text(encoding="utf-8", errors="replace")
        try:
            data = json.loads(raw_report)
        except json.JSONDecodeError as exc:
            checks.append(("report-valid", False, f"invalid JSON: {exc}"))
        else:
            report_ok, rep_detail = _validate_report(data)
            checks.append(("report-valid", report_ok, rep_detail))
    else:
        checks.append(("report-valid", False, "missing program/baseline_report.json"))

    if bench_py.is_file() and report_ok:
        fair_ok, fair_detail = _verify_runtime_fairness(ws)
        checks.append(("runtime-fairness-and-parity", fair_ok, fair_detail))
    else:
        checks.append(("runtime-fairness-and-parity", False, "skipped because script or report missing/invalid"))

    texts = [final_text, raw_report]
    if bench_py.is_file():
        texts.append(bench_py.read_text(encoding="utf-8", errors="replace"))
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
