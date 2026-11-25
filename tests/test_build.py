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
        manifests = [
            HARNESS / "claude-code/.claude-plugin/plugin.json",
            HARNESS / "cursor/.cursor-plugin/plugin.json",
            HARNESS / "codex/plugin.json",
            HARNESS / "antigravity/plugin.json",
            HARNESS / "portable/plugin.json",
        ]
        self.assertEqual(len({(load(m)["name"], load(m)["version"]) for m in manifests}), 1)
        for m in manifests:
            data = load(m)
            self.assertEqual(data.get("skills"), "./skills/", f"{m} missing explicit skills path")
            if "claude-code" in str(m):
                self.assertEqual(
                    data.get("agents"),
                    ["./agents/lead.md", "./agents/worker.md", "./agents/reviewer.md", "./agents/researcher.md"],
                    f"{m} must declare all 4 .md agent paths for Claude Code manifest schema",
                )
            else:
                self.assertEqual(data.get("agents"), "./agents/", f"{m} missing explicit agents path")

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
        for tool in ("cursor", "codex", "antigravity", "portable"):
            names = {p.name for p in (HARNESS / tool / "skills").iterdir()}
            self.assertTrue({"astack-go", "astack-lead", "astack-setup", "astack-status", "astack-review"} <= names, names)
            self.assertFalse({"go", "lead", "setup", "status", "review"} & names, names)
        for role in ("lead", "worker", "reviewer", "researcher"):
            self.assertTrue((HARNESS / "claude-code/agents" / f"{role}.md").is_file())
            self.assertTrue((HARNESS / "cursor/agents" / f"astack-{role}.md").is_file())
            self.assertTrue((HARNESS / "codex/agents" / f"astack-{role}.toml").is_file())
            self.assertTrue((HARNESS / "antigravity/agents" / f"astack-{role}.md").is_file())
            self.assertTrue((HARNESS / "portable/agents" / f"astack-{role}.md").is_file())
        # Verify native Antigravity agent & hook frontmatter
        agy_lead_fm, _ = front_matter(HARNESS / "antigravity/agents/astack-lead.md")
        self.assertEqual(agy_lead_fm["subagent"], "true")
        self.assertEqual(agy_lead_fm["mainAgent"], "true")
        agy_rev_fm, _ = front_matter(HARNESS / "antigravity/agents/astack-reviewer.md")
        self.assertEqual(agy_rev_fm["subagent"], "true")
        self.assertEqual(agy_rev_fm["mainAgent"], "false")
        self.assertTrue((HARNESS / "antigravity/hooks.json").is_file())

    def test_only_go_is_visible_in_the_skill_catalog(self):
        for tool, go_name in (("claude-code", "go"), ("cursor", "astack-go"), ("antigravity", "astack-go"), ("portable", "astack-go")):
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

        for tool, go_name in (("claude-code", "go"), ("cursor", "astack-go"), ("codex", "astack-go"), ("antigravity", "astack-go"), ("portable", "astack-go")):
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
        for tool in ("claude-code", "cursor", "codex", "antigravity", "portable"):
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
        for role in ("lead", "worker", "reviewer", "researcher"):
            agent = tomllib.loads((HARNESS / f"codex/agents/astack-{role}.toml").read_text())
            self.assertEqual(agent["name"], f"astack-{role}")
            self.assertTrue(agent["developer_instructions"].strip())
        worker = tomllib.loads((HARNESS / "codex/agents/astack-worker.toml").read_text())
        self.assertIn("$astack-go", worker["description"])
        self.assertIn("$astack-lead", worker["description"])
        self.assertNotIn("Spawn only from", worker["description"])
        self.assertIn("RESULT: DONE | NOT DONE", worker["developer_instructions"])
        reviewer = tomllib.loads((HARNESS / "codex/agents/astack-reviewer.toml").read_text())
        self.assertIn("$astack-go", reviewer["description"])
        self.assertIn("$astack-lead", reviewer["description"])
        self.assertIn("$astack-review", reviewer["description"])

    def test_go_and_review_explicitly_route_to_dedicated_worker_and_reviewer_agents(self):
        # Claude Code
        cc_go = (HARNESS / "claude-code/skills/go/SKILL.md").read_text()
        cc_review = (HARNESS / "claude-code/skills/review/SKILL.md").read_text()
        cc_worker = (HARNESS / "claude-code/agents/worker.md").read_text()
        self.assertIn('subagent_type: "astack:worker"', cc_go)
        self.assertIn('subagent_type: "astack:reviewer"', cc_go)
        self.assertIn('subagent_type: "astack:reviewer"', cc_review)
        self.assertNotIn("Spawn only from", cc_worker)

        # Cursor
        cur_go = (HARNESS / "cursor/skills/astack-go/SKILL.md").read_text()
        cur_review = (HARNESS / "cursor/skills/astack-review/SKILL.md").read_text()
        cur_worker = (HARNESS / "cursor/agents/astack-worker.md").read_text()
        self.assertIn("the `astack-worker` subagent", cur_go)
        self.assertIn("the `astack-reviewer` subagent", cur_go)
        self.assertIn("the `astack-reviewer` subagent", cur_review)
        self.assertNotIn("Spawn only from", cur_worker)

        # Codex
        cx_go = (HARNESS / "codex/skills/astack-go/SKILL.md").read_text()
        cx_review = (HARNESS / "codex/skills/astack-review/SKILL.md").read_text()
        cx_setup = (HARNESS / "codex/skills/astack-setup/SKILL.md").read_text()
        self.assertIn('agent_type: "astack-worker"', cx_go)
        self.assertIn('"astack-reviewer-<slug>"', cx_go)
        self.assertIn('"astack-reviewer-<slug>"', cx_review)
        self.assertIn("one reviewer agent `.toml` per Codex-routable model in `reviewer_pool`", cx_setup)
        self.assertIn("astack-reviewer-<slug>.toml", cx_setup)

    def test_vectored_review_replaces_old_panel_form_in_all_three_harnesses(self):
        for tool, prefix in (("claude-code", ""), ("cursor", "astack-"), ("codex", "astack-"), ("antigravity", "astack-"), ("portable", "astack-")):
            go = (HARNESS / tool / "skills" / f"{prefix}go" / "SKILL.md").read_text()
            review = (HARNESS / tool / "skills" / f"{prefix}review" / "SKILL.md").read_text()
            setup = (HARNESS / tool / "skills" / f"{prefix}setup" / "SKILL.md").read_text()
            lead = (HARNESS / tool / "skills" / f"{prefix}lead" / "SKILL.md").read_text()
            dagify = (HARNESS / tool / "skills" / "dagify" / "SKILL.md").read_text()
            reviewer_agent = (
                HARNESS / tool / "agents" / (
                    "reviewer.md" if tool == "claude-code"
                    else "astack-reviewer.toml" if tool == "codex"
                    else "astack-reviewer.md"
                )
            ).read_text()

            # Every reader uses reviewer_pool and vectored review; old panel form is completely gone
            for text, label in ((go, "go"), (review, "review"), (setup, "setup"), (lead, "lead"), (dagify, "dagify")):
                self.assertIn("reviewer_pool", text, f"{tool}/{label} missing reviewer_pool")
                self.assertNotIn("panel", text.lower(), f"{tool}/{label} still references old panel form")
            for text, label in ((go, "go"), (review, "review"), (lead, "lead"), (dagify, "dagify")):
                self.assertNotIn("roles.reviewer", text, f"{tool}/{label} still references retired roles.reviewer")

            # Vectored review invariants + cross-harness dispatch + cautious stopping + no-internal-leak present in every harness
            self.assertIn("seams", review, f"{tool}/review missing seams vector rule")
            self.assertIn("blast-radius", review, f"{tool}/review missing blast-radius reference")
            self.assertIn("astack-review-ledger", review, f"{tool}/review missing astack-review-ledger")
            self.assertIn("astack-dispatch", review, f"{tool}/review missing astack-dispatch")
            self.assertIn("astack-dispatch", setup, f"{tool}/setup missing astack-dispatch")
            self.assertIn("pi", setup, f"{tool}/setup missing pi harness support")
            self.assertIn("blind to each other", review, f"{tool}/review missing blind-independence rule")
            self.assertIn("Combine, never vote", review, f"{tool}/review missing combine-never-vote rule")
            self.assertIn("fix-equivalence", review, f"{tool}/review missing fix-equivalence overlap rule")
            self.assertIn("Jackknife", review, f"{tool}/review missing 3+-reviewer jackknife rule")
            self.assertIn("landing_blocked", review, f"{tool}/review missing risky landing gate")
            self.assertIn("Never leak internal review status", review, f"{tool}/review missing no-internal-leak rule")
            self.assertIn("LANES.md", review, f"{tool}/review missing LANES.md count logging")
            self.assertIn("which vendors/providers see their code", setup, f"{tool}/setup missing vendor-visibility warning")
            self.assertIn("VECTOR:", reviewer_agent, f"{tool}/reviewer agent missing VECTOR header")
            self.assertIn("MODEL:", reviewer_agent, f"{tool}/reviewer agent missing MODEL header")
            # Review rigor, linked context, plain contradictions, coding rules, leave-feedback, and reviewer/researcher timers
            adv = (HARNESS / tool / "skills" / "adversarial-review" / "SKILL.md").read_text()
            leave_fb = (HARNESS / tool / "skills" / "leave-feedback" / "SKILL.md").read_text()
            researcher_agent = (
                HARNESS / tool / "agents" / (
                    "researcher.md" if tool == "claude-code"
                    else "astack-researcher.toml" if tool == "codex"
                    else "astack-researcher.md"
                )
            ).read_text()
            self.assertIn("no-hidden-flow-control", reviewer_agent, f"{tool}/reviewer missing coding-rule checklist")
            self.assertIn("no-picked-constants", adv, f"{tool}/adversarial-review missing coding-rule checklist")
            self.assertIn("linked issue", review.lower(), f"{tool}/review missing linked-context check")
            self.assertIn("contradiction", reviewer_agent.lower(), f"{tool}/reviewer missing plain-contradiction rule")
            self.assertIn("reviewer_minutes", setup, f"{tool}/setup missing reviewer_minutes")
            self.assertIn("researcher_minutes", setup, f"{tool}/setup missing researcher_minutes")
            self.assertIn("reviewer_minutes", lead, f"{tool}/lead missing reviewer timer enforcement")
            self.assertIn("researcher_minutes", lead, f"{tool}/lead missing researcher timer enforcement")
            self.assertIn("role reviewer", lead, f"{tool}/lead missing reviewer LANES.md clock logging")
            self.assertIn("role researcher", lead, f"{tool}/lead missing researcher LANES.md clock logging")
            self.assertIn("Wind down at", reviewer_agent, f"{tool}/reviewer missing wind-down clock rule")
            self.assertIn("Wind down at", researcher_agent, f"{tool}/researcher missing wind-down clock rule")
            self.assertIn("REVISE", leave_fb, f"{tool}/leave-feedback missing mandatory second-agent pre-post audit")
            self.assertIn("leave-feedback", review, f"{tool}/review missing leave-feedback reference")
            # Self-discovery of hidden skills in ALL 4 agents across ALL 5 harnesses
            for role in ("lead", "worker", "reviewer", "researcher"):
                agent_file = HARNESS / tool / "agents" / (
                    f"{role}.md" if tool == "claude-code"
                    else f"astack-{role}.toml" if tool == "codex"
                    else f"astack-{role}.md"
                )
                atext = agent_file.read_text()
                self.assertIn("Finding astack skills", atext, f"{tool}/{role} missing skill self-discovery block")
                self.assertIn("astack-tools skills-dir", atext, f"{tool}/{role} missing astack-tools skills-dir lookup")
                self.assertIn("Skill", atext, f"{tool}/{role} missing warning not to use Skill tool for hidden skills")
            self.assertNotIn("(`..` from this skill)", go, f"{tool}/go still passes broken relative '..' skills path")
            self.assertNotIn("(`..` from this skill", review, f"{tool}/review still passes broken relative '..' skills path")

    @unittest.skipUnless(shutil.which("codex"), "codex CLI not installed")
    def test_codex_registers_worker_and_reviewer_agents_in_prompt_input(self):
        with tempfile.TemporaryDirectory(prefix="astack-codex-agents-") as scratch:
            root = Path(scratch)
            shutil.copytree(HARNESS / "codex/skills", root / "skills")
            shutil.copytree(HARNESS / "codex/agents", root / "agents")
            # Simulate installing one reviewer agent per approved model from $astack-setup
            tmpl = (root / "agents/astack-reviewer.toml").read_text()
            for slug, model in (("openai-gpt-5-4-high", "gpt-5.4"), ("openai-o3-high", "o3")):
                body = tmpl.replace('name = "astack-reviewer"', f'name = "astack-reviewer-{slug}"', 1)
                body = body.replace('developer_instructions = ', f'model = "{model}"\nmodel_reasoning_effort = "high"\ndeveloper_instructions = ', 1)
                (root / f"agents/astack-reviewer-{slug}.toml").write_text(body)
            (root / "agents/astack-reviewer.toml").unlink()
            env = {**os.environ, "CODEX_HOME": str(root)}
            proc = subprocess.run(
                ["codex", "debug", "prompt-input", "hello"],
                capture_output=True, text=True, env=env, cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("astack-lead", proc.stdout)
            self.assertIn("astack-worker", proc.stdout)
            self.assertIn("astack-researcher", proc.stdout)
            self.assertIn("astack-reviewer-openai-gpt-5-4-high", proc.stdout)
            self.assertIn("astack-reviewer-openai-o3-high", proc.stdout)

    def test_the_scripts_are_executable_in_every_package(self):
        for tool in ("claude-code", "cursor", "codex", "antigravity", "portable"):
            for script in (
                "astack-check-gates", "astack-decisions", "astack-dispatch", "astack-review-ledger",
                "astack-stamp", "astack-stamp-hook", "astack-statechart", "astack-status",
                "astack-tools", "astack-verify-merge",
                "astack-watch-pr", "astack-watch-github", "astack-watch-gitlab", "astack-watch-bitbucket",
            ):
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
            self.assertIn("schema_version:", yaml_text, f"{case.name} case.yaml missing schema_version")
            self.assertIn(f"name: {case.name}", yaml_text)
            _, prompt_body = front_matter(case / "prompt.md")
            if (case / "setup.sh").is_file():
                self.assertIn("context:\n  scaffold_script: setup.sh", yaml_text, f"{case.name} must nest scaffold_script under context:")
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

        # Verify vectored-review evals grade actual Agent tool spawns (binding astack:reviewer + model together & exact counts)
        conc_graders = {p.stem: front_matter(p)[0] for p in (ROOT / "evals/vectored-review-concurrency/graders").glob("*.md")}
        self.assertEqual(conc_graders["reviewer-started"].get("min"), "2")
        self.assertIn("astack:reviewer", conc_graders["sonnet-spawned"].get("input_match", ""))
        self.assertIn("sonnet", conc_graders["sonnet-spawned"].get("input_match", ""))
        self.assertIn("astack:reviewer", conc_graders["haiku-spawned"].get("input_match", ""))
        self.assertIn("haiku", conc_graders["haiku-spawned"].get("input_match", ""))
        self.assertEqual(conc_graders["no-general-purpose"].get("max"), "0")

        small_graders = {p.stem: front_matter(p)[0] for p in (ROOT / "evals/vectored-review-small-change/graders").glob("*.md")}
        self.assertEqual(small_graders["reviewer-started"].get("min"), "1")
        self.assertEqual(small_graders["reviewer-started"].get("max"), "1")
        self.assertIn("astack:reviewer", small_graders["sonnet-spawned"].get("input_match", ""))
        self.assertIn("sonnet", small_graders["sonnet-spawned"].get("input_match", ""))
        self.assertIn("astack:reviewer", small_graders["no-worker-model-spawned"].get("input_match", ""))
        self.assertIn("haiku", small_graders["no-worker-model-spawned"].get("input_match", ""))
        self.assertEqual(small_graders["no-worker-model-spawned"].get("min"), "0")
        self.assertEqual(small_graders["no-worker-model-spawned"].get("max"), "0")
        self.assertEqual(small_graders["no-general-purpose"].get("max"), "0")

        cross_graders = {p.stem: front_matter(p)[0] for p in (ROOT / "evals/vectored-review-cross-harness/graders").glob("*.md")}
        self.assertIn("astack-dispatch", cross_graders["dispatch-used"].get("input_match", ""))
        self.assertIn("astack-review-ledger", cross_graders["ledger-used"].get("input_match", ""))
        self.assertEqual(cross_graders["no-general-purpose"].get("max"), "0")
        self.assertIn("no-internal-leak", cross_graders)

        planted_graders = {p.stem: front_matter(p)[0] for p in (ROOT / "evals/vectored-review-planted-bugs/graders").glob("*.md")}
        self.assertEqual(planted_graders["reviewers-continued-past-two"].get("min"), "3")
        self.assertIn("astack-review-ledger", planted_graders["ledger-used"].get("input_match", ""))
        self.assertEqual(planted_graders["no-general-purpose"].get("max"), "0")
        self.assertIn("no-internal-leak", planted_graders)
        for vcase in ("vectored-review-concurrency", "vectored-review-small-change", "vectored-review-cross-harness", "vectored-review-planted-bugs"):
            self.assertTrue((ROOT / "evals" / vcase / "graders" / "no-internal-leak.md").is_file(), f"{vcase} missing no-internal-leak grader")
            # Zero spoon-feeding: prompts must NOT hand the agent internal tool/protocol names!
            _, vprompt = front_matter(ROOT / "evals" / vcase / "prompt.md")
            for leaked_hint in ("astack-review-ledger", "astack-dispatch", "equivalence_checks", "coverage-map", "POOL EXHAUSTED", "risky vector"):
                self.assertNotIn(leaked_hint, vprompt, f"{vcase} prompt spoon-feeds {leaked_hint!r}")
        self.assertTrue((ROOT / "evals/lead-rejects-gamed-gate/verify.py").is_file())
        self.assertTrue((ROOT / "evals/review-checks-context-and-rules/verify.py").is_file())
        self.assertTrue((ROOT / "evals/leave-feedback-audits-before-posting/verify.py").is_file())
        _, gate_prompt = front_matter(ROOT / "evals/lead-rejects-gamed-gate/prompt.md")
        self.assertNotIn("astack-check-gates", gate_prompt)
        self.assertNotIn("astack-verify-merge", gate_prompt)
        _, ctx_prompt = front_matter(ROOT / "evals/review-checks-context-and-rules/prompt.md")
        for leaked_hint in ("no-hidden-flow-control", "no-picked-constants", "no-implicit-states", "tools-useast1-prod", "AD-003"):
            self.assertNotIn(leaked_hint, ctx_prompt, f"review-checks-context-and-rules prompt spoon-feeds {leaked_hint!r}")
        _, lf_prompt = front_matter(ROOT / "evals/leave-feedback-audits-before-posting/prompt.md")
        for leaked_hint in ("leave-feedback", "astack:reviewer", "POOL EXHAUSTED", "coverage-map", "AD-003"):
            self.assertNotIn(leaked_hint, lf_prompt, f"leave-feedback-audits-before-posting prompt spoon-feeds {leaked_hint!r}")

        # Verify find-it/fix-it and bugbash workflows, role separation, and their new evals
        find_it = (ROOT / "skills/find-it/SKILL.md").read_text()
        self.assertLess(
            find_it.index("## 4. Shrink the repro before diagnosing"),
            find_it.index("## 5. Narrow the root cause with runtime evidence"),
            "find-it must shrink the repro BEFORE narrowing the root cause",
        )
        self.assertIn("two consecutive disproved hypotheses", find_it)
        self.assertNotIn("two consecutive misses", find_it)

        lead_src = (ROOT / "skills/lead/SKILL.md").read_text()
        self.assertNotIn("may land directly", lead_src, "lead must never land worker lanes without a reviewer")
        self.assertIn("never land code without a reviewer", lead_src)

        bugbash = (ROOT / "skills/bugbash/SKILL.md").read_text()
        self.assertIn("shrink the repro first", bugbash)
        self.assertIn("reset timers", bugbash)
        self.assertIn("No convergence / stalled", bugbash)
        self.assertIn("prove-it", bugbash)
        self.assertIn("complementary reproduction and investigation methods", bugbash)
        self.assertIn("never writing or applying fixes themselves", bugbash)
        self.assertIn("dispatches a fresh `astack:worker`", bugbash)
        self.assertIn("**slates**", bugbash)

        slates_skill = (ROOT / "skills/slates/SKILL.md").read_text()
        self.assertIn("https://github.com/hyper-light/slates", slates_skill)
        self.assertIn("slates status", slates_skill)
        self.assertIn("git worktree", slates_skill)
        self.assertIn("slates volume destroy", slates_skill)
        self.assertIn("never writing or applying fixes themselves", slates_skill)

        for path in (
            "skills/dagify/SKILL.md",
            "skills/bugbash/SKILL.md",
            "skills/lead/SKILL.md",
            "skills/review/SKILL.md",
            "skills/ab-test/SKILL.md",
            "skills/swarm-hypothesis/SKILL.md",
            "skills/modularize/SKILL.md",
            "agents/worker.md",
            "agents/reviewer.md",
            "agents/lead.md",
        ):
            text = (ROOT / path).read_text()
            self.assertIn("https://github.com/hyper-light/slates", text, f"{path} missing Slates definition/link")
        reviewer_md = (ROOT / "agents/reviewer.md").read_text()
        self.assertIn("resubmits the changes to you for verification", reviewer_md)
        self.assertNotIn("When testing a proposed fix", reviewer_md)
        self.assertIn("make-it-stick", bugbash)
        self.assertIn("rejected root-cause theory", bugbash)
        self.assertIn("failed fix approaches", bugbash)
        self.assertIn("make-it-stick", lead_src)
        self.assertIn("rejected theories", lead_src)
        self.assertIn("failed fix approaches/attempts", (ROOT / "skills/review/SKILL.md").read_text())
        self.assertIn("rejected root-cause theories", (ROOT / "skills/make-it-stick/SKILL.md").read_text())

        bb_fm, _ = front_matter(ROOT / "evals/bugbash-investigates-and-proves-fix/prompt.md")
        self.assertGreaterEqual(int(bb_fm["timeout_seconds"]), 1200)
        bb_judge = (ROOT / "evals/bugbash-investigates-and-proves-fix/graders/judged.md").read_text()
        self.assertIn("not** require internal review-orchestration narration", bb_judge)

        # Verify time-limit watch/swap across swarm flows, deterministic/data-backed prove-it, and whole-environment find-it
        for swarm_path in (
            "skills/bugbash/SKILL.md",
            "skills/ab-test/SKILL.md",
            "skills/swarm-hypothesis/SKILL.md",
            "skills/modularize/SKILL.md",
            "skills/dagify/SKILL.md",
        ):
            stext = (ROOT / swarm_path).read_text()
            self.assertIn("astack-status", stext, f"{swarm_path} missing time-limit watch/swap via astack-status")
            self.assertIn("check_in_minutes", stext, f"{swarm_path} missing check_in_minutes clock check")
            self.assertIn("fresh successor", stext, f"{swarm_path} missing fresh-successor swap rule")

        prove_it = (ROOT / "skills/prove-it/SKILL.md").read_text()
        self.assertIn("Deterministic reproduction", prove_it)
        self.assertIn("usage analytics", prove_it)

        self.assertIn("correlated real data", find_it)
        self.assertIn("never block when unavailable", find_it)
        self.assertIn("traffic emulation", find_it)
        self.assertIn("Build missing acquisition tools or skills", find_it)
        self.assertIn("whole failure environment", find_it)
        self.assertIn("CPU architecture", find_it)

        self.assertTrue((ROOT / "evals/find-it-and-fix-it-bug/verify.py").is_file())
        self.assertTrue((ROOT / "evals/bugbash-investigates-and-proves-fix/verify.py").is_file())
        _, fi_prompt = front_matter(ROOT / "evals/find-it-and-fix-it-bug/prompt.md")
        for leaked_hint in ("find-it", "fix-it", "_in_retry", "no-implicit-states", "shrink"):
            self.assertNotIn(leaked_hint, fi_prompt, f"find-it-and-fix-it-bug prompt spoon-feeds {leaked_hint!r}")
        _, bb_prompt = front_matter(ROOT / "evals/bugbash-investigates-and-proves-fix/prompt.md")
        for leaked_hint in ("find-it", "fix-it", "challenge", "prove-it", "astack:reviewer", "astack:worker", "tenant_id"):
            self.assertNotIn(leaked_hint, bb_prompt, f"bugbash-investigates-and-proves-fix prompt spoon-feeds {leaked_hint!r}")


if __name__ == "__main__":
    unittest.main()
