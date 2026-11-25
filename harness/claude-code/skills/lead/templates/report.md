# Lane report

A worker's final message, in this format. Losses come first; "none" where a section is empty. The worker agent
carries the same format, so change both together.

```
RESULT: DONE | NOT DONE: <what is missing, in one line>

LOSSES
- <what failed, wasn't done, or couldn't be checked>

MERGED
- <sha> on <target>: <what it does>. Checks: `<command>` -> <result>

PUSHED, NOT MERGED
- <branch> @ <sha>: <its state, and what is left>

EVIDENCE
- <the done-when check>: `<command>` -> <result>

DECISIONS
- <the question, rejected theory, or failed/reverted fix attempt> -> <the choice or why rejected>: <the options or approach tried>; settled by <an earlier decision | the repository | research | an A/B | a proof of concept | failing test/repro>; evidence: <numbers, link or path>

SIDE FINDINGS (left alone)
- <one line each>

NEEDS THE PERSON
- <what only they can do or decide, why, and what you tried first>

NEXT
- <the first thing a successor does>
```

- RESULT comes first: a run that ends with the deliverable unbuilt has failed, and says so up front.
- LOSSES come before wins: the lead plans the successor from what is missing.
- MERGED carries its checks: the lead verifies every claimed merge, and the SHA and commands make that quick.
- SIDE FINDINGS stand apart: they are logged, not worked.
- DECISIONS lists every choice—including rejected theories and failed/reverted fix approaches or attempts—with what settled or disproved it. The lead logs each as a `decided:` line, passes them to post-fix reviewers, and folds key lessons into `make-it-stick`.
- NEEDS THE PERSON holds only what nothing else could settle; the lead tries again before asking.
