---
name: challenge
description: "Peer-to-peer adversarial challenge between any agents (or against your own reasoning) to stress-test hypotheses, repeated fixes, diagnoses, designs, and implementations until every assumption is proven or conceded. Use whenever an approach, diagnosis, or choice needs rigorous pushback."
disable-model-invocation: true
---

# Challenge

Adversarially interrogate a hypothesis, diagnosis, design choice, repeated fix, or implementation—peer to peer, regardless of agent role—until every load-bearing assumption is backed by evidence or revised.

Invoke `/challenge` whenever fixes keep recurring in the same area, a root-cause theory or benchmark explanation feels convenient, a design adds complexity on untested assumptions, or any agent's claim (including your own) hasn't been falsified.

## Rules of engagement

- **Role-agnostic and peer-to-peer:** a worker challenges a lead's plan or diagnosis on the exact same footing as a reviewer challenging a worker's diff or a lead challenging a report. Rank and seniority carry zero weight—only evidence counts.
- **Adversarial, never polite rubber-stamping:** your job as challenger is to break the claim, not validate it. Don't soften real flaws into hedged suggestions.
- **No contrarianism for sport:** every challenge must name a concrete falsifiable assumption, failure scenario, or rival hypothesis/design.

## Challenge protocol

1. **Pin down the claim.** Restate the target hypothesis, root-cause diagnosis, design choice, or implementation in 1–2 sentences and list the explicit assumptions that must hold for it to be right.
2. **Attack from every angle that applies:**
   - **Root cause vs. symptom:** especially on repeated fixes—why didn't the prior fix stop this, and what upstream defect or structural flaw keeps producing it?
   - **Falsification test:** what concrete input, trace, fault, or experiment would *disprove* this diagnosis or break this implementation?
   - **Assumed constraints:** which limits are real (measured or cited via **rtfm** / **research-this**) versus inherited habits, outdated context, or convenience?
   - **Rival hypothesis or simpler alternative:** propose at least one concrete competing explanation or simpler design, and walk a specific scenario showing where the two diverge.
   - **Trust-ladder check:** state which rung of **prove-it** the claim actually sits on (memory/reasoning, unrun code, read-only inspection, or real execution/measurement).
3. **Force an evidenced defense.** The defending agent must answer each attacked assumption with concrete evidence—a runnable test, measurement, trace, exact `file:line`, or graded **research-this** finding. Restating the original rationale or citing authority doesn't count. Any undefended assumption is **conceded**.
4. **Settle disputes with reality, not debate.** Wherever a quick reproduction, prototype (**play-with-me**), or controlled experiment (**ab-test**) can decide between two sides, run it instead of arguing another round.
5. **Close with an explicit verdict:**
   - **Upheld:** the claim survived falsification—cite the proof.
   - **Revised:** specific assumptions failed—state what changed in the diagnosis, design, or implementation.
   - **Rejected:** replaced by a concrete alternative—state why it won.

Record any settled choice as a `decided:` entry (in `LANES.md` or your report) so the same argument isn't relitigated later.
