"""Recursive-descent parser turning raw TLC state strings into native Python dicts.

Handles TLA+ state conjuncts (`/\\ var = val`), single-variable states (`x = 0`),
strings with escapes, integers, booleans (`TRUE`/`FALSE`), sets (`{...}`),
sequences (`<<...>>`), records (`[k |-> v, ...]`), and function literals
(`(k1 :> v1 @@ k2 :> v2)`), with graceful fallback to raw text for exotic terms.
"""
from __future__ import annotations

import re
from typing import Any

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INT_RE = re.compile(r"-?\d+")


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.n = len(text)
        self.pos = 0

    def skip_ws(self) -> None:
        while self.pos < self.n and self.text[self.pos].isspace():
            self.pos += 1

    def peek(self, count: int = 1) -> str:
        return self.text[self.pos : self.pos + count]

    def match(self, literal: str) -> bool:
        self.skip_ws()
        if self.text.startswith(literal, self.pos):
            self.pos += len(literal)
            return True
        return False

    def parse_value(self) -> Any:
        self.skip_ws()
        if self.pos >= self.n:
            return ""
        ch = self.text[self.pos]
        if ch == '"':
            return self._parse_string()
        if self.peek(2) == "<<":
            return self._parse_sequence()
        if ch == "{":
            return self._parse_set()
        if ch == "[":
            return self._parse_record()
        if ch == "(":
            return self._parse_parens()
        return self._parse_atom()

    def _parse_string(self) -> str:
        assert self.text[self.pos] == '"'
        self.pos += 1
        out: list[str] = []
        while self.pos < self.n:
            c = self.text[self.pos]
            if c == "\\" and self.pos + 1 < self.n:
                nxt = self.text[self.pos + 1]
                esc = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(nxt, nxt)
                out.append(esc)
                self.pos += 2
                continue
            if c == '"':
                self.pos += 1
                break
            out.append(c)
            self.pos += 1
        return "".join(out)

    def _parse_sequence(self) -> list[Any]:
        self.pos += 2  # skip <<
        items: list[Any] = []
        self.skip_ws()
        if self.peek(2) == ">>":
            self.pos += 2
            return items
        while self.pos < self.n:
            items.append(self.parse_value())
            self.skip_ws()
            if self.match(","):
                continue
            if self.peek(2) == ">>":
                self.pos += 2
                break
            break
        return items

    def _parse_set(self) -> Any:
        self.pos += 1  # skip {
        items: list[Any] = []
        self.skip_ws()
        if self.peek(1) == "}":
            self.pos += 1
            return set()
        while self.pos < self.n:
            items.append(self.parse_value())
            self.skip_ws()
            if self.match(","):
                continue
            if self.peek(1) == "}":
                self.pos += 1
                break
            break
        try:
            return set(items)
        except TypeError:
            return items

    def _parse_record(self) -> Any:
        start = self.pos
        self.pos += 1  # skip [
        rec: dict[str, Any] = {}
        self.skip_ws()
        if self.peek(1) == "]":
            self.pos += 1
            return rec
        while self.pos < self.n:
            self.skip_ws()
            key_start = self.pos
            m = _IDENT_RE.match(self.text, self.pos)
            if not m:
                # Fallback: consume until matching ']'
                return self._consume_balanced(start, "[", "]")
            key = m.group(0)
            self.pos = m.end()
            if not self.match("|->"):
                self.pos = key_start
                return self._consume_balanced(start, "[", "]")
            val = self.parse_value()
            rec[key] = val
            self.skip_ws()
            if self.match(","):
                continue
            if self.peek(1) == "]":
                self.pos += 1
                break
            return self._consume_balanced(start, "[", "]")
        return rec

    def _parse_parens(self) -> Any:
        """Parse parenthesized TLA+ function literal `(k1 :> v1 @@ k2 :> v2)` or grouped value."""
        start = self.pos
        self.pos += 1  # skip (
        self.skip_ws()
        if self.peek(1) == ")":
            self.pos += 1
            return {}
        first = self.parse_value()
        self.skip_ws()
        if self.match(":>"):
            mapping: dict[Any, Any] = {}
            val = self.parse_value()
            try:
                mapping[first] = val
            except TypeError:
                mapping[str(first)] = val
            while self.pos < self.n:
                self.skip_ws()
                if self.match("@@"):
                    k = self.parse_value()
                    if not self.match(":>"):
                        return self._consume_balanced(start, "(", ")")
                    v = self.parse_value()
                    try:
                        mapping[k] = v
                    except TypeError:
                        mapping[str(k)] = v
                    continue
                if self.peek(1) == ")":
                    self.pos += 1
                    break
                return self._consume_balanced(start, "(", ")")
            return mapping
        if self.peek(1) == ")":
            self.pos += 1
            return first
        return self._consume_balanced(start, "(", ")")

    def _consume_balanced(self, start: int, open_ch: str, close_ch: str) -> str:
        self.pos = start
        depth = 0
        in_str = False
        while self.pos < self.n:
            c = self.text[self.pos]
            if in_str:
                if c == "\\" and self.pos + 1 < self.n:
                    self.pos += 2
                    continue
                if c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == open_ch:
                    depth += 1
                elif c == close_ch:
                    depth -= 1
                    if depth == 0:
                        self.pos += 1
                        break
            self.pos += 1
        return self.text[start : self.pos].strip()

    def _parse_atom(self) -> Any:
        self.skip_ws()
        start = self.pos
        while self.pos < self.n:
            ch = self.text[self.pos]
            if ch in ",]}):":
                break
            if self.peek(2) in (">>", "@@", ":>"):
                break
            self.pos += 1
        raw = self.text[start : self.pos].strip()
        if raw == "TRUE":
            return True
        if raw == "FALSE":
            return False
        if _INT_RE.fullmatch(raw):
            return int(raw)
        return raw


