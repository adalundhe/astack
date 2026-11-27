"""CLI parser and subcommand handlers for astack-watch-tickets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from astack_tickets.adapters import build_adapter, run_adapter_search
from astack_tickets.brief import build_ticket_brief, dispatch_ticket_lead
from astack_tickets.http_client import RateLimitGovernor
from astack_tickets.models import (
    BadInputError,
    EXIT_API_OR_TIMEOUT,
    EXIT_BAD_INPUT,
    EXIT_OK,
    SCHEMA_VERSION,
    TicketItem,
    TicketState,
    TrackerAuthError,
    TrackerKind,
    TrackerNotFoundError,
    TrackerRateLimitError,
    TrackerTransientError,
    atomic_write_text,
    safe_ticket_filename,
    sanitize_text,
    utc_iso,
)
from astack_tickets.state import (
    DurableSprintState,
    WatchLock,
    default_cache_root,
    load_autonomy_from_settings,
    resolve_merge_policy,
    resolve_skills_dir,
    watch_key,
)


def format_tickets_table(items: Sequence[TicketItem]) -> str:
    if not items:
        return "No matching tickets."
    lines = ["| Ticket | Status | Assignee | Labels | Title |", "|---|---|---|---|---|"]
    for t in items:
        lines.append(
            f"| {sanitize_text(t.key, 60, single_line=True)} | "
            f"{sanitize_text(t.status, 40, single_line=True)} | "
            f"{sanitize_text(t.assignee or '-', 40, single_line=True)} | "
            f"{sanitize_text(', '.join(t.labels) or '-', 50, single_line=True)} | "
            f"{sanitize_text(t.title, 80, single_line=True)} |"
        )
    return "\n".join(lines)


def cmd_auth_check(args: argparse.Namespace, opener: Optional[Callable[..., Any]] = None) -> int:
    gov = RateLimitGovernor()
    adapter, _ = build_adapter(args, gov, opener=opener)
    info = adapter.auth_check()
    if args.as_json:
        print(json.dumps(info, indent=2))
    else:
        print(f"{info['tracker']}: authenticated as {info.get('user') or '(unknown)'}")
    return EXIT_OK


def cmd_query(args: argparse.Namespace, opener: Optional[Callable[..., Any]] = None) -> int:
    gov = RateLimitGovernor()
    adapter, _ = build_adapter(args, gov, opener=opener)
    resolved_query, items = run_adapter_search(adapter, args)
    if args.as_json:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "tracker": adapter.tracker.value,
            "query": resolved_query,
            "count": len(items),
            "tickets": [t.to_dict(include_body=False) for t in items],
            "api_budget": gov.state.to_dict(),
        }, indent=2))
    else:
        print(f"Query ({adapter.tracker.value}): {resolved_query}")
        print(format_tickets_table(items))
    return EXIT_OK


def cmd_ingest(args: argparse.Namespace, opener: Optional[Callable[..., Any]] = None) -> int:
    gov = RateLimitGovernor()
    adapter, _ = build_adapter(args, gov, opener=opener)
    if adapter.tracker == TrackerKind.GITHUB:
        ticket = adapter.fetch_ticket(args.ticket, repo=args.repo or "")
    else:
        ticket = adapter.fetch_ticket(args.ticket)

    settings_path = Path(args.settings).expanduser() if args.settings else None
    autonomy = load_autonomy_from_settings(settings_path)
    merge_policy = resolve_merge_policy(autonomy, allow_merge_flag=bool(args.allow_merge))
    state_dir = Path(args.state_dir).expanduser() if args.state_dir else None
    brief_text = build_ticket_brief(
        ticket,
        autonomy=autonomy,
        merge_policy=merge_policy,
        state_dir=state_dir,
        skills_dir=resolve_skills_dir(),
    )

    out_path: Optional[Path] = Path(args.out).expanduser() if args.out else None
    if out_path is None and state_dir is not None:
        out_path = state_dir / "briefs" / f"{safe_ticket_filename(ticket.key)}.md"
    if out_path is not None:
        atomic_write_text(out_path, brief_text)

    if state_dir is not None:
        state = DurableSprintState(state_dir)
        state.upsert_observed(ticket, baseline_ignore=False)
        state.mark(
            ticket.canonical_id,
            TicketState.CLAIMED,
            brief_path=str(out_path) if out_path else None,
            increment_attempts=True,
        )
        state.save()

    if args.as_json:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "ticket": ticket.to_dict(include_body=True),
            "merge_policy": merge_policy,
            "brief_path": str(out_path) if out_path else None,
            "brief": brief_text,
            "api_budget": gov.state.to_dict(),
        }, indent=2))
    elif out_path is not None:
        print(str(out_path))
    else:
        print(brief_text, end="")
    return EXIT_OK


def _dispatch_matched_tickets(
    adapter: Any,
    items: Sequence[TicketItem],
    *,
    state: DurableSprintState,
    state_dir: Path,
    autonomy: Dict[str, Any],
    merge_policy: Dict[str, Any],
    settings_path: Optional[Path],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    dispatches: List[Dict[str, Any]] = []
    for item in items:
        full = (
            adapter.fetch_ticket(item.key, repo=item.project)
            if adapter.tracker == TrackerKind.GITHUB
            else adapter.fetch_ticket(item.key)
        )
        safe_key = safe_ticket_filename(full.key)
        brief_path = state_dir / "briefs" / f"{safe_key}.md"
        report_path = state_dir / "reports" / f"{safe_key}.md"
        atomic_write_text(
            brief_path,
            build_ticket_brief(
                full,
                autonomy=autonomy,
                merge_policy=merge_policy,
                state_dir=state_dir,
                skills_dir=resolve_skills_dir(),
            ),
        )
        d_res = dispatch_ticket_lead(
            full,
            brief_path,
            report_path,
            settings_path=settings_path,
            dispatch_cmd=args.dispatch_cmd,
            cwd=Path(args.cwd).expanduser() if args.cwd else None,
            dry_run=bool(args.dry_run),
        )
        if not args.dry_run:
            new_st = TicketState.IN_PROGRESS if d_res.get("returncode") == 0 else TicketState.FAILED
            state.mark(
                full.canonical_id,
                new_st,
                brief_path=str(brief_path),
                report_path=str(report_path),
                increment_attempts=True,
            )
            state.save()
        dispatches.append({"ticket": full.canonical_id, **d_res})
    return dispatches


def cmd_watch(
    args: argparse.Namespace,
    *,
    opener: Optional[Callable[..., Any]] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    gov = RateLimitGovernor(base_interval=args.interval, max_interval=args.max_interval)
    raw_sig = f"{args.query or ''}|{args.filter_json or ''}|{args.repo or ''}|{args.assignee or ''}|{','.join(args.label or ())}"
    state_dir = (
        Path(args.state_dir).expanduser()
        if args.state_dir
        else (default_cache_root() / watch_key(args.tracker, raw_sig))
    )

    with WatchLock(state_dir / "watch.lock"):
        state = DurableSprintState(state_dir)
        adapter, client = build_adapter(args, gov, initial_etags=state.data.get("etags") or {}, opener=opener)
        settings_path = Path(args.settings).expanduser() if args.settings else None
        autonomy = load_autonomy_from_settings(settings_path)
        merge_policy = resolve_merge_policy(autonomy, allow_merge_flag=bool(args.allow_merge))

        started_mono = time.monotonic()
        idle_polls = 0
        transient_streak = 0
        first_poll = True

        while True:
            try:
                resolved_query, items = run_adapter_search(adapter, args)
                transient_streak = 0
            except TrackerRateLimitError as err:
                elapsed = time.monotonic() - started_mono
                if args.max_wait and (elapsed + err.retry_after) > args.max_wait:
                    print(
                        f"rate limit wait ({err.retry_after:.0f}s) exceeds --max-wait ({args.max_wait}s): {err}",
                        file=sys.stderr,
                    )
                    return EXIT_API_OR_TIMEOUT
                if args.once:
                    print(f"rate limited: {err}", file=sys.stderr)
                    return EXIT_API_OR_TIMEOUT
                sleep_fn(err.retry_after)
                continue
            except TrackerTransientError as err:
                transient_streak += 1
                backoff = min(args.max_interval, max(5.0, (2 ** min(transient_streak, 5)) * 2.0))
                elapsed = time.monotonic() - started_mono
                if args.once or transient_streak >= 5 or (args.max_wait and (elapsed + backoff) > args.max_wait):
                    print(f"tracker unavailable: {err}", file=sys.stderr)
                    return EXIT_API_OR_TIMEOUT
                sleep_fn(backoff)
                continue

            state.data["tracker"] = adapter.tracker.value
            state.data["query"] = resolved_query
            state.data["etags"] = client.export_etags()
            state.data["api_budget"] = gov.state.to_dict()

            baseline = first_poll and bool(args.ignore_existing)
            first_poll = False

            newly_actionable: List[TicketItem] = []
            for item in items:
                is_actionable, _ = state.upsert_observed(item, baseline_ignore=baseline)
                if is_actionable:
                    newly_actionable.append(item)
            state.save()

            if newly_actionable:
                idle_polls = 0
                dispatches = (
                    _dispatch_matched_tickets(
                        adapter,
                        newly_actionable,
                        state=state,
                        state_dir=state_dir,
                        autonomy=autonomy,
                        merge_policy=merge_policy,
                        settings_path=settings_path,
                        args=args,
                    )
                    if args.dispatch
                    else []
                )
                payload = {
                    "schema_version": SCHEMA_VERSION,
                    "event": "tickets_matched",
                    "tracker": adapter.tracker.value,
                    "query": resolved_query,
                    "state_dir": str(state_dir),
                    "merge_policy": merge_policy,
                    "matched": [t.to_dict(include_body=False) for t in newly_actionable],
                    "dispatches": dispatches,
                    "api_budget": gov.state.to_dict(),
                }
                if args.format == "json":
                    print(json.dumps(payload, indent=2), flush=True)
                elif args.format == "table":
                    print(format_tickets_table(newly_actionable), flush=True)
                else:
                    for t in newly_actionable:
                        print(
                            f"{utc_iso()} MATCH {t.canonical_id} [{sanitize_text(t.status, 30, single_line=True)}] "
                            f"{sanitize_text(t.title, 80, single_line=True)} ({t.url})",
                            flush=True,
                        )
                if not args.continuous or args.once:
                    return EXIT_OK
            else:
                idle_polls += 1
                if args.once:
                    if args.format == "json":
                        print(json.dumps({
                            "schema_version": SCHEMA_VERSION,
                            "event": "no_new_matches",
                            "tracker": adapter.tracker.value,
                            "query": resolved_query,
                            "state_dir": str(state_dir),
                            "matched": [],
                            "api_budget": gov.state.to_dict(),
                        }, indent=2))
                    elif args.format == "table":
                        print("No new matching tickets.")
                    return EXIT_OK

            wait_s = gov.compute_sleep(idle_polls=idle_polls)
            elapsed = time.monotonic() - started_mono
            if args.max_wait and (elapsed + wait_s) > args.max_wait:
                print(f"reached --max-wait ({args.max_wait}s) with no new tickets", file=sys.stderr)
                return EXIT_API_OR_TIMEOUT
            sleep_fn(wait_s)


def cmd_status(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).expanduser()
    state = DurableSprintState(state_dir)
    if args.as_json:
        print(json.dumps(state.data, indent=2))
        return EXIT_OK
    tickets = state.data.get("tickets") or {}
    print(f"Sprint state: {state.path} ({len(tickets)} tracked ticket(s))")
    if not tickets:
        return EXIT_OK
    for cid, rec in sorted(tickets.items()):
        pr = f" pr={rec['pr_url']}" if rec.get("pr_url") else ""
        note = f" ({rec['note']})" if rec.get("note") else ""
        print(f"  {cid}: {rec.get('state')} [attempts={rec.get('attempts', 0)}]{pr}{note}")
    return EXIT_OK


def cmd_mark(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).expanduser()
    state = DurableSprintState(state_dir)
    cid = state.find_ticket_key(args.ticket) or args.ticket
    rec = state.mark(cid, TicketState(args.state), pr_url=args.pr, note=args.note)
    state.save()
    if args.as_json:
        print(json.dumps(rec, indent=2))
    else:
        print(f"marked {cid} -> {rec['state']}")
    return EXIT_OK


def _add_tracker_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tracker", required=True, choices=[t.value for t in TrackerKind],
        help="issue tracker (github, jira, linear)",
    )
    parser.add_argument("--host", default="github.com", help="GitHub host (default: github.com, or GHES hostname)")
    parser.add_argument(
        "--github-transport", choices=("graphql", "rest"), default="graphql",
        help="GitHub API transport (default: graphql, with automatic REST fallback when GraphQL quota gets low)",
    )
    parser.add_argument("--base-url", default="", help="Jira base URL (https://org.atlassian.net) or custom Linear GraphQL URL")
    parser.add_argument("--jira-api-version", choices=("auto", "2", "3"), default="auto", help="Jira REST API version")


def _add_query_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", default="", help="GitHub search query, Jira JQL, or Linear shorthand/JSON filter")
    parser.add_argument("--filter-json", default="", help="Linear GraphQL IssueFilter JSON object")
    parser.add_argument("--repo", default="", help="GitHub repository (owner/name)")
    parser.add_argument("--assignee", default="", help="GitHub assignee filter (username or @me)")
    parser.add_argument("--label", action="append", default=[], help="GitHub label filter (repeatable)")
    parser.add_argument("--type", dest="issue_type", default="", help="GitHub issue type filter (e.g. Bug)")
    parser.add_argument("--issue-state", default="", help="GitHub issue state (open|closed)")
    parser.add_argument("--limit", type=int, default=30, help="maximum results per poll (default: 30, max: 100)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="astack-watch-tickets",
        description="Good-citizen ticket queue watcher and ingester for GitHub Issues, Jira, and Linear.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_auth = sub.add_parser("auth-check", help="verify read-only tracker authentication and identity")
    _add_tracker_args(p_auth)
    p_auth.add_argument("--json", action="store_true", dest="as_json")

    p_q = sub.add_parser("query", help="dry-run a tracker query once and print matching tickets")
    _add_tracker_args(p_q)
    _add_query_args(p_q)
    p_q.add_argument("--json", action="store_true", dest="as_json")

    p_w = sub.add_parser("watch", help="watch a tracker query with rate-limit stewardship and durable state")
    _add_tracker_args(p_w)
    _add_query_args(p_w)
    p_w.add_argument("--state-dir", help="durable state/lock directory (default: ~/.cache/astack/sprints/<hash>)")
    p_w.add_argument("--interval", type=float, default=60.0, help="base poll interval in seconds (default: 60)")
    p_w.add_argument("--max-interval", type=float, default=300.0, help="max idle backoff interval in seconds (default: 300)")
    p_w.add_argument("--max-wait", type=float, default=0.0, help="optional max total wait in seconds (0 = unlimited)")
    p_w.add_argument("--once", action="store_true", help="poll once and exit immediately")
    p_w.add_argument("--continuous", action="store_true", help="keep watching after emitting/dispatching matches")
    p_w.add_argument("--ignore-existing", action="store_true", help="mark existing matches seen on first poll and only trigger on new matches")
    p_w.add_argument("--format", choices=("events", "json", "table"), default="events")
    p_w.add_argument("--dispatch", action="store_true", help="autonomously dispatch `astack-dispatch run --role lead` per matched ticket")
    p_w.add_argument("--dispatch-cmd", default="", help="custom dispatch command template ({brief_file}, {report_file}, {ticket_id}, ...)")
    p_w.add_argument("--allow-merge", action="store_true", help="explicitly permit PR merge for matched tickets on this sprint")
    p_w.add_argument("--settings", help="path to settings.json (default: ~/.config/astack/settings.json)")
    p_w.add_argument("--cwd", help="working repository directory for dispatched lead runs")
    p_w.add_argument("--dry-run", action="store_true", help="with --dispatch, write briefs and print commands without executing")

    p_in = sub.add_parser("ingest", help="fetch full ticket details/comments and emit a security-fenced /astack:go brief")
    _add_tracker_args(p_in)
    p_in.add_argument("--ticket", required=True, help="ticket ref (owner/repo#42, #42 with --repo, ENG-123, URL)")
    p_in.add_argument("--repo", default="", help="GitHub repo (owner/name) when --ticket is a bare number")
    p_in.add_argument("--state-dir", help="optional sprint state dir to mark ticket claimed and save brief")
    p_in.add_argument("--out", help="write brief Markdown to this path")
    p_in.add_argument("--allow-merge", action="store_true", help="explicitly permit PR merge for this ticket")
    p_in.add_argument("--settings", help="path to settings.json")
    p_in.add_argument("--json", action="store_true", dest="as_json")

    p_st = sub.add_parser("status", help="display durable sprint queue status")
    p_st.add_argument("--state-dir", required=True)
    p_st.add_argument("--json", action="store_true", dest="as_json")

    p_mk = sub.add_parser("mark", help="update a tracked ticket's lifecycle state in state.json")
    p_mk.add_argument("--state-dir", required=True)
    p_mk.add_argument("--ticket", required=True)
    p_mk.add_argument("--state", required=True, choices=[s.value for s in TicketState])
    p_mk.add_argument("--pr", default=None, help="associated PR/MR URL")
    p_mk.add_argument("--note", default=None, help="short status note")
    p_mk.add_argument("--json", action="store_true", dest="as_json")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "auth-check":
            return cmd_auth_check(args)
        if args.command == "query":
            return cmd_query(args)
        if args.command == "watch":
            return cmd_watch(args)
        if args.command == "ingest":
            return cmd_ingest(args)
        if args.command == "status":
            return cmd_status(args)
        if args.command == "mark":
            return cmd_mark(args)
    except (BadInputError, TrackerAuthError, TrackerNotFoundError) as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_BAD_INPUT
    except (TrackerRateLimitError, TrackerTransientError) as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_API_OR_TIMEOUT
    return EXIT_BAD_INPUT
