"""Linear GraphQL adapter and IssueFilter shorthand/JSON parser."""
from __future__ import annotations

import json
import os
import re
import shlex
import time
from typing import Any, Dict, List, Optional

from ..http_client import (
    GoodCitizenHTTPClient,
    compute_rate_limit_wait,
    is_rate_limited_response,
)
from ..models import (
    BadInputError,
    TicketComment,
    TicketItem,
    TrackerAuthError,
    TrackerKind,
    TrackerNotFoundError,
    TrackerRateLimitError,
)

LINEAR_SEARCH_QUERY = """
query WatchLinearIssues($filter: IssueFilter, $first: Int!) {
  issues(filter: $filter, first: $first, orderBy: updatedAt) {
    nodes {
      id
      identifier
      title
      url
      priority
      priorityLabel
      createdAt
      updatedAt
      state { name type }
      assignee { name email }
      creator { name email }
      team { key name }
      project { name }
      labels(first: 20) { nodes { name } }
    }
  }
}
"""

LINEAR_GET_ISSUE_QUERY = """
query GetLinearIssue($id: String!) {
  issue(id: $id) {
    id
    identifier
    title
    description
    url
    priority
    priorityLabel
    createdAt
    updatedAt
    state { name type }
    assignee { name email }
    creator { name email }
    team { key name }
    project { name }
    labels(first: 30) { nodes { name } }
    comments(first: 50) {
      nodes {
        id
        body
        createdAt
        url
        user { name email }
      }
    }
  }
}
"""

LINEAR_VIEWER_QUERY = """
query LinearViewer {
  viewer {
    id
    name
    email
  }
}
"""


def parse_linear_filter(raw_query: str = "", filter_json: str = "") -> Dict[str, Any]:
    """Build a Linear GraphQL IssueFilter from explicit --filter-json or concise key:value shorthand."""
    if filter_json and filter_json.strip():
        try:
            parsed = json.loads(filter_json)
        except ValueError as exc:
            raise BadInputError(f"invalid --filter-json for Linear: {exc}")
        if not isinstance(parsed, dict):
            raise BadInputError("Linear --filter-json must be a JSON object matching IssueFilter")
        return parsed

    q = (raw_query or "").strip()
    if not q:
        return {"assignee": {"isMe": {"eq": True}}, "state": {"type": {"nin": ["completed", "canceled"]}}}
    if q.startswith("{"):
        return parse_linear_filter(filter_json=q)

    flt: Dict[str, Any] = {}
    for tok in shlex.split(q):
        if ":" not in tok:
            raise BadInputError(
                f"unrecognized Linear filter token {tok!r}; use JSON IssueFilter (--filter-json) "
                "or key:value terms (assignee:me|email, team:KEY, state:Todo,Ready, state_type:unstarted, label:Bug, project:Name)"
            )
        k, _, v = tok.partition(":")
        key = k.strip().lower()
        val = v.strip()
        vals = [x.strip() for x in val.split(",") if x.strip()]
        if key == "assignee":
            if val.lower() in ("me", "@me", "self"):
                flt["assignee"] = {"isMe": {"eq": True}}
            elif "@" in val:
                flt["assignee"] = {"email": {"eqIgnoreCase": val}}
            else:
                flt["assignee"] = {"name": {"eqIgnoreCase": val}}
        elif key == "team":
            flt["team"] = {"key": {"in": vals}} if len(vals) > 1 else {"key": {"eqIgnoreCase": val}}
        elif key == "state":
            flt["state"] = {"name": {"in": vals}} if len(vals) > 1 else {"name": {"eqIgnoreCase": val}}
        elif key in ("state_type", "statetype"):
            flt["state"] = {"type": {"in": vals}} if len(vals) > 1 else {"type": {"eq": val}}
        elif key in ("label", "labels"):
            flt["labels"] = {"some": {"name": {"in": vals}}} if len(vals) > 1 else {"some": {"name": {"eqIgnoreCase": val}}}
        elif key == "project":
            flt["project"] = {"name": {"eqIgnoreCase": val}}
        elif key == "priority":
            try:
                flt["priority"] = {"eq": int(val)}
            except ValueError:
                raise BadInputError(f"Linear priority must be an integer 0..4, got {val!r}")
        else:
            raise BadInputError(f"unsupported Linear shorthand key {key!r}; pass --filter-json for custom IssueFilter fields")
    return flt


