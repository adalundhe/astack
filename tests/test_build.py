"""Checks on the three packages: current with source, shaped for each tool, Go-mode index & cross-refs valid, Codex hiding verified, and evals sound."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


def front_matter(path):
    text = Path(path).read_text()
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise AssertionError(f"{path} has no front matter")
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, text[match.end():]


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
            fields, _ = front_matter(skill)
            self.assertEqual(fields["name"], skill.parent.name, skill)

    def test_cursor_and_codex_use_prefixed_names(self):
        for tool in ("cursor", "codex"):
            names = {p.name for p in (HARNESS / tool / "skills").iterdir()}
            self.assertTrue({"astack-go", "astack-lead", "astack-setup", "astack-status", "astack-review"} <= names, names)
            self.assertFalse({"go", "lead", "setup", "status", "review"} & names, names)
        self.assertTrue((HARNESS / "cursor/agents/astack-worker.md").is_file())
        self.assertTrue((HARNESS / "cursor/agents/astack-reviewer.md").is_file())

    def test_only_go_is_visible_in_the_skill_catalog(self):
        for tool, go_name in (("claude-code", "go"), ("cursor", "astack-go")):
            visible = []
            for skill in sorted((HARNESS / tool / "skills").glob("*/SKILL.md")):
                fields, _ = front_matter(skill)
                if fields.get("disable-model-invocation") != "true":
                    visible.append(skill.parent.name)
            self.assertEqual(visible, [go_name], f"{tool} visible skills: {visible}")

        # Codex hides skills via agents/openai.yaml (allow_implicit_invocation: false), not SKILL.md frontmatter.
        codex_visible = []
        for skill in sorted((HARNESS / "codex/skills").glob("*/SKILL.md")):
            fields, _ = front_matter(skill)
            self.assertNotIn("disable-model-invocation", fields, skill)
            policy = skill.parent / "agents" / "openai.yaml"
            if policy.is_file():
                self.assertIn("allow_implicit_invocation: false", policy.read_text(), policy)
            else:
                codex_visible.append(skill.parent.name)
        self.assertEqual(codex_visible, ["astack-go"], f"codex visible skills: {codex_visible}")

    @unittest.skipUnless(shutil.which("codex"), "codex CLI not installed")
    def test_codex_actually_hides_non_go_skills_in_prompt_input(self):
        with tempfile.TemporaryDirectory(prefix="astack-codex-check-") as scratch:
            root = Path(scratch)
            shutil.copytree(HARNESS / "codex/skills", root / "skills")
            env = {**os.environ, "CODEX_HOME": str(root)}
            proc = subprocess.run(
                ["codex", "debug", "prompt-input", "hello"],
                capture_output=True, text=True, env=env, cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            items = json.loads(proc.stdout)
            catalog = "\n".join(
                part.get("text", "")
                for item in items
                if item.get("role") == "developer"
                for part in item.get("content", [])
                if "<skills_instructions>" in part.get("text", "")
            )
            self.assertIn("- astack-go:", catalog)
            for skill in sorted((HARNESS / "codex/skills").iterdir()):
                if skill.name == "astack-go":
                    continue
                self.assertNotIn(f"- {skill.name}:", catalog, f"hidden skill leaked into Codex catalog: {skill.name}")

    def test_go_indexes_every_other_skill_with_valid_paths(self):
        source_skills = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
        go_text = (ROOT / "skills/go/SKILL.md").read_text()
        linked = set(re.findall(r"\$\{CLAUDE_SKILL_DIR\}/\.\./([a-z0-9-]+)/SKILL\.md", go_text))
        self.assertEqual(linked, source_skills - {"go"})

        for tool, go_name in (("claude-code", "go"), ("cursor", "astack-go"), ("codex", "astack-go")):
            go_file = HARNESS / tool / "skills" / go_name / "SKILL.md"
            text = go_file.read_text()
            if tool == "claude-code":
                refs = re.findall(r"\$\{CLAUDE_SKILL_DIR\}/(\.\./[a-z0-9-]+/SKILL\.md)", text)
            else:
                refs = re.findall(r"(\.\./[a-z0-9-]+/SKILL\.md)", text)
            self.assertEqual(len(set(refs)), len(source_skills) - 1, f"{tool} ref count")
            for rel in refs:
                target = (go_file.parent / rel).resolve()
                self.assertTrue(target.is_file(), f"{tool}: missing {rel} -> {target}")

    def test_skills_that_cite_other_skills_include_valid_sibling_paths(self):
        source_skills = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
        for tool in ("claude-code", "cursor", "codex"):
            for skill_file in sorted((HARNESS / tool / "skills").glob("*/SKILL.md")):
                if skill_file.parent.name in ("go", "astack-go"):
                    continue
                _, body = front_matter(skill_file)
                own_source = skill_file.parent.name.removeprefix("astack-")
                cited = {r for r in re.findall(r"\*\*([a-z][a-z0-9-]*)\*\*", body) if r in source_skills and r != own_source}
                if not cited:
                    continue
                match = re.search(r"^Referenced skills: (.+)$", body, re.M)
                self.assertIsNotNone(match, f"{tool}/{skill_file.parent.name} cites {cited} without Referenced skills line")
                line = match.group(1)
                if tool == "claude-code":
                    paths = re.findall(r"\$\{CLAUDE_SKILL_DIR\}/(\.\./[a-z0-9-]+/SKILL\.md)", line)
                else:
                    paths = re.findall(r"\(`(\.\./[a-z0-9-]+/SKILL\.md)`\)", line)
                self.assertEqual(len(paths), len(cited), f"{tool}/{skill_file.parent.name}: {line}")
                for rel in paths:
                    self.assertTrue((skill_file.parent / rel).resolve().is_file(), f"{tool}: broken ref {rel}")

    def test_the_codex_agents_are_valid_toml_files(self):
        worker = tomllib.loads((HARNESS / "codex/agents/astack-worker.toml").read_text())
        self.assertEqual(worker["name"], "astack-worker")
        self.assertIn("RESULT: DONE | NOT DONE", worker["developer_instructions"])
        reviewer = tomllib.loads((HARNESS / "codex/agents/astack-reviewer.toml").read_text())
        self.assertEqual(reviewer["name"], "astack-reviewer")
        self.assertIn("$astack-lead or $astack-review", reviewer["description"])

    def test_the_scripts_are_executable_in_every_package(self):
        for tool in ("claude-code", "cursor", "codex"):
            for script in ("astack-decisions", "astack-stamp", "astack-stamp-hook", "astack-status", "astack-tools", "astack-verify-merge"):
                self.assertTrue((HARNESS / tool / "bin" / script).stat().st_mode & 0o111, f"{tool}/{script}")

    def test_readme_lists_every_skill_and_notice_attributions_hold(self):
        skills = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
        readme = (ROOT / "README.md").read_text()
        listed = set(re.findall(r"^- `([a-z0-9-]+)`:", readme, re.M))
        self.assertEqual(listed, skills)

        notice = (ROOT / "NOTICE.md").read_text()
        adapted = sorted({m for m in re.findall(r"`(skills/[^`]+)`", notice) if (ROOT / m).is_file()})
        for rel in adapted:
            self.assertIn("See NOTICE.md.", (ROOT / rel).read_text(), rel)

    def test_evals_are_well_formed_and_rule_evals_check_rule_reads_without_giving_away_the_name(self):
        cases = sorted(p for p in (ROOT / "evals").iterdir() if p.is_dir())
        self.assertGreaterEqual(len(cases), 9)
        for case in cases:
            yaml_text = (case / "case.yaml").read_text()
            self.assertIn(f"name: {case.name}", yaml_text)
            _, prompt_body = front_matter(case / "prompt.md")
            if "scaffold_script: setup.sh" in yaml_text:
                self.assertTrue((case / "setup.sh").stat().st_mode & 0o111, case.name)
            graders = sorted((case / "graders").glob("*.md"))
            self.assertTrue(graders, f"{case.name} has no graders")
            types = set()
            for grader in graders:
                fields, body = front_matter(grader)
                gtype = fields.get("type")
                self.assertIn(gtype, {"llm", "regex", "tool_used"}, grader)
                types.add(gtype)
                if gtype == "regex":
                    re.compile(fields["pattern"].strip("'\""))
                elif gtype == "llm":
                    self.assertTrue(body.strip(), grader)
            if case.name.startswith("rule-"):
                rule_name = case.name.removeprefix("rule-")
                self.assertNotIn(rule_name, prompt_body, f"{case.name} prompt gives away the rule name")
                self.assertIn("tool_used", types, f"{case.name} must verify the hidden rule was read")
                self.assertIn("llm", types, f"{case.name} must grade the output")


if __name__ == "__main__":
    unittest.main()
