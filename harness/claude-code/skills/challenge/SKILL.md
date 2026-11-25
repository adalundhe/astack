---
name: challenge
description: "Adversarially stress-test hypotheses, diagnoses, designs, and fixes until assumptions are proven or conceded. Use whenever a claim or choice needs rigorous pushback."
disable-model-invocation: true
---

# Challenge

Interrogate a hypothesis, diagnosis, design choice, repeated fix, or implementation peer to peer until every load-bearing assumption is proven or revised. For pushing back on external PR comments or review threads, use `worrywart` instead.

Run a challenge whenever fixes recur in the same area, a diagnosis feels convenient, or a claim remains unfalsified.

## Rules of engagement

- **Role-agnostic and peer-to-peer:** a worker challenges Lead's plan on the same footing as a reviewer challenging a worker's diff. Rank carries zero weight—only evidence counts. Non-Lead agents raise challenges inline in their report or escalation without spawning subagents.
- **Adversarial, never polite rubber-stamping:** your job as challenger is to break the claim, not validate it. Never soften real flaws into hedged suggestions.
- **No contrarianism for sport:** every challenge must name a falsifiable assumption, failure scenario, or rival hypothesis.

## Challenge protocol

1. **Pin down the claim.** Restate the target diagnosis, design, or implementation in 1–2 sentences. List every assumption that must hold for it to be right.
2. **Attack from every angle that applies:**
   - **Root cause vs. symptom:** on repeated fixes, ask why the prior fix missed this. Name the upstream defect reproducing it.
   - **Falsification test:** name the input, trace, fault, or experiment that would *disprove* the diagnosis or break the implementation.
   - **Assumed constraints:** separate real limits (measured or cited via `rtfm` / **research-this**) from inherited habits or convenience.
   - **Rival hypothesis or simpler alternative:** propose a concrete rival explanation or simpler design. Walk a scenario showing where the two diverge.
   - **Trust-ladder check:** name the rung on **prove-it**'s five-rung ladder:
     1. reasoning or memory;
     2. unverified code or mocks/proxies;
     3. read-only code or docs;
     4. authoritative external references;
     5. running and measuring the real system.
3. **Force an evidenced defense.** The defender must answer each attacked assumption with evidence: a runnable test, measurement, trace, `file:line`, or graded **research-this** finding. Restating rationale or authority never counts. Any undefended assumption is **conceded**.
4. **Settle disputes with reality, not debate.** Run a quick repro, prototype (**play-with-me**), or controlled experiment (**ab-test**) instead of arguing another round.
   - **Stall guard:** if a round produces no new runnable evidence, stop debating immediately. Escalate surviving options with your recommendation.
5. **Close with an explicit verdict:**
   - **Upheld:** the claim survived falsification—cite the proof.
   - **Revised:** specific assumptions failed—state what changed.
   - **Rejected:** replaced by a concrete alternative—state why it won.

**Done when:** the verdict and proof are logged as `decided:` (in `LANES.md` or your report) so the argument is never relitigated.

Referenced skills: `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `play-with-me` (`${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.
