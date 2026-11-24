---
name: watch-pr
description: "Take reviewed work through its pull request: open it, wait on CI and feedback without checking by hand, fix what fails, address every comment, flag the person every 24 hours it stays open, hand over at the time limit, and tell the lead when it is ready to merge. Use once a reviewer has cleared your work, and when you take over another worker's PR."
---

# Watch a PR

Take a pull request to ready-to-merge, then hand it to the lead.

Ready means CI fully green, every comment from people and agents addressed, and every required approval in. The lead merges it.

1. **Open it** only after a reviewer clears the work: no blockers, and every suggestion and nit fixed, answered, or refuted (**worrywart**). Describe it in plain words: the problem, what changed, how it was tested, and how to check it.
2. **Keep its marker.** In the program folder, `watch/<PR number>.md` holds the PR's link, branch and head commit, its CI state, each comment and its status, when it opened, and when the next flag is due. Update it at every event: the next worker picks up from it.
3. **Wait on events, not by hand.** Run a watcher in the background that returns when CI finishes, a comment or review arrives, or the next flag falls due (**automate-this**). Never spend turns re-checking.
4. **When CI fails,** fix it. If the failure isn't yours (main already broken, a failed scan, a dependency, a flaky check), fix it anyway, as its own PR (**leave-it-better**), and keep this one moving.
5. **When feedback arrives,** address it at once (**address-feedback**): fix it, answer it, or refute it with evidence. Every comment ends resolved.
6. **Every 24 hours** it stays open, flag the person: a comment on the PR that mentions them and says what it waits on, and a line in the program's log.
7. **At your time limit,** bring the marker up to date, tell the lead where the PR stands, and end. The lead's next worker continues from the marker.
8. **When it's ready,** tell the lead and stop. Never merge it yourself: the lead merges.
