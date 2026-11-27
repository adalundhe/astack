"""Separated offline oracle for `skill-werkflow`."""
from __future__ import annotations

import json
from pathlib import Path

_WORKFLOW_SCRIPT = '''"""Composable Werkflow + werkflow-modules pipeline for jira-migrate."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from werkflow import Workflow, WorkflowGroup, requires, step
from werkflow_file import File
from werkflow_jira import Issue, Jira


@requires(File)
class BacklogValidationWorkflow(Workflow):
    file = File()

    @step()
    async def load_backlog(self) -> dict[str, Any]:
        backlog_path = self.get_project_option("backlog_path") or "./repo/data/backlog.json"
        raw = await self.file.read(backlog_path)
        data = json.loads(raw)
        return {"project_key": data["project_key"], "epics": data["epics"]}

    @step("load_backlog")
    async def validate_backlog(self, project_key: str, epics: list[dict[str, Any]]) -> dict[str, Any]:
        if not project_key or not epics:
            raise ValueError("backlog requires non-empty project_key and epics")
        plan = [
            {"project_key": project_key, "epic_key": epic["key"], "summary": epic["summary"], "stories": epic["stories"]}
            for epic in epics
        ]
        return {"migration_plan": plan}

    async def close(self) -> None:
        await self.file.close()


@requires(Jira)
class JiraMigrationWorkflow(Workflow):
    jira = Jira()

    @step()
    async def prepare_issues(self) -> dict[str, Any]:
        dry_run = bool(self.get_project_option("dry_run"))
        backlog_path = Path(self.get_project_option("backlog_path") or "./repo/data/backlog.json")
        data = json.loads(backlog_path.read_text(encoding="utf-8"))
        issues = [
            Issue(project=data["project_key"], summary=epic["summary"], issue_type="Epic")
            for epic in data["epics"]
        ]
        return {"issues": issues, "dry_run": dry_run}

    @step("prepare_issues")
    async def sync_to_jira(self, issues: list[Any], dry_run: bool) -> dict[str, Any]:
        if dry_run:
            await self.logger.console.aio.info(f"dry-run: prepared {len(issues)} epic(s)")
            return {"created_count": 0, "planned_count": len(issues)}
        created = await self.batch(*(self.jira.create_issue(issue) for issue in issues))
        return {"created_count": len(created), "planned_count": len(issues)}

    async def close(self) -> None:
        await self.jira.close()


class JiraMigrateGroup(WorkflowGroup):
    workflows = [BacklogValidationWorkflow, JiraMigrationWorkflow]
'''


def apply(ws: Path) -> dict[str, object]:
    auto_dir = ws / "program" / "astack_home" / "jira-migrate" / "automations" / "epic-migration"
    auto_dir.mkdir(parents=True, exist_ok=True)
    (auto_dir / "automation.json").write_text(
        json.dumps(
            {
                "runner": "werkflow",
                "entrypoint": "workflow.py",
                "description": "Composable Jira epic migration pipeline with BacklogValidationWorkflow and JiraMigrationWorkflow",
                "modules": ["werkflow-file", "werkflow-jira"],
                "updated": "2026-11-26T09:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (auto_dir / ".werkflow.json.example").write_text(
        json.dumps(
            {
                "project_options": {
                    "backlog_path": "./repo/data/backlog.json",
                    "dry_run": True,
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (auto_dir / "workflow.py").write_text(_WORKFLOW_SCRIPT, encoding="utf-8")
    return {
        "final_text": (
            "Saved the jira-migrate Werkflow pipeline under "
            "program/astack_home/jira-migrate/automations/epic-migration/ (./repo left untouched).\n"
            "- Run non-interactively: `astack-tools werkflow run "
            "\"program/astack_home/jira-migrate/automations/epic-migration/workflow.py\" "
            "--ci --no-prompt --graceful-abort "
            "--config-path \"program/astack_home/jira-migrate/automations/epic-migration/.werkflow.json\" "
            "--log-level info --logfiles-directory \"program/astack_home/jira-migrate/automations/epic-migration/logs\"`"
        ),
    }
