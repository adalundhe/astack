# <program> lane log

One hour per lane. Work, then robust, then fast. Merge after lint and the tests a lane touched.
Rules: <absolute path to RULES.md>.
Stamp every line with `date -u +%H:%MZ`, never an estimate. Append only: correct a line with a new line.

## Line formats

```
<HH:MMZ> started <lane> (<agent id>) | hour ends <HH:MMZ> | deliverable: <one line> | done when: <evidence>
<HH:MMZ> steer <lane>: <the directive, one line>
<HH:MMZ> person: "<their words, verbatim>" -> <what changed; lanes told>
<HH:MMZ> decided by data: <the question> -> <the answer> (<the numbers, and where they are>)
<HH:MMZ> rules rev: <what changed in RULES.md, and why>; told: <lanes>
<HH:MMZ> ended <lane>: MERGED <sha> (verified: <how>) | NOT MERGED <branch>@<sha>; losses: <...>; asks: <...>
<HH:MMZ> successor <lane> started from <previous lane>'s report | hour ends <HH:MMZ>
<HH:MMZ> correction: <what an earlier line got wrong, and the right value>
```

## Example

```
14:02Z started search-1 (a3f9c2e1) | hour ends 15:02Z | deliverable: prefix search returns ranked results from the new index | done when: `make test-search` passes and the three sample queries in docs/search.md return their documented rows
14:31Z steer search-1: stop the latency A/B; the deliverable doesn't work end to end yet
14:58Z ended search-1: NOT MERGED search/index@9c41d07; losses: ties unranked, 2 of 3 sample queries pass; asks: none
14:59Z successor search-2 started from search-1's report | hour ends 15:59Z
15:12Z person: "ties break by recency" -> search-2 told
15:47Z ended search-2: MERGED 5be2a10 (verified: on origin/main, `make test-search` green on main, 3 of 3 sample queries); losses: none
```

## Findings

One line each. Findings are not lanes. One becomes work only when it blocks a deliverable or the person makes it one.

- <HH:MMZ> <lane>: <finding>

## Waiting on the person

- <HH:MMZ> asked: "<the question, as asked>"

## Log

