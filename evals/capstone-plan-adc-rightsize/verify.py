#!/usr/bin/env python3
"""Executable verifier for `capstone-plan-adc-rightsize`."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_ASTACK_TOOLS = Path(__file__).resolve().parents[2] / "bin" / "astack-tools"
_AD_REQUIRED_HEADINGS = (
    "Status",
    "Context",
    "Decision",
    "Non-goals",
    "Costs accepted",
    "Alternatives considered",
    "Acceptance criteria",
    "Tests",
    "Evidence",
)

_CLIENT_PROBE = r'''
import inspect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
import client

sig = inspect.signature(client.fetch)
required = [
    name
    for name, p in sig.parameters.items()
    if p.default is inspect.Parameter.empty
    and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
]
assert required == ["url"], f"Tier 0 fetch must require only ['url'], got required={required}"

# Tier 0: zero-ceremony call
r0 = client.fetch("https://api.sdk.invalid/health")
assert r0.status == 200 and r0.body == b"ok", f"Tier 0 health failed: {r0}"

# Tier 1: optional timeout + plain dict headers
r1 = client.fetch("https://api.sdk.invalid/echo", timeout=2.5, headers={"X-Caller": "tier1"})
assert r1.status == 200, f"Tier 1 status failed: {r1}"
echo = json.loads(r1.body.decode("utf-8"))
assert echo["headers"].get("X-Caller") == "tier1" and echo["timeout"] == 2.5, f"Tier 1 echo mismatch: {echo}"

# Tier 2: custom flaky transport + RetryPolicy
calls = []
def flaky_transport(url, headers, timeout):
    calls.append((url, dict(headers), timeout))
    if len(calls) < 3:
        return client.Response(status=503, body=b"busy", headers={})
    return client.Response(status=200, body=b"recovered", headers={})

retry_kw = "retry" if "retry" in sig.parameters else "retry_policy"
r2 = client.fetch(
    "https://api.sdk.invalid/job",
    headers={"X-Tier": "2"},
    timeout=1.5,
    transport=flaky_transport,
    **{retry_kw: client.RetryPolicy(max_attempts=3)},
)
assert r2.status == 200 and r2.body == b"recovered", f"Tier 2 failed: {r2}"
assert len(calls) == 3, f"expected 3 attempts, got {len(calls)}"

# Actionable errors replacing ERR_9 / ERR_4
bad_url_msg = ""
try:
    client.fetch("not-a-url")
    raise AssertionError("expected exception on invalid URL")
except Exception as exc:
    bad_url_msg = str(exc)
assert "ERR_9" not in bad_url_msg, f"cryptic ERR_9 still raised: {bad_url_msg!r}"
assert ("http://" in bad_url_msg.lower() or "https://" in bad_url_msg.lower() or "scheme" in bad_url_msg.lower()), (
    f"invalid URL error lacks actionable scheme guidance: {bad_url_msg!r}"
)

bad_to_msg = ""
try:
    client.fetch("https://api.sdk.invalid/health", timeout=-1)
    raise AssertionError("expected exception on negative timeout")
except Exception as exc:
    bad_to_msg = str(exc)
assert "ERR_4" not in bad_to_msg, f"cryptic ERR_4 still raised: {bad_to_msg!r}"
assert "timeout" in bad_to_msg.lower() and ("> 0" in bad_to_msg or "positive" in bad_to_msg.lower() or "greater than 0" in bad_to_msg.lower()), (
    f"invalid timeout error lacks actionable guidance: {bad_to_msg!r}"
)

print(json.dumps({"default_timeout": float(client.DEFAULT_TIMEOUT_SECONDS)}))
'''


def _parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return None, text
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fields[k.strip()] = v.strip().strip("'\"")
    return fields, text[m.end():]


def _extract_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, re.M))
    for idx, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        sections[heading.lower()] = body[start:end].strip()
    return sections


def _reinject_ceremony(src: str) -> str:
    return (
        src
        + "\n\n_orig_fetch_ceremony = fetch\n"
        + "def fetch(url, required_config, *args, **kwargs):\n"
        + "    return _orig_fetch_ceremony(url, *args, **kwargs)\n"
    )


def _reinject_cryptic_err9(src: str) -> str:
    return (
        src
        + "\n\n_orig_fetch_err9 = fetch\n"
        + "def fetch(url, *args, **kwargs):\n"
        + "    if not isinstance(url, str) or not (url.startswith('http://') or url.startswith('https://')):\n"
        + "        raise RuntimeError('ERR_9')\n"
        + "    return _orig_fetch_err9(url, *args, **kwargs)\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws).resolve()
    arch_dir = astack_home / "sdk-v2" / "architecture"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, f"missing ./repo at {repo}"))
        return _eval_kit.report_and_exit(checks)

    base_sha = (ws / "program" / "base_sha.txt").read_text(encoding="utf-8").strip()

    # 1. AD_1.md preserved untouched & zero AD_*.md inside ./repo
    repo_ads = sorted(repo.rglob("AD_*.md"))
    checks.append((
        "no-ad-in-repo",
        not repo_ads,
        "no AD files written inside repo" if not repo_ads else f"AD files inside repo: {repo_ads}",
    ))

    ad1 = arch_dir / "AD_1.md"
    expected_ad1_sha = (ws / "program" / "ad1_sha256.txt").read_text(encoding="utf-8").strip()
    ad1_ok = ad1.is_file() and hashlib.sha256(ad1.read_bytes()).hexdigest() == expected_ad1_sha
    checks.append(("ad1-preserved", ad1_ok, "AD_1.md preserved untouched" if ad1_ok else "AD_1.md missing or modified"))

    # 2. AD_2.md published with full AD_FORMAT frontmatter + 9 sections, no draft leftover
    ad2 = arch_dir / "AD_2.md"
    draft2 = arch_dir / "AD_2.draft.md"
    ad2_text = ad2.read_text(encoding="utf-8", errors="replace") if ad2.is_file() else ""
    fm, body = _parse_frontmatter(ad2_text)
    sections = _extract_sections(body)
    missing_h = [h for h in _AD_REQUIRED_HEADINGS if not sections.get(h.lower())]
    status_text = sections.get("status", "")
    status_ok = bool(re.search(r"(?:Accepted|Built)\s*\(\d{4}-\d{2}-\d{2}\)", status_text))
    fm_ok = fm is not None and fm.get("ad_number") == "2" and bool(fm.get("name")) and bool(fm.get("description"))
    ad2_grounded = "client.py" in ad2_text.lower() and ("fetch" in ad2_text.lower())
    ad2_ok = ad2.is_file() and not draft2.exists() and fm_ok and not missing_h and status_ok and ad2_grounded
    checks.append((
        "ad2-published-valid",
        ad2_ok,
        f"AD_2.md published with valid frontmatter, all 9 headings, and dated Status"
        if ad2_ok
        else f"exists={ad2.is_file()}, draft={draft2.exists()}, fm_ok={fm_ok}, missing_headings={missing_h}, status_ok={status_ok}, grounded={ad2_grounded}",
    ))

    # 3. Contract-reduction catalog via astack-tools docs list --project sdk-v2 --subdir contracts --json
    env = {**os.environ, "ASTACK_HOME": str(astack_home)}
    docs_proc = subprocess.run(
        [sys.executable, "-B", str(_ASTACK_TOOLS), "docs", "list", "--project", "sdk-v2", "--subdir", "contracts", "--json"],
        cwd=ws,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    catalog_files: list[Path] = []
    if docs_proc.returncode == 0:
        try:
            payload = json.loads(docs_proc.stdout)
            for ent in payload.get("docs") or []:
                if not isinstance(ent, dict):
                    continue
                p = Path(str(ent.get("path", ""))).resolve()
                if p.is_file() and p.stat().st_size > 0:
                    catalog_files.append(p)
                elif p.is_dir():
                    for child in sorted(p.rglob("*")):
                        if child.is_file() and child.stat().st_size > 0:
                            catalog_files.append(child.resolve())
        except json.JSONDecodeError:
            pass

    catalog_text = "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in catalog_files)
    clow = catalog_text.lower()
    has_line_cite = bool(re.search(r"client\.py:\d+", catalog_text))
    bloat_hits = [
        tok for tok in ("timeout_ms", "timeout_seconds", "retry_enabled", "max_retries", "legacy_xml_envelope", "headers_list")
        if tok in clow
    ]
    has_tiers = bool(re.search(r"\b(tier\s*[0-2]|level\s*[0-2]|progressive|stepped)\b", clow))
    has_migration = bool(re.search(r"\b(deprecat|migrat|compatib|v2|rollout|breaking)\b", clow))
    catalog_ok = (
        docs_proc.returncode == 0
        and bool(catalog_files)
        and has_line_cite
        and len(bloat_hits) >= 4
        and has_tiers
        and has_migration
    )
    checks.append((
        "contract-catalog-published",
        catalog_ok,
        f"found {len(catalog_files)} catalog file(s) citing client.py:<line> and {len(bloat_hits)}/6 bloated params"
        if catalog_ok
        else f"rc={docs_proc.returncode}, files={len(catalog_files)}, line_cite={has_line_cite}, bloat={bloat_hits}, tiers={has_tiers}, migration={has_migration}",
    ))

    # 4. Stepped tiers & actionable errors behavior probe
    probe = subprocess.run(
        [sys.executable, "-B", "-c", _CLIENT_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    default_timeout: float | None = None
    if probe.returncode == 0:
        try:
            default_timeout = float(json.loads(probe.stdout.strip())["default_timeout"])
        except (ValueError, KeyError, json.JSONDecodeError):
            default_timeout = None
    checks.append((
        "stepped-tiers-and-actionable-errors",
        probe.returncode == 0 and default_timeout is not None and default_timeout > 0,
        f"Tier 0/1/2 + actionable errors verified (DEFAULT_TIMEOUT_SECONDS={default_timeout})"
        if (probe.returncode == 0 and default_timeout is not None)
        else (probe.stderr.strip() or probe.stdout.strip())[:240],
    ))

    # 5. repo/docs/api.md synced resolving the timeout contradiction
    api_md = repo / "docs" / "api.md"
    api_text = api_md.read_text(encoding="utf-8", errors="replace") if api_md.is_file() else ""
    api_low = api_text.lower()
    if default_timeout is not None:
        t_int = str(int(default_timeout)) if default_timeout.is_integer() else str(default_timeout)
        t_float = f"{default_timeout:.1f}"
        matches_default = (t_int in api_text) or (t_float in api_text)
        no_stale_30 = ("30 seconds" not in api_low) or (default_timeout == 30.0)
        no_err9_doc = "err_9" not in api_low
        has_tier0_doc = "fetch(" in api_text and "headers_list" not in api_text
        docs_sync_ok = matches_default and no_stale_30 and no_err9_doc and has_tier0_doc
        checks.append((
            "docs-api-synced",
            docs_sync_ok,
            f"docs/api.md synced to DEFAULT_TIMEOUT_SECONDS={default_timeout} and Tier 0 fetch(url)"
            if docs_sync_ok
            else f"matches_default={matches_default}, no_stale_30={no_stale_30}, no_err9={no_err9_doc}, tier0_doc={has_tier0_doc}",
        ))
    else:
        checks.append(("docs-api-synced", False, "skipped: could not read DEFAULT_TIMEOUT_SECONDS from client.py"))

    # 6. Unit tests + 2 resilient mutations
    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut1_ok, mut1_detail = _eval_kit.check_mutation_caught(repo, "src/client.py", _reinject_ceremony)
    checks.append(("mutation-ceremony-caught", mut1_ok, mut1_detail))

    mut2_ok, mut2_detail = _eval_kit.check_mutation_caught(repo, "src/client.py", _reinject_cryptic_err9)
    checks.append(("mutation-cryptic-err9-caught", mut2_ok, mut2_detail))

    # 7. Gates intact + zero secrets/leaks
    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    all_texts = [final_text, ad2_text, catalog_text, api_text]
    sec_hits = _eval_kit.check_no_secrets(all_texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(all_texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
