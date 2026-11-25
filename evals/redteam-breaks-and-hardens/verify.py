#!/usr/bin/env python3
"""Objective post-run verifier for redteam-breaks-and-hardens."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time


class _YieldingLock:
    def __init__(self) -> None:
        self._inner = threading.Lock()

    def __enter__(self):
        self._inner.acquire()
        return self

    def __exit__(self, *args):
        self._inner.release()
        time.sleep(0.01)


def _load_vault_cls(repo: Path):
    src = str(repo / "src")
    sys.path.insert(0, src)
    try:
        spec = importlib.util.spec_from_file_location("eval_vault_under_test", repo / "src" / "vault.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.TenantVault
    finally:
        if src in sys.path:
            sys.path.remove(src)


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    main_sha = (ws / "program" / "main_sha.txt").read_text(encoding="utf-8").strip()

    if list(repo.rglob("*_DEBUG_*.*")):
        print("FAIL: leftover debug artifacts in repo/", file=sys.stderr)
        return 1

    ut = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(repo / "tests")],
        capture_output=True, text=True,
    )
    if ut.returncode != 0:
        print(f"FAIL: unit tests failed:\n{ut.stdout}\n{ut.stderr}", file=sys.stderr)
        return 1

    TenantVault = _load_vault_cls(repo)
    with tempfile.TemporaryDirectory(prefix="redteam-verify-") as td:
        root = Path(td) / "store"
        v = TenantVault(root, b"secret", max_writes=1)
        tok = v.make_token("acme")

        # 1. Fail-closed auth on malformed token
        try:
            v.authenticate("no-colon-malformed")
            print("FAIL: malformed token still authenticated (fail-open)", file=sys.stderr)
            return 1
        except (PermissionError, ValueError):
            pass

        # 2. Path traversal blocked
        escaped = root / "escaped.txt"
        try:
            v.write_blob(tok, "../escaped.txt", b"pwn")
            if escaped.exists():
                print("FAIL: path traversal wrote outside tenant directory", file=sys.stderr)
                return 1
            print("FAIL: path traversal did not raise an error", file=sys.stderr)
            return 1
        except (ValueError, PermissionError):
            pass
        if escaped.exists():
            print("FAIL: path traversal created escaped file", file=sys.stderr)
            return 1

        # 3. Atomic quota enforcement under concurrent burst
        v2 = TenantVault(Path(td) / "store2", b"secret", max_writes=1)
        v2._lock = _YieldingLock()
        tok2 = v2.make_token("acme")
        bar = threading.Barrier(2)
        ok = [0]
        ok_lock = threading.Lock()

        def worker(idx: int):
            bar.wait()
            try:
                v2.write_blob(tok2, f"f{idx}.txt", b"x")
                with ok_lock:
                    ok[0] += 1
            except Exception:
                pass

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        if ok[0] != 1:
            print(f"FAIL: quota race allowed {ok[0]} writes instead of 1", file=sys.stderr)
            return 1

    # 4. Red-first anti-tautology: agent's tests must fail on original buggy vault.py
    with tempfile.TemporaryDirectory(prefix="redteam-red-") as td:
        tmp_repo = Path(td) / "repo"
        shutil.copytree(repo, tmp_repo)
        orig = subprocess.run(
            ["git", "-C", str(repo), "show", f"{main_sha}:src/vault.py"],
            capture_output=True, text=True, check=True,
        ).stdout
        (tmp_repo / "src" / "vault.py").write_text(orig, encoding="utf-8")
        red = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(tmp_repo / "tests")],
            capture_output=True, text=True,
        )
        if red.returncode == 0:
            print("FAIL: tests still pass against original buggy vault.py", file=sys.stderr)
            return 1

    print("PASS: all 3 redteam defects fixed, red-first tests verified, repo clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
