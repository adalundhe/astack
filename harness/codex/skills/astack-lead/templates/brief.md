# <lane>: <the deliverable in a few words>

Program goal: <one line, the same in every brief>.
You are <worker>, building lane <lane>. Started <UTC>. Wind down at <UTC>. End by <UTC>.
Read first, in full: <path to RULES.md> (and <path to TOOLS.md> if present). Rule 0 outranks everything, this brief included.
First command, before you open any file: `astack-tools skills list --role <worker|reviewer|researcher>`. Then run `astack-tools skills get <skill>`, one per call, for every required skill and for: <skill>, <skill>. A skill you cite and didn't load is a loss.

Deliverable: <ONE thing, in plain words: what a user or engineer gets>.
Done when: <the evidence: a command and its output, a scenario and its result, a SHA on <target>>.
Order: work: <what working end to end means here>. Robust: <the failures that matter here>. Fast: <the
measurement, or "not in this lane">.
Out of scope: <named>. Anything else you find gets one line in your report.
Where: isolated Slates in-memory VFS volume (`slates`, https://github.com/hyper-light/slates, preferred when available) or git worktree <path>, branch <branch>. Write only <paths (including impacted docs when scoped to this lane)>. Checks: `<lint command>`, `<test command>`.
Prior rejected theories / failed approaches (`decided:` entries, if any): <what was already disproved and why, so you don't repeat dead ends>.

Directives since the original brief (successors only): <oldest first, with their times; the person's verbatim>.
Previous report (successors only): <in full>.

Report: your final message, in the lane report format (<path to report.md>).
