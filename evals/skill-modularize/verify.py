#!/usr/bin/env python3
"""Objective post-run verifier for skill-modularize."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _nonempty_lines(text: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.strip())


def _src_imports(py_file: Path, known_modules: set[str]) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = (node.module or "").lstrip(".")
            if mod.startswith("src."):
                mod = mod.removeprefix("src.")
            if mod in known_modules:
                deps.add(mod)
            elif node.level >= 1 and not mod:
                for alias in node.names:
                    if alias.name in known_modules:
                        deps.add(alias.name)
            elif mod == "src":
                for alias in node.names:
                    if alias.name in known_modules:
                        deps.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.removeprefix("src.")
                if name in known_modules:
                    deps.add(name)
    deps.discard(py_file.stem)
    return deps


def _has_cycle(graph: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def _dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, ()):
            if _dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(_dfs(n) for n in graph)


def _break_first_public_func(src: str) -> str:
    tree = ast.parse(src)
    funcs = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]
    if not funcs:
        return src
    sabotage = "\n".join(
        f"\ndef {fn}(*args, **kwargs):\n    raise RuntimeError('injected mutation in {fn}')\n"
        for fn in funcs
    )
    return src + sabotage


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    base_sha_file = ws / "program" / "base_sha.txt"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not base_sha_file.is_file():
        checks.append(("workspace-intact", False, "missing repo or program/base_sha.txt"))
        return _eval_kit.report_and_exit(checks)

    base_sha = base_sha_file.read_text(encoding="utf-8").strip()
    orig_monolith = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/monolith.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    orig_nonempty = _nonempty_lines(orig_monolith)

    src_dir = (repo / "src").resolve()
    monolith_path = src_dir / "monolith.py"
    if not monolith_path.is_file():
        checks.append(("monolith-exists", False, "src/monolith.py missing"))
        return _eval_kit.report_and_exit(checks)

    cur_nonempty = _nonempty_lines(monolith_path.read_text(encoding="utf-8"))
    shrank_ok = cur_nonempty <= max(75, int(orig_nonempty * 0.5))
    checks.append((
        "monolith-shrank",
        shrank_ok,
        f"src/monolith.py non-empty lines: {orig_nonempty} -> {cur_nonempty}",
    ))

    py_modules = sorted(
        p for p in src_dir.glob("*.py")
        if p.name not in ("__init__.py", "monolith.py") and _nonempty_lines(p.read_text(encoding="utf-8")) >= 8
    )
    all_mod_names = {p.stem for p in src_dir.glob("*.py") if p.name != "__init__.py"}
    import_graph = {
        p.stem: _src_imports(p, all_mod_names)
        for p in src_dir.glob("*.py")
        if p.name != "__init__.py"
    }
    used_extracted = sorted(
        p for p in py_modules
        if p.stem in import_graph.get("monolith", set())
        or any(p.stem in deps for deps in import_graph.values())
    )
    checks.append((
        "extracted-modules-exist-and-wired",
        len(used_extracted) >= 2,
        f"found {len(used_extracted)} wired extracted module(s): {[p.name for p in used_extracted]}",
    ))

    cyclic = _has_cycle(import_graph)
    checks.append((
        "acyclic-imports",
        not cyclic,
        f"import graph acyclic ({import_graph})" if not cyclic else f"circular import detected: {import_graph}",
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_mono_ok, mut_mono_detail = _eval_kit.check_mutation_caught(
        repo,
        "src/monolith.py",
        lambda s: s + "\ndef process_batch(*args, **kwargs):\n    return {'count': 0, 'totals_by_currency': {}, 'payload': ''}\n",
    )
    checks.append(("mutation-monolith-caught", mut_mono_ok, mut_mono_detail))

    if used_extracted:
        ext_rel = f"src/{used_extracted[0].name}"
        mut_ext_ok, mut_ext_detail = _eval_kit.check_mutation_caught(
            repo, ext_rel, _break_first_public_func
        )
        checks.append(("mutation-extracted-module-caught", mut_ext_ok, mut_ext_detail))
    else:
        checks.append(("mutation-extracted-module-caught", False, "no extracted module available to mutate"))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    sec_hits = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
