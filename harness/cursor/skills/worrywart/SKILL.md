---
name: worrywart
description: "Push back on a review point that is unproven, unreproducible, already handled by the code's setting, or not worth its cost, with a preponderance of evidence. Use when a reviewer raises an issue you believe is wrong or overstated, before changing code to satisfy it."
---

# Worrywart

Refute a review point you believe is wrong, with evidence, rather than arguing it away or obeying it unproven.

1. **Restate the point** in plain words: what the reviewer says breaks, for whom, and when.
2. **Test it first.** Run the reviewer's reproduction, or build the scenario it describes. If it reproduces, it is real: fix it instead.
3. **Bring a preponderance of evidence** that it is wrong, whatever the point calls for:
   - traces, logs and screenshots from runs of the real code;
   - a demo run, and a script the reviewer can run to watch it hold;
   - where the setting already handles it: the system, setting or documented practice that does, cited;
   - for a design or architecture point: counter-evidence or research (**research-this**, **prove-it**).
4. **Answer once**, impact first, with the evidence attached. The reviewer either withdraws the point or proves it with a reproduction.

A reviewer whose points keep failing this way is replaced with a fresh one.
