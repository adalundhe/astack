"""Core domain models, typed errors, sanitization, security fencing, and atomic I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import html
import os
from pathlib import Path
import re
from typing import Any, Dict, Optional, Tuple

USER_AGENT = "astack-watch-tickets/1.0 (+https://github.com/adalundhe/astack)"
SCHEMA_VERSION = 1

EXIT_OK = 0
EXIT_BAD_INPUT = 2
EXIT_API_OR_TIMEOUT = 8

ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])"
)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")

DEFAULT_AUTONOMY_ALLOW: Tuple[str, ...] = (
    "local_worktrees_and_experiments",
    "out_of_dir_work",
    "user_space_tool_install",
    "feature_branch_push",
    "feature_branch_rebase_force_with_lease",
    "open_and_update_pr",
    "watch_pr_and_fix_ci",
    "post_audited_pr_replies",
)
DEFAULT_AUTONOMY_DENY: Tuple[str, ...] = (
    "merge_pr",
    "push_protected_branch",
    "close_or_delete_others_pr",
    "prod_deploy_or_destructive_migration",
    "spend_money_or_billing_changes",
    "publish_external_release",
    "weaken_verification_gates",
)


class TrackerKind(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    LINEAR = "linear"


class TicketState(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    PR_OPEN = "pr_open"
    MERGE_READY = "merge_ready"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"


ACTIVE_STATES = frozenset({
    TicketState.CLAIMED.value,
    TicketState.IN_PROGRESS.value,
    TicketState.PR_OPEN.value,
    TicketState.MERGE_READY.value,
    TicketState.DONE.value,
    TicketState.BLOCKED.value,
})


class TicketWatcherError(Exception):
    """Base typed boundary error for ticket watchers."""


class BadInputError(TicketWatcherError):
    """Invalid arguments, query syntax, or lock contention (exit 2)."""


class TrackerAuthError(TicketWatcherError):
    """Authentication or authorization failure (non-retryable, exit 2)."""


class TrackerNotFoundError(TicketWatcherError):
    """Target ticket, project, or repo not found (exit 2)."""


class TrackerRateLimitError(TicketWatcherError):
    """Tracker API rate limit reached (retryable after retry_after seconds)."""

    def __init__(self, message: str, retry_after: float, resource: str = "core") -> None:
        super().__init__(message)
        self.retry_after = max(1.0, float(retry_after))
        self.resource = resource


class TrackerTransientError(TicketWatcherError):
    """Transient HTTP 5xx or network failure (retryable with backoff)."""


@dataclass(frozen=True)
class TicketComment:
    comment_id: str
    author: str
    body: str
    created_at: str = ""
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comment_id": self.comment_id,
            "author": self.author,
            "body": self.body,
            "created_at": self.created_at,
            "url": self.url,
        }


@dataclass(frozen=True)
class TicketItem:
    tracker: TrackerKind
    ticket_id: str
    key: str
    title: str
    url: str
    status: str = ""
    issue_type: str = ""
    priority: str = ""
    assignee: str = ""
    reporter: str = ""
    project: str = ""
    labels: Tuple[str, ...] = ()
    body: str = ""
    created_at: str = ""
    updated_at: str = ""
    comments: Tuple[TicketComment, ...] = ()
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def canonical_id(self) -> str:
        return f"{self.tracker.value}:{self.key}"

    def to_dict(self, include_body: bool = True) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "canonical_id": self.canonical_id,
            "tracker": self.tracker.value,
            "ticket_id": self.ticket_id,
            "key": self.key,
            "title": self.title,
            "url": self.url,
            "status": self.status,
            "issue_type": self.issue_type,
            "priority": self.priority,
            "assignee": self.assignee,
            "reporter": self.reporter,
            "project": self.project,
            "labels": list(self.labels),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_body:
            data["body"] = self.body
            data["comments"] = [c.to_dict() for c in self.comments]
        if self.extra:
            data["extra"] = dict(self.extra)
        return data


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime] = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_timestamp(value: str) -> Optional[datetime]:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def sanitize_text(text: str, max_len: Optional[int] = None, single_line: bool = False) -> str:
    """Strip ANSI escapes, HTML comments/tags, and C0/C1 control characters."""
    cleaned = ANSI_ESCAPE_RE.sub("", text or "")
    cleaned = HTML_COMMENT_RE.sub(" ", cleaned)
    cleaned = HTML_TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = CONTROL_CHAR_RE.sub("", cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    if single_line:
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
    else:
        cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines()).strip()
    if max_len is not None and len(cleaned) > max_len:
        return cleaned[: max(1, max_len - 3)].rstrip() + "..."
    return cleaned


def fence_untrusted(label: str, text: str, max_len: int = 8000) -> str:
    """Wrap untrusted external ticket content inside non-escapable fences."""
    safe_tag = re.sub(r"[^A-Z0-9_]+", "_", label.upper()).strip("_") or "DATA"
    end_marker = f"<<<END_UNTRUSTED_{safe_tag}>>>"
    # Escape closing fences both before HTML tag stripping and after HTML entity unescaping.
    pre_escaped = (text or "").replace(end_marker, "[escaped-fence]")
    cleaned = sanitize_text(pre_escaped, max_len=max_len, single_line=False)
    cleaned = cleaned.replace(end_marker, "[escaped-fence]")
    return f"<<<UNTRUSTED_{safe_tag}>>>\n{cleaned}\n{end_marker}"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    os.replace(tmp, path)


def safe_ticket_filename(key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", key)
