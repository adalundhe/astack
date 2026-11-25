<!-- astack lane log -->
# <program> lane log

Repository: <absolute path to the repository>
Rules: <absolute path to RULES.md>

One deliverable per lane, one time limit per worker. Write one line per event under Log: append, never rewrite,
and fix a wrong line with a correction line. The astack hook stamps each line with the UTC time as it is saved,
such as 2026-11-23T14:02Z. Without the hook, start each line with `date -u +%Y-%m-%dT%H:%MZ`; never with a
time from memory.

## Line formats

    started <worker> on <lane> (<agent id>) | branch <branch> | wind-down <UTC> | ends <UTC> | deliverable: <one line> | done when: <evidence>
    started <worker> on <lane> (<agent id>) | successor of <worker> | branch <branch> | wind-down <UTC> | ends <UTC> | deliverable: <one line> | done when: <evidence>
    started <reviewer> on <vector> (<agent id>) | role reviewer | model <provider>/<model> | wind-down <UTC> | ends <UTC> | scope: <scope>
    started <researcher> on <topic> (<agent id>) | role researcher | wind-down <UTC> | ends <UTC> | question: <one line>
    plan reviewed: <reviewer> (<agent id>) -> <verdict>; changed: <what, or none>
    check-in: <N> active | <what astack-status showed, and what you did>
    steer <agent>: <the directive>
    asked: "<the question, as asked>"
    person: "<their words, verbatim>" -> <what changed; agents told>
    decided: <the question> -> <the choice> (settled by <what>; evidence: <where>)
    rules rev: <what changed, and why>; told: <agents>
    verified <sha>: astack-verify-merge <result> | astack-check-gates <result> | <other checks>
    ledger: <vector> -> <astack-review-ledger state>
    ended <worker>: MERGED <sha> (verified) | NOT MERGED <branch>@<sha>; losses: <...>
    ended <reviewer>: <VERDICT>; blocking=<N> minor=<N> dropped=<N>
    ended <researcher>: <summary>; gaps: <...>
    closed <lane>: <the done-when, and its evidence>
    finding <worker>: <one line>
    correction: <what an earlier line got wrong, and the right value>

## Log

