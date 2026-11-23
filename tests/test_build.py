"""Checks on the three packages: current with the source, and shaped the way each tool reads them."""
import json
import re
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "harness"
NAME = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")
# From Cursor's schemas/plugin.schema.json and schemas/marketplace.schema.json (cursor/plugins), which reject other keys.
CURSOR_PLUGIN_KEYS = {"agents", "author", "category", "commands", "description", "displayName", "homepage", "hooks",
                      "keywords", "license", "logo", "mcpServers", "minClientVersions", "name", "publisher",
                      "repository", "rules", "skills", "tags", "variables", "version"}
CURSOR_MARKETPLACE_KEYS = {"metadata", "name", "owner", "plugins"}
CURSOR_ENTRY_KEYS = {"name", "source", "description", "minClientVersions"}


def load(path):
    return json.loads(Path(path).read_text())


class BuildTest(unittest.TestCase):
    def test_the_packages_are_current_with_the_source(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_manifest_has_the_same_name_and_version(self):
        manifests = [HARNESS / "claude-code/.claude-plugin/plugin.json", HARNESS / "cursor/.cursor-plugin/plugin.json",
                     HARNESS / "codex/plugin.json"]
        self.assertEqual(len({(load(m)["name"], load(m)["version"]) for m in manifests}), 1)

    def test_each_marketplace_points_at_its_package(self):
        claude = load(ROOT / ".claude-plugin/marketplace.json")["plugins"][0]
        self.assertEqual(load(ROOT / claude["source"] / ".claude-plugin/plugin.json")["name"], claude["name"])
        cursor = load(ROOT / ".cursor-plugin/marketplace.json")["plugins"][0]
        self.assertEqual(load(ROOT / cursor["source"] / ".cursor-plugin/plugin.json")["name"], cursor["name"])
        codex = load(ROOT / ".agents/plugins/marketplace.json")["plugins"][0]
        self.assertEqual(load(ROOT / codex["source"]["path"] / "plugin.json")["name"], codex["name"])

    def test_cursor_files_meet_cursors_schema(self):
        plugin = load(HARNESS / "cursor/.cursor-plugin/plugin.json")
        self.assertLessEqual(set(plugin), CURSOR_PLUGIN_KEYS)
        self.assertRegex(plugin["name"], NAME)
        market = load(ROOT / ".cursor-plugin/marketplace.json")
        self.assertLessEqual(set(market), CURSOR_MARKETPLACE_KEYS)
        self.assertLessEqual(set(market["owner"]), {"name", "email"})
        for entry in market["plugins"]:
            self.assertLessEqual(set(entry), CURSOR_ENTRY_KEYS)
            self.assertIsInstance(entry["source"], str)
            self.assertRegex(entry["name"], NAME)

    def test_skill_names_match_their_folders(self):
        for skill in HARNESS.glob("*/skills/*/SKILL.md"):
            name = re.search(r"^name: (.+)$", skill.read_text(), re.M).group(1)
            self.assertEqual(name, skill.parent.name, skill)

    def test_cursor_and_codex_use_prefixed_names(self):
        for tool in ("cursor", "codex"):
            names = {p.name for p in (HARNESS / tool / "skills").iterdir()}
            self.assertTrue({"astack-lead", "astack-setup", "astack-status"} <= names, names)
            self.assertFalse({"lead", "setup", "status"} & names, names)
        self.assertTrue((HARNESS / "cursor/agents/astack-worker.md").is_file())

    def test_the_codex_worker_is_a_valid_agent_file(self):
        agent = tomllib.loads((HARNESS / "codex/agents/astack-worker.toml").read_text())
        self.assertEqual(agent["name"], "astack-worker")
        self.assertIn("RESULT: DONE | NOT DONE", agent["developer_instructions"])

    def test_the_hook_scripts_are_executable_in_every_package(self):
        for tool in ("claude-code", "cursor", "codex"):
            for script in ("astack-stamp", "astack-stamp-hook", "astack-status", "astack-verify-merge"):
                self.assertTrue((HARNESS / tool / "bin" / script).stat().st_mode & 0o111, f"{tool}/{script}")


if __name__ == "__main__":
    unittest.main()
