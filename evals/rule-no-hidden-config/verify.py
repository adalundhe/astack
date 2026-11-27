#!/usr/bin/env python3
"""Executable verifier for `rule-no-hidden-config`."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _check_no_scattered_env_reads(repo: Path) -> tuple[bool, str]:
    hits: list[str] = []
    src_dir = repo / "src"
    for py_file in sorted(src_dir.rglob("*.py")):
        rel = py_file.relative_to(repo).as_posix()
        if rel == "src/config.py":
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            hits.append(f"{rel}:{exc.lineno} syntax error: {exc.msg}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("environ", "getenv"):
                hits.append(f"{rel}:{node.lineno} accesses .{node.attr}")
            elif isinstance(node, ast.ImportFrom) and node.module == "os":
                for alias in node.names:
                    if alias.name in ("environ", "getenv"):
                        hits.append(f"{rel}:{node.lineno} imports {alias.name} from os")
    if hits:
        return False, "; ".join(hits)
    return True, "zero direct os.environ/os.getenv reads outside src/config.py"


def _check_readme_docs(repo: Path) -> tuple[bool, str]:
    readme = repo / "README.md"
    if not readme.is_file():
        return False, "missing README.md"
    low = readme.read_text(encoding="utf-8").lower()
    required_groups = (
        ("endpoint", ("--endpoint", "sync_endpoint")),
        ("batch_size", ("--batch-size", "sync_batch_size")),
        ("output_format", ("--output-format", "sync_output_format")),
        ("log_level", ("--log-level", "sync_log_level")),
        ("verify_tls", ("--verify-tls", "--no-verify-tls", "sync_verify_tls")),
    )
    missing = [name for name, tokens in required_groups if not any(t in low for t in tokens)]
    if missing:
        return False, f"README.md missing option documentation for: {', '.join(missing)}"
    return True, "all 5 options documented in README.md"


_BEHAVIOR_PROBE = r'''
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
import config
import worker

# 1. Defaults
cfg_default = config.load_config([], env={})
assert cfg_default.endpoint == "https://api.example.invalid", cfg_default
assert cfg_default.batch_size == 50, cfg_default
assert cfg_default.output_format == "json", cfg_default
assert cfg_default.log_level == "info", cfg_default
assert cfg_default.verify_tls is True, cfg_default

# 2. Env loading
cfg_env = config.load_config(
    [],
    env={
        "SYNC_ENDPOINT": "https://sync.internal.invalid",
        "SYNC_BATCH_SIZE": "25",
        "SYNC_OUTPUT_FORMAT": "ndjson",
        "SYNC_LOG_LEVEL": "debug",
        "SYNC_VERIFY_TLS": "true",
    },
)
assert cfg_env.endpoint == "https://sync.internal.invalid"
assert cfg_env.batch_size == 25
assert cfg_env.output_format == "ndjson"
assert cfg_env.log_level == "debug"
assert cfg_env.verify_tls is True, "debug log level must not disable verify_tls"

# 3. CLI overrides env; debug does not disable TLS; --no-verify-tls works independently
cfg_cli = config.load_config(
    ["--endpoint", "http://127.0.0.1:9000", "--batch-size", "10", "--output-format", "csv", "--log-level", "debug"],
    env={"SYNC_BATCH_SIZE": "200", "SYNC_OUTPUT_FORMAT": "json", "SYNC_VERIFY_TLS": "true"},
)
assert cfg_cli.endpoint == "http://127.0.0.1:9000"
assert cfg_cli.batch_size == 10
assert cfg_cli.output_format == "csv"
assert cfg_cli.log_level == "debug"
assert cfg_cli.verify_tls is True

cfg_no_tls = config.load_config(["--no-verify-tls"], env={})
assert cfg_no_tls.verify_tls is False
assert cfg_no_tls.log_level == "info"

# 4. Worker honors passed AppConfig even if os.environ has conflicting values
old_env = dict(os.environ)
try:
    os.environ["SYNC_ENDPOINT"] = "https://poison.invalid"
    os.environ["SYNC_BATCH_SIZE"] = "999"
    os.environ["SYNC_OUTPUT_FORMAT"] = "ndjson"
    os.environ["SYNC_DEBUG"] = "1"
    os.environ["SYNC_VERIFY_TLS"] = "false"
    res = worker.run_sync([{"id": "1"}, {"id": "2"}, {"id": "3"}], cfg_cli)
    assert res["endpoint"] == "http://127.0.0.1:9000", res
    assert res["batch_size"] == 10, res
    assert res["verify_tls"] is True, res
    assert res["output_format"] == "csv", res
finally:
    os.environ.clear()
    os.environ.update(old_env)

# 5. Fail-fast on invalid values
bad_cases = [
    ("bad endpoint", ["--endpoint", "ftp://bad"], {}),
    ("batch_size=0", ["--batch-size", "0"], {}),
    ("batch_size=1001", ["--batch-size", "1001"], {}),
    ("batch_size non-int env", [], {"SYNC_BATCH_SIZE": "abc"}),
    ("bad output_format", ["--output-format", "xml"], {}),
    ("bad log_level", ["--log-level", "verbose"], {}),
    ("bad verify_tls env", [], {"SYNC_VERIFY_TLS": "maybe"}),
]
for label, argv, env_map in bad_cases:
    try:
        config.load_config(argv, env=env_map)
        raise AssertionError(f"expected ValueError or SystemExit for {label}")
    except (ValueError, SystemExit):
        pass

print(json.dumps({"central_config_ok": True}))
'''


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    buggy_config = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/config.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    env_ok, env_detail = _check_no_scattered_env_reads(repo)
    checks.append(("no-scattered-env-reads", env_ok, env_detail))

    docs_ok, docs_detail = _check_readme_docs(repo)
    checks.append(("readme-docs", docs_ok, docs_detail))

    # CLI --help and invalid-arg fail-fast
    help_proc = subprocess.run(
        [sys.executable, "-B", str(repo / "src" / "cli.py"), "--help"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=10,
    )
    help_out = (help_proc.stdout + "\n" + help_proc.stderr).lower()
    help_flags_ok = help_proc.returncode == 0 and all(
        tok in help_out for tok in ("--endpoint", "--batch-size", "--output-format", "--log-level")
    ) and ("--verify-tls" in help_out or "--no-verify-tls" in help_out)
    checks.append(("cli-help", help_flags_ok, "all flags shown in --help" if help_flags_ok else help_out[:200]))

    bad_cli = subprocess.run(
        [sys.executable, "-B", str(repo / "src" / "cli.py"), "--batch-size", "-5"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=10,
    )
    checks.append((
        "cli-fail-fast",
        bad_cli.returncode != 0,
        f"exited {bad_cli.returncode} on invalid --batch-size" if bad_cli.returncode != 0 else "accepted invalid --batch-size -5",
    ))

    probe = subprocess.run(
        [sys.executable, "-B", "-c", _BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if probe.returncode == 0:
        checks.append(("behavior-config", True, probe.stdout.strip()))
    else:
        detail = (probe.stderr.strip() or probe.stdout.strip() or f"exit {probe.returncode}")[:300]
        checks.append(("behavior-config", False, detail))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_ok, mut_detail = _eval_kit.check_mutation_caught(repo, "src/config.py", lambda _: buggy_config)
    checks.append(("mutation-caught", mut_ok, mut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    final_text = _eval_kit.final_text_from_env()
    sec_hits = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))
    leak_hits = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
