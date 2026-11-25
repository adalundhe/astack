---
name: werkflow
description: "Author, configure, and run modular DAG workflows with werkflow and werkflow-modules (@step, @requires, CLI). Use for scripted multi-system pipelines."
---

# Werkflow

Author, configure, and run modular DAG workflows with `werkflow` (`https://github.com/adalundhe/werkflow`) and `werkflow-modules` (`https://github.com/adalundhe/werkflow-modules`, Python >= 3.11).

## Setup and execution

- Check `automation.mode` in `~/.config/astack/settings.json` and run `astack-tools doctor`. Never install Python packages under `agentic-only` without explicit permission.
- Under `python-stack`, run `astack-tools install` (`--profile standard` for core modules, or `--profile all` / `--modules docker,aws,jira,metrikflow,appito`). Load into a shell with `eval "$(astack-tools env)"`.
- Prefer `astack-tools install --profile all` over `pip install 'werkflow[all]'`, because it pins fixed `werkflow-docker>=0.4.1` and `werkflow-metrikflow>=0.3.1` releases plus `werkflow-jira` and `werkflow-appito`.
- **Run non-interactively (for agents and CI):**
  ```bash
  astack-tools werkflow run path/to/workflow.py --ci --no-prompt --graceful-abort \
    --config-path .werkflow.json --log-level info --logfiles-directory ./logs
  ```
  - `--ci` disables spinners and interactive graphics.
  - `--no-prompt` resolves prompt values from `.werkflow.json` (`project_options`) or uppercase env vars (`RESULT_KEY.upper()`).
  - `--graceful-abort` catches step exceptions cleanly and calls `workflow.close()`.

## Authoring pattern

```python
from werkflow import Workflow, step, requires
from werkflow_shell import Shell
from werkflow_file import File


@requires(Shell, File)
class RepoCheckWorkflow(Workflow):
    shell = Shell()
    file = File()

    @step()
    async def locate(self):
        cwd = await self.shell.get_current_directory()
        files = await self.file.list_matching_files(cwd, "*.py")
        return {"cwd": cwd, "py_files": files}

    @step("locate")
    async def check(self, cwd: str, py_files: list[str]):
        await self.logger.console.aio.info(f"Checking {len(py_files)} files in {cwd}")
        await self.batch(
            self.shell.run("ruff check ."),
            self.shell.run("pytest -q"),
        )

    async def close(self):
        await self.shell.close()
        await self.file.close()
```

### Core rules and gotchas

- **DAG & concurrency:** `@step('dep_a', 'dep_b', condition=lambda ctx: ..., skip_on_fail=False, prompts=[...])` builds a `networkx.DiGraph`. Each topological wave runs concurrently via `asyncio.gather`.
- **Data passing:**
  - Returning a `dict` merges non-`None` keys into downstream context (`next_args`).
  - Returning a non-dict stores the value under the step method's name (`self.shortname`).
  - Downstream `@step` methods declare matching parameter names. `.env` keys (lowercased), `.werkflow.json` `project_options`, and `command_directory` inject automatically.
- **`Workflow` helpers:**
  - `await self.batch(*coros, timeout=None)` — concurrent `asyncio.gather` (flattens returned lists).
  - `await self.sequence(*coros)` — sequential execution.
  - `await self.as_async(sync_fn, *args, **kwargs)` — offload sync calls via `asyncio.to_thread`.
  - `self.defer(coro_fn, *args, timeout=60, fail_on_timeout=True)` + `await self.finalize(timeout=None)` — background tasks drained later.
  - `await self.wait(coro, timeout=60, fail_on_timeout=True)` — timeout wrapper raising or returning `StepTimeoutError`.
  - `self.get_project_option("key")` — reads `project_options` from `.werkflow.json`.
- **Prompts (`werkflow.prompt`):** `InputPrompt`, `SecurePrompt`, `ConfirmationPrompt`, `OptionPrompt`, `KeyValuePrompt`, `RepeatPrompt`. Give every prompt a `result_key` so `--no-prompt` resolves it from `.werkflow.json` or `RESULT_KEY.upper()`.
- **Single-group discovery rule:** `werkflow run` scans all `Workflow` and `WorkflowGroup` subclasses in the file. In multi-workflow files, either set `priority = 1, 2, ...` on each `Workflow` (no `WorkflowGroup`) or list **every** `Workflow` in one `WorkflowGroup`. Leaving an ungrouped `Workflow` beside a `WorkflowGroup` raises `MultipleWorkflowsViolationError`.
- **Cleanup:** always close modules in `async def close(self)` and keep `logs/` out of git (**cleanup**).

## Available `werkflow-modules`

| Package | Import & class | What it provides |
|---|---|---|
| `werkflow-core` | `werkflow_core.Module` | Base class for authoring custom modules |
| `werkflow-shell` | `werkflow_shell.Shell` | `run`, `eval`, `get_current_directory`, `change_directory`, `get_envar`/`set_envar`, `copy`/`move`/`touch`/`rm` |
| `werkflow-file` | `werkflow_file.File` | `list_matching_files`, `read`, `write` |
| `werkflow-git` | `werkflow_git.Git` | `clone`, `init`, `checkout`, `fetch`, `pull`, `add`, `commit`, `push`, remotes, `.gitignore` |
| `werkflow-github` | `werkflow_github.Github` | Repos, branch protections, repo secrets/variables, security/vulnerability settings |
| `werkflow-http` | `werkflow_http.HTTP` | Async `get`, `post`, `put`, `patch`, `delete`, `options`, `head` |
| `werkflow-docker` | `werkflow_docker.Docker` | Docker image builds/loads, build options/labels/secrets |
| `werkflow-aws` | `werkflow_aws.AWS` | AWS credentials/region config and `boto3` service connections |
| `werkflow-jira` | `werkflow_jira.Jira`, `Issue` | Issue creation (single/batch), lookups, priorities, issue links |
| `werkflow-python` | `werkflow_python.Python` | Python version selection, venv creation/activation, installing requirements |
| `werkflow-secrets` | `werkflow_secrets.Secrets` | Encrypted secret storage/loading across env, files, and JSON |
| `werkflow-encryption` | `werkflow_encryption.Encryption` | Key generation and NaCl / AES-256-GCM encryption & decryption |
| `werkflow-system` | `werkflow_system.System` | OS, CPU, memory, drives, architecture, and users |
| `werkflow-metrikflow` | `werkflow_metrikflow.Metrik` | Recording and sending metrics (`Event`, `Interval`, `Rate`) |
| `werkflow-appito` | `werkflow_appito.Appito` | `upload_file` |

## Managing werkflow automation

- Keep project workflows in `workflows/` (or `scripts/workflows/`) with a `.werkflow.json.example`. Pass secrets via env vars or `werkflow-secrets`, never committed files.
- Test with `--ci --no-prompt --graceful-abort` on a safe local target before hitting real infrastructure (**prove-it**, **safe-to-rerun**).
- Prefer `orchestral` for lightweight DAG waves with SQLite pause/resume. Prefer `taskex` for standalone tracked tasks, watchers, or schedules.

**Done when:** the workflow passes `--ci --no-prompt --graceful-abort` on a safe target, closes all modules in `close()`, leaves no untracked logs, and reruns cleanly.

Referenced skills: `cleanup` (`../cleanup/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `safe-to-rerun` (`../safe-to-rerun/SKILL.md`). Read any cited skill file before acting when its trigger applies.
