---
name: net-trace
description: "Diagnose network, DNS, routing, firewall, edge/WAF, and TLS/mTLS failures hop-by-hop with read-only probes. Use when traffic times out, resets, fails TLS, or hits edge/policy blocks."
disable-model-invocation: true
---

# Net trace

Pinpoint the exact hop, policy, edge rule, route, or handshake where network traffic fails. Work read-only from DNS, edge/WAF, and flow logs down to packet captures without leaking payload secrets.

Discover whichever cloud, edge, mesh, cluster, or host networking tools apply via `analyze-environment` and **jack-in**; provider examples below are illustrative, never exhaustive.

## 1. Lock context and classify the wire symptom

1. **Confirm active target context (`analyze-environment`):** verify account, zone, region, VPC, and cluster or namespace in `TOOLS.md`. Confirm exact source/dest IP or CIDR, hostname, port, and protocol.
2. **Classify the symptom before guessing:**
   - **Silent timeout / hang:** stateful or stateless policy drop (SG/NSG/ACL/NetworkPolicy), route blackhole, NAT/`conntrack` exhaustion, or PMTU blackhole.
   - **Immediate `ECONNREFUSED` / TCP `RST`:** reached host/proxy with nothing listening, LB reset, idle-timeout skew, or upstream abort.
   - **TLS alert / redirect loop:** SNI, cert chain, SAN, expiry/clock skew, TLS version/cipher, ALPN, edge SSL mode mismatch, or mTLS identity mismatch.
   - **Edge/WAF block or 403/502/503/504:** WAF, bot, or rate-limit rule (check headers like `CF-Ray`), origin health mismatch, keep-alive skew, or drain race (`fail-safely`).

## 2. Trace hop-by-hop (read-only probes first)

Work top-down from DNS and edge to packets, because cheap control-plane signals isolate hops faster than raw captures:

1. **DNS & service discovery:** test private and cluster DNS against the failing source's own configured resolver first (`dig <name>`, `resolvectl`, `nslookup`, checking `/etc/resolv.conf`, `ndots`, TTLs, and port `53` egress). Use `dig +trace` or `drill` only for public authoritative delegation (it bypasses private, split-horizon, and cluster resolvers). Check targets, CNAME flattening, and DNSSEC.
2. **Edge, CDN, & WAF:** isolate edge vs. origin first. Inspect ray/cache headers, edge SSL mode, and WAF logs, then probe the origin from an authorized vantage point.
3. **Routing & path analyzers:** check route tables, NAT, peering, transit hubs, private endpoints, and LB target health. Run the platform path analyzer when available (AWS Reachability Analyzer, GCP Connectivity Tests, Azure Network Watcher).
4. **Flow logs & bidirectional policies:** query virtual-network, firewall, or CNI flow logs (VPC/NSG Flow Logs, Hubble/Cilium) for verdicts and post-NAT addresses. Always check **both directions**, because asymmetric return drops look identical to outbound blocks:
   - stateful firewalls (ingress *and* egress rules, tag/group selectors);
   - stateless ACLs (destination port *and* ephemeral return ports);
   - cluster/mesh policies (source egress and target ingress).
5. **TLS / SSL / mTLS:** run `openssl s_client -connect <host>:<port> -servername <host> -showcerts -alpn h2,http/1.1` and `curl -vk` (`--http2` / `--http3`). Check cert chain, intermediates, SANs, expiry, ALPN, and mTLS policies.
6. **Packets, sockets, & kernel state:** when policy and flow logs don't settle it, take bounded, filtered captures from the failing workload:
   - `ss -tinp`, `ip route get <dst>`, `mtr -rwzbc 20 <dst>`, `tracepath <dst>` (asymmetric routes, loss, PMTU);
   - `conntrack -S` and socket/ephemeral port counts (NAT/`conntrack` exhaustion);
   - `tcpdump -nn -i <iface> -c <N> -s 54` (Ethernet+IPv4+TCP) or `-s 74` (Ethernet+IPv6+TCP) for SYN/RST, retransmits, or zero-window. Use `-s 42` / `-s 62` for Ethernet+UDP. Subtract 14 bytes on L3/tun interfaces so no payload leaks. TLS alerts live inside TCP payload after byte 54/74. Inspect them with `openssl s_client` instead of raising snaplen on cleartext (`-s 96` leaks ~30–42 bytes of payload and tokens).

## 3. Keep captures safe and hand off cleanly

- Save retained header-only traces or flow-log captures under `$HOME/.astack/<project_name>/logging/traces/[FILE_YYYY_MM_DD_HH_MM_SS]` (`astack-tools logging path <project> traces <name> --ensure`). Keep scratch workspace captures named `<file>_DEBUG_<shorthash>.<type>` with header-bounded snaplens matching link and transport headers (`-s 54`/`-s 74` Ethernet+TCP, `-s 42`/`-s 62` Ethernet+UDP, minus 14 on L3/tun). Never capture cleartext payloads or tokens (**no-leaked-secrets**). Delete every scratch capture afterward (**cleanup**).
- Cite exact commands, flow-log verdicts, or packet frames proving the failing hop (ran vs. read).
- Route firewall/WAF/IAM fixes through `least-privilege`, `safe-iac`, and `safe-to-deploy`. Route timeout/drain fixes through `fail-safely`, and confirmed code/IaC bugs through **bugbash**.

**Done when:** the failing hop is proven with exact ran commands, verdicts, or frames, handoff is routed, and every capture is cleaned up.

Referenced skills: `jack-in` (`${CLAUDE_SKILL_DIR}/../jack-in/SKILL.md`), `no-leaked-secrets` (`${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md`), `cleanup` (`${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`), `bugbash` (`${CLAUDE_SKILL_DIR}/../bugbash/SKILL.md`). Read any cited skill file before acting when its trigger applies.
