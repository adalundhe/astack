#!/usr/bin/env python3
"""Objective post-run verifier for skill-create-adc."""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

REQUIRED_HEADINGS = (
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


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws)
    arch_dir = astack_home / "payments" / "architecture"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    repo_ads = sorted(repo.rglob("AD_*.md"))
    checks.append((
        "no-ad-in-repo",
        not repo_ads,
        "no AD files written inside repo" if not repo_ads else f"AD files found inside repo: {repo_ads}",
    ))

    ad1 = arch_dir / "AD_1.md"
    expected_sha = (ws / "program" / "ad1_sha256.txt").read_text(encoding="utf-8").strip()
    ad1_ok = ad1.is_file() and hashlib.sha256(ad1.read_bytes()).hexdigest() == expected_sha
    checks.append((
        "ad1-preserved",
        ad1_ok,
        "AD_1.md preserved untouched" if ad1_ok else "AD_1.md missing or modified",
    ))

    ad2 = arch_dir / "AD_2.md"
    draft2 = arch_dir / "AD_2.draft.md"
    ad2_exists = ad2.is_file() and not draft2.exists()
    checks.append((
        "ad2-published-no-draft",
        ad2_exists,
        "AD_2.md published and no draft leftover"
        if ad2_exists
        else f"ad2_exists={ad2.is_file()}, draft_leftover={draft2.exists()}",
    ))

    ad2_text = ad2.read_text(encoding="utf-8") if ad2.is_file() else ""
    fm, body = _parse_frontmatter(ad2_text)
    fm_ok = (
        fm is not None
        and fm.get("ad_number") == "2"
        and bool(fm.get("name"))
        and bool(fm.get("description"))
    )
    checks.append((
        "ad2-frontmatter",
        fm_ok,
        f"valid frontmatter (ad_number=2, name={fm.get('name')!r})" if fm_ok and fm else f"invalid frontmatter: {fm}",
    ))

    sections = _extract_sections(body)
    missing_headings = [h for h in REQUIRED_HEADINGS if not sections.get(h.lower())]
    checks.append((
        "ad2-required-headings",
        not missing_headings,
        f"all {len(REQUIRED_HEADINGS)} required headings present with content"
        if not missing_headings
        else f"missing or empty headings: {', '.join(missing_headings)}",
    ))

    status_text = sections.get("status", "")
    status_ok = bool(re.search(r"Accepted\s*\(\d{4}-\d{2}-\d{2}\)", status_text))
    checks.append((
        "ad2-status-accepted-date",
        status_ok,
        f"status accepted with date: {status_text.splitlines()[0] if status_text else ''}"
        if status_ok
        else f"Status must include 'Accepted (YYYY-MM-DD)', got: {status_text[:80]!r}",
    ))

    low = ad2_text.lower()
    grounded = ("ledger.py" in low or "idempotency_keys" in low) and "redis" in low and "24" in low
    checks.append((
        "ad2-grounded",
        grounded,
        "AD_2.md grounded in ledger/idempotency_keys, Redis alternative, and 24h TTL"
        if grounded
        else "AD_2.md missing key concrete details from decision-brief.md",
    ))

    sec = _eval_kit.check_no_secrets([ad2_text, final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
