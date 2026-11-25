# <program>: shared tools & environment catalog

Environment summary: <OS / arch, key runtime/toolchain versions, local dev services>.
Active target contexts (cloud / edge / cluster / IaC): <account, project/subscription, edge zone, cluster/namespace, IaC workspace/stack, or none>.
Updated by: <lead / researcher / worker>. Never write secret values, tokens, or credentials here (`no-leaked-secrets`).

## Tools & Access Catalog

| Tool / API / MCP | Purpose | Status (`ready` / `needs-install` / `needs-human-auth` / `unreachable`) | Location or non-root install command | Auth check & read-only / dry-run command | Human action (only if `needs-human-auth`) |
|---|---|---|---|---|---|
| `<name>` | `<what it accesses>` | `ready` | `<path or install cmd>` | `<auth check>; <read-only/dry-run cmd>` | `none` |

## Shared helper scripts & notes

- `<path>`: <what it fetches/emulates and how to run it>
