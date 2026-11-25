#!/usr/bin/env python3
"""Objective post-run verifier for lookback-and-lookup-lessons."""
from __future__ import annotations

from pathlib import Path
import re
import sys

REQUIRED_FM = ("lesson:", "project:", "related_projects:", "keywords:", "status:", "created:", "updated:")
REQUIRED_SECTIONS = (
    "## Overview",
    "## Skills and tools used",
    "## Details",
    "## Successes",
    "## Issues",
    "## Best path & guards",
    "## References",
)
UTC_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z\b")


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    astack_home = ws / "program" / "astack_home"

    if (repo / "lessons").exists() or (repo / "LESSONS.md").exists() or list(repo.rglob("LESSON.md")):
        print("FAIL: lesson file created inside repository", file=sys.stderr)
        return 1

    stale = astack_home / "billing" / "lessons" / "legacy-xml-parser" / "LESSON.md"
    if stale.is_file():
        stext = stale.read_text(encoding="utf-8")
        if "status: superseded" not in stext and "status: retired" not in stext:
            print("FAIL: stale legacy-xml-parser lesson was left active without superseding or deleting", file=sys.stderr)
            return 1

    lessons_dir = astack_home / "billing" / "lessons"
    candidates = [
        p for p in lessons_dir.glob("*/LESSON.md")
        if p.parent.name != "legacy-xml-parser"
    ] if lessons_dir.is_dir() else []
    if not candidates:
        print("FAIL: no new LESSON.md written under program/astack_home/billing/lessons/", file=sys.stderr)
        return 1

    for lesson_file in candidates:
        text = lesson_file.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        if not m:
            print(f"FAIL: {lesson_file} missing YAML frontmatter", file=sys.stderr)
            return 1
        fm = m.group(1)
        for key in REQUIRED_FM:
            if key not in fm:
                print(f"FAIL: {lesson_file} missing frontmatter key {key}", file=sys.stderr)
                return 1
        if not UTC_RE.search(fm):
            print(f"FAIL: {lesson_file} missing UTC YYYY-MM-DDTHH:MMZ timestamp", file=sys.stderr)
            return 1
        for sec in REQUIRED_SECTIONS:
            if sec not in text:
                print(f"FAIL: {lesson_file} missing section {sec}", file=sys.stderr)
                return 1

    print(f"PASS: wrote {len(candidates)} valid LESSON.md file(s) under ASTACK_HOME and audited stale lesson")
    return 0


if __name__ == "__main__":
    sys.exit(main())
