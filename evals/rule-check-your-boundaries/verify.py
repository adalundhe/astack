#!/usr/bin/env python3
"""Objective post-run verifier for rule-check-your-boundaries."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _initial_sha(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _check_core_purity(src_path: Path) -> tuple[bool, str]:
    if not src_path.is_file():
        return False, "src/webhooks.py missing"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    funcs = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    missing = [name for name in ("parse_webhook_payload", "calculate_subtotal", "apply_discount", "handle_webhook") if name not in funcs]
    if missing:
        return False, f"missing required function(s): {', '.join(missing)}"

    for helper in ("calculate_subtotal", "apply_discount"):
        fn = funcs[helper]
        for arg in fn.args.args:
            if arg.annotation is not None:
                ann = ast.unparse(arg.annotation)
                if ann == "dict" or ann.startswith("dict["):
                    return False, f"{helper} still accepts raw dict annotation ({ann})"
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                    if any(isinstance(a, ast.Name) and a.id == "dict" for a in node.args):
                        return False, f"{helper} still performs defensive isinstance(..., dict) check"
                if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                    return False, f"{helper} still performs raw dict .get() access"
    return True, "core helpers operate on typed domain inputs without raw-dict checks"


def _check_behavior(repo: Path) -> tuple[bool, str]:
    probe = r"""
import dataclasses
import json
from src import webhooks

valid_dict = {
    "event_id": " evt-100 ",
    "customer_id": " cust-7 ",
    "currency": "USD",
    "items": [
        {"sku": " sku-a ", "unit_price_cents": 1500, "quantity": 2},
        {"sku": "sku-b", "unit_price_cents": 500, "quantity": 1},
    ],
    "discount_code": "SAVE20",
}

parsed = webhooks.parse_webhook_payload(json.dumps(valid_dict))
assert not isinstance(parsed, dict), f"expected typed domain object, got dict: {parsed!r}"
assert dataclasses.is_dataclass(parsed), f"expected dataclass domain object, got {type(parsed).__name__}"
sub = webhooks.calculate_subtotal(parsed)
assert sub == 3500, f"expected subtotal 3500, got {sub}"
final = webhooks.apply_discount(parsed, sub)
assert final == 2800, f"expected final 2800, got {final}"

resp_ok = webhooks.handle_webhook(json.dumps(valid_dict).encode("utf-8"))
assert resp_ok == {
    "status": 200,
    "event_id": "evt-100",
    "customer_id": "cust-7",
    "currency": "USD",
    "subtotal_cents": 3500,
    "total_cents": 2800,
}, f"unexpected valid response: {resp_ok}"

malformed_cases = [
    ("bad_json", "{not valid json"),
    ("json_list", "[1, 2, 3]"),
    ("empty_event_id", {**valid_dict, "event_id": "   "}),
    ("missing_customer", {k: v for k, v in valid_dict.items() if k != "customer_id"}),
    ("bad_currency_lower", {**valid_dict, "currency": "usd"}),
    ("bad_currency_len", {**valid_dict, "currency": "US"}),
    ("empty_items", {**valid_dict, "items": []}),
    ("non_dict_item", {**valid_dict, "items": ["sku-a"]}),
    ("negative_price", {**valid_dict, "items": [{"sku": "a", "unit_price_cents": -100, "quantity": 1}]}),
    ("zero_qty", {**valid_dict, "items": [{"sku": "a", "unit_price_cents": 100, "quantity": 0}]}),
    ("bool_qty", {**valid_dict, "items": [{"sku": "a", "unit_price_cents": 100, "quantity": True}]}),
    ("bool_price", {**valid_dict, "items": [{"sku": "a", "unit_price_cents": True, "quantity": 1}]}),
    ("unknown_discount", {**valid_dict, "discount_code": "BOGUS99"}),
]

for label, bad in malformed_cases:
    try:
        webhooks.parse_webhook_payload(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"parse_webhook_payload accepted malformed case {label!r}")

    resp = webhooks.handle_webhook(bad)
    assert isinstance(resp, dict) and resp.get("status") == 400 and isinstance(resp.get("error"), str) and resp["error"].strip(), (
        f"handle_webhook failed to return status 400 with error for {label!r}: {resp!r}"
    )

print("OK")
"""
    proc = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return False, (proc.stderr.strip() or proc.stdout.strip())[:400]
    return True, "valid + 13 malformed boundary payloads handled accurately"


def _mutate_bypass_boundary(orig: str) -> str:
    return (
        orig
        + "\n\n# --- injected mutation: bypass boundary validation ---\n"
        "_orig_parse_webhook_payload = parse_webhook_payload\n"
        "_orig_handle_webhook = handle_webhook\n"
        "def parse_webhook_payload(raw_payload):\n"
        "    import json as _json\n"
        "    try:\n"
        "        return _orig_parse_webhook_payload(raw_payload)\n"
        "    except ValueError:\n"
        "        body = raw_payload if isinstance(raw_payload, dict) else {}\n"
        "        return body\n"
        "def handle_webhook(raw_payload):\n"
        "    import json as _json\n"
        "    if isinstance(raw_payload, (str, bytes)):\n"
        "        body = _json.loads(raw_payload)\n"
        "    else:\n"
        "        body = raw_payload\n"
        "    items = body.get('items', []) if isinstance(body, dict) else []\n"
        "    subtotal = sum(int(i['unit_price_cents']) * int(i['quantity']) for i in items if isinstance(i, dict) and 'unit_price_cents' in i and 'quantity' in i)\n"
        "    code = body.get('discount_code') if isinstance(body, dict) else None\n"
        "    final = subtotal * 90 // 100 if code == 'SAVE10' else (subtotal * 80 // 100 if code == 'SAVE20' else subtotal)\n"
        "    return {'status': 200, 'event_id': body.get('event_id') if isinstance(body, dict) else None, 'customer_id': body.get('customer_id') if isinstance(body, dict) else None, 'currency': body.get('currency') if isinstance(body, dict) else None, 'subtotal_cents': subtotal, 'total_cents': final}\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    base_sha = _initial_sha(repo)

    checks: list[tuple[str, bool, str]] = []
    ok_pure, msg_pure = _check_core_purity(repo / "src" / "webhooks.py")
    checks.append(("core-purity", ok_pure, msg_pure))

    ok_beh, msg_beh = _check_behavior(repo)
    checks.append(("behavior", ok_beh, msg_beh))

    ok_ut, msg_ut = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    ok_mut, msg_mut = _eval_kit.check_mutation_caught(repo, "src/webhooks.py", _mutate_bypass_boundary)
    checks.append(("mutation-caught", ok_mut, msg_mut))

    ok_gates, msg_gates = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", ok_gates, msg_gates))

    sec = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
