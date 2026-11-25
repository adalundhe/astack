"""Watch locking, durable sprint state, settings/autonomy policy, and install-path discovery."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, Optional, Tuple

from .models import (
    BadInputError,
    DEFAULT_AUTONOMY_ALLOW,
    DEFAULT_AUTONOMY_DENY,
    SCHEMA_VERSION,
    TicketItem,
    TicketState,
    atomic_write_text,
    utc_iso,
)

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None  # type: ignore[assignment]


def default_settings_path() -> Path:
    if xdg := os.environ.get("XDG_CONFIG_HOME"):
        return Path(xdg).expanduser() / "astack" / "settings.json"
    return Path.home() / ".config" / "astack" / "settings.json"


def default_cache_root() -> Path:
    if xdg := os.environ.get("XDG_CACHE_HOME"):
        return Path(xdg).expanduser() / "astack" / "sprints"
    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA")
        base = Path(local_app) if local_app else Path.home() / "AppData" / "Local"
        return base / "astack" / "sprints"
    return Path.home() / ".cache" / "astack" / "sprints"


def watch_key(tracker: str, query_spec: str) -> str:
    digest = hashlib.sha256(f"{tracker}|{query_spec}".encode("utf-8")).hexdigest()[:12]
    return f"{tracker}-{digest}"


def load_autonomy_from_settings(settings_path: Optional[Path] = None) -> Dict[str, Any]:
    path = settings_path or default_settings_path()
    default_cfg: Dict[str, Any] = {
        "mode": "supervised",
        "allow": [],
        "deny": list(DEFAULT_AUTONOMY_DENY),
    }
    try:
        if not path.is_file():
            return default_cfg
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default_cfg
    auto = data.get("autonomy") if isinstance(data, dict) else None
    if not isinstance(auto, dict):
        return default_cfg
    mode = str(auto.get("mode") or "supervised").strip().lower()
    if mode not in ("supervised", "unattended"):
        mode = "supervised"
    raw_allow = auto.get("allow")
    raw_deny = auto.get("deny")
    allow = (
        [str(x).strip() for x in raw_allow if str(x).strip()]
        if isinstance(raw_allow, list)
        else (list(DEFAULT_AUTONOMY_ALLOW) if mode == "unattended" else [])
    )
    deny = (
        [str(x).strip() for x in raw_deny if str(x).strip()]
        if isinstance(raw_deny, list)
        else list(DEFAULT_AUTONOMY_DENY)
    )
    return {"mode": mode, "allow": allow, "deny": deny}


def resolve_merge_policy(autonomy: Dict[str, Any], allow_merge_flag: bool = False) -> Dict[str, Any]:
    """Enforce merge_pr boundary: merge only if explicitly in autonomy.allow or opted in on this sprint."""
    allow_set = set(autonomy.get("allow") or ())
    deny_set = set(autonomy.get("deny") or ())
    if allow_merge_flag:
        return {
            "auto_merge_allowed": True,
            "reason": "explicit sprint --allow-merge opt-in",
        }
    if "merge_pr" in allow_set and "merge_pr" not in deny_set:
        return {
            "auto_merge_allowed": True,
            "reason": "merge_pr explicitly enabled in settings.json autonomy.allow",
        }
    return {
        "auto_merge_allowed": False,
        "reason": "merge_pr is not explicitly allowed; drive to merge_ready via watch-pr and hand off to the person",
    }


def load_lead_role_from_settings(settings_path: Path) -> Dict[str, str]:
    try:
        if not settings_path.is_file():
            return {}
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    roles = data.get("roles") if isinstance(data, dict) else None
    if not isinstance(roles, dict):
        return {}
    for role_name in ("lead", "worker"):
        entry = roles.get(role_name)
        if not isinstance(entry, dict):
            continue
        parsed = {
            k: str(entry[k]).strip()
            for k in ("provider", "model", "effort", "harness")
            if entry.get(k) and str(entry[k]).strip().lower() != "default"
        }
        if parsed.get("provider") and parsed.get("model"):
            return parsed
    return {}


def find_astack_dispatch() -> Optional[Path]:
    """Locate sibling astack-dispatch across repo, harness packages, and link-bin --copy installs."""
    lib_dir = Path(__file__).resolve().parent.parent
    for cand in (lib_dir.parent / "bin" / "astack-dispatch", lib_dir.parent / "astack-dispatch"):
        if cand.is_file():
            return cand
    found = shutil.which("astack-dispatch")
    return Path(found) if found else None


def resolve_skills_dir() -> Optional[Path]:
    lib_dir = Path(__file__).resolve().parent.parent
    install_root = lib_dir.parent
    for cand in (install_root / "skills", install_root.parent / "skills"):
        if cand.is_dir() and ((cand / "go" / "SKILL.md").is_file() or (cand / "astack-go" / "SKILL.md").is_file()):
            return cand.resolve()
    return None


class WatchLock:
    """Exclusive per-watch lock preventing duplicate watchers on the same state directory."""

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self._fp: Any = None
        self._created_exclusive = False

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if fcntl is not None:
            fp = open(self.lock_path, "a+", encoding="utf-8")
            try:
                fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fp.seek(0)
                owner = fp.read().strip()
                fp.close()
                raise BadInputError(
                    f"another ticket watcher already holds lock {self.lock_path} ({owner or 'active'})"
                )
            fp.seek(0)
            fp.truncate()
            fp.write(f"pid={os.getpid()} started={utc_iso()}\n")
            fp.flush()
            self._fp = fp
        else:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except FileExistsError:
                existing = (
                    self.lock_path.read_text(encoding="utf-8", errors="replace").strip()
                    if self.lock_path.is_file()
                    else ""
                )
                raise BadInputError(
                    f"another ticket watcher already holds lock {self.lock_path} ({existing or 'active'})"
                )
            os.write(fd, f"pid={os.getpid()} started={utc_iso()}\n".encode("utf-8"))
            os.close(fd)
            self._created_exclusive = True

    def release(self) -> None:
        if self._fp is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(self._fp.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                self._fp.close()
            except OSError:
                pass
            self._fp = None
        elif self._created_exclusive:
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._created_exclusive = False

    def __enter__(self) -> "WatchLock":
        self.acquire()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.release()


class DurableSprintState:
    """Crash-safe atomic queue & dispatch ledger for watched tickets."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "state.json"
        self.data: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "updated_at": utc_iso(),
            "tracker": "",
            "query": "",
            "tickets": {},
            "etags": {},
            "api_budget": {},
        }
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
                if not isinstance(self.data.get("tickets"), dict):
                    self.data["tickets"] = {}
                if not isinstance(self.data.get("etags"), dict):
                    self.data["etags"] = {}
        except (OSError, ValueError):
            pass

    def save(self) -> None:
        self.data["updated_at"] = utc_iso()
        atomic_write_text(self.path, json.dumps(self.data, indent=2) + "\n")

    def get_ticket(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        val = self.data["tickets"].get(canonical_id)
        return val if isinstance(val, dict) else None

    def find_ticket_key(self, raw_id: str) -> Optional[str]:
        if raw_id in self.data["tickets"]:
            return raw_id
        lowered = raw_id.lower()
        for cid, rec in self.data["tickets"].items():
            if (
                cid.lower() == lowered
                or str(rec.get("key", "")).lower() == lowered
                or str(rec.get("ticket_id", "")).lower() == lowered
            ):
                return cid
        return None

    def upsert_observed(self, item: TicketItem, *, baseline_ignore: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """Record an observed ticket; returns (is_newly_actionable, record)."""
        existing = self.get_ticket(item.canonical_id)
        now = utc_iso()
        if existing is None:
            initial_state = TicketState.DONE.value if baseline_ignore else TicketState.QUEUED.value
            rec: Dict[str, Any] = {
                "canonical_id": item.canonical_id,
                "tracker": item.tracker.value,
                "ticket_id": item.ticket_id,
                "key": item.key,
                "title": item.title,
                "url": item.url,
                "tracker_status": item.status,
                "assignee": item.assignee,
                "updated_at": item.updated_at,
                "state": initial_state,
                "first_seen_at": now,
                "last_seen_at": now,
                "attempts": 0,
                "pr_url": "",
                "note": "ignored existing on baseline startup" if baseline_ignore else "",
            }
            self.data["tickets"][item.canonical_id] = rec
            return (not baseline_ignore), rec

        existing["title"] = item.title
        existing["url"] = item.url
        existing["tracker_status"] = item.status
        existing["assignee"] = item.assignee
        existing["last_seen_at"] = now
        prev_updated = str(existing.get("updated_at") or "")
        existing["updated_at"] = item.updated_at
        cur_state = str(existing.get("state") or TicketState.QUEUED.value)
        if cur_state == TicketState.QUEUED.value:
            return True, existing
        # Re-surface failed ticket only if updated upstream since last failure.
        if cur_state == TicketState.FAILED.value and item.updated_at and prev_updated and item.updated_at > prev_updated:
            existing["state"] = TicketState.QUEUED.value
            return True, existing
        return False, existing

    def mark(
        self,
        canonical_id: str,
        new_state: TicketState,
        *,
        pr_url: Optional[str] = None,
        note: Optional[str] = None,
        brief_path: Optional[str] = None,
        report_path: Optional[str] = None,
        increment_attempts: bool = False,
    ) -> Dict[str, Any]:
        rec = self.data["tickets"].setdefault(
            canonical_id,
            {
                "canonical_id": canonical_id,
                "state": new_state.value,
                "first_seen_at": utc_iso(),
                "attempts": 0,
            },
        )
        rec["state"] = new_state.value
        rec["state_changed_at"] = utc_iso()
        if pr_url is not None:
            rec["pr_url"] = pr_url
        if note is not None:
            rec["note"] = note
        if brief_path is not None:
            rec["brief_path"] = brief_path
        if report_path is not None:
            rec["report_path"] = report_path
        if increment_attempts:
            rec["attempts"] = int(rec.get("attempts") or 0) + 1
        return rec
