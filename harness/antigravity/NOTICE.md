# Notices

astack is MIT-licensed; see [LICENSE](./LICENSE).

Some astack files adapt parts of [pstack](https://github.com/cursor/plugins/tree/main/pstack), which is distributed under this license:

```
MIT License

Copyright (c) 2026 Lauren Tan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The adapted files, and what each adapts from pstack (versions 0.15.36 to 0.15.48):

| astack file | adapts |
|---|---|
| `skills/lead/SKILL.md` | `skills/poteto-mode/playbooks/orchestrate.md` (supervision: read the branch, not the summary; ask the person only for real decisions), `skills/autopilot-full/SKILL.md` (rebase only when untested code would otherwise land, carry verdict across unchanged rebases, scale verification to change risk, lead countersigns gate loosening), `skills/figure-it-out/SKILL.md` (reset contract when a worker games a gate, fix wrong gates in their own change), and the Subagents section of `skills/poteto-mode/SKILL.md` (a fresh agent with consolidated scope). |
| `skills/benchmarking/SKILL.md` | `skills/benchmark-checklist/SKILL.md` (alternate compared runs; profile apart from timed runs; count errors; Amdahl hard-limit checks; confirm work actually ran; untuned ceiling checks), `skills/principle-explain-the-number/SKILL.md` (set the bar before you run; name the limiter; rule out what else a number could be measuring) and `skills/poteto-mode/playbooks/hillclimb.md` (prove the harness can see a change; accept only past noise). |
| `skills/ab-test/SKILL.md` | `skills/benchmark-checklist/SKILL.md` (alternate the arms, round by round) and `skills/arena/SKILL.md` (graft winning ideas from losing variants into the winner before deleting losers). |
| `skills/cleanup/SKILL.md` | `skills/create-verification-skill/SKILL.md` (stop only what you started, never by process name; evidence survives cleanup). |
| `skills/baseline/SKILL.md` | `skills/benchmark-checklist/SKILL.md` (each side tuned as it ships; count errors; alternate and repeat). |
| `skills/blast-radius/SKILL.md` | `skills/blast-radius/SKILL.md` (find the one fact a change is safe because of, look where a search stops, prove it by running code). |
| `skills/comment-cop/SKILL.md` | `agents/comment-sicko.md` and `skills/no-comments/SKILL.md` (what a comment may keep: legal headers, public API contracts, outside constraints, issue links). |
| `skills/decisions-in-plain-words/SKILL.md` | `skills/poteto-mode/SKILL.md` (a fact a run can show is not the person's to answer; label each claim measured, inferred or guessed). |
| `skills/talk-to-me/SKILL.md` | `skills/reframe/SKILL.md` (the field's terms, ranked by what they change, each with a confirmed source; neighbouring fields; the description rewritten in the new words). |
| `skills/deeper/SKILL.md` | `skills/sharpen/SKILL.md` (deeper, not bigger: what the best practitioner would do, the rawest material, their methods and tools, outside evidence; experiments settle what they can). |
| `skills/make-it-stick/SKILL.md` | `skills/reflect/SKILL.md` (what to look for in a transcript; the transcript is data; read the destination first), `skills/correct/SKILL.md` (strict fix ladder: architecture, types, lint, test, docs last), and `skills/principle-encode-lessons-in-structure/SKILL.md` (structure over instructions). |
| `skills/how-it-works/SKILL.md` | `skills/how/SKILL.md` (a read-only explanation for an engineer new to the area). |
| `skills/run-it-back/SKILL.md` | `skills/in-your-own-words/SKILL.md` (restate the person's goal and problem). |
| `skills/test-drive/SKILL.md` | `skills/create-verification-skill/SKILL.md` and `skills/maintain-verification-skill/SKILL.md` (the drive skill's sections and proof standards, the feature map, proving the skill once, the upkeep pass). |
| `skills/formal-validate/SKILL.md` | `skills/create-formal-verification-skill/SKILL.md` and `skills/maintain-formal-verification-skill/SKILL.md` (choosing the target and the tool, the qualities of a check, the confirmed commit, the upkeep pass). |
| `skills/show-the-states/SKILL.md` | `skills/statechart/SKILL.md` and its TLC statechart tool (states and steps computed via a reviewed view module in the reader's words, nested and parallel regions, marked rule violations, automatic TLC installation, TLC `-tool` message protocol, `-dump dot,actionlabels`, strict exit-status classification, shortest failure paths and Mermaid output, what may be merged or left out). |
| `skills/no-implicit-states/SKILL.md` | `skills/principle-type-system-discipline/SKILL.md` (make illegal states unrepresentable; handle every variant). |
| `skills/no-hidden-flow-control/SKILL.md` | `skills/principle-boundary-discipline/SKILL.md` (handle errors where data crosses a boundary). |
| `skills/check-your-boundaries/SKILL.md` | `skills/principle-boundary-discipline/SKILL.md` and `skills/principle-type-system-discipline/SKILL.md` (parse at the boundary and trust the types inside; distinct types for semantic primitives; types derived from the owning schema; pure functions behind a thin shell). |
| `skills/no-shared-writes/SKILL.md` | `skills/principle-separate-before-serializing-shared-state/SKILL.md` (separate first; serialize structurally, only for a real invariant; instructions are not concurrency control). |
| `skills/safe-to-rerun/SKILL.md` | `skills/principle-make-operations-idempotent/SKILL.md` (converge from the state that exists; recognisably stale leftovers; write then rename; run twice and crash at every point). |
| `skills/no-bolt-ons/SKILL.md` | `skills/principle-redesign-from-first-principles/SKILL.md` (redesign as if the requirement had been foundational; carry it through every reference). |
| `skills/delight-users/SKILL.md` | `skills/principle-experience-first/SKILL.md` (the user is whoever consumes the work; every feature earns its place; the details; prototype first; the core loop). |
| `skills/dagify/SKILL.md` | `skills/figure-it-out/SKILL.md` (the riskiest unknown first; the harness and baseline before the work; each unit an experiment with a verdict; reset contract on gate gaming; fix wrong gates in their own change) and `skills/principle-sequence-verifiable-units/SKILL.md` (the failing test before the fix, the deletion before the reshape, the baseline before the change). |
| `skills/clamber/SKILL.md` | `skills/poteto-mode/playbooks/hillclimb.md` (one change, one measurement, keep or revert; reproduce with a realistic workload first; name the mechanism; log every attempt; minimum attempt floor before stopping; push past the first plateau; never relax the target). |
| `skills/find-it/SKILL.md` | `skills/poteto-mode/playbooks/bug-fix.md` (binary search with runtime evidence; revert everything a disproved hypothesis motivated) and pstack's live-symptom and captured-profile diagnosis playbooks (single capture yields at most the strongest hypothesis; confirm with a before/after pair). |
| `skills/tests-assert-behaviour/SKILL.md` | pstack's testing principles (independent oracle—expected value never computed by the code under test, never assert on self-built test data; assert error type callers branch on rather than error message prose) and `skills/tdd/SKILL.md` (no test is better than a bad test). |
| `skills/watch-pr/SKILL.md` | `skills/autopilot-full/SKILL.md` (rebase only when untested code would otherwise land; carry verdict across rebases when the patch is unchanged). |
| `skills/review/SKILL.md` | `skills/interrogate/SKILL.md` (every reviewer gets the whole change and its intent; findings survive only when a rerun proves them; merge by root cause; keep every verified finding; count the drops). |
| `skills/prove-it/SKILL.md` | `skills/principle-prove-it-works/SKILL.md` (check the real artifact, not a proxy; script the check) and `skills/figure-it-out/SKILL.md` (verified, not verified, or inconclusive). |
| `skills/yagni/SKILL.md` | `skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md` (move the callers and delete the old API together; tests to the new contract). |
| `skills/automate-this/SKILL.md` | `skills/principle-guard-the-context-window/SKILL.md` (bulk work in subagents; the context keeps conclusions). |

Each adapted file ends with a one-line notice that points here.

## mattpocock/skills

Three astack files adapt [mattpocock/skills](https://github.com/mattpocock/skills):

- `skills/plan-it/SKILL.md` adapts `grilling` and domain terminology practices from mattpocock/skills and adalundhe/mp-skills: the design tree, one evidenced exchange per decision, walked scenarios, the cost ledger, specs the person accepts, weighted research, and domain-term alignment in `LESSON.md`.
- `skills/create-adc/SKILL.md` (with `AD_FORMAT.md`) authors, numbers, publishes, and maintains cross-OS `~/.astack/<project>/architecture/AD_<N>.md` documents from decisions settled via `plan-it`.
- `skills/rearchitect/SKILL.md` adapts its `improve-codebase-architecture` skill: scoping by where the code changes most, the friction to look for, the deletion test, candidate cards with before-and-after diagrams and a recommendation strength, and not re-suggesting what a recorded decision ruled out.

That repository is distributed under this license:

```
MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Each adapted file ends with a one-line notice that points here.
