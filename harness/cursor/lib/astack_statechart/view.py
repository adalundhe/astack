"""Checked statechart view projection and Mermaid stateDiagram-v2 renderer.

Maps concrete checked model states (from TLC/DOT) through a
small user-supplied view module (`.py`) or declarative view spec (`.json`) into
human-readable flat, nested (composite), and parallel (orthogonal `--`)
statecharts — computed mechanically from the verified graph so the chart a person
reads is checked against the model rather than renamed by hand.

Soundness guarantees:
1. Totality: every reachable state in the checked graph must be mapped by the view.
2. Zero hidden violations: clean and violating concrete states that project to the
   same human label are automatically split so rule breaks are never masked.
3. Explicit parallel synchronization and cross-region rule violations: multi-region
   transitions are tagged `[sync: ...]` and cross-region invariant violations are
   surfaced as explicit red-highlighted violation states.
4. Failure-path pinning: `--max-states` always retains initial, violating, and
   shortest-counterexample states.
"""
from __future__ import annotations

import importlib.util
import json
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from astack_statechart.tla_state import parse_tla_state

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class ViewError(ValueError):
    """Raised when a view module is malformed or fails to map a checked model state."""


@dataclass
class ViewConfig:
    """Loaded view module/spec contract."""

    source: str
    state_fn: Callable[[dict[str, Any]], Any]
    transition_fn: Callable[[dict[str, Any], str, dict[str, Any]], Any] | None = None
    action_labels: dict[str, str] = field(default_factory=dict)
    rule_labels: dict[str, str] = field(default_factory=dict)
    rules: dict[str, Callable[[dict[str, Any]], bool]] = field(default_factory=dict)
    end_states: set[str] = field(default_factory=set)
    collapse_self_loops: bool = False
    title: str = ""


@dataclass
class _MappedState:
    kind: str  # "single" | "parallel"
    path: tuple[str, ...]  # for single: full (parent..., leaf); for parallel: composite parent path
    regions: dict[str, tuple[str, ...]] = field(default_factory=dict)  # region_name -> nested path inside region
    is_end: bool = False
    note: str = ""


@dataclass
class ViewRenderResult:
    mermaid: str
    concrete_states: int
    concrete_transitions: int
    abstract_states: int
    abstract_transitions: int
    collapsed_states: int
    omitted_states: int
    omitted_transitions: int
    nested_groups: list[str]
    parallel_groups: list[str]
    violation_splits: list[dict[str, Any]]
    synchronized_transitions: list[dict[str, Any]]
    cross_region_violations: list[dict[str, Any]]
    extra_rule_violations: dict[str, list[str]]
    translated_violations: list[dict[str, Any]]
    view_source: str

    def to_metadata(self) -> dict[str, Any]:
        return {
            "view_source": self.view_source,
            "concrete_states": self.concrete_states,
            "concrete_transitions": self.concrete_transitions,
            "abstract_states": self.abstract_states,
            "abstract_transitions": self.abstract_transitions,
            "collapsed_states": self.collapsed_states,
            "omitted_states": self.omitted_states,
            "omitted_transitions": self.omitted_transitions,
            "nested_groups": self.nested_groups,
            "parallel_groups": self.parallel_groups,
            "violation_splits": self.violation_splits,
            "synchronized_transitions": self.synchronized_transitions,
            "cross_region_violations": self.cross_region_violations,
            "extra_rule_violations": self.extra_rule_violations,
            "translated_violations": self.translated_violations,
        }


def _clean_text(text: str, *, max_len: int = 120) -> str:
    cleaned = _CONTROL_CHARS.sub("", str(text))
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    parts = [line.strip() for line in cleaned.split("\n") if line.strip()]
    joined = ", ".join(parts) if parts else "(empty)"
    joined = (
        joined.replace('"', "'")
        .replace("-->", "->")
        .replace("[*]", "(star)")
        .replace("%%", "% %")
    )
    if len(joined) > max_len:
        joined = joined[: max_len - 3] + "..."
    if joined.endswith("\\"):
        joined = joined + " "
    return joined


def _clean_edge(text: str, *, max_len: int = 96) -> str:
    return _clean_text(text, max_len=max_len).replace(":", " -")


def _normalize_path(raw: Any, *, field_name: str = "state") -> tuple[str, ...]:
    if isinstance(raw, str):
        val = raw.strip()
        if not val:
            raise ViewError(f"{field_name} returned an empty string")
        return (val,)
    if isinstance(raw, (tuple, list)):
        parts = [str(p).strip() for p in raw if str(p).strip()]
        if not parts:
            raise ViewError(f"{field_name} returned an empty path sequence")
        return tuple(parts)
    raise ViewError(f"{field_name} must return a string, sequence of strings, or dict; got {type(raw).__name__}")


