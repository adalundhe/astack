"""Separated offline oracle for `rule-data-structures-first`."""
from __future__ import annotations

from pathlib import Path

FIXED_SRC = '''from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Route:
    route_id: str
    region: str
    worker_id: str
    priority: int
    cost_cents: int


@dataclass
class Worker:
    worker_id: str
    capacity: int
    route_ids: set[str] = field(default_factory=set)

    @property
    def load(self) -> int:
        return len(self.route_ids)


def _is_valid_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class RouteScheduler:
    """Indexed route scheduler with canonical Route/Worker ownership and strict invariants."""

    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}
        self._routes_by_id: dict[str, Route] = {}
        self._routes_by_region: dict[str, set[str]] = {}

    def register_worker(self, worker_id: str, capacity: int) -> None:
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("worker_id must be a non-empty string")
        if worker_id in self._workers:
            raise ValueError(f"worker already registered: {worker_id}")
        if not _is_valid_non_negative_int(capacity):
            raise ValueError("capacity must be a non-negative integer")
        self._workers[worker_id] = Worker(worker_id=worker_id, capacity=capacity)

    def unregister_worker(self, worker_id: str) -> None:
        worker = self._workers.get(worker_id)
        if worker is None:
            raise ValueError(f"unknown worker: {worker_id}")
        if worker.route_ids:
            raise ValueError(f"cannot unregister worker {worker_id} with active routes")
        del self._workers[worker_id]

    def add_route(
        self,
        route_id: str,
        region: str,
        worker_id: str,
        priority: int,
        cost_cents: int,
    ) -> None:
        if not isinstance(route_id, str) or not route_id.strip():
            raise ValueError("route_id must be a non-empty string")
        if route_id in self._routes_by_id:
            raise ValueError(f"duplicate route_id: {route_id}")
        if not isinstance(region, str) or not region.strip():
            raise ValueError("region must be a non-empty string")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise ValueError("priority must be an integer")
        if not _is_valid_non_negative_int(cost_cents):
            raise ValueError("cost_cents must be a non-negative integer")

        worker = self._workers.get(worker_id)
        if worker is None:
            raise ValueError(f"unknown worker: {worker_id}")
        if worker.load >= worker.capacity:
            raise ValueError(f"worker {worker_id} is at capacity ({worker.capacity})")

        route = Route(
            route_id=route_id,
            region=region,
            worker_id=worker_id,
            priority=priority,
            cost_cents=cost_cents,
        )
        self._routes_by_id[route_id] = route
        worker.route_ids.add(route_id)
        self._routes_by_region.setdefault(region, set()).add(route_id)

    def reassign_route(self, route_id: str, new_worker_id: str) -> None:
        existing = self._routes_by_id.get(route_id)
        if existing is None:
            raise ValueError(f"unknown route: {route_id}")
        new_worker = self._workers.get(new_worker_id)
        if new_worker is None:
            raise ValueError(f"unknown worker: {new_worker_id}")
        if existing.worker_id == new_worker_id:
            return
        if new_worker.load >= new_worker.capacity:
            raise ValueError(f"worker {new_worker_id} is at capacity ({new_worker.capacity})")

        old_worker = self._workers[existing.worker_id]
        old_worker.route_ids.remove(route_id)
        new_worker.route_ids.add(route_id)
        self._routes_by_id[route_id] = Route(
            route_id=existing.route_id,
            region=existing.region,
            worker_id=new_worker_id,
            priority=existing.priority,
            cost_cents=existing.cost_cents,
        )

    def remove_route(self, route_id: str) -> None:
        existing = self._routes_by_id.pop(route_id, None)
        if existing is None:
            raise ValueError(f"unknown route: {route_id}")
        self._workers[existing.worker_id].route_ids.remove(route_id)
        region_ids = self._routes_by_region.get(existing.region)
        if region_ids is not None:
            region_ids.discard(route_id)
            if not region_ids:
                del self._routes_by_region[existing.region]

    def get_route(self, route_id: str) -> Route | None:
        return self._routes_by_id.get(route_id)

    def routes_for_worker(self, worker_id: str) -> list[Route]:
        worker = self._workers.get(worker_id)
        if worker is None:
            raise ValueError(f"unknown worker: {worker_id}")
        return [self._routes_by_id[rid] for rid in sorted(worker.route_ids)]

    def best_route(self, region: str) -> Route | None:
        region_ids = self._routes_by_region.get(region)
        if not region_ids:
            return None
        candidates = (self._routes_by_id[rid] for rid in region_ids)
        return min(candidates, key=lambda r: (-r.priority, r.cost_cents, r.route_id))

    def worker_load(self, worker_id: str) -> int:
        worker = self._workers.get(worker_id)
        if worker is None:
            raise ValueError(f"unknown worker: {worker_id}")
        return worker.load

    def total_cost_cents(self) -> int:
        return sum(route.cost_cents for route in self._routes_by_id.values())
'''

