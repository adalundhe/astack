"""Thorough tests for bin/astack-statechart: DOT parsing, TLC -tool mode, fixtures, fuzzing, and live TLC differential tests."""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import deque
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tlc"


def run_sc(*args, env=None):
    return subprocess.run(
        [sys.executable, "-B", str(BIN / "astack-statechart"), *args],
        capture_output=True, text=True, env=env,
    )


def _java_works():
    java = shutil.which("java")
    if not java:
        return False
    try:
        return subprocess.run([java, "-version"], capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _has_real_tlc():
    if shutil.which("tlc"):
        return True
    if not _java_works():
        return False
    candidates = [
        Path(os.environ["TLA2TOOLS_JAR"]).expanduser() if os.environ.get("TLA2TOOLS_JAR") else None,
        Path(os.environ["TLA2TOOLS"]).expanduser() if os.environ.get("TLA2TOOLS") else None,
        Path("/opt/homebrew/share/tla+/tla2tools.jar"),
        Path("/usr/local/share/tla+/tla2tools.jar"),
        Path.home() / ".local" / "share" / "tla+" / "tla2tools.jar",
        Path("/Applications/TLA+ Toolbox.app/Contents/Eclipse/tla2tools.jar"),
    ]
    return any(p is not None and p.is_file() for p in candidates)


def _dot_escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _independent_min_hops(initial_ids, edges, target_id):
    """Independent BFS oracle for verifying shortest-path distances."""
    adj = {}
    for src, dst in edges:
        adj.setdefault(src, []).append(dst)
    dist = {}
    q = deque()
    for init in initial_ids:
        if init not in dist:
            dist[init] = 0
            q.append(init)
    while q:
        cur = q.popleft()
        if cur == target_id:
            return dist[cur]
        for nxt in adj.get(cur, ()):
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                q.append(nxt)
    return -1


_STATE_DECL_RE = re.compile(r'^    state "([^"]*)" as (s\d+)$')
_EDGE_RE = re.compile(r"^    (\[\*\]|s\d+) --> (s\d+)(?:: .*)?$")


def _assert_valid_mermaid(testcase, mermaid_text, expected_states=None, label=""):
    lines = mermaid_text.splitlines()
    testcase.assertGreaterEqual(len(lines), 1, f"{label}: empty mermaid")
    testcase.assertEqual(lines[0], "stateDiagram-v2", f"{label}: bad header {lines[0]!r}")
    declared = set()
    for line in lines[1:]:
        if line.startswith("    classDef ") or line.startswith("    class ") or line.startswith("    %% "):
            continue
        if m := _STATE_DECL_RE.match(line):
            body, sid = m.group(1), m.group(2)
            testcase.assertNotIn("%%", body, f"{label}: comment leaked in {line!r}")
            testcase.assertNotIn("-->", body, f"{label}: arrow leaked in {line!r}")
            testcase.assertNotIn("[*]", body, f"{label}: [*] leaked in {line!r}")
            testcase.assertFalse(body.endswith("\\"), f"{label}: trailing backslash in {line!r}")
            declared.add(sid)
        elif m := _EDGE_RE.match(line):
            src_id, dst_id = m.group(1), m.group(2)
            if src_id != "[*]":
                testcase.assertIn(src_id, declared, f"{label}: undeclared src {src_id}")
            testcase.assertIn(dst_id, declared, f"{label}: undeclared dst {dst_id}")
        else:
            testcase.fail(f"{label}: unexpected Mermaid line {line!r}")
    if expected_states is not None:
        testcase.assertEqual(len(declared), expected_states, f"{label}: state count mismatch")
    return declared


class StatechartUnitTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="astack-sc-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_dot_parser_torture_comments_chains_continuations_selfloops_and_malformed(self):
        # Malformed non-DOT input MUST exit 2 (never silently succeed with 0 states)
        bad = self.dir / "garbage.dot"
        bad.write_text("definitely not a graphviz file\n")
        res_bad = run_sc("render", str(bad))
        self.assertEqual(res_bad.returncode, 2)
        self.assertIn("invalid DOT", res_bad.stderr)

        # Valid empty DOT graph still parses cleanly (0 states)
        empty = self.dir / "empty.dot"
        empty.write_text("strict digraph DiskGraph {}\n")
        res_empty = run_sc("render", str(empty), "--json")
        self.assertEqual(res_empty.returncode, 0, res_empty.stderr)
        self.assertEqual(json.loads(res_empty.stdout)["states"], 0)

        # Comments (//, /* */, #), chained edges, line continuation, parallel action edges, self-loop
        rich = self.dir / "rich.dot"
        rich.write_text(
            "# leading hash comment\n"
            "strict digraph DiskGraph {\n"
            "  // line comment\n"
            "  /* block\n"
            "     comment */\n"
            "  node [shape=box];\n"
            "  edge [color=black];\n"
            "  subgraph cluster_0 {\n"
            '    -100 [label="part1\\\npart2", style = filled];\n'
            '    200 [label="mid"];\n'
            '    300 [label="bad", color=red, invariant="InvChain"];\n'
            '    -100 -> 200 -> 300 [label="Step"];\n'
            '    -100 -> 200 [label="AltStep"];\n'
            '    200 -> 200 [label="Tick"];\n'
            "  }\n"
            "  {rank = same; -100;}\n"
            "}\n"
        )
        res_rich = run_sc("render", str(rich), "--json")
        self.assertEqual(res_rich.returncode, 0, res_rich.stderr)
        data = json.loads(res_rich.stdout)
        self.assertEqual(data["states"], 3)
        self.assertEqual(data["transitions"], 4)
        self.assertEqual(data["violations"][0]["hops"], 2)
        self.assertIn("part1part2", data["mermaid"])
        self.assertIn("AltStep", data["mermaid"])
        self.assertIn("Tick", data["mermaid"])
        _assert_valid_mermaid(self, data["mermaid"], expected_states=3, label="rich")

    def test_render_dot_finds_shortest_path_to_each_broken_invariant(self):
        dot = self.dir / "states.dot"
        dot.write_text(
            'digraph DiskGraph {\n'
            '  -1001 [label="/\\\\ x = 0\\n/\\\\ y = 0", style = filled];\n'
            '  2002 [label="/\\\\ x = 1\\n/\\\\ y = 0"];\n'
            '  3003 [label="/\\\\ x = 2\\n/\\\\ y = 0"];\n'
            '  4004 [label="/\\\\ x = 3\\n/\\\\ y = 1", color=red, invariant="InvA"];\n'
            '  5005 [label="/\\\\ x = 0\\n/\\\\ y = 9", color=red, invariant="InvB"];\n'
            '  6006 [label="isolated bad", color=red, invariant="InvUnreachable"];\n'
            '  -1001 -> 2002 [label="Slow1"];\n'
            '  2002 -> 3003 [label="Slow2"];\n'
            '  3003 -> 4004 [label="Slow3"];\n'
            '  -1001 -> 4004 [label="Shortcut"];\n'
            '  2002 -> 5005 [label="BreakB"];\n'
            '}\n'
        )
        res = run_sc("render", str(dot), "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        by_name = {v["name"]: v for v in data["violations"]}
        self.assertEqual(by_name["InvA"]["hops"], 1)
        self.assertEqual([s["action"] for s in by_name["InvA"]["steps"]], ["Initial", "Shortcut"])
        self.assertEqual(by_name["InvB"]["hops"], 2)
        self.assertEqual(by_name["InvUnreachable"]["hops"], -1)
        _assert_valid_mermaid(self, data["mermaid"], expected_states=6, label="shortest")

    def test_long_shared_prefix_states_mark_exact_violating_node_and_disambiguate_labels(self):
        long_q = "<<" + ", ".join(str(i) for i in range(1, 45)) + ">>"
        healthy = f"/\\ q = {long_q}\n/\\ y = 0"
        broken = f"/\\ q = {long_q}\n/\\ y = 1"
        dot = self.dir / "long_prefix.dot"
        dot.write_text(
            "strict digraph DiskGraph {\n"
            f'  -100 [label="{_dot_escape(healthy)}", style = filled];\n'
            f'  -200 [label="{_dot_escape(broken)}"];\n'
            '  -100 -> -200 [label="Flip", color="black"];\n'
            "}\n"
        )
        trace = self.dir / "long_prefix.tool.out"
        trace.write_text(
            "@!@!@STARTMSG 2110:1 @!@!@\nInvariant YZero is violated.\n@!@!@ENDMSG 2110 @!@!@\n"
            f"@!@!@STARTMSG 2217:4 @!@!@\n1: <Initial predicate>\n{healthy}\n@!@!@ENDMSG 2217 @!@!@\n"
            f"@!@!@STARTMSG 2217:4 @!@!@\n2: <Flip line 10, col 1 to line 10, col 12 of module Q>\n{broken}\n@!@!@ENDMSG 2217 @!@!@\n"
        )
        res = run_sc("render", str(dot), "--trace", str(trace), "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["violating_states"], {"-200": "YZero"})
        state_lines = [ln for ln in data["mermaid"].splitlines() if ln.strip().startswith('state "')]
        self.assertEqual(len(state_lines), 2)
        self.assertIn("y = 0", state_lines[0])
        self.assertNotIn("[VIOLATION:", state_lines[0])
        self.assertIn("y = 1", state_lines[1])
        self.assertIn("[VIOLATION: YZero]", state_lines[1])

    def test_recorded_tlc_219_corpus_fixtures(self):
        empty_dot = self.dir / "empty.dot"
        empty_dot.write_text("strict digraph DiskGraph { subgraph cluster_graph { color=\"white\"; } }\n")

        # 1. Deadlock with real TLC 2.19 -tool output + -dump dot,actionlabels
        dl = run_sc("render", str(FIXTURES / "counter_deadlock.dot"), "--trace", str(FIXTURES / "counter_deadlock.tool.out"), "--json")
        self.assertEqual(dl.returncode, 0, dl.stderr)
        dl_data = json.loads(dl.stdout)
        self.assertEqual(dl_data["violating_states"], {"-4900539538744082733": "Deadlock"})
        self.assertEqual(dl_data["violations"][0]["hops"], 3)
        self.assertIn("s0 --> s1: Inc", dl_data["mermaid"])

        # 2. Initial-state invariant violation (EC 2107)
        iv = run_sc("render", str(empty_dot), "--trace", str(FIXTURES / "initial_violation.tool.out"), "--json")
        self.assertEqual(iv.returncode, 0, iv.stderr)
        iv_data = json.loads(iv.stdout)
        self.assertEqual(iv_data["violations"][0]["name"], "NotNine")
        self.assertEqual(iv_data["violations"][0]["hops"], 0)

        # 3. Initial-state property violation (EC 2108)
        ip = run_sc("render", str(empty_dot), "--trace", str(FIXTURES / "initial_property.tool.out"), "--json")
        self.assertEqual(ip.returncode, 0, ip.stderr)
        ip_data = json.loads(ip.stdout)
        self.assertEqual(ip_data["violations"][0]["kind"], "property")
        self.assertEqual(ip_data["violations"][0]["name"], "InitSpec")
        self.assertEqual(ip_data["violations"][0]["hops"], 0)

        # 4. Multiple invariants broken on the SAME state (-continue): BOTH labels preserved!
        mi = run_sc("render", str(FIXTURES / "multi_invariant.dot"), "--trace", str(FIXTURES / "multi_invariant.tool.out"), "--json")
        self.assertEqual(mi.returncode, 0, mi.stderr)
        mi_data = json.loads(mi.stdout)
        self.assertEqual({v["name"] for v in mi_data["violations"]}, {"SmallX", "SmallY"})
        self.assertEqual(mi_data["violating_states"]["-104"], "SmallX, SmallY")
        self.assertIn("[VIOLATION: SmallX, SmallY]", mi_data["mermaid"])

        # 5. Multiline wrapped TLA+ records with escaped quotes & backslashes match DOT nodes cleanly
        mr = run_sc("render", str(FIXTURES / "multiline_records.dot"), "--trace", str(FIXTURES / "multiline_records.tool.out"), "--json")
        self.assertEqual(mr.returncode, 0, mr.stderr)
        mr_data = json.loads(mr.stdout)
        self.assertEqual(mr_data["violating_states"], {"-502": "PathSafe"})
        self.assertEqual(mr_data["states"], 2)

        # 6. Temporal lasso loop (EC 2116 + 2122)
        tl = run_sc("render", str(empty_dot), "--trace", str(FIXTURES / "temporal_loop.tool.out"), "--json")
        self.assertEqual(tl.returncode, 0, tl.stderr)
        tl_data = json.loads(tl.stdout)
        self.assertEqual(tl_data["violations"][0]["cycle_back_to"], 2)
        self.assertIn("cycle", tl_data["mermaid"])

        # 7. Action property (EC 2112) + stuttering (EC 2218)
        act = run_sc("render", str(empty_dot), "--trace", str(FIXTURES / "action_and_stuttering.tool.out"), "--json")
        self.assertEqual(act.returncode, 0, act.stderr)
        by_name = {v["name"]: v for v in json.loads(act.stdout)["violations"]}
        self.assertEqual(by_name["Monotonic"]["kind"], "property")
        self.assertEqual(by_name["Monotonic"]["steps"][1]["action"], "Drop")
        self.assertEqual(by_name["TemporalProperty"]["cycle_back_to"], 1)

    def test_check_flags_strict_exit_codes_truncated_crash_and_timeout(self):
        model = self.dir / "Mini.tla"
        model.write_text("---- MODULE Mini ----\n====\n")

        # Missing model -> exit 2
        self.assertEqual(run_sc("check", str(self.dir / "nope.tla")).returncode, 2)

        # Missing TLC -> exit 2
        no_tlc = run_sc("check", str(model), "--jar", str(self.dir / "nope.jar"), env={"HOME": str(self.dir), "PATH": "/usr/bin:/bin"})
        self.assertEqual(no_tlc.returncode, 2)

        # Clean TLC stub: verifies -tool, -workers 1, -lncheck final, -dump dot,actionlabels, -continue
        args_log = self.dir / "tlc_args.txt"
        tlc_ok = self.dir / "fake-tlc-ok"
        tlc_ok.write_text(
            "#!/bin/sh\n"
            f'printf "%s\\n" "$@" > "{args_log}"\n'
            'dot_file=""; prev=""\n'
            'for a in "$@"; do\n'
            '  if [ "$prev" = "dot,actionlabels" ] || [ "$prev" = "dot" ]; then dot_file="$a"; fi\n'
            '  prev="$a"\n'
            'done\n'
            'printf \'strict digraph DiskGraph { -1 [label="x = 0", style = filled]; 2 [label="x = 1"]; -1 -> 2 [label="Inc"]; }\\n\' > "$dot_file"\n'
            "printf '%s\\n' '@!@!@STARTMSG 2199:0 @!@!@' '2 states generated, 2 distinct states found, 0 states left on queue.' '@!@!@ENDMSG 2199 @!@!@'\n"
            "exit 0\n"
        )
        tlc_ok.chmod(0o755)
        ok = run_sc("check", str(model), "--tlc", str(tlc_ok), "--json")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        args_used = args_log.read_text().splitlines()
        self.assertIn("-tool", args_used)
        self.assertIn("dot,actionlabels", args_used)
        self.assertIn("-continue", args_used)
        self.assertIn("-lncheck", args_used)
        idx_w = args_used.index("-workers")
        self.assertEqual(args_used[idx_w + 1], "1")

        # --no-deadlock and --stop-on-first flags
        ok2 = run_sc("check", str(model), "--tlc", str(tlc_ok), "--no-deadlock", "--stop-on-first", "--json")
        self.assertEqual(ok2.returncode, 0, ok2.stderr)
        args_used2 = args_log.read_text().splitlines()
        self.assertIn("-deadlock", args_used2)
        self.assertNotIn("-continue", args_used2)

        # Unrecognized exit 12 with DOT -> MUST exit 1, NEVER false pass
        tlc_12 = self.dir / "fake-tlc-12"
        tlc_12.write_text(
            "#!/bin/sh\n"
            'dot_file=""; prev=""\n'
            'for a in "$@"; do if [ "$prev" = "dot,actionlabels" ]; then dot_file="$a"; fi; prev="$a"; done\n'
            'printf \'digraph G { 1 [label="x = 0", style=filled]; 2 [label="x = 1"]; 1 -> 2 [label="S"]; }\\n\' > "$dot_file"\n'
            "printf '%s\\n' 'Error: Assertion failed.'\n"
            "exit 12\n"
        )
        tlc_12.chmod(0o755)
        r12 = run_sc("check", str(model), "--tlc", str(tlc_12))
        self.assertEqual(r12.returncode, 1, r12.stdout)
        self.assertNotIn("All checked invariants held", r12.stdout)

        # Truncated crash exit 255 with partial DOT -> MUST exit 2, NEVER 0 or 1
        tlc_255 = self.dir / "fake-tlc-255"
        tlc_255.write_text(
            "#!/bin/sh\n"
            'dot_file=""; prev=""\n'
            'for a in "$@"; do if [ "$prev" = "dot,actionlabels" ]; then dot_file="$a"; fi; prev="$a"; done\n'
            'printf \'digraph G { 1 [label="x = 0", style=filled]; }\\n\' > "$dot_file"\n'
            f'cat "{FIXTURES / "truncated_crash.tool.out"}"\n'
            "exit 255\n"
        )
        tlc_255.chmod(0o755)
        r255 = run_sc("check", str(model), "--tlc", str(tlc_255))
        self.assertEqual(r255.returncode, 2, r255.stdout)
        self.assertIn("heap space", r255.stderr)

        # Timeout terminates runaway TLC cleanly with exit 2
        tlc_slow = self.dir / "fake-tlc-slow"
        tlc_slow.write_text("#!/bin/sh\nsleep 10\n")
        tlc_slow.chmod(0o755)
        r_to = run_sc("check", str(model), "--tlc", str(tlc_slow), "--timeout", "0.3")
        self.assertEqual(r_to.returncode, 2)
        self.assertIn("timed out", r_to.stderr)

    def test_property_based_50_adversarial_graphs_and_bfs_minimality(self):
        adversarial = [
            "__proto__", "constructor", "prototype", "toString", "hasOwnProperty",
            "valueOf", "end", "state", "note", "classDef", "node", "edge", "digraph",
            "[*]", "-->", "a --> b", 'quote"inside', "line1\nline2", "comment%%here",
            "trailing\\", "a:b:c", "/\\ x = 0\n/\\ y = 1", "",
        ]
        rng = random.Random(20261124)
        for trial in range(50):
            n_nodes = rng.randint(4, 15)
            pinned = ["__proto__", "constructor", "[*]", "end"]
            rest = [name for name in adversarial if name not in pinned]
            rng.shuffle(rest)
            node_ids = list(pinned) + rest[: n_nodes - len(pinned)]
            initial = [node_ids[0]]
            violating = {}
            for idx in rng.sample(range(1, n_nodes), k=rng.randint(1, min(3, n_nodes - 1))):
                violating[node_ids[idx]] = f"Inv_{adversarial[(idx + trial) % len(adversarial)]}_{idx}"

            edges = []
            dot_lines = ["digraph Prop {"]
            for nid in node_ids:
                lbl = rng.choice(adversarial)
                attrs = [f'label="{_dot_escape(lbl)}"']
                if nid in initial:
                    attrs.append("style=filled")
                if nid in violating:
                    attrs.append("color=red")
                    attrs.append(f'invariant="{_dot_escape(violating[nid])}"')
                dot_lines.append(f'  "{_dot_escape(nid)}" [{", ".join(attrs)}];')
            for _ in range(rng.randint(n_nodes, n_nodes * 2)):
                src, dst = rng.choice(node_ids), rng.choice(node_ids)
                edges.append((src, dst))
                dot_lines.append(f'  "{_dot_escape(src)}" -> "{_dot_escape(dst)}" [label="{_dot_escape(rng.choice(adversarial))}"];')
            dot_lines.append("}")

            dot_path = self.dir / f"prop_{trial}.dot"
            dot_path.write_text("\n".join(dot_lines) + "\n")
            res = run_sc("render", str(dot_path), "--json")
            self.assertEqual(res.returncode, 0, f"trial {trial}: {res.stderr}")
            data = json.loads(res.stdout)
            self.assertEqual(data["states"], n_nodes)
            by_inv = {v["name"]: v["hops"] for v in data["violations"]}
            for bad_id, inv_name in violating.items():
                self.assertEqual(by_inv[inv_name], _independent_min_hops(initial, edges, bad_id), f"trial {trial} {inv_name}")
            _assert_valid_mermaid(self, data["mermaid"], expected_states=n_nodes, label=f"prop_{trial}")

    def test_property_based_50_tool_stream_fuzz_and_max_states_pinning(self):
        rng = random.Random(20261125)
        for trial in range(50):
            n_states = rng.randint(10, 28)
            dot_lines = ["strict digraph DiskGraph {"]
            for i in range(n_states):
                style = ", style = filled" if i == 0 else ""
                dot_lines.append(f'  {i} [label="/\\\\ x = {i}\\n/\\\\ tag = \\"s{i}\\""{style}];')
            # Create branching tree + guaranteed chain to last state
            for i in range(1, n_states - 4):
                dot_lines.append(f'  0 -> {i} [label="Branch{i}"];')
            chain = [0, n_states - 4, n_states - 3, n_states - 2, n_states - 1]
            for a, b in zip(chain, chain[1:]):
                dot_lines.append(f'  {a} -> {b} [label="Step{b}"];')
            dot_lines.append("}")
            dot_path = self.dir / f"fuzz_{trial}.dot"
            dot_path.write_text("\n".join(dot_lines) + "\n")

            # Build -tool output violating invariant at chain[-1]
            msgs = [
                "@!@!@STARTMSG 2110:1 @!@!@\nInvariant ChainBound is violated.\n@!@!@ENDMSG 2110 @!@!@",
                "@!@!@STARTMSG 2121:1 @!@!@\nThe behavior up to this point is:\n@!@!@ENDMSG 2121 @!@!@",
            ]
            for idx, st in enumerate(chain):
                act = "<Initial predicate>" if idx == 0 else f"<Step{st} line {idx}, col 1 to line {idx}, col 10 of module F>"
                msgs.append(
                    f"@!@!@STARTMSG 2217:4 @!@!@\n{idx + 1}: {act}\n/\\ x = {st}\n/\\ tag = \"s{st}\"\n@!@!@ENDMSG 2217 @!@!@"
                )
            trace_path = self.dir / f"fuzz_{trial}.tool.out"
            trace_path.write_text("\n".join(msgs) + "\n")

            cap = len(chain) + rng.randint(0, 3)
            res = run_sc("render", str(dot_path), "--trace", str(trace_path), "--max-states", str(cap), "--json")
            self.assertEqual(res.returncode, 0, f"trial {trial}: {res.stderr}")
            data = json.loads(res.stdout)
            self.assertEqual(data["violations"][0]["hops"], len(chain) - 1)
            self.assertEqual(data["violating_states"], {str(chain[-1]): "ChainBound"})
            # Every state along the failure path MUST survive --max-states capping
            for st in chain:
                self.assertIn(f"x = {st}", data["mermaid"], f"trial {trial}: missing pinned state {st}")
            _assert_valid_mermaid(self, data["mermaid"], expected_states=min(n_states, cap), label=f"fuzz_{trial}")


@unittest.skipUnless(_has_real_tlc(), "TLC / tla2tools.jar with runnable Java not installed")
class LiveTlcTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="astack-live-tlc-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_real_tlc_clean_behavior_initial_deadlock_multi_and_temporal(self):
        # 1. Clean + behavior invariant violation
        tla = self.dir / "Counter.tla"
        tla.write_text(
            "---- MODULE Counter ----\n"
            "EXTENDS Naturals\n"
            "VARIABLE x\n"
            "Init == x = 0\n"
            "Inc == x < 4 /\\ x' = x + 1\n"
            "Reset == x = 4 /\\ x' = 0\n"
            "Next == Inc \\/ Reset\n"
            "Safe == x <= 4\n"
            "Broken == x <= 2\n"
            "====\n"
        )
        cfg_ok = self.dir / "ok.cfg"
        cfg_ok.write_text("INIT Init\nNEXT Next\nINVARIANT Safe\n")
        ok = run_sc("check", str(tla), "--cfg", str(cfg_ok), "--json")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        ok_data = json.loads(ok.stdout)
        self.assertEqual(ok_data["parser_mode"], "tool")
        self.assertEqual(ok_data["violations"], [])
        self.assertIn("Inc", ok_data["mermaid"])
        self.assertIn("Reset", ok_data["mermaid"])
        _assert_valid_mermaid(self, ok_data["mermaid"], expected_states=5, label="live_clean")

        cfg_bad = self.dir / "bad.cfg"
        cfg_bad.write_text("INIT Init\nNEXT Next\nINVARIANT Broken\n")
        bad = run_sc("check", str(tla), "--cfg", str(cfg_bad), "--json")
        self.assertEqual(bad.returncode, 1, bad.stderr)
        bad_data = json.loads(bad.stdout)
        self.assertEqual(bad_data["violations"][0]["name"], "Broken")
        self.assertEqual(bad_data["violations"][0]["hops"], 3)

        # 2. Initial-state invariant violation (hops == 0)
        tla_init = self.dir / "InitBad.tla"
        tla_init.write_text(
            "---- MODULE InitBad ----\n"
            "EXTENDS Naturals\n"
            "VARIABLE x\n"
            "Init == x = 9\n"
            "Next == x' = x\n"
            "NotNine == x # 9\n"
            "====\n"
        )
        cfg_init = self.dir / "InitBad.cfg"
        cfg_init.write_text("INIT Init\nNEXT Next\nINVARIANT NotNine\n")
        init_res = run_sc("check", str(tla_init), "--cfg", str(cfg_init), "--json")
        self.assertEqual(init_res.returncode, 1, init_res.stderr)
        init_data = json.loads(init_res.stdout)
        self.assertEqual(init_data["violations"][0]["name"], "NotNine")
        self.assertEqual(init_data["violations"][0]["hops"], 0)

        # 3. Deadlock detection
        tla_dl = self.dir / "DeadlockSpec.tla"
        tla_dl.write_text(
            "---- MODULE DeadlockSpec ----\n"
            "EXTENDS Naturals\n"
            "VARIABLE x\n"
            "Init == x = 0\n"
            "Inc == x < 3 /\\ x' = x + 1\n"
            "Next == Inc\n"
            "====\n"
        )
        cfg_dl = self.dir / "DeadlockSpec.cfg"
        cfg_dl.write_text("INIT Init\nNEXT Next\n")
        dl_res = run_sc("check", str(tla_dl), "--cfg", str(cfg_dl), "--json")
        self.assertEqual(dl_res.returncode, 1, dl_res.stderr)
        dl_data = json.loads(dl_res.stdout)
        self.assertEqual(dl_data["violations"][0]["kind"], "deadlock")
        self.assertEqual(dl_data["violations"][0]["hops"], 3)

        # 4. Multi-invariant (-continue) finding BOTH broken invariants at different depths
        tla_multi = self.dir / "MultiInv.tla"
        tla_multi.write_text(
            "---- MODULE MultiInv ----\n"
            "EXTENDS Naturals\n"
            "VARIABLE x\n"
            "Init == x = 0\n"
            "Step == x < 5 /\\ x' = x + 1\n"
            "Stay == x = 5 /\\ x' = 5\n"
            "Next == Step \\/ Stay\n"
            "InvA == x < 2\n"
            "InvB == x < 4\n"
            "====\n"
        )
        cfg_multi = self.dir / "MultiInv.cfg"
        cfg_multi.write_text("INIT Init\nNEXT Next\nINVARIANT InvA\nINVARIANT InvB\n")
        m_res = run_sc("check", str(tla_multi), "--cfg", str(cfg_multi), "--json")
        self.assertEqual(m_res.returncode, 1, m_res.stderr)
        by_inv = {v["name"]: v["hops"] for v in json.loads(m_res.stdout)["violations"]}
        self.assertEqual(by_inv["InvA"], 2)
        self.assertEqual(by_inv["InvB"], 4)

        # 5. Liveness / temporal lasso cycle
        tla_loop = self.dir / "LassoSpec.tla"
        tla_loop.write_text(
            "---- MODULE LassoSpec ----\n"
            "EXTENDS Naturals\n"
            "VARIABLE x\n"
            "Init == x = 0\n"
            "Up == x < 2 /\\ x' = x + 1\n"
            "Back == x = 2 /\\ x' = 1\n"
            "Next == Up \\/ Back\n"
            "Spec == Init /\\ [][Next]_x /\\ WF_x(Next)\n"
            "ReachesThree == <>(x = 3)\n"
            "====\n"
        )
        cfg_loop = self.dir / "LassoSpec.cfg"
        cfg_loop.write_text("SPECIFICATION Spec\nPROPERTY ReachesThree\n")
        l_res = run_sc("check", str(tla_loop), "--cfg", str(cfg_loop), "--json")
        self.assertEqual(l_res.returncode, 1, l_res.stderr)
        l_data = json.loads(l_res.stdout)
        self.assertEqual(l_data["violations"][0]["kind"], "temporal")
        self.assertIsNotNone(l_data["violations"][0]["cycle_back_to"])

    def test_live_tlc_differential_fuzzer_against_independent_bfs_oracle(self):
        """Generate 10 random finite-state TLA+ specs, solve shortest paths independently, and verify live TLC matches 100%."""
        rng = random.Random(20261126)
        for trial in range(10):
            n_states = rng.randint(4, 9)
            bad_state = rng.randint(1, n_states - 1)
            edges = []
            # Guarantee every state has an outgoing edge so deadlock doesn't confound invariant check
            for u in range(n_states):
                targets = rng.sample(range(n_states), k=rng.randint(1, min(3, n_states)))
                for v in targets:
                    edges.append((u, v))

            expected_hops = _independent_min_hops([0], edges, bad_state)
            mod = f"DiffFuzz{trial}"
            disjuncts = [f"(s = {u} /\\ s' = {v})" for u, v in edges]
            tla = self.dir / f"{mod}.tla"
            tla.write_text(
                f"---- MODULE {mod} ----\n"
                "EXTENDS Naturals\n"
                "VARIABLE s\n"
                "Init == s = 0\n"
                f"Next == {' \\/ '.join(disjuncts)}\n"
                f"NotBad == s # {bad_state}\n"
                "====\n"
            )
            cfg = self.dir / f"{mod}.cfg"
            cfg.write_text("INIT Init\nNEXT Next\nINVARIANT NotBad\n")
            res = run_sc("check", str(tla), "--cfg", str(cfg), "--no-deadlock", "--json")
            if expected_hops == -1:
                self.assertEqual(res.returncode, 0, f"trial {trial}: expected clean, got {res.stdout} {res.stderr}")
                self.assertEqual(json.loads(res.stdout)["violations"], [])
            else:
                self.assertEqual(res.returncode, 1, f"trial {trial}: expected violation at {expected_hops} hops")
                v = json.loads(res.stdout)["violations"][0]
                self.assertEqual(v["name"], "NotBad")
                self.assertEqual(v["hops"], expected_hops, f"trial {trial}: oracle={expected_hops}, tlc={v}")


if __name__ == "__main__":
    unittest.main()
