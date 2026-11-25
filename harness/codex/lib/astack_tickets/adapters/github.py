"""GitHub Issues adapter (GraphQL default + older-GHES schema fallback + REST ETag/304 fallback)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib import parse as urllib_parse

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

GITHUB_VIEWER_GQL = """
query GitHubTicketViewer {
  rateLimit { cost remaining limit resetAt }
  viewer { login name }
}
"""


def _github_search_gql(include_issue_type: bool = True) -> str:
    itype_field = "issueType { name }" if include_issue_type else ""
    return f"""
query WatchGitHubIssues($query: String!, $first: Int!) {{
  rateLimit {{ cost remaining limit resetAt }}
  viewer {{ login }}
  search(query: $query, type: ISSUE, first: $first) {{
    nodes {{
      ... on Issue {{
        id
        databaseId
        number
        title
        url
        state
        createdAt
        updatedAt
        repository {{ nameWithOwner }}
        author {{ login }}
        assignees(first: 10) {{ nodes {{ login }} }}
        labels(first: 25) {{ nodes {{ name }} }}
        {itype_field}
      }}
    }}
  }}
}}
"""


def _github_get_issue_gql(include_issue_type: bool = True) -> str:
    itype_field = "issueType { name }" if include_issue_type else ""
    return f"""
