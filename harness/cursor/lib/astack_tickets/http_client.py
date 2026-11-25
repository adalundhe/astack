"""Good-citizen HTTP transport, ETag/304 conditional caching, and adaptive rate-limit governor."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import email.utils
import gzip
import io
import json
import random
import re
import time
from typing import Any, Callable, Dict, Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

from .models import (
    BadInputError,
    TrackerAuthError,
    TrackerNotFoundError,
    TrackerRateLimitError,
    TrackerTransientError,
    USER_AGENT,
    parse_iso_timestamp,
    sanitize_text,
    utc_iso,
)


@dataclass
class RateLimitState:
    resource: str = "core"
    limit: Optional[int] = None
    remaining: Optional[int] = None
    reset_epoch: Optional[float] = None
    graphql_limit: Optional[int] = None
    graphql_remaining: Optional[int] = None
    graphql_reset_epoch: Optional[float] = None
    graphql_cost_total: int = 0
    complexity_limit: Optional[int] = None
    complexity_remaining: Optional[int] = None
    complexity_reset_epoch: Optional[float] = None
    poll_interval_floor: Optional[float] = None
    near_limit: bool = False
    retry_after: Optional[float] = None
    requests_total: int = 0
    not_modified_304: int = 0
    transport: str = "graphql"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource": self.resource,
            "transport": self.transport,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_at": utc_iso(datetime.fromtimestamp(self.reset_epoch, tz=timezone.utc))
            if self.reset_epoch is not None else None,
            "graphql_limit": self.graphql_limit,
            "graphql_remaining": self.graphql_remaining,
            "graphql_reset_at": utc_iso(datetime.fromtimestamp(self.graphql_reset_epoch, tz=timezone.utc))
            if self.graphql_reset_epoch is not None else None,
            "graphql_cost_total": self.graphql_cost_total,
            "complexity_limit": self.complexity_limit,
            "complexity_remaining": self.complexity_remaining,
            "complexity_reset_at": utc_iso(datetime.fromtimestamp(self.complexity_reset_epoch, tz=timezone.utc))
            if self.complexity_reset_epoch is not None else None,
            "poll_interval_floor": self.poll_interval_floor,
            "near_limit": self.near_limit,
            "requests_total": self.requests_total,
            "not_modified_304": self.not_modified_304,
        }


def parse_retry_after(raw: Optional[str], now: float) -> Optional[float]:
    if not raw:
        return None
    val = raw.strip()
    if not val:
        return None
    try:
        return max(1.0, float(val))
    except ValueError:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(1.0, dt.timestamp() - now)
    except (TypeError, ValueError):
        return None


def parse_reset_header(raw: Optional[str], now: float) -> Optional[float]:
    """Parse epoch milliseconds (>1e12), epoch seconds (>1e9), delta seconds, or ISO-8601."""
    if not raw:
        return None
    val = raw.strip()
    if not val:
        return None
    try:
        num = float(val)
        if num > 1_000_000_000_000:
            return num / 1000.0
        if num > 1_000_000_000:
            return num
        return now + max(1.0, num)
    except ValueError:
        pass
    dt = parse_iso_timestamp(val)
    return dt.timestamp() if dt is not None else None


class RateLimitGovernor:
    """Adaptive rate-limit steward across GitHub (GraphQL + REST), Jira, and Linear."""

    def __init__(
        self,
        base_interval: float = 60.0,
        max_interval: float = 300.0,
        jitter_ratio: float = 0.1,
        rng: Optional[Callable[[float, float], float]] = None,
    ) -> None:
        self.base_interval = max(0.0, float(base_interval))
        self.max_interval = max(self.base_interval, float(max_interval))
        self.jitter_ratio = max(0.0, min(0.25, float(jitter_ratio)))
        self._rng = rng or random.uniform
        self.state = RateLimitState()

    def observe_headers(self, headers: Dict[str, str], now: Optional[float] = None) -> None:
        t = time.time() if now is None else now
        lower = {k.lower(): v for k, v in headers.items()}
        if "x-ratelimit-resource" in lower:
            self.state.resource = lower["x-ratelimit-resource"].strip() or self.state.resource
        for key in ("x-ratelimit-limit", "ratelimit-limit", "x-ratelimit-requests-limit"):
            if key in lower:
                try:
                    self.state.limit = int(float(lower[key].strip()))
                    break
                except ValueError:
                    pass
        for key in ("x-ratelimit-remaining", "ratelimit-remaining", "x-ratelimit-requests-remaining"):
            if key in lower:
                try:
                    self.state.remaining = int(float(lower[key].strip()))
                    break
                except ValueError:
                    pass
        for key in ("x-ratelimit-reset", "ratelimit-reset", "ratelimit-resettime", "x-ratelimit-requests-reset"):
            if key in lower:
                parsed = parse_reset_header(lower[key], t)
                if parsed is not None:
                    self.state.reset_epoch = parsed
                    break
        if "x-ratelimit-complexity-limit" in lower:
            try:
                self.state.complexity_limit = int(float(lower["x-ratelimit-complexity-limit"].strip()))
            except ValueError:
                pass
        if "x-ratelimit-complexity-remaining" in lower:
            try:
                self.state.complexity_remaining = int(float(lower["x-ratelimit-complexity-remaining"].strip()))
            except ValueError:
                pass
        if "x-ratelimit-complexity-reset" in lower:
            parsed = parse_reset_header(lower["x-ratelimit-complexity-reset"], t)
            if parsed is not None:
                self.state.complexity_reset_epoch = parsed
        if "x-poll-interval" in lower:
            try:
                self.state.poll_interval_floor = max(1.0, float(lower["x-poll-interval"].strip()))
            except ValueError:
                pass
        if "x-ratelimit-nearlimit" in lower:
            self.state.near_limit = lower["x-ratelimit-nearlimit"].strip().lower() in ("true", "1", "yes")
        if "retry-after" in lower:
            self.state.retry_after = parse_retry_after(lower["retry-after"], t)

    def observe_graphql_rate_limit(self, rl: Any, now: Optional[float] = None) -> None:
        if not isinstance(rl, dict):
            return
        t = time.time() if now is None else now
        if isinstance(rl.get("limit"), int):
            self.state.graphql_limit = rl["limit"]
        if isinstance(rl.get("remaining"), int):
            self.state.graphql_remaining = rl["remaining"]
        if isinstance(rl.get("cost"), int):
            self.state.graphql_cost_total += max(0, rl["cost"])
        if isinstance(rl.get("resetAt"), str):
            parsed = parse_reset_header(rl["resetAt"], t)
            if parsed is not None:
                self.state.graphql_reset_epoch = parsed

    def should_prefer_rest_over_graphql(self) -> bool:
        rem = self.state.graphql_remaining
        lim = self.state.graphql_limit
        if rem is None:
            return False
        reserve = max(20, int(lim * 0.05)) if lim else 20
        return rem <= reserve

    def _bucket_wait(
        self,
        rem: Optional[int],
        lim: Optional[int],
        reset: Optional[float],
        now: float,
        interval: float,
        est_cost: int,
    ) -> Tuple[Optional[float], float]:
        if rem is not None and rem <= 0 and reset is not None:
            return max(1.0, reset - now), interval
        low_ratio = (rem is not None and lim is not None and lim > 0 and (rem / float(lim)) < 0.20)
        if self.state.near_limit or low_ratio:
            throttled = max(interval * 2.0, self.base_interval * 2.0)
            if rem is not None and reset is not None and reset > now:
                sustainable = ((reset - now) / max(1, rem)) * max(1, est_cost)
                throttled = max(throttled, sustainable)
            interval = min(self.max_interval, throttled) if self.max_interval > 0 else throttled
        return None, interval

    def compute_sleep(
        self,
        idle_polls: int,
        now: Optional[float] = None,
        est_calls_per_poll: int = 1,
        est_complexity_per_poll: int = 250,
    ) -> float:
        t = time.time() if now is None else now
        if self.state.retry_after is not None:
            wait = self.state.retry_after
            self.state.retry_after = None
            return self._apply_jitter(wait, floor=wait)

        if idle_polls > 0 and self.base_interval > 0:
            interval = min(self.max_interval, self.base_interval * (1.5 ** min(idle_polls, 6)))
        else:
            interval = self.base_interval

        if self.state.poll_interval_floor is not None and self.base_interval > 0:
            interval = max(interval, self.state.poll_interval_floor)

        hard_req, interval = self._bucket_wait(
            self.state.remaining, self.state.limit, self.state.reset_epoch, t, interval, est_calls_per_poll
        )
        hard_gql, interval = self._bucket_wait(
            self.state.graphql_remaining,
            self.state.graphql_limit,
            self.state.graphql_reset_epoch,
            t,
            interval,
            est_calls_per_poll,
        )
        hard_cplx, interval = self._bucket_wait(
            self.state.complexity_remaining,
            self.state.complexity_limit,
            self.state.complexity_reset_epoch,
            t,
            interval,
            est_complexity_per_poll,
        )
        hard_waits = [w for w in (hard_req, hard_gql, hard_cplx) if w is not None]
        if hard_waits:
            wait = max(hard_waits)
            return self._apply_jitter(wait, floor=wait)

        return self._apply_jitter(interval, floor=0.0)

    def _apply_jitter(self, seconds: float, floor: float) -> float:
        if seconds <= 0 or self.jitter_ratio <= 0:
            return max(floor, seconds)
        delta = seconds * self.jitter_ratio
        jittered = seconds + self._rng(-delta, delta)
        return max(floor, round(jittered, 3))


@dataclass
class HTTPResponse:
    status: int
    body: bytes
    headers: Dict[str, str]
    from_cache_304: bool = False

    def json(self) -> Any:
        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def _maybe_gunzip(raw: bytes, headers: Dict[str, str]) -> bytes:
    encoding = next((v for k, v in headers.items() if k.lower() == "content-encoding"), "")
    if "gzip" in encoding.lower() and raw:
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
                return gz.read()
        except OSError:
            return raw
    return raw


def is_rate_limited_response(headers: Dict[str, str], body_text: str) -> bool:
    lower = {k.lower(): v for k, v in headers.items()}
    if "retry-after" in lower:
        return True
    for key in (
        "x-ratelimit-remaining",
        "ratelimit-remaining",
        "x-ratelimit-requests-remaining",
        "x-ratelimit-complexity-remaining",
    ):
        if lower.get(key, "").strip() == "0":
            return True
    return bool(
        re.search(
            r"rate\s*limit|too\s+many\s+requests|abuse\s+detection|secondary\s+rate|RATELIMITED",
            body_text,
            re.IGNORECASE,
        )
    )


def compute_rate_limit_wait(governor: RateLimitGovernor, headers: Dict[str, str], now: float) -> float:
    lower = {k.lower(): v for k, v in headers.items()}
    ra = parse_retry_after(lower.get("retry-after"), now)
    if ra is not None:
        return ra
    resets = [
        r
        for r in (
            governor.state.reset_epoch,
            governor.state.graphql_reset_epoch,
            governor.state.complexity_reset_epoch,
        )
        if r is not None and r > now
    ]
    if resets:
        return max(1.0, max(resets) - now + 2.0)
    return max(30.0, governor.base_interval * 2.0)


class GoodCitizenHTTPClient:
    """Stdlib HTTP client with gzip, conditional ETag/304 caching, and rate-limit awareness."""

    def __init__(
        self,
        governor: RateLimitGovernor,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        initial_etags: Optional[Dict[str, str]] = None,
        opener: Optional[Callable[[urllib_request.Request, float], Any]] = None,
    ) -> None:
        self.governor = governor
        self.default_headers = dict(default_headers or {})
        self.timeout = timeout
        self._etags: Dict[str, str] = dict(initial_etags or {})
        self._last_modified: Dict[str, str] = {}
        self._cache: Dict[str, bytes] = {}
        self._opener = opener

    def export_etags(self) -> Dict[str, str]:
        return dict(self._etags)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_body: Any = None,
        use_etag: bool = True,
        allow_404: bool = False,
    ) -> HTTPResponse:
        req_headers = {
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip",
            **self.default_headers,
            **(headers or {}),
        }
        data: Optional[bytes] = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")

        upper = method.upper()
        if upper == "GET" and use_etag and url in self._cache:
            if url in self._etags:
                req_headers["If-None-Match"] = self._etags[url]
            if url in self._last_modified:
                req_headers["If-Modified-Since"] = self._last_modified[url]

        req = urllib_request.Request(url, data=data, headers=req_headers, method=upper)
        self.governor.state.requests_total += 1
        now = time.time()

        try:
            resp_obj = (
                self._opener(req, self.timeout)
                if self._opener
                else urllib_request.urlopen(req, timeout=self.timeout)
            )
            with resp_obj as resp:
                status = getattr(resp, "status", 200)
                resp_headers = {k: v for k, v in resp.headers.items()}
                raw_bytes = resp.read()
        except urllib_error.HTTPError as err:
            status = err.code
            resp_headers = {k: v for k, v in err.headers.items()} if err.headers else {}
            raw_bytes = err.read() if err.fp else b""
            self.governor.observe_headers(resp_headers, now=now)
            if status == 304 and url in self._cache:
                self.governor.state.not_modified_304 += 1
                return HTTPResponse(status=304, body=self._cache[url], headers=resp_headers, from_cache_304=True)
            body_bytes = _maybe_gunzip(raw_bytes, resp_headers)
            body_text = body_bytes.decode("utf-8", errors="replace")
            if status == 404 and allow_404:
                return HTTPResponse(status=404, body=body_bytes, headers=resp_headers)
            if status == 429 or (status == 403 and is_rate_limited_response(resp_headers, body_text)):
                wait = compute_rate_limit_wait(self.governor, resp_headers, now)
                raise TrackerRateLimitError(
                    f"HTTP {status} rate limited on {url}: {sanitize_text(body_text, 200, single_line=True)}",
                    retry_after=wait,
                    resource=self.governor.state.resource,
                )
            if status in (401, 403):
                raise TrackerAuthError(
                    f"HTTP {status} authentication/permission error on {url}: "
                    f"{sanitize_text(body_text, 200, single_line=True)}"
                )
            if status == 404:
                raise TrackerNotFoundError(
                    f"HTTP 404 not found on {url}: {sanitize_text(body_text, 200, single_line=True)}"
                )
            if status >= 500:
                raise TrackerTransientError(
                    f"HTTP {status} server error on {url}: {sanitize_text(body_text, 200, single_line=True)}"
                )
            raise BadInputError(
                f"HTTP {status} error on {url}: {sanitize_text(body_text, 200, single_line=True)}"
            )
        except (urllib_error.URLError, TimeoutError, OSError) as err:
            raise TrackerTransientError(f"network error on {url}: {err}")

        self.governor.observe_headers(resp_headers, now=now)
        body_bytes = _maybe_gunzip(raw_bytes, resp_headers)
        if upper == "GET" and status == 200 and use_etag:
            lower = {k.lower(): v for k, v in resp_headers.items()}
            if "etag" in lower:
                self._etags[url] = lower["etag"]
                self._cache[url] = body_bytes
            if "last-modified" in lower:
                self._last_modified[url] = lower["last-modified"]
                self._cache[url] = body_bytes
        return HTTPResponse(status=status, body=body_bytes, headers=resp_headers)
