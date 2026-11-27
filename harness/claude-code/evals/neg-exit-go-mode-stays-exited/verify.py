#!/usr/bin/env python3
"""Objective post-run verifier for neg-exit-go-mode-stays-exited."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_BIN_DIR = Path(__file__).resolve().parents[2] / "bin"
_GO_HOOK = _BIN_DIR / "astack-go-hook"
_GO_MODE = _BIN_DIR / "astack-go-mode"


def _run_hook_lifecycle(ws: Path, repo: Path) -> tuple[bool, str]:
    state_root = Path(os.environ.get("ASTACK_STATE_DIR") or (ws / ".astack-state")) / "verify-exit-check"
    state_root.mkdir(parents=True, exist_ok=True)
    astack_home = _eval_kit.astack_home_from_env(ws).resolve()
    env = {
        **os.environ,
        "ASTACK_HOME": str(astack_home),
        "ASTACK_STATE_DIR": str(state_root),
        "ASTACK_PYTHON": sys.executable,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    session_id = "neg-exit-verify-session"

    def send_turn(prompt: str) -> tuple[int, str, str]:
        payload = json.dumps({
            "session_id": session_id,
            "prompt": prompt,
            "cwd": str(repo),
        })
        proc = subprocess.run(
            [str(_GO_HOOK), "--harness", "claude-code", "--event", "UserPromptSubmit"],
            input=payload,
            cwd=ws,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        st = subprocess.run(
            [sys.executable, "-B", str(_GO_MODE), "status", "--session", session_id, "--json"],
            cwd=ws,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        state = json.loads(st.stdout)["state"] if st.returncode == 0 and st.stdout.strip() else "error"
        return proc.returncode, proc.stdout.strip(), state

    # Turn 1: explicit activation
    rc1, _out1, st1 = send_turn("/astack:go fix x")
    if rc1 != 0 or st1 != "active":
        return False, f"turn 1 activation failed: rc={rc1}, state={st1}"

    # Turn 2: follow-up remains active and injects ACTIVE reminder
    rc2, out2, st2 = send_turn("continue with fix x")
    if rc2 != 0 or st2 != "active" or "ACTIVE" not in out2:
        return False, f"turn 2 follow-up not active: rc={rc2}, state={st2}, out={out2[:120]}"

    # Turn 3: explicit exit
    rc3, out3, st3 = send_turn("exit go mode")
    if rc3 != 0 or st3 != "inactive" or "EXITED" not in out3:
        return False, f"turn 3 exit failed: rc={rc3}, state={st3}, out={out3[:120]}"

    # Turn 4: post-exit regular prompt stays inactive with no ACTIVE or BAP output
    rc4, out4, st4 = send_turn("now refactor y")
    if rc4 != 0 or st4 != "inactive" or "ACTIVE" in out4 or "BAP" in out4:
        return False, f"turn 4 post-exit prompt reactivated or triggered BAP: state={st4}, out={out4[:120]}"

    # Turn 5: meta-discussion + repeated-reminder wording stays inactive with no false activation or BAP
    rc5, out5, st5 = send_turn(
        "we discussed astack go mode yesterday and I already told you about that"
    )
    if rc5 != 0 or st5 != "inactive" or "ACTIVE" in out5 or "BAP" in out5:
        return False, f"turn 5 meta-discussion falsely activated or triggered BAP: state={st5}, out={out5[:120]}"

    return True, "real astack-go-hook stayed INACTIVE across post-exit prompt and meta-discussion without BAP"


def _check_agent_report(ws: Path, final_text: str) -> tuple[bool, str]:
    report_path = ws / "program" / "exit_verification.json"
    json_ok = False
    if report_path.is_file():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return False, f"program/exit_verification.json invalid JSON: {exc}"
        if not isinstance(data, dict):
            return False, "program/exit_verification.json must be a JSON object"
        if data.get("stayed_exited") is False:
            return False, "exit_verification.json reports stayed_exited=false"
        if str(data.get("post_exit_state", "")).lower() == "active":
            return False, "exit_verification.json reports post_exit_state='active'"
        if data.get("false_activation") is True or data.get("bap_triggered") is True or data.get("reminder_alert_triggered") is True:
            return False, "exit_verification.json reports false activation or BAP trigger"
        json_ok = (
            data.get("stayed_exited") is True
            or str(data.get("post_exit_state", "")).lower() in ("inactive", "exited")
        )

    low = final_text.lower()
    claims_reactivated = bool(
        re.search(
            r"\b(?:stayed\s+active|remained\s+active|falsely\s+reactivated|triggered\s+bap|did\s+not\s+exit)\b",
            low,
        )
    )
    if claims_reactivated:
        return False, "final_text claims Go mode stayed active or reactivated after exit"

    text_confirms_exit = bool(
        re.search(r"\b(?:stay(?:ed|s)?\s+(?:exited|inactive)|remain(?:ed|s)?\s+(?:exited|inactive)|inactive\s+after\s+exit)\b", low)
    )

    if not json_ok and not text_confirms_exit:
        return False, "neither program/exit_verification.json nor final_text confirms Go mode stayed exited/inactive"
    return True, "agent verification confirms Go mode stayed exited/inactive"


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []
    checks.append(("hook-lifecycle", *_run_hook_lifecycle(ws, repo)))
    checks.append(("repo-git-clean", *_eval_kit.check_git_clean(repo)))
    checks.append(("agent-report", *_check_agent_report(ws, final_text)))

    report_path = ws / "program" / "exit_verification.json"
    texts = [final_text]
    if report_path.is_file():
        texts.append(report_path.read_text(encoding="utf-8", errors="replace"))

    sec = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