query GetGitHubIssue($owner: String!, $repo: String!, $number: Int!) {{
  rateLimit {{ cost remaining limit resetAt }}
  repository(owner: $owner, name: $repo) {{
    issue(number: $number) {{
      id
      databaseId
      number
      title
      body
      url
      state
      createdAt
      updatedAt
      repository {{ nameWithOwner }}
      author {{ login }}
      assignees(first: 10) {{ nodes {{ login }} }}
      labels(first: 30) {{ nodes {{ name }} }}
      {itype_field}
      comments(last: 50) {{
        nodes {{
          id
          url
          body
          createdAt
          author {{ login }}
        }}
      }}
    }}
  }}
}}
"""


class GitHubIssuesAdapter:
    tracker = TrackerKind.GITHUB

    def __init__(
        self,
        client: GoodCitizenHTTPClient,
        *,
        host: str = "github.com",
        token: Optional[str] = None,
        transport: str = "graphql",
    ) -> None:
        self.host = (host or "github.com").strip().lower()
        self.api_base = "https://api.github.com" if self.host == "github.com" else f"https://{self.host}/api/v3"
        self.graphql_url = (
            "https://api.github.com/graphql" if self.host == "github.com" else f"https://{self.host}/api/graphql"
        )
        self.transport = "rest" if (transport or "graphql").strip().lower() == "rest" else "graphql"
        self.client = client
        self._token = token if token is not None else self._discover_token()
        self._viewer: Optional[str] = None
        self._supports_issue_type: bool = True
        if not self._token:
            raise TrackerAuthError(
                f"GitHub authentication not found for {self.host}. "
                "Set GH_TOKEN / GITHUB_TOKEN or run `gh auth login`."
            )
        self.client.default_headers.update({
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _discover_token(self) -> str:
        for env_key in ("GH_TOKEN", "GITHUB_TOKEN"):
            if val := os.environ.get(env_key, "").strip():
                return val
        if shutil.which("gh"):
            cmd = ["gh", "auth", "token"]
            if self.host != "github.com":
                cmd.extend(["--hostname", self.host])
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if proc.returncode == 0 and proc.stdout.strip():
                    return proc.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                pass
        return ""

    def _use_graphql(self) -> bool:
        if self.transport == "rest":
            return False
        return not self.client.governor.should_prefer_rest_over_graphql()

    def _graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.client.governor.state.transport = "graphql"
        resp = self.client.request(
            "POST",
            self.graphql_url,
            json_body={"query": query, "variables": variables or {}},
            use_etag=False,
        )
        payload = resp.json() or {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if isinstance(data.get("rateLimit"), dict):
            self.client.governor.observe_graphql_rate_limit(data["rateLimit"])
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            msg = "; ".join(str(e.get("message") or e) for e in errors if isinstance(e, dict))
            if any(
                isinstance(e, dict) and str(e.get("type") or "").upper() == "RATE_LIMITED"
                for e in errors
            ) or is_rate_limited_response(resp.headers, msg):
                wait = compute_rate_limit_wait(self.client.governor, resp.headers, time.time())
                raise TrackerRateLimitError(f"GitHub GraphQL rate limited: {msg}", retry_after=wait, resource="graphql")
            if any(
                isinstance(e, dict) and str(e.get("type") or "").upper() in ("FORBIDDEN", "UNAUTHORIZED")
                for e in errors
            ):
                raise TrackerAuthError(f"GitHub GraphQL authentication/permission error: {msg}")
            if not data:
                raise BadInputError(f"GitHub GraphQL error: {msg}")
            if "issueType" in msg:
                raise BadInputError(f"GitHub GraphQL schema error: {msg}")
        return data

    def auth_check(self) -> Dict[str, Any]:
        if self._use_graphql():
            data = self._graphql(GITHUB_VIEWER_GQL)
            user_obj = data.get("viewer") if isinstance(data.get("viewer"), dict) else {}
            transport = "graphql"
        else:
            self.client.governor.state.transport = "rest"
            user_obj = self.client.request("GET", f"{self.api_base}/user", use_etag=False).json() or {}
            transport = "rest"
        login = str(user_obj.get("login") or "")
        self._viewer = login or self._viewer
        return {
            "tracker": self.tracker.value,
            "host": self.host,
            "transport": transport,
            "authenticated": bool(login),
            "user": login,
            "name": str(user_obj.get("name") or ""),
            "api_budget": self.client.governor.state.to_dict(),
        }

    def viewer_login(self) -> str:
        if not self._viewer:
            info = self.auth_check()
            self._viewer = str(info.get("user") or "")
        return self._viewer

    def build_query(
        self,
        raw_query: str = "",
        *,
        repo: str = "",
        assignee: str = "",
        labels: Sequence[str] = (),
        issue_type: str = "",
        state: str = "",
    ) -> str:
        parts: List[str] = []
        base = (raw_query or "").strip()
        if base:
            parts.append(base)
        if repo and "repo:" not in base:
            parts.append(f"repo:{repo.strip()}")
        if "is:issue" not in base and "is:pr" not in base:
            parts.append("is:issue")
        if state and "is:open" not in base and "is:closed" not in base and "state:" not in base:
            parts.append(f"is:{state.strip().lower()}")
        elif not base and "is:open" not in " ".join(parts) and "is:closed" not in " ".join(parts):
            parts.append("is:open")
        if issue_type and "type:" not in base:
            parts.append(f'type:"{issue_type.strip()}"' if " " in issue_type else f"type:{issue_type.strip()}")
        for lbl in labels:
            clean = lbl.strip()
            if clean:
                parts.append(f'label:"{clean}"' if " " in clean else f"label:{clean}")
        if assignee and "assignee:" not in base:
            parts.append(f"assignee:{assignee.strip()}")
        joined = " ".join(parts).strip()
        if not joined:
            raise BadInputError("GitHub query must not be empty (pass --query or --repo/--assignee/--label)")
        if "@me" in joined:
            me = self.viewer_login()
            if me:
                joined = joined.replace("@me", me)
        return joined

    def search(self, query: str, *, limit: int = 30) -> List[TicketItem]:
        per_page = max(1, min(100, int(limit)))
        if self._use_graphql():
            gql_query = query if "sort:" in query else f"{query} sort:updated-desc"
            try:
                return self._search_graphql(gql_query, first=per_page)
            except TrackerRateLimitError:
                return self._search_rest(query, per_page=per_page)
        return self._search_rest(query, per_page=per_page)

    def _search_graphql(self, gql_query: str, *, first: int) -> List[TicketItem]:
        try:
            data = self._graphql(_github_search_gql(self._supports_issue_type), {"query": gql_query, "first": first})
        except BadInputError as err:
            if self._supports_issue_type and "issueType" in str(err):
                self._supports_issue_type = False
                data = self._graphql(_github_search_gql(False), {"query": gql_query, "first": first})
            else:
                raise
        viewer = data.get("viewer") if isinstance(data.get("viewer"), dict) else {}
        if viewer.get("login"):
            self._viewer = str(viewer["login"])
        nodes = ((data.get("search") or {}).get("nodes") or []) if isinstance(data.get("search"), dict) else []
        return [self._parse_graphql_issue(n) for n in nodes if isinstance(n, dict) and n.get("number")]

    def _search_rest(self, query: str, *, per_page: int) -> List[TicketItem]:
        self.client.governor.state.transport = "rest"
        params = urllib_parse.urlencode({
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": str(per_page),
        })
        url = f"{self.api_base}/search/issues?{params}"
        payload = self.client.request("GET", url, use_etag=True).json() or {}
        items: List[TicketItem] = []
        for raw in payload.get("items") or []:
            if not isinstance(raw, dict) or "pull_request" in raw:
                continue
            items.append(self._parse_issue(raw))
        return items

    def fetch_ticket(self, ticket_ref: str, *, repo: str = "", include_comments: bool = True) -> TicketItem:
        owner_repo, num = self._parse_ref(ticket_ref, repo)
        if self._use_graphql():
            owner, _, repo_name = owner_repo.partition("/")
            try:
                return self._fetch_ticket_graphql(owner, repo_name, num, include_comments=include_comments)
            except TrackerRateLimitError:
                return self._fetch_ticket_rest(owner_repo, num, include_comments=include_comments)
        return self._fetch_ticket_rest(owner_repo, num, include_comments=include_comments)

    def _fetch_ticket_graphql(self, owner: str, repo_name: str, num: int, *, include_comments: bool) -> TicketItem:
        variables = {"owner": owner, "repo": repo_name, "number": num}
        try:
            data = self._graphql(_github_get_issue_gql(self._supports_issue_type), variables)
        except BadInputError as err:
            if self._supports_issue_type and "issueType" in str(err):
                self._supports_issue_type = False
                data = self._graphql(_github_get_issue_gql(False), variables)
            else:
                raise
        repo_obj = data.get("repository") if isinstance(data.get("repository"), dict) else {}
        raw = repo_obj.get("issue") if isinstance(repo_obj.get("issue"), dict) else None
        if raw is None:
            raise TrackerNotFoundError(f"GitHub issue not found: {owner}/{repo_name}#{num}")
        return self._parse_graphql_issue(raw, repo_hint=f"{owner}/{repo_name}", include_comments=include_comments)

    def _fetch_ticket_rest(self, owner_repo: str, num: int, *, include_comments: bool) -> TicketItem:
        self.client.governor.state.transport = "rest"
        raw = self.client.request("GET", f"{self.api_base}/repos/{owner_repo}/issues/{num}", use_etag=False).json() or {}
        comments: List[TicketComment] = []
        if include_comments and int(raw.get("comments") or 0) > 0:
            c_url = f"{self.api_base}/repos/{owner_repo}/issues/{num}/comments?per_page=50"
            for c in self.client.request("GET", c_url, use_etag=False).json() or []:
                if not isinstance(c, dict):
                    continue
                comments.append(TicketComment(
                    comment_id=str(c.get("id") or ""),
                    author=str((c.get("user") or {}).get("login") or ""),
                    body=str(c.get("body") or ""),
                    created_at=str(c.get("created_at") or ""),
                    url=str(c.get("html_url") or ""),
                ))
        return self._parse_issue(raw, repo_hint=owner_repo, comments=tuple(comments))

    def _parse_graphql_issue(
        self,
        raw: Dict[str, Any],
        *,
        repo_hint: str = "",
        include_comments: bool = False,
    ) -> TicketItem:
        repo_obj = raw.get("repository") if isinstance(raw.get("repository"), dict) else {}
        repo_name = repo_hint or str(repo_obj.get("nameWithOwner") or "")
        num = int(raw.get("number") or 0)
        key = f"{repo_name}#{num}" if repo_name else f"#{num}"
        assignee_nodes = ((raw.get("assignees") or {}).get("nodes") or []) if isinstance(raw.get("assignees"), dict) else []
        assignees = [str(a.get("login")) for a in assignee_nodes if isinstance(a, dict) and a.get("login")]
        label_nodes = ((raw.get("labels") or {}).get("nodes") or []) if isinstance(raw.get("labels"), dict) else []
        labels = tuple(str(n.get("name")) for n in label_nodes if isinstance(n, dict) and n.get("name"))
        itype_obj = raw.get("issueType") if isinstance(raw.get("issueType"), dict) else {}
        comments: List[TicketComment] = []
        if include_comments and isinstance(raw.get("comments"), dict):
            for c in raw["comments"].get("nodes") or []:
                if not isinstance(c, dict):
                    continue
                comments.append(TicketComment(
                    comment_id=str(c.get("id") or ""),
                    author=str((c.get("author") or {}).get("login") or ""),
                    body=str(c.get("body") or ""),
                    created_at=str(c.get("createdAt") or ""),
                    url=str(c.get("url") or ""),
                ))
        return TicketItem(
            tracker=TrackerKind.GITHUB,
            ticket_id=str(raw.get("databaseId") or raw.get("id") or key),
            key=key,
            title=str(raw.get("title") or ""),
            url=str(raw.get("url") or ""),
            status=str(raw.get("state") or "").lower(),
            issue_type=str(itype_obj.get("name") or ""),
            assignee=", ".join(assignees),
            reporter=str((raw.get("author") or {}).get("login") or ""),
            project=repo_name,
            labels=labels,
            body=str(raw.get("body") or ""),
            created_at=str(raw.get("createdAt") or ""),
            updated_at=str(raw.get("updatedAt") or ""),
            comments=tuple(comments),
        )

    def _parse_ref(self, ticket_ref: str, repo_hint: str) -> Tuple[str, int]:
        ref = (ticket_ref or "").strip()
        if ref.startswith("github:"):
            ref = ref.split(":", 1)[1]
        m_url = re.match(r"https?://[^/]+/([^/]+/[^/]+)/issues/(\d+)", ref)
        if m_url:
            return m_url.group(1), int(m_url.group(2))
        m_full = re.match(r"^([^/#\s]+/[^/#\s]+)#(\d+)$", ref)
        if m_full:
            return m_full.group(1), int(m_full.group(2))
        m_num = re.match(r"^#?(\d+)$", ref)
        if m_num and repo_hint:
            return repo_hint.strip(), int(m_num.group(1))
        raise BadInputError(
            f"invalid GitHub issue ref {ticket_ref!r}; use owner/repo#123, full URL, or #123 with --repo"
        )

    def _parse_issue(
        self,
        raw: Dict[str, Any],
        *,
        repo_hint: str = "",
        comments: Tuple[TicketComment, ...] = (),
    ) -> TicketItem:
        repo_url = str(raw.get("repository_url") or "")
        repo_name = repo_hint
        if not repo_name and "/repos/" in repo_url:
            repo_name = repo_url.split("/repos/", 1)[1].strip("/")
        num = int(raw.get("number") or 0)
        key = f"{repo_name}#{num}" if repo_name else f"#{num}"
        assignees = [str(a.get("login")) for a in (raw.get("assignees") or []) if isinstance(a, dict) and a.get("login")]
        if not assignees and isinstance(raw.get("assignee"), dict) and raw["assignee"].get("login"):
            assignees = [str(raw["assignee"]["login"])]
        labels = tuple(
            str(lbl.get("name")) for lbl in (raw.get("labels") or []) if isinstance(lbl, dict) and lbl.get("name")
        )
        itype = str(raw["type"].get("name") or "") if isinstance(raw.get("type"), dict) else ""
        return TicketItem(
            tracker=TrackerKind.GITHUB,
            ticket_id=str(raw.get("id") or key),
            key=key,
            title=str(raw.get("title") or ""),
            url=str(raw.get("html_url") or ""),
            status=str(raw.get("state") or ""),
            issue_type=itype,
            assignee=", ".join(assignees),
            reporter=str((raw.get("user") or {}).get("login") or ""),
            project=repo_name,
            labels=labels,
            body=str(raw.get("body") or ""),
            created_at=str(raw.get("created_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            comments=comments,
        )