class LinearAdapter:
    tracker = TrackerKind.LINEAR

    def __init__(
        self,
        client: GoodCitizenHTTPClient,
        *,
        api_url: str = "https://api.linear.app/graphql",
        token: str = "",
    ) -> None:
        self.api_url = (api_url or os.environ.get("LINEAR_API_URL") or "https://api.linear.app/graphql").strip()
        self.token = (token or os.environ.get("LINEAR_API_KEY") or os.environ.get("LINEAR_TOKEN") or "").strip()
        if not self.token:
            raise TrackerAuthError(
                "Linear authentication not found. Set LINEAR_API_KEY (personal API key or OAuth Bearer token)."
            )
        self.client = client
        # Linear accepts personal API keys (`lin_api_...`) or explicit `Bearer <token>` directly in Authorization.
        self.client.default_headers.update({
            "Authorization": self.token,
            "Accept": "application/json",
        })

    def _graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = self.client.request(
            "POST",
            self.api_url,
            json_body={"query": query, "variables": variables or {}},
            use_etag=False,
        )
        payload = resp.json() or {}
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            msg = "; ".join(str(e.get("message") or e) for e in errors if isinstance(e, dict))
            if any(
                isinstance(e, dict)
                and str((e.get("extensions") or {}).get("code") or "").upper() == "RATELIMITED"
                for e in errors
            ) or is_rate_limited_response(resp.headers, msg):
                wait = compute_rate_limit_wait(self.client.governor, resp.headers, time.time())
                raise TrackerRateLimitError(f"Linear GraphQL rate limited: {msg}", retry_after=wait, resource="graphql")
            if any(
                isinstance(e, dict)
                and str((e.get("extensions") or {}).get("code") or "").upper() in ("AUTHENTICATION_ERROR", "FORBIDDEN")
                for e in errors
            ):
                raise TrackerAuthError(f"Linear authentication/permission error: {msg}")
            raise BadInputError(f"Linear GraphQL error: {msg}")
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    def auth_check(self) -> Dict[str, Any]:
        data = self._graphql(LINEAR_VIEWER_QUERY)
        viewer = data.get("viewer") if isinstance(data.get("viewer"), dict) else {}
        return {
            "tracker": self.tracker.value,
            "api_url": self.api_url,
            "authenticated": bool(viewer.get("id")),
            "user": str(viewer.get("email") or viewer.get("name") or ""),
            "name": str(viewer.get("name") or ""),
            "api_budget": self.client.governor.state.to_dict(),
        }

    def search(self, issue_filter: Dict[str, Any], *, limit: int = 30) -> List[TicketItem]:
        first = max(1, min(100, int(limit)))
        data = self._graphql(LINEAR_SEARCH_QUERY, {"filter": issue_filter, "first": first})
        nodes = ((data.get("issues") or {}).get("nodes") or []) if isinstance(data.get("issues"), dict) else []
        return [self._parse_issue(n) for n in nodes if isinstance(n, dict)]

    def fetch_ticket(self, ticket_id: str) -> TicketItem:
        ref = (ticket_id or "").strip()
        if ref.startswith("linear:"):
            ref = ref.split(":", 1)[1]
        m_url = re.search(r"/issue/([A-Za-z0-9]+-\d+)", ref)
        if m_url:
            ref = m_url.group(1)
        data = self._graphql(LINEAR_GET_ISSUE_QUERY, {"id": ref})
        raw = data.get("issue")
        if not isinstance(raw, dict):
            raise TrackerNotFoundError(f"Linear issue not found: {ticket_id}")
        return self._parse_issue(raw)

    def _parse_issue(self, raw: Dict[str, Any]) -> TicketItem:
        state_obj = raw.get("state") if isinstance(raw.get("state"), dict) else {}
        assignee_obj = raw.get("assignee") if isinstance(raw.get("assignee"), dict) else {}
        creator_obj = raw.get("creator") if isinstance(raw.get("creator"), dict) else {}
        team_obj = raw.get("team") if isinstance(raw.get("team"), dict) else {}
        proj_obj = raw.get("project") if isinstance(raw.get("project"), dict) else {}
        labels_nodes = ((raw.get("labels") or {}).get("nodes") or []) if isinstance(raw.get("labels"), dict) else []
        comments_nodes = ((raw.get("comments") or {}).get("nodes") or []) if isinstance(raw.get("comments"), dict) else []
        comments = tuple(
            TicketComment(
                comment_id=str(c.get("id") or ""),
                author=str((c.get("user") or {}).get("email") or (c.get("user") or {}).get("name") or ""),
                body=str(c.get("body") or ""),
                created_at=str(c.get("createdAt") or ""),
                url=str(c.get("url") or ""),
            )
            for c in comments_nodes
            if isinstance(c, dict)
        )
        key = str(raw.get("identifier") or raw.get("id") or "")
        return TicketItem(
            tracker=TrackerKind.LINEAR,
            ticket_id=str(raw.get("id") or key),
            key=key,
            title=str(raw.get("title") or ""),
            url=str(raw.get("url") or ""),
            status=str(state_obj.get("name") or ""),
            priority=str(raw.get("priorityLabel") or raw.get("priority") or ""),
            assignee=str(assignee_obj.get("email") or assignee_obj.get("name") or ""),
            reporter=str(creator_obj.get("email") or creator_obj.get("name") or ""),
            project=str(proj_obj.get("name") or team_obj.get("key") or ""),
            labels=tuple(str(n.get("name")) for n in labels_nodes if isinstance(n, dict) and n.get("name")),
            body=str(raw.get("description") or ""),
            created_at=str(raw.get("createdAt") or ""),
            updated_at=str(raw.get("updatedAt") or ""),
            comments=comments,
        )
