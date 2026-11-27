"""Separated offline oracle for `skill-idk`."""
from __future__ import annotations

from pathlib import Path

_DEMO_SCRIPT = '''#!/usr/bin/env python3
"""Interactive/CLI demo exercising repo/src/limiter.py (TokenBucket vs LeakyBucket)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))
from limiter import LeakyBucket, TokenBucket


def run_comparison(capacity: float, rate: float, burst_size: int) -> None:
    tb = TokenBucket(capacity=capacity, refill_rate=rate, now=0.0)
    lb = LeakyBucket(capacity=capacity, leak_rate=rate, now=0.0)

    print(f"Scenario: capacity={capacity}, rate={rate}/s, immediate burst of {burst_size} requests at t=0.0s")
    tb_allowed = 0
    lb_accepted = 0
    for idx in range(1, burst_size + 1):
        ok_tb = tb.allow(now=0.0)
        ok_lb, delay = lb.submit(now=0.0)
        tb_allowed += int(ok_tb)
        lb_accepted += int(ok_lb)
        print(
            f"  req#{idx} @ t=0.0s | TokenBucket: {'ALLOW (immediate)' if ok_tb else 'REJECT'} "
            f"| LeakyBucket: {f'QUEUE (drain delay {delay}s)' if ok_lb else 'DROP (overflow)'}"
        )

    print(f"Summary at t=0.0s -> TokenBucket immediate allows={tb_allowed}/{burst_size}, LeakyBucket queued={lb_accepted}/{burst_size}")
    print("At t=1.0s (after 1s refill/drain):")
    ok_tb_later = tb.allow(now=1.0)
    ok_lb_later, delay_later = lb.submit(now=1.0)
    print(f"  req#{burst_size + 1} @ t=1.0s | TokenBucket: {'ALLOW' if ok_tb_later else 'REJECT'} | LeakyBucket: {'QUEUE (' + str(delay_later) + 's)' if ok_lb_later else 'DROP'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare TokenBucket and LeakyBucket from repo/src/limiter.py")
    parser.add_argument("--capacity", type=float, default=3.0)
    parser.add_argument("--rate", type=float, default=1.0)
    parser.add_argument("--burst", type=int, default=5)
    args = parser.parse_args()
    run_comparison(args.capacity, args.rate, args.burst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def apply(ws: Path) -> dict[str, object]:
    """Save structured research notes, runnable demo script, and Mermaid explainer for rate-demo."""
    research_dir = ws / "program" / "astack_home" / "rate-demo" / "research" / "rate-limiting"
    research_dir.mkdir(parents=True, exist_ok=True)
    (research_dir / "notes.md").write_text(
        "# Rate Limiting Research — Token Bucket vs Leaky Bucket\n\n"
        "## Question\n"
        "When should `rate-demo` choose `TokenBucket` vs `LeakyBucket` in `repo/src/limiter.py`?\n\n"
        "## Findings\n"
        "1. **TokenBucket permits immediate bursts up to `capacity` and enforces long-term average `refill_rate`** — **Grade A (90)**.\n"
        "   - Source (code, weight 0.9, quote verified): `repo/src/limiter.py:7` — `Allows bursts up to capacity, refilling at refill_rate tokens/sec.`\n"
        "   - Best fit: user-facing APIs where short bursts should complete immediately without queuing delay.\n"
        "2. **LeakyBucket smooths output to a constant `leak_rate` by returning a drain delay and dropping overflow beyond `capacity`** — **Grade A (90)**.\n"
        "   - Source (code, weight 0.9, quote verified): `repo/src/limiter.py:30` — `Queues work up to capacity and drains at a fixed leak_rate units/sec.`\n"
        "   - Best fit: protecting downstream databases or third-party APIs that cannot tolerate traffic spikes.\n",
        encoding="utf-8",
    )

    demo_dir = ws / "program" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    demo_script = demo_dir / "try_limiters.py"
    demo_script.write_text(_DEMO_SCRIPT, encoding="utf-8")
    demo_script.chmod(0o755)

    explainer = (
        "# Token Bucket vs Leaky Bucket in `repo/src/limiter.py`\n\n"
        "## Bottom Line\n"
        "Pick **`TokenBucket`** when short bursts should pass immediately (good for interactive API requests). "
        "Pick **`LeakyBucket`** when downstream services need a steady, paced request stream and bursts must be smoothed or dropped.\n\n"
        "## Flow Comparison\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  Req[Incoming Burst] --> TB[TokenBucket.allow]\n"
        "  TB -->|tokens >= cost| PassNow[Immediate Pass]\n"
        "  TB -->|tokens < cost| RejTB[Reject]\n"
        "  Req --> LB[LeakyBucket.submit]\n"
        "  LB -->|level + units <= capacity| Queue[Accepted with Drain Delay]\n"
        "  LB -->|overflow| DropLB[Drop]\n"
        "```\n\n"
        "## Analogy (and Where It Breaks Down)\n"
        "- **Token bucket** is like an arcade card preloaded with `capacity` tokens that earns `refill_rate` new tokens every second: you can spend saved tokens back-to-back in a burst.\n"
        "- **Leaky bucket** is like a funnel with a narrow spout: pouring a bucket in all at once fills the funnel (queuing delay) and anything past the rim spills (drops).\n"
        "- **Where the analogy breaks down:** `LeakyBucket.submit` in `src/limiter.py` does not hold actual request payloads in memory — it calculates `estimated_drain_delay_sec` mathematically from `level / leak_rate`.\n\n"
        "## Try It Locally\n"
        "- Saved research: `program/astack_home/rate-demo/research/rate-limiting/notes.md`\n"
        "- Run default walkthrough: `python3 -B program/demo/try_limiters.py`\n"
        "- Try a larger burst: `python3 -B program/demo/try_limiters.py --capacity 4 --rate 2 --burst 7`\n"
    )
    (ws / "program" / "EXPLAINER.md").write_text(explainer, encoding="utf-8")

    return {"final_text": explainer}
