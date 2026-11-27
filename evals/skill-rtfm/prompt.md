---
description: "Check repository docs and git history before asking humans: explain why MAX_RETRIES is 3 with exact docs/AD-007.md and commit SHA citations instead of telling the user to ask the author."
expected_outcome: "Reads rtfm/SKILL.md, inspects repo/docs/AD-007.md, repo/src/retry.py, and git log in ./repo, answers directly that MAX_RETRIES is capped at 3 because the upstream API enforces a strict 429 ban on the 4th attempt, cites docs/AD-007.md and the exact commit SHA, tells the user not to ask the author, and leaves ./repo clean."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Answer the question in `./program/question.md` against `./repo`.

Check existing repository documentation, source code, and git history before escalating or telling me to ask anyone. Reply directly (in your final response or `./program/ANSWER.md`) with exact source and commit citations, and leave `./repo` untouched.
