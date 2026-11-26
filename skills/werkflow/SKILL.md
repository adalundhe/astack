---
name: werkflow
description: "Turn prompts into saved Werkflow DAG workflows with werkflow-modules, or run, update, and manage them. Use for modular multi-system pipelines."
disable-model-invocation: true
---

# Werkflow

Turn a prompt into a saved, reusable Werkflow workflow—or inspect, author, run, update, and manage existing ones with `werkflow` (`https://github.com/adalundhe/werkflow`) and `werkflow-modules` (`https://github.com/adalundhe/werkflow-modules`, Python >= 3.11).

**When to choose Werkflow:** reach for Werkflow when composing `werkflow-modules` integrations, robust implicit state-passing, or multi-class `WorkflowGroup` pipelines pays off. Strong fits include mass-generating Jira epics and tickets for migrations, collecting enterprise-wide Docker image stats, mass-migrating `requirements.txt` repos to Poetry, and building DORA metrics or small-scale CI/CD engines. You can also pair `taskex` (`TaskRunner`) inside Werkflow for background task management.

## Storage, setup, and lifecycle (cross-OS)

- **Canonical path:** `$HOME/.astack/<project_name>/automations/<automation_name>/` (`%USERPROFILE%\.astack\<project_name>\automations\<automation_name>\` on Windows; `ASTACK_HOME` overrides). Use repo-local `workflows/` only when the user wants it checked into git.
- Resolve and create folders via `astack-tools automations path <project_name> <automation_name> --ensure`. List saved workflows via `astack-tools automations list [--project <project_name>] --runner werkflow [--json]`.
- Check `automation.mode` in `~/.config/astack/settings.json` and run `astack-tools doctor --json`. Under `agentic-only`, ask permission before installing Python packages or running **setup**.
- Under `python-stack`, run `astack-tools install` (`--profile standard`, `--profile all`, or `--modules <comma-list>`). Prefer `astack-tools install --profile all` over `pip install 'werkflow[all]'`, because it pins fixed `werkflow-docker>=0.4.1` and `werkflow-metrikflow>=0.3.1` releases plus `werkflow-jira` and `werkflow-appito`. Load into a shell with `eval "$(astack-tools env)"`.
- **Manage by intent:**
  1. **List / inspect:** run `astack-tools automations list --project <project_name> --runner werkflow` and read `automation.json`, `.werkflow.json.example`, and the entrypoint.
  2. **Create from a prompt:** check **rtfm**, **lookup**, and **analyze-environment** first. Clarify only missing targets, inputs, secrets, or destructive side effects. Replace unnecessary LLM loops with deterministic Python and `werkflow-modules` steps.
  3. **Run non-interactively:** honor `autonomy` (**decisions-in-plain-words**) and test on a safe or dry-run target before touching live infrastructure:
     ```bash
     astack-tools werkflow run "<automation_dir>/workflow.py" --ci --no-prompt --graceful-abort \
       --config-path "<automation_dir>/.werkflow.json" --log-level info --logfiles-directory "<automation_dir>/logs"
     ```
     - `--ci` disables spinners and interactive graphics.
     - `--no-prompt` resolves prompt values from `.werkflow.json` (`project_options`) or uppercase env vars (`RESULT_KEY.upper()`).
     - `--graceful-abort` catches step exceptions cleanly and calls `workflow.close()`.
  4. **Update / retire:** inspect existing files and `.werkflow.json` keys first, keep reruns idempotent (**safe-to-rerun**), prune stale `logs/` cleanly (**cleanup**), and confirm before deleting a saved workflow.

## Folder layout

Keep each `<automation_name>/` folder self-contained:

- `automation.json`: metadata (`runner`: `"werkflow"`, `entrypoint`: `"workflow.py"`, `description`, `modules`, `updated` UTC).
- `workflow.py`: `@requires(...)` `Workflow` subclass(es) and `@step(...)` DAG.
- `.werkflow.json.example`: non-secret `project_options` template (never commit or save real secrets; use env vars or `werkflow-secrets` per **no-leaked-secrets**).
- `logs/`: local run logs (never committed into a repo).

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
- **Cleanup:** always close every module in `async def close(self)` and keep `logs/` out of git (**cleanup**).

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

## Verify and compare

- Test with `--ci --no-prompt --graceful-abort` on a safe local or dry-run target before hitting real infrastructure (**prove-it**, **safe-to-rerun**).
- Prefer **orchestral** for shorter, scriptish shell or stdlib-Python DAG waves where you own state-passing and branching. Prefer **taskex** for general automations, background task management, schedules, watchers, and keep/discard retention (which can also use `werkflow-modules`).

**Done when:** the workflow is saved under `$HOME/.astack/<project_name>/automations/<automation_name>/` (or Windows equivalent), passes `--ci --no-prompt --graceful-abort` on a safe target, closes all modules in `close()`, reruns cleanly, and your reply gives the exact run command.
