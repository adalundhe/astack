---
name: research-this
description: "Research internal and external sources, verify quotes in place, and grade every finding A–F. Use before unsettled decisions, functionality trade-offs, or graded claims."
disable-model-invocation: true
---

# Research this

Investigate a question across internal and external sources. Quote every source, verify each quote in place, and grade every finding A–F.

## Look inside and outside

1. **Frame the question:** state the decision or limit this serves and what finding would change course. When hitting a wall, ask how other systems hit the target without sacrificing functionality.
2. **Search inside:** inspect code, measurements, data, logs, traces, docs, media, and past records. Check available CLIs, APIs, MCPs, and services (**analyze-environment**), publishing discovered tools to `TOOLS.md`.
3. **Search outside:** check standards, official docs, peer-reviewed papers (arXiv, Semantic Scholar, Crossref, PubMed), books, preprints, blogs, and forums.
4. **Cover both sides,** because internal habits miss external breakthroughs and external theory misses local constraints. State explicitly whenever one side has no sources.
5. **Parallelize lookups (Lead-only, per `lead`):** check `roles.researcher` (`provider`, `model`, `effort`) in `~/.config/astack/settings.json` when present. Fan out independent strands to read-only researchers. Collect competing implementations to prototype and measure (`swarm-hypothesis`, `ab-test`) alongside proven limits.

## Record and store what you find

- **Canonical research store (cross-OS):** persist external research, specs, and references under `$HOME/.astack/<project_name>/research/<topic_or_repo>` (`%USERPROFILE%\.astack\<project_name>\research\<topic_or_repo>` on Windows; `ASTACK_HOME` overrides). Resolve paths via `astack-tools research path <project_name> <topic> [--file <file>] --ensure` and check prior work via `astack-tools research list --project <project_name>`. Read-only researchers never edit repo files; return the draft and target `research/` path for the lead when you cannot write there directly.
- **Each source:** record its kind and exact location (`file:line`, URL + section, DOI, record ID, or command run). Note author, date, host, and shared origin (e.g. a vendor's docs and blog), and flag stale sources.
- **Each finding:** state one concrete claim with citations (source, exact quote, location). Mark inferred claims that go beyond what the source states.
- **Counterclaims:** list any source arguing against a finding. Rate unsourced doubts `strong`, `moderate`, or `weak`.

## Check the quotes

Verify every quote at its cited location. A quote is **found** when its words appear in order (`...` marks omissions). Ignore whitespace, case, quote/dash style, and edge punctuation. Mark uninspectable sources (PDFs, gated/JS pages, unreachable files) **unchecked** with the reason.

## Grade each finding

Source trust weights:

| Inside | Weight | Outside | Weight |
|---|---:|---|---:|
| measurement (command run + output) | 0.95 | standard or specification | 0.9 |
| code | 0.9 | peer-reviewed paper | 0.85 |
| data | 0.8 | product's own docs | 0.85 |
| logs, traces, metrics | 0.8 | book | 0.75 |
| document (README, design, notes) | 0.7 | preprint, news | 0.6 |
| past records (conversations, plans, runs) | 0.65 | blog, wiki | 0.5 |
| pictures, video, sound | 0.6 | forum, Q&A, issue | 0.4 |
| | | vendor on its own product | 0.35 |
| | | any other web page | 0.3 |
| | | social media | 0.25 |

Multiply any out-of-date source's weight by `0.75`.

Citation verification multipliers:

| Citation check | Multiplier |
|---|---:|
| quote found where cited | 1.0 |
| quote + location, unchecked | 0.75 |
| quote without location, unchecked | 0.65 |
| image or non-text file, present | 0.7 |
| link or path only | 0.5 |
| nothing to follow | 0.2 |
| checked where cited, not found | 0.3 |
| dead link or missing file | 0.1 |

Compute each finding's score:

1. **Per-citation contribution:** `source_weight × citation_multiplier`.
2. **Deduplicate by origin:** count citations from one site, file, DOI, or vendor once at their highest value. Deduplication matters because ten pages from one vendor are still one voice. Combine independent origins as `support = 1 − ∏(1 − origin_max)`.
3. **Discount inferences:** multiply `support` by `0.8` when a claim is inferred rather than stated.
4. **Combine counterclaims:** score sourced counterclaims the same way. For unsourced doubts, use `strong = 0.6`, `moderate = 0.35`, `weak = 0.15`, combined as `against = 1 − ∏(1 − c)`.
5. **Final score:** `round(support × (1 − 0.8 × against) × 100)`.

| Grade | Score | Confidence |
|---|---|---|
| A | 85+ | high |
| B | 70–84 | good |
| C | 50–69 | moderate |
| D | 30–49 | low |
| F | < 30 | very low |

Examples: one verified product-doc quote scores **A** (`0.85 × 1.0 = 85`). The same quote unchecked scores **C** (`0.85 × 0.75 = 64`), and an unquoted blog link scores **F** (`0.5 × 0.5 = 25`).

## Present it

Report each finding with its grade, score, and one-line rationale (e.g. `"2 independent sources (code, standard); 2/2 quotes verified"`). Include quotes, verification status, counterclaims, and numbered sources. Never present a research claim without its sources and grade.

When `kiln` is available, record findings via `research_start`, `research_add`, and `research_get`, which verify quotes and compute identical grades.

**Done when:** both internal and external sides are covered, every quote is verified or marked unchecked, and every finding carries an A–F grade.

Referenced skills: `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`). Read any cited skill file before acting when its trigger applies.
