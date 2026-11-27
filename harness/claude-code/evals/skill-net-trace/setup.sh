#!/bin/bash
set -euo pipefail
mkdir -p program/net_bundle program/astack_home/edge-gw repo/infra

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/infra/README.md <<'EOF'
# edge-gw networking

- Target service: `https://api.partner.internal:443` (`198.51.100.44/32`)
- Healthy app tier: `subnet-app-1` (`10.20.1.0/24`, `sg-app-1`)
- Failing app tier: `subnet-app-2` (`10.20.2.0/24`, `sg-app-2`)
EOF

git -C repo add .
git -C repo commit -q -m "initial edge-gw infra docs"

cat > program/net_bundle/dns.txt <<'EOF'
; Resolver check from subnet-app-1 (10.20.0.2)
api.partner.internal.   300 IN CNAME gw-prod.edge.internal.
gw-prod.edge.internal.  300 IN A     198.51.100.44
; status: NOERROR

; Resolver check from subnet-app-2 (10.20.0.2)
api.partner.internal.   300 IN CNAME gw-prod.edge.internal.
gw-prod.edge.internal.  300 IN A     198.51.100.44
; status: NOERROR
EOF

cat > program/net_bundle/tls_cert.txt <<'EOF'
depth=1 CN = Partner Internal Issuing CA
depth=0 CN = api.partner.internal
X509v3 Subject Alternative Name: DNS:api.partner.internal, DNS:gw-prod.edge.internal
Not Before: Jan 01 00:00:00 2026 GMT
Not After : Jun 01 00:00:00 2027 GMT
Protocol  : TLSv1.3
Verify return code: 0 (ok)
Observed from subnet-app-1: HTTP/2 200 OK in 18ms
Observed from subnet-app-2: connect() timed out after 10000ms before ClientHello
EOF

cat > program/net_bundle/routes.json <<'EOF'
{
  "vpc": "vpc-edge-prod",
  "subnets": [
    {
      "subnet_id": "subnet-app-1",
      "cidr": "10.20.1.0/24",
      "route_table": "rtb-app-1",
      "routes": [
        {"destination": "10.20.0.0/16", "target": "local", "state": "active"},
        {"destination": "198.51.100.0/24", "target": "nat-gw-01", "state": "active"}
      ]
    },
    {
      "subnet_id": "subnet-app-2",
      "cidr": "10.20.2.0/24",
      "route_table": "rtb-app-2",
      "routes": [
        {"destination": "10.20.0.0/16", "target": "local", "state": "active"},
        {"destination": "198.51.100.0/24", "target": "nat-gw-01", "state": "active"}
      ]
    }
  ]
}
EOF

cat > program/net_bundle/policies.json <<'EOF'
{
  "security_groups": [
    {
      "id": "sg-app-1",
      "attached_subnet": "subnet-app-1",
      "egress": [
        {"proto": "tcp", "port": 5432, "dst_cidr": "10.20.10.0/24", "action": "ALLOW"},
        {"proto": "tcp", "port": 443, "dst_cidr": "198.51.100.44/32", "action": "ALLOW"}
      ]
    },
    {
      "id": "sg-app-2",
      "attached_subnet": "subnet-app-2",
      "egress": [
        {"proto": "tcp", "port": 5432, "dst_cidr": "10.20.10.0/24", "action": "ALLOW"}
      ]
    }
  ],
  "network_acls": [
    {
      "id": "nacl-app-1",
      "subnet": "subnet-app-1",
      "outbound": [
        {"rule": 100, "proto": "tcp", "port": 443, "dst_cidr": "198.51.100.44/32", "action": "ALLOW"},
        {"rule": 110, "proto": "tcp", "port": 5432, "dst_cidr": "10.20.10.0/24", "action": "ALLOW"}
      ],
      "inbound": [
        {"rule": 100, "proto": "tcp", "port": "1024-65535", "src_cidr": "198.51.100.44/32", "action": "ALLOW"}
      ]
    },
    {
      "id": "nacl-app-2",
      "subnet": "subnet-app-2",
      "outbound": [
        {"rule": 110, "proto": "tcp", "port": 5432, "dst_cidr": "10.20.10.0/24", "action": "ALLOW"}
      ],
      "inbound": [
        {"rule": 100, "proto": "tcp", "port": "1024-65535", "src_cidr": "198.51.100.44/32", "action": "ALLOW"}
      ]
    }
  ]
}
EOF

cat > program/net_bundle/flow_logs.log <<'EOF'
2026-11-26T05:01:10Z subnet=subnet-app-1 sg=sg-app-1 nacl=nacl-app-1 src=10.20.1.14:51240 dst=198.51.100.44:443 proto=TCP dir=EGRESS action=ACCEPT bytes=1420
2026-11-26T05:01:10Z subnet=subnet-app-1 sg=sg-app-1 nacl=nacl-app-1 src=198.51.100.44:443 dst=10.20.1.14:51240 proto=TCP dir=INGRESS action=ACCEPT bytes=3840
2026-11-26T05:01:12Z subnet=subnet-app-2 sg=sg-app-2 nacl=nacl-app-2 src=10.20.2.21:49812 dst=198.51.100.44:443 proto=TCP dir=EGRESS action=DROP reason=NO_MATCHING_EGRESS_RULE
2026-11-26T05:01:13Z subnet=subnet-app-2 sg=sg-app-2 nacl=nacl-app-2 src=10.20.2.21:49812 dst=198.51.100.44:443 proto=TCP dir=EGRESS action=DROP reason=NO_MATCHING_EGRESS_RULE
2026-11-26T05:01:15Z subnet=subnet-app-2 sg=sg-app-2 nacl=nacl-app-2 src=10.20.2.21:49812 dst=198.51.100.44:443 proto=TCP dir=EGRESS action=DROP reason=NO_MATCHING_EGRESS_RULE
EOF
