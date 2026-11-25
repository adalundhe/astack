"""Jira adapter (Cloud REST v3 /search/jql + Server/DC v2 fallback + ADF extraction)."""
from __future__ import annotations

import base64
import os
import re
from typing import Any, Dict, List
from urllib import parse as urllib_parse

from ..http_client import GoodCitizenHTTPClient
from ..models import (
    BadInputError,
    TicketComment,
    TicketItem,
    TrackerAuthError,
    TrackerKind,
)


def adf_to_text(node: Any) -> str:
    """Extract clean Markdown-like plain text from Jira Cloud ADF JSON or plain strings."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(item) for item in node)
    if not isinstance(node, dict):
        return str(node)
    ntype = str(node.get("type") or "")
    if ntype == "text":
        return str(node.get("text") or "")
    if ntype == "hardBreak":
        return "\n"
    if ntype == "mention":
        attrs = node.get("attrs") or {}
        return str(attrs.get("text") or attrs.get("id") or "")
    if ntype == "inlineCard":
        attrs = node.get("attrs") or {}
        return str(attrs.get("url") or "")
    children = node.get("content") or []
    inner = "".join(adf_to_text(c) for c in children)
    if ntype in ("paragraph", "heading", "blockquote"):
        return inner.strip() + "\n\n" if inner.strip() else ""
    if ntype == "codeBlock":
        return f"```\n{inner.rstrip()}\n```\n\n"
    if ntype == "listItem":
        return f"- {inner.strip()}\n"
    if ntype in ("bulletList", "orderedList"):
        return inner + "\n"
    return inner


class JiraAdapter:
    tracker = TrackerKind.JIRA

    def __init__(
        self,
        client: GoodCitizenHTTPClient,
        *,
        base_url: str = "",
        email: str = "",
        token: str = "",
        api_version: str = "auto",
    ) -> None:
        raw_base = (base_url or os.environ.get("JIRA_BASE_URL") or os.environ.get("JIRA_URL") or "").strip().rstrip("/")
        if not raw_base:
            raise BadInputError("Jira base URL required: pass --base-url https://your-org.atlassian.net or set JIRA_BASE_URL")
        if not raw_base.startswith(("https://", "http://")):
            raw_base = "https://" + raw_base
        self.base_url = raw_base
        self.email = (email or os.environ.get("JIRA_EMAIL") or os.environ.get("JIRA_USER") or "").strip()
        self.token = (
            token
            or os.environ.get("JIRA_API_TOKEN")
            or os.environ.get("JIRA_TOKEN")
            or os.environ.get("JIRA_PAT")
            or ""
        ).strip()
        if not self.token:
            raise TrackerAuthError(
                f"Jira authentication not found for {self.base_url}. "
                "Set JIRA_EMAIL + JIRA_API_TOKEN (Jira Cloud) or JIRA_TOKEN / JIRA_PAT (Jira Server/DC)."
            )
        self.client = client
        self.api_version = api_version
        if self.email:
            cred = base64.b64encode(f"{self.email}:{self.token}".encode("utf-8")).decode("ascii")
            auth_header = f"Basic {cred}"
        else:
            auth_header = f"Bearer {self.token}"
        self.client.default_headers.update({
            "Authorization": auth_header,
            "Accept": "application/json",
        })

    def _api_v(self) -> str:
        if self.api_version in ("2", "3"):
            return self.api_version
        return "3" if "atlassian.net" in self.base_url.lower() else "2"

    def auth_check(self) -> Dict[str, Any]:
        ver = self._api_v()
        data = self.client.request("GET", f"{self.base_url}/rest/api/{ver}/myself", use_etag=False).json() or {}
        return {
            "tracker": self.tracker.value,
            "base_url": self.base_url,
            "api_version": ver,
            "authenticated": bool(data.get("accountId") or data.get("name") or data.get("emailAddress")),
            "user": str(data.get("emailAddress") or data.get("name") or data.get("displayName") or ""),
            "display_name": str(data.get("displayName") or ""),
            "api_budget": self.client.governor.state.to_dict(),
        }

    def search(self, jql: str, *, limit: int = 30) -> List[TicketItem]:
        clean_jql = (jql or "").strip()
        if not clean_jql:
            raise BadInputError("Jira JQL query required via --query")
        max_results = max(1, min(100, int(limit)))
        fields = [
            "summary", "status", "assignee", "reporter", "issuetype",
            "priority", "labels", "project", "created", "updated",
        ]
        body = {"jql": clean_jql, "maxResults": max_results, "fields": fields}
        ver = self._api_v()
        if ver == "3":
            resp = self.client.request(
                "POST",
                f"{self.base_url}/rest/api/3/search/jql",
                json_body=body,
                use_etag=False,
                allow_404=True,
            )
            if resp.status == 404:
                resp = self.client.request(
                    "POST",
                    f"{self.base_url}/rest/api/2/search",
                    json_body=body,
                    use_etag=False,
                )
        else:
            resp = self.client.request(
                "POST",
                f"{self.base_url}/rest/api/2/search",
                json_body=body,
                use_etag=False,
            )
        payload = resp.json() or {}
        return [self._parse_issue(raw) for raw in (payload.get("issues") or []) if isinstance(raw, dict)]

    def fetch_ticket(self, ticket_key: str, *, include_comments: bool = True) -> TicketItem:
        key = (ticket_key or "").strip()
        if key.startswith("jira:"):
            key = key.split(":", 1)[1]
        m_url = re.search(r"/browse/([A-Za-z][A-Za-z0-9_]*-\d+)", key)
        if m_url:
            key = m_url.group(1)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*-\d+", key):
            raise BadInputError(f"invalid Jira issue key {ticket_key!r}; expected e.g. ENG-123")
        ver = self._api_v()
        fields = "summary,description,status,assignee,reporter,issuetype,priority,labels,project,created,updated,comment"
        url = f"{self.base_url}/rest/api/{ver}/issue/{urllib_parse.quote(key)}?fields={fields}"
        raw = self.client.request("GET", url, use_etag=False).json() or {}
        return self._parse_issue(raw, include_comments=include_comments)

    def _parse_issue(self, raw: Dict[str, Any], *, include_comments: bool = False) -> TicketItem:
        fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
        key = str(raw.get("key") or raw.get("id") or "")
        assignee_obj = fields.get("assignee") if isinstance(fields.get("assignee"), dict) else {}
        reporter_obj = fields.get("reporter") if isinstance(fields.get("reporter"), dict) else {}
        status_obj = fields.get("status") if isinstance(fields.get("status"), dict) else {}
        type_obj = fields.get("issuetype") if isinstance(fields.get("issuetype"), dict) else {}
        prio_obj = fields.get("priority") if isinstance(fields.get("priority"), dict) else {}
        proj_obj = fields.get("project") if isinstance(fields.get("project"), dict) else {}
        comments: List[TicketComment] = []
        if include_comments and isinstance(fields.get("comment"), dict):
            for c in fields["comment"].get("comments") or []:
                if not isinstance(c, dict):
                    continue
                author_obj = c.get("author") if isinstance(c.get("author"), dict) else {}
                comments.append(TicketComment(
                    comment_id=str(c.get("id") or ""),
                    author=str(author_obj.get("emailAddress") or author_obj.get("displayName") or ""),
                    body=adf_to_text(c.get("body")).strip(),
                    created_at=str(c.get("created") or ""),
                ))
        return TicketItem(
            tracker=TrackerKind.JIRA,
            ticket_id=str(raw.get("id") or key),
            key=key,
            title=str(fields.get("summary") or ""),
            url=f"{self.base_url}/browse/{key}" if key else self.base_url,
            status=str(status_obj.get("name") or ""),
            issue_type=str(type_obj.get("name") or ""),
            priority=str(prio_obj.get("name") or ""),
            assignee=str(assignee_obj.get("emailAddress") or assignee_obj.get("displayName") or ""),
            reporter=str(reporter_obj.get("emailAddress") or reporter_obj.get("displayName") or ""),
            project=str(proj_obj.get("key") or ""),
            labels=tuple(str(x) for x in (fields.get("labels") or []) if x),
            body=adf_to_text(fields.get("description")).strip(),
            created_at=str(fields.get("created") or ""),
            updated_at=str(fields.get("updated") or ""),
            comments=tuple(comments),
        )
