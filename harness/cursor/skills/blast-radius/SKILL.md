---
name: blast-radius
description: "Find what a change could break beyond its diff, and prove the fact it is safe because of by running real code. Use before removing, reshaping or changing shared code, when reviewing a change you don't yet trust, or when asked what a change could break."
---

# Blast radius

Find what a change could break beyond its diff, before it ships.

1. **Read the change:** what it adds, changes and removes, including what it now does differently that the diff doesn't spell out.
2. **Find the fact it's safe because of.** Most risky-looking changes are safe because of one fact, such as "this only drops entries that are already dead". Find it, and most worries fall with it.
3. **Look where a search stops:** the source of every library it calls, at the pinned version; when things run (startup, shutdown, retries, concurrency); data that crosses a boundary (APIs, stored data, wire formats, configuration, other services and languages); code several hops downstream.
4. **Prove the fact by running it,** as high on the trust ladder as you can reach (**prove-it**): a script or test against the real code, or a reproduction in a local or test environment.
5. **Report:** what the change does; the fact it's safe because of, proven or marked unproven; each real risk, with how it breaks, where, how likely and how bad; what you checked and cleared; the cheapest check that would catch the real breakage.

<!-- Adapts pstack's blast-radius skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
