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

SKILLS READ
- <skill>: <what it changed in the work>

DECISIONS
- <the question> -> <the choice>: <the options>; settled by <an earlier decision | the repository | research | an A/B | a proof of concept>; evidence: <numbers, link or path>

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
- SKILLS READ lists each skill opened, so the lead can tell a cited skill from a read one.
- SIDE FINDINGS stand apart: they are logged, not worked.
- DECISIONS lists every choice, not only measured ones, with what settled it. The lead logs each.
- NEEDS THE PERSON holds only what nothing else could settle; the lead tries again before asking.
