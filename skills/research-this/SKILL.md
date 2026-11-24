---
name: research-this
description: "Research a question inside the work (code, data, logs, docs, past records) and outside it (standards, papers, official docs, the web): quote every source, check the quotes, and grade each finding A to F the same way every time. Use before a decision the repository can't settle, when a claim needs evidence, and whenever you present what you found."
---

# Research this

Find out what's known about a question, quote where you found it, check the quotes, and grade every finding.

## Look inside and outside

1. **Frame the question:** the decision it serves, and what answer would change it.
2. **Search inside:** code, data, logs, traces and metrics, documents, pictures and recordings on the machines you work on, and past records such as earlier conversations, plans, CI runs and deployments.
3. **Search outside:** standards and official docs, papers (arXiv, Semantic Scholar, Crossref, PubMed), books, news, blogs and forums.
4. **Cover both sides.** Research is done only with sources from inside and outside, or a stated reason why one side has none.
5. **Split the search** across subagents, one per strand, and collect the competing implementations worth building and measuring.

## Record what you find

- **Each source:** its kind (from the table below) and exactly where it is: a file and its lines, a URL and its section, a DOI, a record's ID, or, for a measurement, the command you ran. Add its author, date, the machine it's on, and its origin (who stands behind it, when several sources share one, like a vendor's docs and its blog) where you know them. Mark it out of date if it is, for this question.
- **Each finding:** one claim, with its citations: the source, the exact words quoted, and where they are. Say when a claim is your inference rather than something a source states.
- **Counterclaims:** each source that argues against a finding, or, if you have doubts but no source, how strong they are: strong, moderate or weak.

## Check the quotes

Look for each quote where its citation says it is. It counts as found if its words appear there in order, ignoring spacing, case, curly versus straight quotes and dashes, and punctuation at either end; `...` stands for words left out. What you can't read (a PDF, a page drawn by scripts or behind a sign-in, a file on a machine you can't reach) stays unchecked, with the reason.

## Grade each finding

How far a source is taken at its word:

| Inside | | Outside | |
|---|---|---|---|
| a measurement (a command run, and its output) | 0.95 | a standard or specification | 0.9 |
| code | 0.9 | a peer-reviewed paper | 0.85 |
| data | 0.8 | a product's own docs | 0.85 |
| logs, traces, metrics | 0.8 | a book | 0.75 |
| a document (README, design, notes) | 0.7 | a preprint, news | 0.6 |
| past records (conversations, plans, runs) | 0.65 | a blog, a wiki | 0.5 |
| pictures, video, sound | 0.6 | a forum, Q&A, an issue | 0.4 |
| | | a vendor on its own product | 0.35 |
| | | any other web page | 0.3 |
| | | social media | 0.25 |

An out-of-date source counts 0.75 of its weight.

How much a citation counts:

| The citation | Counts |
|---|---|
| its quote found where it says | 1.0 |
| a quote and where it is, not checked | 0.75 |
| a quote without where it is, not checked | 0.65 |
| a picture or other non-text file, present | 0.7 |
| a link or a path only | 0.5 |
| nothing to follow | 0.2 |
| looked for where it says, and not there | 0.3 |
| a dead link or a missing file | 0.1 |

Then, for each finding:

1. **Each citation lends** its source's weight times what the citation counts.
2. **Sources with one origin count once,** at their strongest: one site, one file, one DOI, or an origin you named. Independent origins add up: support is 1 minus the product of (1 minus each origin's strongest).
3. **An inferred claim** keeps 0.8 of its support.
4. **Counterclaims weigh the same way** by their own sources; with none, strong is 0.6, moderate 0.35 and weak 0.15. Together, against is 1 minus the product of (1 minus each).
5. **Score** is support × (1 − 0.8 × against) × 100, rounded.

| Grade | Score | Confidence |
|---|---|---|
| A | 85 and up | high |
| B | 70 to 84 | good |
| C | 50 to 69 | moderate |
| D | 30 to 49 | low |
| F | below 30 | very low |

For example, one product doc, quoted and found, is an A (0.85 × 1.0 = 85). The same quote, unchecked, is a C (0.85 × 0.75 = 64). A blog post linked without a quote is an F (0.5 × 0.5 = 25).

## Present it

Give each finding with its grade, its score and why ("2 independent sources (code, a standard); 2 of 2 quotes found where cited"), its quotes and how each check came out, and its counterclaims; then the sources, numbered. Never present a claim without its sources and its grade.

Where kiln is available, record the research there (`research_start`, `research_add`, `research_get`): it checks the quotes and grades the findings for you, the same way.
