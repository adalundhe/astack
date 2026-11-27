#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Route Scheduler

Assigns regional routes to workers with bounded capacity in `src/router.py`.

## Public Contract

### `Route`
Typed domain dataclass (not a raw tuple or dict) with attributes:
- `route_id: str`
- `region: str`
- `worker_id: str`
- `priority: int`
- `cost_cents: int` (exact integer minor units, never `float`)

### `RouteScheduler`
Maintains canonical ownership and consistent indexed lookups with the following invariants:
- `register_worker(worker_id: str, capacity: int) -> None`: registers a worker; raises `ValueError` if `worker_id` is empty/already registered or `capacity < 0` (or boolean).
- `unregister_worker(worker_id: str) -> None`: removes a worker; raises `ValueError` if `worker_id` is unknown or still has active assigned routes.
- `add_route(route_id: str, region: str, worker_id: str, priority: int, cost_cents: int) -> None`: adds a route; raises `ValueError` if `route_id` is empty/already exists in any region, `worker_id` is unknown, `cost_cents < 0` (or boolean), or worker is at full capacity.
- `reassign_route(route_id: str, new_worker_id: str) -> None`: moves an existing route to `new_worker_id`; raises `ValueError` if `route_id` or `new_worker_id` is unknown, or if `new_worker_id` (when different from the current worker) has no spare capacity. Updates worker loads and indexes consistently.
- `remove_route(route_id: str) -> None`: removes an existing route and frees its worker's capacity; raises `ValueError` if `route_id` is unknown.
- `get_route(route_id: str) -> Route | None`: O(1) indexed lookup returning the typed `Route` or `None`.
- `routes_for_worker(worker_id: str) -> list[Route]`: raises `ValueError` if `worker_id` is unknown; returns all routes assigned to `worker_id`, sorted by `route_id`.
- `best_route(region: str) -> Route | None`: returns the route in `region` with highest `priority`, tie-breaking by lowest `cost_cents`, then lexicographically smallest `route_id` (`None` if no routes in `region`).
- `worker_load(worker_id: str) -> int`: raises `ValueError` if `worker_id` is unknown; always equals `len(routes_for_worker(worker_id))`.
- `total_cost_cents() -> int`: exact integer sum of `cost_cents` across all active routes.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/router.py <<'EOF'
from __future__ import annotations


class RouteScheduler:
    """Tangled nested dict-of-tuples and parallel-array route scheduler."""

    def __init__(self) -> None:
        # region -> list of (route_id, worker_id, priority, cost_dollars_float)
        self._routes: dict[str, list[tuple[str, str, int, float]]] = {}
        self._worker_names: list[str] = []
        self._worker_capacities: list[int] = []
        self._worker_loads: list[int] = []

    def register_worker(self, worker_id: str, capacity: int) -> None:
        if not worker_id or worker_id in self._worker_names or capacity < 0:
            raise ValueError("invalid worker")
        self._worker_names.append(worker_id)
        self._worker_capacities.append(capacity)
        self._worker_loads.append(0)

    def unregister_worker(self, worker_id: str) -> None:
        idx = self._worker_names.index(worker_id)
        self._worker_names.pop(idx)
        self._worker_capacities.pop(idx)

    def add_route(self, route_id: str, region: str, worker_id: str, priority: int, cost_cents: int) -> None:
        if worker_id not in self._worker_names:
            raise ValueError("unknown worker")
        idx = self._worker_names.index(worker_id)
        if self._worker_loads[idx] >= self._worker_capacities[idx]:
            raise ValueError("worker at capacity")
        self._routes.setdefault(region, []).append((route_id, worker_id, priority, cost_cents / 100.0))
        self._worker_loads[idx] += 1

    def reassign_route(self, route_id: str, new_worker_id: str) -> None:
        found = None
        found_region = None
        for region, entries in self._routes.items():
            for entry in entries:
                if entry[0] == route_id:
                    found = entry
                    found_region = region
                    break
        if found is None or found_region is None:
            raise ValueError("unknown route")
        self._routes[found_region].append((found[0], new_worker_id, found[2], found[3]))

    def remove_route(self, route_id: str) -> None:
        for entries in self._routes.values():
            for i, entry in enumerate(entries):
                if entry[0] == route_id:
                    entries.pop(i)
                    return
        raise ValueError("unknown route")

    def get_route(self, route_id: str):
        for region, entries in self._routes.items():
            for entry in entries:
                if entry[0] == route_id:
                    return {
                        "route_id": entry[0],
                        "region": region,
                        "worker_id": entry[1],
                        "priority": entry[2],
                        "cost_cents": int(entry[3] * 100),
                    }
        return None

    def routes_for_worker(self, worker_id: str) -> list:
        out = []
        for region, entries in self._routes.items():
            for entry in entries:
                if entry[1] == worker_id:
                    out.append((entry[0], region, entry[1], entry[2], entry[3]))
        out.sort(key=lambda e: e[0])
        return out

    def best_route(self, region: str):
        entries = self._routes.get(region, [])
        if not entries:
            return None
        best = max(entries, key=lambda e: (e[2], -e[3]))
        return {
            "route_id": best[0],
            "region": region,
            "worker_id": best[1],
            "priority": best[2],
            "cost_cents": int(best[3] * 100),
        }

    def worker_load(self, worker_id: str) -> int:
        idx = self._worker_names.index(worker_id)
        return self._worker_loads[idx]

    def total_cost_cents(self) -> int:
        total_dollars = 0.0
        for entries in self._routes.values():
            for entry in entries:
                total_dollars += entry[3]
        return int(total_dollars * 100)
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_router.py <<'EOF'
import unittest

from src.router import RouteScheduler


class RouteSchedulerBasicTest(unittest.TestCase):
    def test_register_worker_and_add_route(self):
        sched = RouteScheduler()
        sched.register_worker("w-1", capacity=2)
        sched.add_route("r-1", "us-east", "w-1", priority=10, cost_cents=500)
        self.assertEqual(sched.worker_load("w-1"), 1)
        self.assertEqual(sched.total_cost_cents(), 500)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
