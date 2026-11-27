"""Separated offline oracle for `rule-no-hidden-flow-control`."""
from __future__ import annotations

from pathlib import Path

FIXED_SRC = '''from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class LoadErrorKind(Enum):
    NOT_FOUND = "not_found"
    INVALID_JSON = "invalid_json"
    INVALID_PROFILE = "invalid_profile"


@dataclass(frozen=True)
class UserProfile:
    id: int
    name: str


@dataclass(frozen=True)
class ProfileLoadError:
    kind: LoadErrorKind
    detail: str


ProfileResult = UserProfile | ProfileLoadError


def load_user_profile(path: Path) -> ProfileResult:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ProfileLoadError(LoadErrorKind.NOT_FOUND, f"profile file not found: {path}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ProfileLoadError(LoadErrorKind.INVALID_JSON, f"malformed JSON: {exc.msg}")

    if not isinstance(data, dict):
        return ProfileLoadError(LoadErrorKind.INVALID_PROFILE, "profile JSON must be an object")

    try:
        raw_id = data["id"]
        raw_name = data["name"]
    except KeyError as exc:
        return ProfileLoadError(LoadErrorKind.INVALID_PROFILE, f"missing required field: {exc.args[0]}")

    if isinstance(raw_id, bool):
        return ProfileLoadError(LoadErrorKind.INVALID_PROFILE, "id must be an integer, not bool")

    try:
        user_id = int(raw_id)
    except (TypeError, ValueError):
        return ProfileLoadError(LoadErrorKind.INVALID_PROFILE, f"invalid integer id: {raw_id!r}")

    if not isinstance(raw_name, str) or not raw_name.strip():
        return ProfileLoadError(LoadErrorKind.INVALID_PROFILE, "name must be a non-empty string")

    return UserProfile(id=user_id, name=raw_name.strip())
'''

FIXED_TESTS = '''from pathlib import Path
import tempfile
import unittest

from src.profile_loader import (
    LoadErrorKind,
    ProfileLoadError,
    UserProfile,
    load_user_profile,
)


class ProfileLoaderTest(unittest.TestCase):
    def test_loads_valid_profile(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "profile.json"
            p.write_text('{"id": 42, "name": "  Ada Lovelace  "}', encoding="utf-8")
            profile = load_user_profile(p)
            self.assertEqual(profile, UserProfile(id=42, name="Ada Lovelace"))
            self.assertEqual(profile.id, 42)
            self.assertEqual(profile.name, "Ada Lovelace")

    def test_missing_file_returns_not_found_error(self):
        with tempfile.TemporaryDirectory() as td:
            res = load_user_profile(Path(td) / "missing.json")
            self.assertIsInstance(res, ProfileLoadError)
            self.assertEqual(res.kind, LoadErrorKind.NOT_FOUND)

    def test_corrupt_json_returns_invalid_json_error(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "corrupt.json"
            p.write_text("{bad json", encoding="utf-8")
            res = load_user_profile(p)
            self.assertIsInstance(res, ProfileLoadError)
            self.assertEqual(res.kind, LoadErrorKind.INVALID_JSON)

    def test_missing_field_and_invalid_values_return_invalid_profile_error(self):
        cases = [
            "[]",
            '{"name": "Ada"}',
            '{"id": 1}',
            '{"id": "abc", "name": "Ada"}',
            '{"id": true, "name": "Ada"}',
            '{"id": 1, "name": "   "}',
        ]
        with tempfile.TemporaryDirectory() as td:
            for idx, payload in enumerate(cases):
                p = Path(td) / f"bad_{idx}.json"
                p.write_text(payload, encoding="utf-8")
                res = load_user_profile(p)
                self.assertIsInstance(res, ProfileLoadError)
                self.assertEqual(res.kind, LoadErrorKind.INVALID_PROFILE)

    def test_unexpected_errors_propagate(self):
        class BrokenPath:
            def read_text(self, *args, **kwargs):
                raise RuntimeError("hardware I/O failure")

        with self.assertRaises(RuntimeError):
            load_user_profile(BrokenPath())


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "profile_loader.py").write_text(FIXED_SRC, encoding="utf-8")
    (repo / "tests" / "test_profile_loader.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Removed the broad `except Exception: return None` catch-all in src/profile_loader.py, "
            "replaced it with narrow catches for FileNotFoundError, json.JSONDecodeError, KeyError, "
            "and ValueError/TypeError returning typed UserProfile or ProfileLoadError values, let "
            "unexpected exceptions propagate, and added unit tests for every failure path."
        ),
    }
