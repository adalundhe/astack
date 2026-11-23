---
name: no-picked-constants
description: "Keep picked numbers out of code: every limit, size, threshold, timeout, rate, weight or interval the system acts on is learned where it runs or derived from a cited source, and the design says which. Use when you write, review or propose a number the system acts on."
---

# No picked constants

Every value the system acts on (a limit, size, threshold, timeout, rate, weight, interval or cap) is learned where it runs or derived from a cited source. A guess is not a value, even one labelled "a starting point".

Ada's words: "We do not support arbitrary constants. We support learned and data derived values."

**Why:** a picked number is right for the machine and the load it was picked on, and wrong everywhere else. It also hides the real question: what the value depends on.

- **Learn it at runtime when it depends on the machine or the load**: an estimator of what the system observes (as TCP learns its retransmit timeout), a calibration at startup, updated as conditions move. **Why:** a value measured once on one host and frozen into the code is still a picked constant.
- **Derive it from a cited source when it's a fact**: a protocol's field size, an OS limit read at runtime, a published specification. Cite the source in the code. **Why:** the citation lets a reader check it.
- **Bound by the resource, not a round number.** A queue is bounded by the memory budget it charges, not by 4,096 entries. **Why:** the resource is what actually runs out.
- **Settings a person configures are different**: how long to keep history, how often to report. Give them a sensible default the person can change. **Why:** those are the person's preferences, not facts about the machine.
- **Moving a picked number to a shared constant doesn't fix it.** **Why:** it is still picked, just in one place.
- **When there is no data yet, say so** and say how to get it. Don't offer the person a menu of values to choose from. **Why:** a picked value fills the gap and stops anyone looking for the real one.

In review, ask of every number in the diff: where does this come from? A number with no answer gets one or goes.

You skipped this when a diff adds a literal limit, timeout or threshold with no estimator and no source.