def _normalize_mapped_state(raw: Any, concrete_state: dict[str, Any]) -> _MappedState:
    if raw is None:
        raise ViewError(f"view returned None for state {concrete_state!r}")
    if isinstance(raw, (str, tuple, list)):
        return _MappedState(kind="single", path=_normalize_path(raw))
    if not isinstance(raw, dict):
        raise ViewError(f"view returned unsupported type {type(raw).__name__} for state {concrete_state!r}")

    is_end = bool(raw.get("end") or raw.get("terminal"))
    note = str(raw.get("note", "") or "").strip()

    parent_raw = raw.get("parent")
    parent_path: tuple[str, ...] = ()
    if parent_raw is not None:
        parent_path = _normalize_path(parent_raw, field_name="parent")

    if "parallel" in raw and raw["parallel"] is not None:
        par = raw["parallel"]
        if not isinstance(par, dict) or not par:
            raise ViewError(f"parallel mapping must be a non-empty dict of {{region: state}} for {concrete_state!r}")
        if "path" in raw and raw["path"] is not None:
            comp_path = _normalize_path(raw["path"], field_name="path")
        elif parent_path:
            comp_path = parent_path + ((str(raw["label"]).strip(),) if raw.get("label") else ())
        elif raw.get("label"):
            comp_path = _normalize_path(raw["label"], field_name="label")
        else:
            comp_path = ("Parallel",)
        regions: dict[str, tuple[str, ...]] = {}
        for rname, rval in par.items():
            rk = str(rname).strip()
            if not rk:
                raise ViewError(f"parallel region name cannot be empty for {concrete_state!r}")
            regions[rk] = _normalize_path(rval, field_name=f"parallel[{rk!r}]")
        return _MappedState(kind="parallel", path=comp_path, regions=regions, is_end=is_end, note=note)

    if "path" in raw and raw["path"] is not None:
        full_path = parent_path + _normalize_path(raw["path"], field_name="path")
    elif "label" in raw and raw["label"] is not None:
        full_path = parent_path + _normalize_path(raw["label"], field_name="label")
    else:
        raise ViewError(f"view dict must contain 'label', 'path', or 'parallel' for state {concrete_state!r}")

    return _MappedState(kind="single", path=full_path, is_end=is_end, note=note)


