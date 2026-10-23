#!/usr/bin/env python3
"""V4 hard-coded business identity admission scanner.

Scans tracked runtime, source, config, migration, and UI files. Candidate
literals are classified by environment and a conservative Python import graph;
unknown dynamic reachability is reported as unresolved, never as a pass.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from collections import deque
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE_RE = re.compile(r"(?<!\d)(?:20\d{2}[-/]\d{2}[-/]\d{2}|20\d{6})(?!\d)")
SEC_RE = re.compile(r"(?i)(?:\b(?:sh|sz|bj)\.?\d{6}\b|\bSEC-[A-Z0-9._-]+\b|(?<!\d)\d{6}(?!\d))")
SECTOR_RE = re.compile(r"(?i)(?:\b(?:INDUSTRY|THEME):[A-Z0-9_-]+\b|\bT\d{4}\b)")
EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".sql", ".json", ".yaml", ".yml", ".toml", ".ini", ".cmd", ".bat", ".ps1", ".sh"}
ROOT_FILES = {"OPEN_RESEARCH_WORKBENCH.cmd", "OPEN_UNIFIED_WORKBENCH.cmd"}


def tracked_files() -> list[str]:
    raw = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"], env=None)
    items = [x.decode("utf-8", "surrogateescape") for x in raw.split(b"\0") if x]
    keep = []
    for rel in items:
        if rel == "config/v4_business_literal_admission_baseline_v1.json":
            # Test-only change detector state is not a runtime business input.
            continue
        p = Path(rel)
        if p.suffix.lower() not in EXT and not ("run_" in p.name and p.suffix.lower() in {".py", ".cmd", ".ps1"}):
            continue
        if rel.startswith("docs/evidence/") or rel.startswith("docs/audits/"):
            continue
        if rel.startswith(("src/", "scripts/", "config/", "migrations/", "tools/", "runtime/", "tests/")) or p.parent == Path(".") or rel in ROOT_FILES:
            keep.append(rel)
    return sorted(set(keep))


def module_map(files: list[str]) -> dict[str, str]:
    result = {}
    for rel in files:
        p = Path(rel)
        if p.suffix != ".py":
            continue
        if p.parts[0] == "src":
            parts = list(p.with_suffix("").parts[1:])
            if parts and parts[-1] == "__init__": parts.pop()
            if parts: result[".".join(parts)] = rel
        elif p.parts[0] in {"scripts", "tools", "tests"}:
            result[p.with_suffix("").as_posix().replace("/", ".")] = rel
    return result


def imports(path: Path, rel: str, modules: dict[str, str]) -> set[str]:
    try: tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (SyntaxError, UnicodeError, OSError): return set()
    found = set()
    package = rel.split("/")[:-1]
    if package and package[0] == "src": package = package[1:]
    base = ".".join(package)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name in modules: found.add(modules[n.name])
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level:
                prefix = base.split(".")
                prefix = prefix[:max(0, len(prefix) - node.level + 1)]
                mod = ".".join(prefix + ([mod] if mod else []))
            candidates = [mod] + [mod + "." + n.name for n in node.names]
            for name in candidates:
                if name in modules: found.add(modules[name])
    return found


def runtime_graph(files: list[str]) -> tuple[set[str], dict[str, list[str]], list[str], dict[str, list[str]]]:
    modules = module_map(files)
    graph = {}
    seeds = set()
    for rel in files:
        p = Path(rel)
        if p.suffix.lower() in {".cmd", ".bat", ".ps1"} and (rel.startswith("scripts/") or p.parent == Path(".")):
            seeds.add(rel)
            try:
                body = p.read_text(encoding="utf-8-sig")
                for target in re.findall(r"(?:python(?:\.exe)?|py)\s+(?:-\w+\s+)*[\"']?([^\s\"']+\.py)", body, re.I):
                    normalized = target.replace("\\", "/")
                    if normalized in files: seeds.add(normalized)
            except OSError: pass
        elif p.parent == Path(".") and p.suffix == ".py" and (p.name.startswith("run_") or p.name.startswith("OPEN_")):
            seeds.add(rel)
    # Known web service modules are roots where the workspace has a server launcher/config.
    seeds.update(rel for rel in files if rel in {"src/workbench_service/v4_server.py", "src/workbench_service/v4_control_server_v2.py"})
    for rel in files:
        if rel.endswith(".py"):
            graph[rel] = imports(ROOT / rel, rel, modules)
        else: graph[rel] = set()
    # Resolve literal Python script references in cmd/PowerShell/config launchers.
    for rel in files:
        if Path(rel).suffix.lower() not in {".cmd", ".bat", ".ps1", ".json", ".yaml", ".yml", ".toml", ".ini"}: continue
        try: body = (ROOT / rel).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError): continue
        for target in re.findall(r"(?:scripts|src|tools)/[A-Za-z0-9_./-]+\.py", body):
            if target in files: graph.setdefault(rel, set()).add(target)
    # Literal runtime data/config references from Python are part of the graph.
    for rel in files:
        if not rel.endswith(".py"): continue
        try: body=(ROOT/rel).read_text(encoding="utf-8-sig")
        except (OSError,UnicodeError): continue
        for target in re.findall(r"(?:config|migrations|src/workbench_service/static)/[A-Za-z0-9_./-]+\.(?:json|ya?ml|sql|html|js|css)",body):
            if target in files: graph.setdefault(rel,set()).add(target)
    reachable = set(); todo = list(seeds)
    while todo:
        item = todo.pop()
        if item in reachable: continue
        reachable.add(item); todo.extend(graph.get(item, ()))
    graph={k: sorted(v) for k, v in graph.items() if v}
    paths={}; queue=deque((s,[s]) for s in seeds)
    while queue:
        node,path=queue.popleft()
        if node in paths: continue
        paths[node]=path
        for child in graph.get(node,[]):
            if child not in paths: queue.append((child,path+[child]))
    return reachable, graph, sorted(seeds), paths


def env_for(rel: str, reachable: bool) -> tuple[str, str]:
    if rel.startswith("tests/"): return "TEST_ONLY", "TEST_ONLY"
    if rel.startswith("docs/evidence/") or rel.startswith("docs/audits/"): return "HISTORICAL_FROZEN", "HISTORICAL_FROZEN"
    if rel.startswith("config/") or rel.startswith("migrations/"): return ("ACTIVE_CONFIG" if reachable else "CONFIG_REACHABILITY_UNRESOLVED"), ("UNRESOLVED" if reachable else "UNRESOLVED")
    if reachable: return "ACTIVE_OR_LEGACY_REQUIRED", "UNRESOLVED"
    if rel.startswith(("scripts/", "tools/")): return "INACTIVE_OR_DYNAMIC_SCRIPT", "UNRESOLVED"
    return "UNREACHABLE_STATIC", "UNRESOLVED"


def scan(files: list[str]) -> tuple[list[dict], dict]:
    reachable, graph, seeds, paths = runtime_graph(files)
    findings = []
    ast_parse_failures = []
    counts = {"python": 0, "javascript": 0, "sql": 0, "config": 0, "ui": 0, "runtime_scripts": 0}
    for rel in files:
        p = Path(rel); ext = p.suffix.lower()
        if ext == ".py": counts["python"] += 1
        if ext in {".js", ".ts", ".tsx", ".jsx"}: counts["javascript"] += 1
        if ext == ".sql": counts["sql"] += 1
        if ext in {".json", ".yaml", ".yml", ".toml", ".ini"}: counts["config"] += 1
        if ext in {".html", ".js", ".ts", ".tsx", ".jsx"}: counts["ui"] += 1
        if rel.startswith("scripts/") or p.name.startswith("run_"): counts["runtime_scripts"] += 1
        try: text = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError): continue
        lines = text.splitlines()
        tree = None
        if ext == ".py":
            try: tree = ast.parse(text)
            except SyntaxError as exc: ast_parse_failures.append({"file":rel,"line":exc.lineno,"reason":exc.msg})
        nodes_by_line = {}
        if tree:
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, (str, int)):
                    nodes_by_line.setdefault(n.lineno, set()).add(type(n).__name__)
                elif isinstance(n, ast.JoinedStr): nodes_by_line.setdefault(n.lineno, set()).add(type(n).__name__)
        for line_no, line in enumerate(lines, 1):
            # Comment-only lines do not drive runtime values.
            if ext == ".py" and line.lstrip().startswith("#"): continue
            matches = []
            for category, regex in (("CONSTANT_DATE", DATE_RE), ("CONSTANT_SECURITY_ID", SEC_RE), ("CONSTANT_SECTOR_ID", SECTOR_RE)):
                for m in regex.finditer(line):
                    # Six digit number literals are only identity candidates in identity-related contexts.
                    if category == "CONSTANT_SECURITY_ID" and re.fullmatch(r"\d{6}", m.group()) and not re.search(r"(?i)(symbol|stock|security|code|ticker|instrument|members?|universe|证券|股票|代码|WHERE|IN\s*\()", line): continue
                    if category == "CONSTANT_SECTOR_ID" and m.group().upper() == "T0002" and "T0002/" in line:
                        continue  # TDX cache directory name, not a taxonomy ID.
                    matches.append((category, m.group(), m.start()+1))
            for category, literal, col in matches:
                env, disposition = env_for(rel, rel in reachable)
                node_types = sorted(nodes_by_line.get(line_no, ()))
                context = line.strip()[:320]
                frozen_path_literal = False
                if tree:
                    for node in ast.walk(tree):
                        if not (isinstance(node, ast.Constant) and isinstance(node.value, str) and node.lineno == line_no):
                            continue
                        segment = ast.get_source_segment(text, node) or ""
                        if literal in node.value and ("docs/evidence/" in node.value or "docs/audits/" in node.value):
                            # Exact immutable evidence bindings are retained as
                            # historical inputs; they are not a current-date default.
                            frozen_path_literal = True
                            break
                # Exempt declaration of documented protocol/formats from date-shaped matches.
                protocol = bool(category == "CONSTANT_DATE" and re.fullmatch(r"YYYY[-/]MM[-/]DD", literal))
                if protocol: disposition = "CONTRACT_CONSTANT"
                if frozen_path_literal: disposition = "HISTORICAL_FROZEN"
                finding_id = f"LIT-{len(findings)+1:06d}"
                candidate_key = hashlib.sha256(f"{rel}\0{line_no}\0{category}\0{literal}\0{context}".encode("utf-8")).hexdigest()
                findings.append({"id": finding_id, "file": rel, "line": line_no, "column": col,
                    "literal": literal, "category": category, "ast_node_types": node_types,
                    "candidate_key": candidate_key,
                    "environment": env, "runtime_reachable": rel in reachable,
                    "entrypoints": [paths[rel][0]] if rel in paths else [], "call_chain": paths.get(rel, []),
                    "classification": disposition, "functional_impact": "Exact immutable evidence path binding; retained only as dated historical input." if frozen_path_literal else "Review source and business context; scanner is candidate recall.",
                    "handling": disposition if disposition in {"CONTRACT_CONSTANT", "HISTORICAL_FROZEN"} else ("TEST_ONLY" if env == "TEST_ONLY" else "UNRESOLVED"),
                    "replacement_source": "immutable evidence manifest/path" if frozen_path_literal else None, "modification_commit": None,
                    "regression_id": None, "context": context,
                    "verifier": "scripts/check_v4_business_literals.py"})
    dynamic_sites=[]
    for rel in files:
        if not rel.endswith('.py'):continue
        try:body=(ROOT/rel).read_text(encoding='utf-8-sig')
        except (OSError,UnicodeError):continue
        if re.search(r"\b(?:importlib\.import_module|__import__|runpy\.run_path|eval\s*\(|exec\s*\()",body):dynamic_sites.append(rel)
    summary = {"files_scanned": len(files), "source_python": counts["python"], "source_js": counts["javascript"],
        "runtime_scripts": counts["runtime_scripts"], "config": counts["config"], "sql": counts["sql"], "ui": counts["ui"],
        "active_reachable": sum(1 for x in reachable if x in files), "inactive_historical": 0,
        "test_only": sum(1 for x in files if x.startswith("tests/")), "python_reachable_files": len(reachable),
        "entrypoints": seeds, "import_edges": sum(len(x) for x in graph.values()), "dynamic_import_sites": dynamic_sites,
        "python_ast_parse_failures": ast_parse_failures}
    return findings, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描 V4 正常运行路径中的固定交易日、证券和板块身份")
    parser.add_argument("--output", type=Path, required=True, help="机器可读清单输出路径")
    parser.add_argument("--fail-on-reachable", action="store_true", help="存在可达路径的固定业务字面量候选时返回失败")
    args = parser.parse_args()
    files = tracked_files(); findings, summary = scan(files)
    reachable, graph, seeds, _ = runtime_graph(files)
    reachable_hits = sum(1 for x in findings if x["runtime_reachable"] and x["handling"] == "UNRESOLVED")
    gate_status = "GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED" if reachable_hits else "GLOBAL_RUNTIME_LITERAL_GATE_PASS"
    payload = {"schema_version": "V4-PRODUCTION-LITERAL-INVENTORY/1", "status": gate_status,
        "summary": summary, "runtime_graph": {"entrypoints":seeds,"edges":graph,"dynamic_import_sites":summary["dynamic_import_sites"]}, "findings": findings}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.output)
    compact_summary={k:v for k,v in summary.items() if k not in {"entrypoints","dynamic_import_sites","python_ast_parse_failures"}}
    compact_summary.update(entrypoint_count=len(seeds),dynamic_import_site_count=len(summary["dynamic_import_sites"]),python_ast_parse_failure_count=len(summary["python_ast_parse_failures"]))
    print(json.dumps({"output": args.output.as_posix(), "summary": compact_summary, "literal_candidates": len(findings),
                      "reachable_unresolved_candidates": reachable_hits}, ensure_ascii=False))
    return 1 if args.fail_on_reachable and reachable_hits else 0


if __name__ == "__main__":
    sys.exit(main())
