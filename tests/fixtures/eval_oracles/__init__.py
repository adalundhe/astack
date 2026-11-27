"""Separated offline verification oracles for astack eval cases.

Each `<case-name>.py` module provides `apply(ws: Path)` (and optional `violate(ws: Path)`)
for RED -> GREEN verification of `evals/<case-name>/verify.py` without exposing solutions inside `evals/`.
"""
