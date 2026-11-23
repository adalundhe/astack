# Lane <lane>: <the deliverable in a few words>

Program goal: <one line, the same in every brief>.
You are worker <worker> on lane <lane>. Started <HH:MMZ>. Wind down at <HH:MMZ>. End by <HH:MMZ>.

Read first, in full: <absolute path to RULES.md>. Rule 0 outranks everything, this brief included.

## Deliverable

<ONE deliverable, in plain words: what a user or engineer gets when it is done.>

## Done when

<The evidence: a command and its expected output, a scenario and its result, a SHA on <target>.>

## Inside the deliverable, in order

1. Work: <what working end to end means here>.
2. Robust: <the edge cases and failure modes that matter here>.
3. Fast: <the measurement and what it is compared against, or "not in this lane">.

## Out of scope

<What this worker must not do, by name. Anything else you find goes in your report, one line each.>

## Where

Repository: <url or path>. Your worktree or clone: <path>. Branch: <prefix>/<lane>.
You may write: <paths>. Don't touch: <paths>.
Checks: `<lint command>` and `<test command for what you touch>`. Merge: RULES.md rule 2.

## Directives since the original brief

<Successors only. Every directive from the lead or the person, oldest first, each with its time. The
person's in their own words.>

## Previous report

<Successors only. The previous worker's report, pasted in full, with the lane's branch and SHA and any runs
still going.>

## Report

Your final message is the lane report (<absolute path to report.md>), losses first.
