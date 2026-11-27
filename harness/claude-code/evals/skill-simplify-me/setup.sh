#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/report.py <<'EOF'
"""Over-engineered report formatting module with excessive abstraction ceremony."""
from __future__ import annotations

from abc import ABC, abstractmethod
import csv
import io
import json
from typing import Any, Callable


# Adapter class that wraps formatting configuration options into an object.
class ConfigAdapter:
    """Adapts primitive keyword flags into a configuration dictionary wrapper."""

    def __init__(self, fmt: str, include_header: bool) -> None:
        # Store raw format string after normalizing whitespace and case.
        self._raw_fmt = fmt
        self._include_header = bool(include_header)

    def get_format_key(self) -> str:
        # Return normalized lowercase format key.
        return self._raw_fmt.strip().lower()

    def should_include_header(self) -> bool:
        # Return whether CSV output should emit a header row.
        return self._include_header

    def as_dict(self) -> dict[str, Any]:
        return {
            "format_key": self.get_format_key(),
            "include_header": self.should_include_header(),
        }


# Abstract base class for every report formatter implementation.
class AbstractBaseFormatter(ABC):
    """Defines the contract for concrete report formatters."""

    @abstractmethod
    def format_payload(self, rows: list[dict[str, Any]], config: ConfigAdapter) -> str:
        """Render rows according to config."""


# Concrete CSV implementation inheriting from AbstractBaseFormatter.
class CsvConcreteFormatter(AbstractBaseFormatter):
    """Formats rows into RFC-4180 CSV lines using csv.DictWriter."""

    def format_payload(self, rows: list[dict[str, Any]], config: ConfigAdapter) -> str:
        if not rows:
            return ""
        fieldnames = list(rows[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        if config.should_include_header():
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()


# Concrete JSON implementation inheriting from AbstractBaseFormatter.
class JsonConcreteFormatter(AbstractBaseFormatter):
    """Formats rows into a deterministic sorted-key JSON string."""

    def format_payload(self, rows: list[dict[str, Any]], config: ConfigAdapter) -> str:
        return json.dumps(rows, sort_keys=True)


# Registry holding formatter builder callables keyed by format name.
class StrategyRegistry:
    """Global-style strategy registry for mapping format keys to builders."""

    def __init__(self) -> None:
        self._builders: dict[str, Callable[[], AbstractBaseFormatter]] = {}

    def register(self, key: str, builder: Callable[[], AbstractBaseFormatter]) -> None:
        # Register a builder callable under the given lowercase key.
        self._builders[key.strip().lower()] = builder

    def lookup(self, key: str) -> Callable[[], AbstractBaseFormatter]:
        normalized = key.strip().lower()
        if normalized not in self._builders:
            raise ValueError(f"unsupported report format: {key!r}")
        return self._builders[normalized]

    def registered_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._builders))


# Factory that pulls a builder from StrategyRegistry and instantiates it.
class FormatterFactory:
    """Constructs concrete formatters from a StrategyRegistry."""

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry

    def build_for_config(self, config: ConfigAdapter) -> AbstractBaseFormatter:
        # Look up builder and invoke it to return a new formatter instance.
        builder = self._registry.lookup(config.get_format_key())
        return builder()


# Proxy wrapper adding an extra pass-through indirection around the formatter.
class FormatterProxyWrapper:
    """Forwards format_payload calls to an underlying AbstractBaseFormatter."""

    def __init__(self, target: AbstractBaseFormatter) -> None:
        self._target = target
        self._invocations = 0

    def execute(self, rows: list[dict[str, Any]], config: ConfigAdapter) -> str:
        # Increment local invocation counter and delegate directly to target.
        self._invocations += 1
        return self._target.format_payload(rows, config)

    @property
    def invocations(self) -> int:
        return self._invocations


def _build_default_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register("csv", CsvConcreteFormatter)
    registry.register("json", JsonConcreteFormatter)
    return registry


def render_report(
    rows: list[dict[str, Any]],
    fmt: str = "csv",
    include_header: bool = True,
) -> str:
    """Render tabular dict rows as CSV or JSON."""
    config = ConfigAdapter(fmt=fmt, include_header=include_header)
    registry = _build_default_registry()
    factory = FormatterFactory(registry)
    concrete = factory.build_for_config(config)
    proxy = FormatterProxyWrapper(concrete)
    return proxy.execute(rows, config)
EOF

cat > repo/tests/test_report.py <<'EOF'
import json
import unittest

from src.report import render_report


class ReportBehaviorTest(unittest.TestCase):
    def test_csv_with_header_and_quoting(self):
        rows = [
            {"id": 1, "name": "Alpha, Inc.", "total": 1200},
            {"id": 2, "name": 'Beta "Labs"', "total": 3400},
        ]
        out = render_report(rows, fmt="csv", include_header=True)
        expected = 'id,name,total\n1,"Alpha, Inc.",1200\n2,"Beta ""Labs""",3400\n'
        self.assertEqual(out, expected)

    def test_csv_without_header(self):
        rows = [{"id": 1, "name": "Solo", "total": 500}]
        out = render_report(rows, fmt="CSV", include_header=False)
        self.assertEqual(out, "1,Solo,500\n")

    def test_csv_empty_rows(self):
        self.assertEqual(render_report([], fmt="csv"), "")

    def test_json_output_is_sorted_and_parseable(self):
        rows = [{"z": 1, "a": 2}]
        out = render_report(rows, fmt="json")
        self.assertEqual(out, '[{"a": 2, "z": 1}]')
        self.assertEqual(json.loads(out), rows)

    def test_json_empty_rows(self):
        self.assertEqual(render_report([], fmt="json"), "[]")

    def test_unknown_format_raises_value_error(self):
        with self.assertRaises(ValueError):
            render_report([{"a": 1}], fmt="yaml")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial over-engineered report formatter"
git -C repo rev-parse HEAD > program/base_sha.txt
