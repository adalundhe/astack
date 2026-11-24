---
name: research-this
description: "Research a question across internal sources (code, logs, data, docs) and external sources (specs, papers, official docs, web), verify quotes against their citations, and grade each finding A–F. Use before unsettled decisions, before accepting a functionality trade-off, or when claims need graded evidence."
disable-model-invocation: true
---

# Research this

Investigate a question across internal and external sources, quote every source, verify each quote in place, and grade every finding A–F consistently.

## Look inside and outside

1. **Frame the question:** state the decision or suspected limit this serves and what finding would change your approach. When hitting a performance or design wall, explicitly ask how other systems hit the target without sacrificing functionality or guarantees.
2. **Search inside:** code, measurements, data, logs, traces, metrics, docs, media on your machines, and past records (earlier conversations, plans, CI runs, deployments).
3. **Search outside:** standards and official docs, peer-reviewed papers (arXiv, Semantic Scholar, Crossref, PubMed), books, preprints/news, blogs, and forums.
4. **Cover both sides.** Research isn't complete without both internal and external sources—or an explicit reason why one side has none.
5. **Parallelize lookups:** when subagents are available, fan out independent strands to read-only subagents, collecting viable competing implementations to prototype and measure (**explore-the-limits**, **ab-test**) alongside any proven limits.

## Record what you find

- **Each source:** record its kind (from the table below) and exact location: `file:line`, URL and section, DOI, record ID, or the exact measurement command run. Include author, date, host machine, and origin (shared authority across multiple sources, such as a vendor's docs and blog) when known. Flag out-of-date sources for this question.
- **Each finding:** one concrete claim with its citations (source, exact quoted text, and location). Explicitly mark inferred claims that go beyond what the source directly states.
- **Counterclaims:** list any source arguing against a finding; if you have doubts without a source, rate them `strong`, `moderate`, or `weak`.

## Check the quotes

Verify every quote at its cited location. A quote counts as **found** if its words appear in order (ignoring whitespace, case, curly vs. straight quotes/dashes, and edge punctuation; `...` marks omitted words). Anything you can't inspect directly (PDFs, JS-rendered or gated pages, unreachable files) stays **unchecked** with the reason noted.

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
2. **Deduplicate by origin:** multiple citations sharing one origin (same site, file, DOI, or named origin) count once at their highest value. Combine independent origins as `support = 1 − ∏(1 − origin_max)`.
3. **Discount inferences:** if the claim is inferred rather than directly stated, multiply `support` by `0.8`.
4. **Combine counterclaims:** score sourced counterclaims the same way; for unsourced doubts, use `strong = 0.6`, `moderate = 0.35`, `weak = 0.15`. Combine as `against = 1 − ∏(1 − c)`.
5. **Final score:** `round(support × (1 − 0.8 × against) × 100)`.

| Grade | Score | Confidence |
|---|---|---|
| A | 85+ | high |
| B | 70–84 | good |
| C | 50–69 | moderate |
| D | 30–49 | low |
| F | < 30 | very low |

Examples: one product doc with a verified quote scores **A** (`0.85 × 1.0 = 85`); the same quote unchecked scores **C** (`0.85 × 0.75 = 64`); a blog link with no quote scores **F** (`0.5 × 0.5 = 25`).

## Present it

Report each finding with its grade, score, and one-line rationale (e.g. `"2 independent sources (code, standard); 2 of 2 quotes verified"`), its quotes and verification status, and any counterclaims, followed by numbered sources. Never present a research claim without its sources and grade.

When `kiln` is available, record findings through it (`research_start`, `research_add`, `research_get`), which checks quotes and computes grades identically.
