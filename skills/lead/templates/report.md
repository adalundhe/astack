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

SIDE FINDINGS (left alone)
- <one line each>

DECISIONS FOR THE PERSON
- <Today X happens. Option A gains ..., costs .... Option B .... I recommend A because ....>

NEXT
- <the first thing a successor does>
```

- RESULT comes first: a run that ends with the deliverable unbuilt has failed, and says so up front.
- LOSSES come before wins: the lead plans the successor from what is missing.
- MERGED carries its checks: the lead verifies every claimed merge, and the SHA and commands make that quick.
- SIDE FINDINGS stand apart: they are logged, not worked.
- DECISIONS are plain choices: the lead asks the person these outright.