def parse_tla_value(expr: str) -> Any:
    """Parse a single TLA+ value expression into a native Python value."""
    text = expr.strip()
    if not text:
        return ""
    p = _Parser(text)
    val = p.parse_value()
    p.skip_ws()
    if p.pos < p.n:
        # Unconsumed trailing syntax (e.g. an unparsed infix expression) — check if it's a bare function `(k :> v @@ ...)`
        if text.find(":>") != -1 and not text.startswith("("):
            p2 = _Parser("(" + text + ")")
            v2 = p2.parse_value()
            p2.skip_ws()
            if p2.pos >= p2.n:
                return v2
        return text
    return val


def _split_top_level_conjuncts(raw: str) -> list[str]:
    """Split a TLC state string into top-level `var = value` clauses, preserving nested brackets/strings."""
    cleaned = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return []

    clauses: list[str] = []
    buf: list[str] = []
    depth_paren = 0
    depth_brace = 0
    depth_brack = 0
    depth_angle = 0
    in_str = False

    lines = cleaned.split("\n")
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        at_top = (depth_paren == 0 and depth_brace == 0 and depth_brack == 0 and depth_angle == 0 and not in_str)
        if at_top and stripped.startswith("/\\"):
            if buf:
                clauses.append("\n".join(buf).strip())
                buf = []
            piece = stripped[2:].strip()
            if piece:
                buf.append(piece)
        else:
            buf.append(stripped)

        # Update nesting depth across this line
        i = 0
        ln = len(stripped)
        while i < ln:
            c = stripped[i]
            if in_str:
                if c == "\\" and i + 1 < ln:
                    i += 2
                    continue
                if c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "(":
                    depth_paren += 1
                elif c == ")" and depth_paren > 0:
                    depth_paren -= 1
                elif c == "{":
                    depth_brace += 1
                elif c == "}" and depth_brace > 0:
                    depth_brace -= 1
                elif c == "[":
                    depth_brack += 1
                elif c == "]" and depth_brack > 0:
                    depth_brack -= 1
                elif stripped[i : i + 2] == "<<":
                    depth_angle += 1
                    i += 2
                    continue
                elif stripped[i : i + 2] == ">>" and depth_angle > 0:
                    depth_angle -= 1
                    i += 2
                    continue
            i += 1

    if buf:
        clauses.append("\n".join(buf).strip())
    return clauses


def parse_tla_state(raw: str | dict[str, Any]) -> dict[str, Any]:
    """Parse a TLC state label (or pass through a dict) into `{var_name: python_value}`."""
    if isinstance(raw, dict):
        return dict(raw)
    text = str(raw or "").strip()
    if not text:
        return {}

    result: dict[str, Any] = {}
    clauses = _split_top_level_conjuncts(text)
    for clause in clauses:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", clause, re.S)
        if m:
            result[m.group(1)] = parse_tla_value(m.group(2))
        else:
            # Handle single-line comma-separated fallback (`x=0, y=1`) or bare state name
            if not result and len(clauses) == 1:
                result["_raw"] = text
    if not result:
        result["_raw"] = text
    return result