FIXED_TESTS = '''import unittest

from src.router import Route, RouteScheduler


class RouteSchedulerBasicTest(unittest.TestCase):
    def test_register_worker_and_add_route(self):
        sched = RouteScheduler()
        sched.register_worker("w-1", capacity=2)
        sched.add_route("r-1", "us-east", "w-1", priority=10, cost_cents=500)
        self.assertEqual(sched.worker_load("w-1"), 1)
        self.assertEqual(sched.total_cost_cents(), 500)
        self.assertEqual(
            sched.get_route("r-1"),
            Route("r-1", "us-east", "w-1", priority=10, cost_cents=500),
        )

    def test_duplicate_route_and_capacity_invariants(self):
        sched = RouteScheduler()
        sched.register_worker("w-1", capacity=1)
        sched.register_worker("w-2", capacity=1)
        sched.add_route("r-1", "us-east", "w-1", priority=5, cost_cents=100)

        with self.assertRaises(ValueError):
            sched.add_route("r-1", "eu-west", "w-2", priority=5, cost_cents=100)
        with self.assertRaises(ValueError):
            sched.add_route("r-2", "us-east", "w-1", priority=5, cost_cents=100)
        self.assertEqual(sched.worker_load("w-1"), 1)
        self.assertEqual(sched.worker_load("w-2"), 0)

    def test_reassign_remove_and_unregister_preserve_ownership(self):
        sched = RouteScheduler()
        sched.register_worker("w-1", capacity=2)
        sched.register_worker("w-2", capacity=1)
        sched.add_route("r-1", "us-east", "w-1", priority=10, cost_cents=300)
        sched.add_route("r-2", "us-east", "w-1", priority=20, cost_cents=400)

        sched.reassign_route("r-1", "w-2")
        self.assertEqual(sched.worker_load("w-1"), 1)
        self.assertEqual(sched.worker_load("w-2"), 1)
        self.assertEqual([r.route_id for r in sched.routes_for_worker("w-1")], ["r-2"])
        self.assertEqual([r.route_id for r in sched.routes_for_worker("w-2")], ["r-1"])

        with self.assertRaises(ValueError):
            sched.reassign_route("r-2", "w-2")
        with self.assertRaises(ValueError):
            sched.unregister_worker("w-2")

        sched.remove_route("r-1")
        self.assertIsNone(sched.get_route("r-1"))
        self.assertEqual(sched.worker_load("w-2"), 0)
        sched.unregister_worker("w-2")

    def test_best_route_tiebreaking_and_exact_integer_costs(self):
        sched = RouteScheduler()
        sched.register_worker("w-1", capacity=500)
        sched.add_route("r-b", "ap", "w-1", priority=7, cost_cents=100)
        sched.add_route("r-a", "ap", "w-1", priority=7, cost_cents=100)
        sched.add_route("r-c", "ap", "w-1", priority=7, cost_cents=90)
        self.assertEqual(sched.best_route("ap").route_id, "r-c")
        sched.remove_route("r-c")
        self.assertEqual(sched.best_route("ap").route_id, "r-a")

        for i in range(333):
            sched.add_route(f"m-{i}", "us", "w-1", priority=1, cost_cents=29)
        self.assertEqual(sched.total_cost_cents(), 200 + 333 * 29)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "router.py").write_text(FIXED_SRC, encoding="utf-8")
    (repo / "tests" / "test_router.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Redesigned src/router.py around frozen Route and Worker dataclasses with exact "
            "integer cost_cents, canonical _routes_by_id ownership, and synchronized worker "
            "and region indexes, eliminating O(n^2) scans, parallel-array drift, and float "
            "rounding errors, with invariant unit tests."
        ),
    }
