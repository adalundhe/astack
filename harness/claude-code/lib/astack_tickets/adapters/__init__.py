"""Tracker adapter factory and unified search dispatch."""
from __future__ import annotations

import argparse
import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import request as urllib_request

from ..http_client import GoodCitizenHTTPClient, RateLimitGovernor
from ..models import TicketItem, TrackerKind
from .github import GitHubIssuesAdapter
from .jira import JiraAdapter, adf_to_text
from .linear import LinearAdapter, parse_linear_filter


def build_adapter(
    args: argparse.Namespace,
    governor: RateLimitGovernor,
    initial_etags: Optional[Dict[str, str]] = None,
    opener: Optional[Callable[[urllib_request.Request, float], Any]] = None,
) -> Tuple[Any, GoodCitizenHTTPClient]:
    client = GoodCitizenHTTPClient(governor, initial_etags=initial_etags, opener=opener)
    tracker = TrackerKind(args.tracker)
    if tracker == TrackerKind.GITHUB:
        return GitHubIssuesAdapter(
            client,
            host=getattr(args, "host", "github.com") or "github.com",
            transport=getattr(args, "github_transport", "graphql") or "graphql",
        ), client
    if tracker == TrackerKind.JIRA:
        return JiraAdapter(
            client,
            base_url=getattr(args, "base_url", "") or "",
            api_version=getattr(args, "jira_api_version", "auto") or "auto",
        ), client
    return LinearAdapter(
        client,
        api_url=getattr(args, "base_url", "") or "https://api.linear.app/graphql",
    ), client


def run_adapter_search(adapter: Any, args: argparse.Namespace) -> Tuple[str, List[TicketItem]]:
    tracker = adapter.tracker
    limit = getattr(args, "limit", 30)
    if tracker == TrackerKind.GITHUB:
        q = adapter.build_query(
            raw_query=getattr(args, "query", "") or "",
            repo=getattr(args, "repo", "") or "",
            assignee=getattr(args, "assignee", "") or "",
            labels=getattr(args, "label", None) or (),
            issue_type=getattr(args, "issue_type", "") or "",
            state=getattr(args, "issue_state", "") or "",
        )
        return q, adapter.search(q, limit=limit)
    if tracker == TrackerKind.JIRA:
        q = (getattr(args, "query", "") or "").strip()
        return q, adapter.search(q, limit=limit)
    flt = parse_linear_filter(getattr(args, "query", "") or "", getattr(args, "filter_json", "") or "")
    return json.dumps(flt, sort_keys=True), adapter.search(flt, limit=limit)


__all__ = [
    "GitHubIssuesAdapter",
    "JiraAdapter",
    "LinearAdapter",
    "adf_to_text",
    "build_adapter",
    "parse_linear_filter",
    "run_adapter_search",
]
