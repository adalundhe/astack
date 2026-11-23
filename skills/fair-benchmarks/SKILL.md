---
name: fair-benchmarks
description: "Compare against other systems fairly: the same client and the same platform for every system, each tuned as it ships, errors counted, runs alternated. Use before you run, report or trust any benchmark against a competitor or another implementation."
---

# Fair benchmarks

Every system in a comparison runs on the same platform and is driven by the same client.

Ada's words: "we must also use the same client in our benchmarks." And: "You need to test both on the same platform."

**Why:** a gap measured with different clients or platforms says nothing about the systems. It measures the clients or the platforms.

- **One client for every system.** The same driver program, with the same concurrency, batching, pacing and timeouts. Where the systems speak different protocols, each gets its own native connector inside that one driver. **Why:** a faster client or a bigger batch can be the whole gap.
- **One platform.** The same machine, OS, disk and filesystem. Containers for all of them or for none. **Why:** a native run against a containerized one measures the container.
- **Each side tuned the way it ships**: release builds, production settings, caches as warm or cold as users see them, the same versions and data. **Why:** a competitor left on defaults loses to its configuration, not its design.
- **Count errors and check answers**, not just speed. **Why:** a refused or wrong request is often the fastest one.
- **Alternate and repeat.** Run A, B, A, B until the run-to-run noise is known. Record the machine's load beside each run, and discard runs made while other work loaded the machine. **Why:** drift and noisy neighbours favour whichever side ran in the quiet moment.
- **Record the setup with the numbers**: the client, platform, versions, settings, command and load. **Why:** a number without its setup can't be checked or rerun.

You skipped this when two systems ran on different machines or packaging, when their clients differed, or when a record doesn't name its client and platform.

<!-- Adapts pstack's benchmark-checklist skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
