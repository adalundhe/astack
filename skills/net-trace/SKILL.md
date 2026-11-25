---
name: net-trace
description: "Diagnose networking, packet, routing, firewall, edge/CDN/WAF, DNS, and TLS/mTLS issues end to end across any OS, cluster, edge, or cloud network using read-only path analyzers, flow logs, policy inspection, TLS handshakes, and secret-safe packet captures. Use for connectivity failures, drops/resets, ingress/egress or WAF blocks, TLS/cert errors, or cross-network routing bugs."
disable-model-invocation: true
---

# Net trace

Pinpoint the exact hop, policy, edge rule, route, or handshake where network traffic fails—using read-only probes from DNS, edge/WAF, and cloud flow logs down to packet captures without leaking payload secrets.

Discover whichever cloud, edge/CDN, service-mesh, cluster, or host networking tools apply to the target environment via **analyze-environment**; provider examples below (AWS, GCP, Azure, Cloudflare, Linux/K8s) are illustrative, never exhaustive.

## 1. Lock endpoints, context, and failure signature

1. **Confirm active target context (**analyze-environment**):** verify cloud/edge account, project/subscription/zone, region, virtual network, cluster/namespace, source/destination IP or CIDR, hostname, port, and protocol in `TOOLS.md`.
2. **Classify the wire symptom before guessing:**
   - **Silent timeout / hang:** usually stateful or stateless policy drop (cloud firewall/SG/NSG, stateless ACL, cluster network policy), route blackhole, NAT/`conntrack` exhaustion, or PMTU blackhole.
   - **Immediate `ECONNREFUSED` / TCP `RST`:** reached host/proxy, nothing listening, LB/target reset, idle-timeout skew, or upstream abort.
   - **TLS alert / handshake failure / redirect loop:** SNI, cert chain/intermediate CA, SAN, expiry/clock skew, TLS version/cipher, ALPN, edge-to-origin SSL mode mismatch (e.g., Flexible vs. Full Strict), or mTLS identity mismatch.
   - **Edge/WAF block or HTTP 403 / 502 / 503 / 504 / `5xx` edge codes:** WAF/bot/rate-limit/Zero-Trust rule (check edge trace headers like `CF-Ray`), origin health-check mismatch, keep-alive skew, or deploy drain race (**fail-safely**).

## 2. Trace hop-by-hop (read-only probes first)

1. **DNS & service discovery:** resolve from the actual failing source (`dig +trace` / `drill` / `nslookup`) and inspect authoritative, private/split-horizon, and cluster DNS. Check record targets, apex CNAME flattening, proxy vs. DNS-only state, DNSSEC, TTLs, `ndots` amplification, and whether egress policy allows DNS (`UDP/TCP 53`).
2. **Edge, CDN, & WAF layer:** whenever traffic traverses a CDN, edge proxy, WAF, tunnel, or L7 gateway (e.g., Cloudflare, CloudFront, Cloud Armor, Front Door, Fastly, Ingress/Envoy), isolate edge vs. origin first: inspect edge ray/cache headers, edge error semantics, SSL/TLS origin mode, WAF/firewall/bot/rate-limit/access logs, and test origin directly from an authorized vantage point.
3. **Routing & provider path analysis:** inspect route tables, NAT, peering, transit hubs, private endpoints/PrivateLink/Private Service Connect, and load-balancer target health. Run the platform's read-only path analyzer when available (e.g., AWS Reachability Analyzer, GCP Connectivity Tests, Azure Network Watcher, or equivalents).
4. **Flow logs & bidirectional policies:** query virtual-network / firewall flow logs (e.g., AWS/GCP VPC Flow Logs, Azure NSG/VNet Flow Logs, host/CNI flow logs like Hubble/Cilium) checking accept/reject verdicts, TCP flags, and post-NAT addresses. Always check **both directions**:
   - stateful firewalls (source/dest ingress *and* egress rules, tag/SA/group selectors);
   - stateless ACLs (both destination service port *and* ephemeral return ports);
   - cluster/mesh network policies (both source egress and target ingress, namespace/pod selectors).
5. **TLS / SSL / mTLS inspection:** run `openssl s_client -connect <host>:<port> -servername <host> -showcerts -alpn h2,http/1.1` and `curl -vk` (`--http2` / `--http3`). Verify cert chain + intermediates, SANs, expiry, OCSP/CRL, TLS version/ciphers, ALPN, and mesh mTLS identities/policies.
6. **Packets, sockets, & kernel state:** when policy and flow logs don't settle it, capture bounded, filtered traces from the failing host/workload:
   - `ss -tinp` / `ip route get <dst>` / `mtr -rwzbc 20 <dst>` / `tracepath <dst>` (asymmetric routing, hop loss, MTU/PMTU blackholes);
   - `conntrack -S` / socket & ephemeral port counts (NAT/conntrack exhaustion, `TIME_WAIT` pressure);
   - `tcpdump -nn -i <iface> -c <N> -s 96` (header-only unless payload framing is specifically required) and `tshark` to prove SYN/SYN-ACK/RST, retransmits, zero-window, or TLS alerts.

## 3. Keep captures safe and hand off cleanly

- Save captures as `<file>_DEBUG_<shorthash>.<type>` (e.g., `.pcap`, `.txt`), default to header-only (`-s 96`) to avoid capturing tokens/PII (**no-leaked-secrets**), and clean them up afterward (**cleanup**).
- Cite exact commands, edge/WAF events, flow-log verdicts, or packet frames proving the failing hop (ran vs. read).
- Route firewall/WAF/IAM fixes through **least-privilege** + **safe-iac** + **safe-to-deploy**, timeout/drain/keep-alive fixes through **fail-safely**, and confirmed code/IaC bugs through **bugbash**.