def _load_json_view(path: Path) -> ViewConfig:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ViewError(f"failed to read JSON view {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ViewError(f"JSON view {path} must be an object")

    action_labels = {str(k): str(v) for k, v in (data.get("action_labels") or {}).items()}
    rule_labels = {str(k): str(v) for k, v in (data.get("rule_labels") or {}).items()}
    end_states = {str(x) for x in (data.get("end_states") or [])}
    collapse_self_loops = bool(data.get("collapse_self_loops", False))
    title = str(data.get("title", "") or "")

    regions_spec = data.get("regions")
    if isinstance(regions_spec, dict) and regions_spec:
        par_parent = data.get("parallel_parent", "System")
        region_labels = data.get("region_labels") if isinstance(data.get("region_labels"), dict) else {}

        def _json_parallel_state(s: dict[str, Any]) -> dict[str, Any]:
            par_out: dict[str, Any] = {}
            for rname, var_name in regions_spec.items():
                if var_name not in s:
                    raise ViewError(f"region {rname!r} references missing state variable {var_name!r} in {s!r}")
                raw_v = str(s[var_name])
                rmap = region_labels.get(rname) if isinstance(region_labels.get(rname), dict) else {}
                par_out[str(rname)] = rmap.get(raw_v, raw_v)
            return {"parent": par_parent, "parallel": par_out}

        return ViewConfig(
            source=str(path),
            state_fn=_json_parallel_state,
            action_labels=action_labels,
            rule_labels=rule_labels,
            end_states=end_states,
            collapse_self_loops=collapse_self_loops,
            title=title,
        )

    state_var = data.get("state_var")
    state_labels = data.get("state_labels") if isinstance(data.get("state_labels"), dict) else {}
    state_vars = data.get("state_vars") if isinstance(data.get("state_vars"), list) else None

    if not state_var and not state_vars:
        raise ViewError(f"JSON view {path} must define 'state_var', 'state_vars', or 'regions'")

    def _json_state(s: dict[str, Any]) -> Any:
        if state_var:
            if state_var not in s:
                raise ViewError(f"JSON view references missing state variable {state_var!r} in {s!r}")
            raw_v = str(s[state_var])
            mapped = state_labels.get(raw_v, raw_v)
        else:
            assert state_vars is not None
            parts = []
            for v in state_vars:
                if v not in s:
                    raise ViewError(f"JSON view references missing state variable {v!r} in {s!r}")
                parts.append(str(s[v]))
            key = "/".join(parts)
            mapped = state_labels.get(key, key)
        if isinstance(mapped, str) and mapped in end_states:
            return {"label": mapped, "end": True}
        return mapped

    return ViewConfig(
        source=str(path),
        state_fn=_json_state,
        action_labels=action_labels,
        rule_labels=rule_labels,
        end_states=end_states,
        collapse_self_loops=collapse_self_loops,
        title=title,
    )


def load_view(path: str | Path) -> ViewConfig:
    """Load a checked statechart view module (`.py`) or declarative view spec (`.json`)."""
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ViewError(f"view file not found: {p}")
    if p.suffix.lower() == ".json":
        return _load_json_view(p)

    spec = importlib.util.spec_from_file_location("_astack_statechart_user_view", p)
    if spec is None or spec.loader is None:
        raise ViewError(f"could not load Python view module: {p}")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001 - surface exact user view import error cleanly
        raise ViewError(f"error executing view module {p}: {exc}") from exc

    state_fn = getattr(mod, "state", None) or getattr(mod, "view", None) or getattr(mod, "map_state", None)
    regions_attr = getattr(mod, "regions", None)
    parallel_parent = getattr(mod, "parallel_parent", "System")

    if state_fn is None:
        if isinstance(regions_attr, dict) and regions_attr:
            for rname, rfn in regions_attr.items():
                if not callable(rfn):
                    raise ViewError(f"regions[{rname!r}] in {p} must be callable")

            def _regions_state(s: dict[str, Any]) -> dict[str, Any]:
                return {
                    "parent": parallel_parent,
                    "parallel": {str(r): fn(s) for r, fn in regions_attr.items()},
                }

            state_fn = _regions_state
        else:
            raise ViewError(
                f"view module {p} must define a callable `state(s)` (or `view(s)` / `map_state(s)` / `regions` dict)"
            )
    elif not callable(state_fn):
        raise ViewError(f"`state` in {p} must be callable")

    transition_fn = getattr(mod, "transition", None) or getattr(mod, "edge", None)
    if transition_fn is not None and not callable(transition_fn):
        raise ViewError(f"`transition` in {p} must be callable")

    raw_actions = getattr(mod, "action_labels", None) or {}
    if not isinstance(raw_actions, dict):
        raise ViewError(f"`action_labels` in {p} must be a dict")
    action_labels = {str(k): str(v) for k, v in raw_actions.items()}

    raw_rule_labels = getattr(mod, "rule_labels", None) or {}
    if not isinstance(raw_rule_labels, dict):
        raise ViewError(f"`rule_labels` in {p} must be a dict")
    rule_labels = {str(k): str(v) for k, v in raw_rule_labels.items()}

    raw_rules = getattr(mod, "rules", None) or getattr(mod, "invariants", None) or {}
    if not isinstance(raw_rules, dict):
        raise ViewError(f"`rules` in {p} must be a dict of {{rule_name: callable}}")
    rules: dict[str, Callable[[dict[str, Any]], bool]] = {}
    for rname, rfn in raw_rules.items():
        if not callable(rfn):
            raise ViewError(f"rules[{rname!r}] in {p} must be callable")
        rules[str(rname)] = rfn

    raw_ends = getattr(mod, "end_states", None) or ()
    end_states = {str(x) for x in raw_ends}
    collapse_self_loops = bool(getattr(mod, "collapse_self_loops", False))
    title = str(getattr(mod, "title", "") or "")

    return ViewConfig(
        source=str(p),
        state_fn=state_fn,
        transition_fn=transition_fn,
        action_labels=action_labels,
        rule_labels=rule_labels,
        rules=rules,
        end_states=end_states,
        collapse_self_loops=collapse_self_loops,
        title=title,
    )


def _split_rule_names(raw: str) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def _format_rules(rule_names: tuple[str, ...], rule_labels: dict[str, str]) -> str:
    pretty = [rule_labels.get(r, r) for r in rule_names]
    return ", ".join(pretty)


def _map_edge_label(
    view: ViewConfig,
    src_dict: dict[str, Any],
    action: str,
    dst_dict: dict[str, Any],
) -> tuple[bool, str]:
    """Return `(keep, label)` for a concrete transition."""
    if view.transition_fn is not None:
        try:
            res = view.transition_fn(src_dict, action, dst_dict)
        except Exception as exc:  # noqa: BLE001
            raise ViewError(f"transition({src_dict!r}, {action!r}, {dst_dict!r}) raised {exc}") from exc
        if res is None or res is False:
            return False, ""
        return True, str(res).strip()
    if action in view.action_labels:
        return True, view.action_labels[action]
    return True, action


def _lca_prefix(path_a: tuple[str, ...], path_b: tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    for a, b in zip(path_a, path_b):
        if a == b:
            out.append(a)
        else:
            break
    return tuple(out)


def _render_hierarchy_block(
    *,
    indent: int,
    prefix: tuple[str, ...],
    nodes_by_parent: dict[tuple[str, ...], list[tuple[str, str, bool, str]]],
    child_groups: dict[tuple[str, ...], list[tuple[str, ...]]],
    group_ids: dict[tuple[str, ...], str],
    parallel_blocks: dict[tuple[str, ...], list[str]],
    edges_by_lca: dict[tuple[str, ...], list[tuple[str, str, str]]],
    initial_targets_at_prefix: dict[tuple[str, ...], list[str]],
) -> list[str]:
    """Recursively render nested composite states, parallel blocks, and LCA-scoped transitions."""
    pad = "    " * indent
    lines: list[str] = []

    # Leaf states directly under `prefix`
    for sid, label, is_end, note in nodes_by_parent.get(prefix, ()):
        lines.append(f'{pad}state "{_clean_text(label)}" as {sid}')
        if note:
            lines.append(f"{pad}note right of {sid}: {_clean_text(note, max_len=100)}")

    # Nested composite child groups under `prefix`
    for child_path in child_groups.get(prefix, ()):
        if child_path in parallel_blocks:
            for pline in parallel_blocks[child_path]:
                lines.append(f"{pad}{pline}")
            continue
        gid = group_ids[child_path]
        glabel = _clean_text(child_path[-1])
        lines.append(f'{pad}state "{glabel}" as {gid} {{')
        inner = _render_hierarchy_block(
            indent=indent + 1,
            prefix=child_path,
            nodes_by_parent=nodes_by_parent,
            child_groups=child_groups,
            group_ids=group_ids,
            parallel_blocks=parallel_blocks,
            edges_by_lca=edges_by_lca,
            initial_targets_at_prefix=initial_targets_at_prefix,
        )
        lines.extend(inner)
        lines.append(f"{pad}}}")

    # Initial arrows at this level
    for init_id in initial_targets_at_prefix.get(prefix, ()):
        lines.append(f"{pad}[*] --> {init_id}")

    # End arrows for leaf states directly under `prefix`
    for sid, _label, is_end, _note in nodes_by_parent.get(prefix, ()):
        if is_end:
            lines.append(f"{pad}{sid} --> [*]")

    # Transitions whose LCA is `prefix`
    for src_id, dst_id, elbl in edges_by_lca.get(prefix, ()):
        if elbl:
            lines.append(f"{pad}{src_id} --> {dst_id}: {_clean_edge(elbl)}")
        else:
            lines.append(f"{pad}{src_id} --> {dst_id}")

    return lines


def project_and_render_view(
    *,
    nodes: dict[str, Any],
    edges: list[tuple[str, str, str]],
    initial_ids: list[str],
    violating_ids: dict[str, str],
    violations: list[dict[str, Any]] | None,
    view: ViewConfig,
    max_states: int | None = None,
) -> ViewRenderResult:
    """Compute a checked human-readable statechart strictly from a verified concrete graph.

    Parameters
    ----------
    nodes:
        Mapping `concrete_id -> raw TLA+ state text or already-parsed dict`.
    edges:
        List of `(src_id, dst_id, action_label)` concrete transitions.
    initial_ids:
        Concrete initial node IDs.
    violating_ids:
        Concrete violating node ID -> comma-separated invariant/rule names.
    violations:
        Optional list of shortest-path violation dicts (each having `kind`, `name`, `hops`, `steps`, `cycle_back_to`).
    view:
        Loaded `ViewConfig`.
    max_states:
        Optional display cap on projected abstract states (always pins initial + violating + counterexample states).
    """
    violations = list(violations or [])

    # 1. Parse every concrete state into a Python dict and evaluate view.state + view.rules
    parsed_states: dict[str, dict[str, Any]] = {}
    mapped_states: dict[str, _MappedState] = {}
    effective_viols: dict[str, tuple[str, ...]] = {}
    extra_rule_violations: dict[str, list[str]] = {}

    for nid, raw_state in nodes.items():
        sdict = parse_tla_state(raw_state)
        parsed_states[nid] = sdict
        try:
            raw_mapped = view.state_fn(sdict)
        except ViewError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ViewError(f"view.state() raised {exc} on state {nid} ({sdict!r})") from exc
        m = _normalize_mapped_state(raw_mapped, sdict)
        if m.kind == "single" and (m.path[-1] in view.end_states or " / ".join(m.path) in view.end_states):
            m.is_end = True
        mapped_states[nid] = m

        rules_broken = list(_split_rule_names(violating_ids.get(nid, "")))
        for rname, rfn in view.rules.items():
            try:
                ok = bool(rfn(sdict))
            except Exception as exc:  # noqa: BLE001
                raise ViewError(f"view rule {rname!r} raised {exc} on state {nid} ({sdict!r})") from exc
            if not ok:
                if rname not in rules_broken:
                    rules_broken.append(rname)
                extra_rule_violations.setdefault(rname, []).append(nid)
        effective_viols[nid] = tuple(rules_broken)

    # 2. Group concrete states into abstract entities:
    #    - Single/nested abstract states keyed by (path, rules_broken_tuple) so violations NEVER merge with clean states!
    #    - Parallel composites keyed by (parent_path, tuple(region_names))
    single_groups_by_path: dict[tuple[str, ...], set[tuple[str, ...]]] = {}
    for nid, m in mapped_states.items():
        if m.kind == "single":
            single_groups_by_path.setdefault(m.path, set()).add(effective_viols[nid])

    violation_splits: list[dict[str, Any]] = []
    for path, vsets in single_groups_by_path.items():
        if len(vsets) > 1 and () in vsets:
            broken = sorted({r for vs in vsets for r in vs})
            violation_splits.append(
                {
                    "state": " / ".join(path),
                    "rules": [_format_rules((r,), view.rule_labels) for r in broken],
                    "reason": "clean and rule-violating concrete states shared a label; split automatically to preserve rule violations",
                }
            )

    # Abstract entity keys:
    #   ("single", path, viol_tuple)
    #   ("parallel", parent_path, region_names_tuple)
    #   ("cross_viol", parent_path, combo_label, viol_tuple)
    concrete_to_entity: dict[str, tuple[Any, ...]] = {}
    entity_order: list[tuple[Any, ...]] = []
    entity_members: dict[tuple[Any, ...], list[str]] = {}
    entity_end: dict[tuple[Any, ...], bool] = {}
    entity_note: dict[tuple[Any, ...], str] = {}

    def _register_entity(ekey: tuple[Any, ...], nid: str) -> None:
        if ekey not in entity_members:
            entity_members[ekey] = []
            entity_order.append(ekey)
        entity_members[ekey].append(nid)

    for nid in nodes:
        m = mapped_states[nid]
        if m.kind == "single":
            ekey = ("single", m.path, effective_viols[nid])
            concrete_to_entity[nid] = ekey
            _register_entity(ekey, nid)
            if m.is_end:
                entity_end[ekey] = True
            if m.note and ekey not in entity_note:
                entity_note[ekey] = m.note
        else:
            rnames = tuple(m.regions.keys())
            ekey = ("parallel", m.path, rnames)
            concrete_to_entity[nid] = ekey
            _register_entity(ekey, nid)
            if m.is_end:
                entity_end[ekey] = True

    # 3. Analyze parallel composites: regions, local vs cross-region violations, internal & synchronized transitions
    parallel_groups_info: dict[tuple[Any, ...], dict[str, Any]] = {}
    synchronized_transitions: list[dict[str, Any]] = []
    cross_region_violations: list[dict[str, Any]] = []
    # Map concrete violating node inside parallel composite -> cross-region violation entity if needed
    concrete_cross_viol_entity: dict[str, tuple[Any, ...]] = {}

    for ekey in list(entity_order):
        if ekey[0] != "parallel":
            continue
        _, parent_path, rnames = ekey
        member_nids = entity_members[ekey]
        member_set = set(member_nids)

        # Track region states and which concrete states project to each region leaf
        region_states: dict[str, list[tuple[str, ...]]] = {r: [] for r in rnames}
        region_state_members: dict[tuple[str, tuple[str, ...]], list[str]] = {}
        region_inits: dict[str, list[tuple[str, ...]]] = {r: [] for r in rnames}

        init_set = set(initial_ids)
        # Also detect entry concrete nodes from outside this parallel composite
        entry_nids: set[str] = {nid for nid in member_nids if nid in init_set}
        for src, dst, _act in edges:
            if dst in member_set and src not in member_set:
                entry_nids.add(dst)

        for nid in member_nids:
            m = mapped_states[nid]
            for r in rnames:
                rpath = m.regions[r]
                if rpath not in region_states[r]:
                    region_states[r].append(rpath)
                region_state_members.setdefault((r, rpath), []).append(nid)
                if nid in entry_nids and rpath not in region_inits[r]:
                    region_inits[r].append(rpath)

        # Classify violations inside this parallel composite: region-local vs cross-region combination
        region_local_viols: dict[tuple[str, tuple[str, ...]], list[str]] = {}
        seen_cross_combos: set[tuple[str, tuple[str, ...]]] = set()

        for nid in member_nids:
            vrules = effective_viols[nid]
            if not vrules:
                continue
            m = mapped_states[nid]
            for rule in vrules:
                # Check if some region's state ALWAYS breaks this rule across all reachable states in P
                local_regions = [
                    r
                    for r in rnames
                    if all(rule in effective_viols[other] for other in region_state_members[(r, m.regions[r])])
                ]
                if local_regions:
                    for r in local_regions:
                        lst = region_local_viols.setdefault((r, m.regions[r]), [])
                        if rule not in lst:
                            lst.append(rule)
                else:
                    # Cross-region violation! Only breaks when this combination of region states coincides.
                    combo = " + ".join(f"{r}={' / '.join(m.regions[r])}" for r in rnames)
                    ckey = (combo, vrules)
                    viol_ekey = ("cross_viol", parent_path[:-1], combo, vrules)
                    concrete_cross_viol_entity[nid] = viol_ekey
                    _register_entity(viol_ekey, nid)
                    if ckey not in seen_cross_combos:
                        seen_cross_combos.add(ckey)
                        cross_region_violations.append(
                            {
                                "parallel": " / ".join(parent_path),
                                "combination": combo,
                                "rules": [_format_rules((r,), view.rule_labels) for r in vrules],
                            }
                        )

        # Project internal transitions inside this parallel composite onto regions
        region_edges: dict[str, list[tuple[tuple[str, ...], tuple[str, ...], str]]] = {r: [] for r in rnames}
        seen_reg_edge: set[tuple[str, tuple[str, ...], tuple[str, ...], str]] = set()
        seen_sync: set[tuple[tuple[str, ...], str]] = set()
        internal_omitted = 0

        for src, dst, raw_act in edges:
            if src not in member_set or dst not in member_set:
                continue
            keep, elbl = _map_edge_label(view, parsed_states[src], raw_act, parsed_states[dst])
            if not keep:
                internal_omitted += 1
                continue
            ms = mapped_states[src]
            md = mapped_states[dst]
            changed = [r for r in rnames if ms.regions[r] != md.regions[r]]
            if len(changed) == 1:
                r = changed[0]
                key = (r, ms.regions[r], md.regions[r], elbl)
                if key not in seen_reg_edge:
                    seen_reg_edge.add(key)
                    region_edges[r].append((ms.regions[r], md.regions[r], elbl))
            elif len(changed) > 1:
                sync_tag = f"[sync {'+'.join(changed)}]"
                tagged = f"{elbl} {sync_tag}".strip() if elbl else sync_tag
                skey = (tuple(changed), elbl)
                if skey not in seen_sync:
                    seen_sync.add(skey)
                    synchronized_transitions.append(
                        {
                            "parallel": " / ".join(parent_path),
                            "regions": list(changed),
                            "label": elbl or "(unlabeled)",
                        }
                    )
                for r in changed:
                    key = (r, ms.regions[r], md.regions[r], tagged)
                    if key not in seen_reg_edge:
                        seen_reg_edge.add(key)
                        region_edges[r].append((ms.regions[r], md.regions[r], tagged))
            else:
                # Neither region changed: self-loop on all regions only if not collapsed and explicitly labeled
                if not view.collapse_self_loops and elbl and view.transition_fn is not None:
                    r0 = rnames[0]
                    key = (r0, ms.regions[r0], md.regions[r0], elbl)
                    if key not in seen_reg_edge:
                        seen_reg_edge.add(key)
                        region_edges[r0].append((ms.regions[r0], md.regions[r0], elbl))
                else:
                    internal_omitted += 1

        parallel_groups_info[ekey] = {
            "parent_path": parent_path,
            "rnames": rnames,
            "region_states": region_states,
            "region_inits": region_inits,
            "region_local_viols": region_local_viols,
            "region_edges": region_edges,
            "internal_omitted": internal_omitted,
        }

    # 4. Build top-level abstract edges (between single states, parallel composites, and cross-region violation nodes)
    abstract_edges: list[tuple[tuple[Any, ...], tuple[Any, ...], str]] = []
    seen_abs_edges: set[tuple[tuple[Any, ...], tuple[Any, ...], str]] = set()
    omitted_transitions = sum(info["internal_omitted"] for info in parallel_groups_info.values())

    for src, dst, raw_act in edges:
        if src not in concrete_to_entity or dst not in concrete_to_entity:
            continue
        esrc = concrete_to_entity[src]
        edst = concrete_to_entity[dst]

        # Internal transitions inside the same parallel composite were already projected onto regions,
        # EXCEPT when dst triggers a cross-region violation: emit an edge from P -> cross_viol node!
        if esrc[0] == "parallel" and edst == esrc:
            if dst in concrete_cross_viol_entity:
                keep, elbl = _map_edge_label(view, parsed_states[src], raw_act, parsed_states[dst])
                if keep:
                    cv = concrete_cross_viol_entity[dst]
                    k = (esrc, cv, elbl)
                    if k not in seen_abs_edges:
                        seen_abs_edges.add(k)
                        abstract_edges.append(k)
            continue

        keep, elbl = _map_edge_label(view, parsed_states[src], raw_act, parsed_states[dst])
        if not keep:
            omitted_transitions += 1
            continue
        if esrc == edst and (view.collapse_self_loops or (not elbl and src != dst)):
            omitted_transitions += 1
            continue
        k = (esrc, edst, elbl)
        if k not in seen_abs_edges:
            seen_abs_edges.add(k)
            abstract_edges.append(k)
        # If entering a parallel composite directly into a cross-region violation state, link it too
        if dst in concrete_cross_viol_entity:
            cv = concrete_cross_viol_entity[dst]
            k2 = (esrc, cv, elbl)
            if k2 not in seen_abs_edges:
                seen_abs_edges.add(k2)
                abstract_edges.append(k2)

    # 5. Translate shortest-path violations into reader's words & determine pinned abstract entities
    initial_entities: list[tuple[Any, ...]] = []
    for iid in initial_ids:
        if iid in concrete_to_entity:
            ek = concrete_to_entity[iid]
            if ek not in initial_entities:
                initial_entities.append(ek)
            if iid in concrete_cross_viol_entity:
                cv = concrete_cross_viol_entity[iid]
                if cv not in initial_entities:
                    initial_entities.append(cv)

    def _entity_human_name(ekey: tuple[Any, ...]) -> str:
        if ekey[0] == "single":
            base = " / ".join(ekey[1])
            if ekey[2]:
                return f"{base} [VIOLATION: {_format_rules(ekey[2], view.rule_labels)}]"
            return base
        if ekey[0] == "parallel":
            return " / ".join(ekey[1])
        # cross_viol
        return f"{ekey[2]} [VIOLATION: {_format_rules(ekey[3], view.rule_labels)}]"

    def _concrete_human_name(nid: str) -> str:
        if nid in concrete_cross_viol_entity:
            return _entity_human_name(concrete_cross_viol_entity[nid])
        m = mapped_states[nid]
        vr = effective_viols[nid]
        if m.kind == "parallel":
            combo = " + ".join(f"{r}={' / '.join(m.regions[r])}" for r in m.regions)
            base = f"{' / '.join(m.path)} ({combo})"
        else:
            base = " / ".join(m.path)
        if vr:
            return f"{base} [VIOLATION: {_format_rules(vr, view.rule_labels)}]"
        return base

    pinned_entities: list[tuple[Any, ...]] = []
    pinned_set: set[tuple[Any, ...]] = set()

    def _pin(ekey: tuple[Any, ...]) -> None:
        if ekey not in pinned_set:
            pinned_set.add(ekey)
            pinned_entities.append(ekey)

    for ek in initial_entities:
        _pin(ek)
    for ek in entity_order:
        if (ek[0] == "single" and ek[2]) or ek[0] == "cross_viol":
            _pin(ek)
        elif ek[0] == "parallel" and parallel_groups_info[ek]["region_local_viols"]:
            _pin(ek)

    translated_violations: list[dict[str, Any]] = []
    for v in violations:
        raw_name = str(v.get("name", ""))
        pretty_name = _format_rules(tuple(_split_rule_names(raw_name)), view.rule_labels) if raw_name else raw_name
        t_steps: list[dict[str, Any]] = []
        raw_steps = list(v.get("steps") or [])
        prev_sdict: dict[str, Any] | None = None
        for idx, step in enumerate(raw_steps):
            sid = step.get("id")
            raw_act = str(step.get("action", ""))
            if sid and sid in parsed_states:
                sdict = parsed_states[sid]
                label = _concrete_human_name(sid)
                _pin(concrete_to_entity[sid])
                if sid in concrete_cross_viol_entity:
                    _pin(concrete_cross_viol_entity[sid])
            else:
                sdict = parse_tla_state(step.get("state", ""))
                try:
                    mm = _normalize_mapped_state(view.state_fn(sdict), sdict)
                    if mm.kind == "parallel":
                        combo = " + ".join(f"{r}={' / '.join(mm.regions[r])}" for r in mm.regions)
                        label = f"{' / '.join(mm.path)} ({combo})"
                    else:
                        label = " / ".join(mm.path)
                except Exception:  # noqa: BLE001
                    label = _clean_text(step.get("state", ""))
            if idx == 0 or not raw_act or raw_act in ("Initial", "Initial predicate"):
                act_label = raw_act
            elif prev_sdict is not None:
                _, act_label = _map_edge_label(view, prev_sdict, raw_act, sdict)
            else:
                act_label = view.action_labels.get(raw_act, raw_act)
            t_steps.append(
                {
                    "step": str(step.get("step", idx + 1)),
                    "action": act_label,
                    "state_label": label,
                    "raw_state": step.get("state", ""),
                }
            )
            prev_sdict = sdict
        translated_violations.append(
            {
                "kind": v.get("kind", "violation"),
                "name": pretty_name,
                "raw_name": raw_name,
                "hops": v.get("hops", max(0, len(t_steps) - 1)),
                "steps": t_steps,
                "cycle_back_to": v.get("cycle_back_to"),
            }
        )

    # 6. Apply optional --max-states cap on abstract entities (keeping all pinned entities!)
    if max_states is not None and max_states > 0 and len(entity_order) > max_states:
        adj: dict[tuple[Any, ...], list[tuple[Any, ...]]] = {ek: [] for ek in entity_order}
        for s_ek, d_ek, _lbl in abstract_edges:
            if s_ek in adj:
                adj[s_ek].append(d_ek)
        q: deque[tuple[Any, ...]] = deque(pinned_entities or entity_order[:1])
        while q and len(pinned_entities) < max_states:
            cur = q.popleft()
            for nxt in adj.get(cur, ()):
                if len(pinned_entities) >= max_states:
                    break
                if nxt not in pinned_set:
                    _pin(nxt)
                    q.append(nxt)
        for ek in entity_order:
            if len(pinned_entities) >= max_states:
                break
            _pin(ek)
        kept_entities = pinned_entities
    else:
        kept_entities = list(entity_order)

    kept_set = set(kept_entities)
    omitted_states = len(entity_order) - len(kept_entities)

    # 7. Assign Mermaid IDs and build composite hierarchy + parallel blocks
    entity_ids: dict[tuple[Any, ...], str] = {}
    entity_parent: dict[tuple[Any, ...], tuple[str, ...]] = {}
    group_ids: dict[tuple[str, ...], str] = {}
    child_groups: dict[tuple[str, ...], list[tuple[str, ...]]] = {}
    nodes_by_parent: dict[tuple[str, ...], list[tuple[str, str, bool, str]]] = {}
    parallel_blocks: dict[tuple[str, ...], list[str]] = {}
    violating_mermaid_ids: list[str] = []

    def _ensure_group_chain(path: tuple[str, ...]) -> None:
        for depth in range(1, len(path) + 1):
            sub = path[:depth]
            parent = path[: depth - 1]
            if sub not in group_ids:
                group_ids[sub] = f"g{len(group_ids)}"
            lst = child_groups.setdefault(parent, [])
            if sub not in lst:
                lst.append(sub)

    nid_counter = 0
    reg_counter = 0
    rnode_counter = 0

    nested_group_names: list[str] = []
    parallel_group_names: list[str] = []

    for ek in kept_entities:
        if ek[0] == "single":
            path, vrules = ek[1], ek[2]
            parent = path[:-1]
            if parent:
                _ensure_group_chain(parent)
            sid = f"s{nid_counter}"
            nid_counter += 1
            entity_ids[ek] = sid
            entity_parent[ek] = parent
            leaf_lbl = path[-1]
            if vrules:
                leaf_lbl = f"{leaf_lbl} [VIOLATION: {_format_rules(vrules, view.rule_labels)}]"
                violating_mermaid_ids.append(sid)
            nodes_by_parent.setdefault(parent, []).append(
                (sid, leaf_lbl, bool(entity_end.get(ek, False)), entity_note.get(ek, ""))
            )
        elif ek[0] == "cross_viol":
            parent, combo, vrules = ek[1], ek[2], ek[3]
            if parent:
                _ensure_group_chain(parent)
            sid = f"v{nid_counter}"
            nid_counter += 1
            entity_ids[ek] = sid
            entity_parent[ek] = parent
            lbl = f"{combo} [VIOLATION: {_format_rules(vrules, view.rule_labels)}]"
            violating_mermaid_ids.append(sid)
            nodes_by_parent.setdefault(parent, []).append((sid, lbl, False, ""))
        else:
            # Parallel composite block!
            info = parallel_groups_info[ek]
            par_path = info["parent_path"]
            _ensure_group_chain(par_path)
            pid = group_ids[par_path]
            entity_ids[ek] = pid
            entity_parent[ek] = par_path[:-1]
            parallel_group_names.append(" / ".join(par_path))

            p_lines: list[str] = [f'state "{_clean_text(par_path[-1])}" as {pid} {{']
            rnames = info["rnames"]
            for r_idx, rname in enumerate(rnames):
                if r_idx > 0:
                    p_lines.append("    --")
                rid = f"r{reg_counter}"
                reg_counter += 1
                p_lines.append(f'    state "{_clean_text(rname)}" as {rid} {{')

                # Build nested hierarchy INSIDE this region!
                r_nodes_by_parent: dict[tuple[str, ...], list[tuple[str, str, bool, str]]] = {}
                r_child_groups: dict[tuple[str, ...], list[tuple[str, ...]]] = {}
                r_group_ids: dict[tuple[str, ...], str] = {}
                r_leaf_ids: dict[tuple[str, ...], str] = {}

                def _ensure_rgroup(rpath: tuple[str, ...]) -> None:
                    for d in range(1, len(rpath) + 1):
                        sub = rpath[:d]
                        par = rpath[: d - 1]
                        if sub not in r_group_ids:
                            r_group_ids[sub] = f"{rid}_g{len(r_group_ids)}"
                        lst = r_child_groups.setdefault(par, [])
                        if sub not in lst:
                            lst.append(sub)

                for rpath in info["region_states"][rname]:
                    rpar = rpath[:-1]
                    if rpar:
                        _ensure_rgroup(rpar)
                    rsid = f"rs{rnode_counter}"
                    rnode_counter += 1
                    r_leaf_ids[rpath] = rsid
                    rlbl = rpath[-1]
                    local_v = info["region_local_viols"].get((rname, rpath), [])
                    if local_v:
                        rlbl = f"{rlbl} [VIOLATION: {_format_rules(tuple(local_v), view.rule_labels)}]"
                        violating_mermaid_ids.append(rsid)
                    r_nodes_by_parent.setdefault(rpar, []).append((rsid, rlbl, False, ""))

                r_inits: dict[tuple[str, ...], list[str]] = {}
                for rinit in info["region_inits"][rname]:
                    if rinit in r_leaf_ids:
                        r_inits.setdefault((), []).append(r_leaf_ids[rinit])

                r_edges_by_lca: dict[tuple[str, ...], list[tuple[str, str, str]]] = {}
                for rs_src, rs_dst, relbl in info["region_edges"][rname]:
                    if rs_src in r_leaf_ids and rs_dst in r_leaf_ids:
                        lca = _lca_prefix(rs_src[:-1], rs_dst[:-1])
                        r_edges_by_lca.setdefault(lca, []).append((r_leaf_ids[rs_src], r_leaf_ids[rs_dst], relbl))

                inner_reg = _render_hierarchy_block(
                    indent=2,
                    prefix=(),
                    nodes_by_parent=r_nodes_by_parent,
                    child_groups=r_child_groups,
                    group_ids=r_group_ids,
                    parallel_blocks={},
                    edges_by_lca=r_edges_by_lca,
                    initial_targets_at_prefix=r_inits,
                )
                p_lines.extend(inner_reg)
                p_lines.append("    }")
            p_lines.append("}")
            parallel_blocks[par_path] = p_lines

    for gpath in group_ids:
        if gpath not in parallel_blocks:
            nested_group_names.append(" / ".join(gpath))

    # 8. Scope top-level abstract edges by Lowest Common Ancestor composite block
    edges_by_lca: dict[tuple[str, ...], list[tuple[str, str, str]]] = {}
    rendered_edge_count = 0
    for s_ek, d_ek, elbl in abstract_edges:
        if s_ek not in kept_set or d_ek not in kept_set:
            continue
        lca = _lca_prefix(entity_parent[s_ek], entity_parent[d_ek])
        edges_by_lca.setdefault(lca, []).append((entity_ids[s_ek], entity_ids[d_ek], elbl))
        rendered_edge_count += 1

    # Add internal region edge count to abstract_transitions total
    for ek in kept_entities:
        if ek[0] == "parallel":
            info = parallel_groups_info[ek]
            rendered_edge_count += sum(len(es) for es in info["region_edges"].values())

    initial_targets: dict[tuple[str, ...], list[str]] = {}
    for ek in initial_entities:
        if ek in entity_ids:
            initial_targets.setdefault((), []).append(entity_ids[ek])

    # 9. Emit complete Mermaid stateDiagram-v2
    lines = ["stateDiagram-v2"]
    if view.title:
        lines.append(f"    %% {_clean_text(view.title, max_len=100)}")

    body = _render_hierarchy_block(
        indent=1,
        prefix=(),
        nodes_by_parent=nodes_by_parent,
        child_groups=child_groups,
        group_ids=group_ids,
        parallel_blocks=parallel_blocks,
        edges_by_lca=edges_by_lca,
        initial_targets_at_prefix=initial_targets,
    )
    lines.extend(body)

    if violating_mermaid_ids:
        lines.append("    classDef violation fill:#fee,stroke:#c00,stroke-width:2px")
        lines.append("    class " + ",".join(violating_mermaid_ids) + " violation")

    collapsed = max(0, len(nodes) - len(entity_order))
    if omitted_states > 0:
        lines.append(f"    %% {omitted_states} additional abstract states omitted (--max-states {max_states})")
    if omitted_transitions > 0:
        lines.append(f"    %% {omitted_transitions} internal/filtered transition(s) omitted by view")

    # Compute total distinct rendered abstract states (count region leaves inside parallel blocks too)
    total_abstract_states = 0
    for ek in kept_entities:
        if ek[0] == "parallel":
            total_abstract_states += sum(len(v) for v in parallel_groups_info[ek]["region_states"].values())
        else:
            total_abstract_states += 1

    return ViewRenderResult(
        mermaid="\n".join(lines) + "\n",
        concrete_states=len(nodes),
        concrete_transitions=len(edges),
        abstract_states=total_abstract_states,
        abstract_transitions=rendered_edge_count,
        collapsed_states=collapsed,
        omitted_states=omitted_states,
        omitted_transitions=omitted_transitions,
        nested_groups=nested_group_names,
        parallel_groups=parallel_group_names,
        violation_splits=violation_splits,
        synchronized_transitions=synchronized_transitions,
        cross_region_violations=cross_region_violations,
        extra_rule_violations=extra_rule_violations,
        translated_violations=translated_violations,
        view_source=view.source,
    )
