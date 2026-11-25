---
name: net-trace
description: "Diagnose network, DNS, routing, firewall, edge/WAF, and TLS/mTLS failures hop-by-hop with read-only probes. Use when traffic times out, resets, fails TLS, or hits edge/policy blocks."
disable-model-invocation: true
---

# Net trace

Pinpoint the exact hop, policy, edge rule, route, or handshake where network traffic fails. Work read-only from DNS, edge/WAF, and flow logs down to packet captures without leaking payload secrets.

Discover whichever cloud, edge, mesh, cluster, or host networking tools apply via `analyze-environment`; provider examples below are illustrative, never exhaustive.

## 1. Lock context and classify the wire symptom

1. **Confirm active target context (`analyze-environment`):** verify account, zone, region, VPC, and cluster or namespace in `TOOLS.md`. Confirm exact source/dest IP or CIDR, hostname, port, and protocol.
2. **Classify the symptom before guessing:**
   - **Silent timeout / hang:** stateful or stateless policy drop (SG/NSG/ACL/NetworkPolicy), route blackhole, NAT/`conntrack` exhaustion, or PMTU blackhole.
   - **Immediate `ECONNREFUSED` / TCP `RST`:** reached host/proxy with nothing listening, LB reset, idle-timeout skew, or upstream abort.
   - **TLS alert / redirect loop:** SNI, cert chain, SAN, expiry/clock skew, TLS version/cipher, ALPN, edge SSL mode mismatch, or mTLS identity mismatch.
   - **Edge/WAF block or 403/502/503/504:** WAF, bot, or rate-limit rule (check headers like `CF-Ray`), origin health mismatch, keep-alive skew, or drain race (`fail-safely`).

## 2. Trace hop-by-hop (read-only probes first)

Work top-down from DNS and edge to packets, because cheap control-plane signals isolate hops faster than raw captures:

1. **DNS & service discovery:** resolve from the failing source (`dig +trace`, `drill`, `nslookup`) across authoritative, private, and cluster DNS. Check targets, CNAME flattening, DNSSEC, TTLs, `ndots`, and port `53` egress.
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
   - `tcpdump -nn -i <iface> -c <N> -s 96` (header-only by default) and `tshark` for SYN/RST, retransmits, zero-window, or TLS alerts.

## 3. Keep captures safe and hand off cleanly

- Save captures as `<file>_DEBUG_<shorthash>.<type>` with header-only `-s 96` by default (**no-leaked-secrets**). Delete every capture afterward (**cleanup**).
- Cite exact commands, flow-log verdicts, or packet frames proving the failing hop (ran vs. read).
- Route firewall/WAF/IAM fixes through `least-privilege`, `safe-iac`, and `safe-to-deploy`. Route timeout/drain fixes through `fail-safely`, and confirmed code/IaC bugs through **bugbash**.

**Done when:** the failing hop is proven with exact ran commands, verdicts, or frames, handoff is routed, and every capture is cleaned up.

Referenced skills: `no-leaked-secrets` (`${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md`), `cleanup` (`${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`), `bugbash` (`${CLAUDE_SKILL_DIR}/../bugbash/SKILL.md`). Read any cited skill file before acting when its trigger applies.
