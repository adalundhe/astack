---
description: "Atomic outcome eval for net-trace: traces an offline network diagnostic bundle hop-by-hop, persists a trace capture under ASTACK_HOME/edge-gw/logging/traces/, pinpoints the subnet-app-2 egress TCP/443 DROP while clearing DNS, TLS, and decoy subnet-app-1, and leaves ./repo clean."
expected_outcome: "Reads net-trace/SKILL.md, saves a UTC-stamped trace capture under program/astack_home/edge-gw/logging/traces/, traces DNS/routes/TLS/flow-logs/SG rules hop-by-hop, pinpoints the exact failing hop (subnet-app-2 / sg-app-2 egress DROP on TCP/443 to 198.51.100.44), clears DNS, TLS cert chain, and subnet-app-1, proposes a minimal least-privilege fix in program/NET_TRACE.md, and leaves ./repo clean."
timeout_seconds: 360
---

`/astack:go` Workloads in `subnet-app-2` under project `edge-gw` are timing out when calling `https://api.partner.internal:443`, while `subnet-app-1` succeeds. An offline network diagnostic bundle is saved under `program/net_bundle/` with infrastructure notes in `./repo`. Using `program/astack_home` as `ASTACK_HOME`, trace the path hop-by-hop without modifying `./repo`: save a retained trace capture in the project's logging traces directory, prove the exact failing hop and cleared hops from the bundle evidence, and document the minimal fix in `program/NET_TRACE.md`.
