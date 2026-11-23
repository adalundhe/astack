# Lane report

A lane's final message, in this format. Losses come first. A heading with nothing under it says "none".
The lane agent (`agents/lane.md`) carries the same format, so change both together.

```
RESULT: DONE | NOT DONE: <what of the deliverable is missing, in one line>

LOSSES
- <what didn't get done, what failed, what couldn't be checked; one line each>

MERGED
- <sha> on <target>: <what it does>. Checks: `<command>` -> <result>.

PUSHED, NOT MERGED
- <branch> @ <sha>: <the state it is in and what is left>.

EVIDENCE
- <the done-when check>: `<command>` -> <result>.

SIDE FINDINGS (left alone)
- <one line each>

DECISIONS FOR THE PERSON
- <Today X happens. Option A does ..., gains ..., gives up .... Option B .... I recommend A because ....>

NEXT
- <the first thing a successor does>
```

## Why this shape

- **RESULT first.** An hour that ends with the deliverable unbuilt is a failed hour, and the first line says so.
- **LOSSES before wins.** The lead plans the successor from what is missing, so it reads that first.
- **MERGED with its checks.** The lead verifies every claimed merge against the branch. The SHA and the commands make that quick.
- **SIDE FINDINGS apart.** They are logged, not worked. Keeping them apart keeps them from becoming scope.
- **DECISIONS as plain choices.** The lead asks the person these outright, in close to these words.
- **NEXT.** A successor starts from it, so the hand-over loses nothing.
