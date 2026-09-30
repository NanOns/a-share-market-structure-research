"""Versioned, fail-closed governance scan for named-equity runtime logic."""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
from pathlib import Path
import re

POLICY_ID = "NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC"
POLICY_VERSION = "1.2.1"
SYMBOL = re.compile(r"\b(?:SH|SZ|BJ)\.\d{6}\b", re.IGNORECASE)
CANONICAL = re.compile(r"\bSEC-[A-F0-9]{16,}\b")
PLAIN_CODE = re.compile(r"^\d{6}$")
IDENTIFIER_CONTEXT = re.compile(r"(security|symbol|ticker|instrument|stock|share|listing|universe|code|index)", re.I)
HARD_GATED = {"PRODUCTION_RUNTIME", "SYSTEM_PIPELINE", "GOVERNANCE_MUTATION", "RUNTIME_CONFIGURATION"}
ALLOWED_DATA = {"TEST_ONLY", "EVIDENCE_ONLY", "AUDIT_INPUT_ONLY", "USER_DATA", "IMMUTABLE_FACT_DATA", "REFERENCE_DATA"}
EXTENSIONS = {".py", ".sql", ".json", ".yaml", ".yml", ".md"}


def _names(node):
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return [name for child in node.elts for name in _names(child)]
    return []


def _identifier_context(node, parents):
    context = []
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.Compare):
            context.extend(_names(current.left))
            for side in current.comparators:
                context.extend(_names(side))
            break
        if isinstance(current, ast.Dict):
            for key, value in zip(current.keys, current.values):
                if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                        and (value is node or any(child is node for child in ast.walk(value)))):
                    context.append(key.value)
        if isinstance(current, ast.Assign):
            context.extend(name.id for target in current.targets for name in ast.walk(target) if isinstance(name, ast.Name))
            break
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module, ast.ClassDef)):
            break
    return context


def _string_literals(tree):
    parents = {}
    docstrings = set()
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
        if isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and parent.body:
            first = parent.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docstrings.add(first.value)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or node in docstrings:
            continue
        value = node.value
        explicit = SYMBOL.findall(value) or CANONICAL.findall(value)
        if not explicit and not PLAIN_CODE.fullmatch(value):
            continue
        parent = parents.get(node)
        context = _identifier_context(node, parents)
        if isinstance(parent, ast.keyword) and parent.arg:
            context.append(parent.arg)
        if any(re.search(r"(sha|hash|digest|fingerprint)", name, re.I) for name in context):
            continue
        if explicit:
            for hit in SYMBOL.finditer(value):
                yield hit.group(0), node.lineno, "EXPLICIT_SECURITY_OR_SYMBOL_LITERAL"
            for hit in CANONICAL.finditer(value):
                yield hit.group(0), node.lineno, "CANONICAL_SECURITY_ID_LITERAL"
            continue
        if PLAIN_CODE.fullmatch(value) and any(IDENTIFIER_CONTEXT.search(name or "") for name in context):
            yield value, node.lineno, "UNQUALIFIED_SECURITY_CODE_IN_IDENTIFIER_CONTEXT"


def _numeric_code_literals(tree):
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, int) or isinstance(node.value, bool):
            continue
        if not 100000 <= node.value <= 999999:
            continue
        context = _identifier_context(node, parents)
        if any(re.search(r"(sha|hash|digest|fingerprint)", name, re.I) for name in context):
            continue
        if any(IDENTIFIER_CONTEXT.search(name or "") for name in context):
            yield str(node.value), node.lineno, "NUMERIC_SECURITY_CODE_IN_IDENTIFIER_CONTEXT"


def scan_file(path: Path, *, root: Path, category: str):
    rel = path.relative_to(root).as_posix()
    hits = []
    raw = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".py":
        try:
            tree = ast.parse(raw.decode("utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            return {"path": rel, "category": category, "parse_error": str(exc), "hits": [], "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        hits.extend({"line": line, "value": value, "kind": kind} for value, line, kind in _string_literals(tree))
        hits.extend({"line": line, "value": value, "kind": kind} for value, line, kind in _numeric_code_literals(tree))
    else:
        text = raw.decode("utf-8", errors="replace")
        patterns = [(SYMBOL, "EXPLICIT_SECURITY_OR_SYMBOL_DATA"), (CANONICAL, "CANONICAL_SECURITY_ID_DATA")]
        if suffix == ".sql":
            patterns = [(SYMBOL, "EXPLICIT_SECURITY_OR_SYMBOL_LITERAL"), (CANONICAL, "CANONICAL_SECURITY_ID_LITERAL")]
        if suffix in {".md"}:
            patterns = [(SYMBOL, "EXPLICIT_SECURITY_OR_SYMBOL_EVIDENCE"), (CANONICAL, "CANONICAL_SECURITY_ID_EVIDENCE")]
        for pattern, kind in patterns:
            hits.extend({"line": text.count("\n", 0, match.start()) + 1, "value": match.group(0), "kind": kind} for match in pattern.finditer(text))
        if suffix == ".json":
            try:
                document = json.loads(text)
            except json.JSONDecodeError:
                document = None

            def visit_json(value, contexts=()):
                if isinstance(value, dict):
                    for key, child in value.items():
                        next_context = contexts + (str(key),)
                        if PLAIN_CODE.fullmatch(str(key)) and any(IDENTIFIER_CONTEXT.search(item) for item in contexts):
                            hits.append({"line": None, "value": str(key),
                                         "kind": "UNQUALIFIED_SECURITY_CODE_IN_IDENTIFIER_CONTEXT"})
                        visit_json(child, next_context)
                elif isinstance(value, list):
                    for child in value:
                        visit_json(child, contexts)
                elif isinstance(value, str) and PLAIN_CODE.fullmatch(value) and any(IDENTIFIER_CONTEXT.search(item) for item in contexts):
                    hits.append({"line": None, "value": value,
                                 "kind": "UNQUALIFIED_SECURITY_CODE_IN_IDENTIFIER_CONTEXT"})
                elif isinstance(value, int) and not isinstance(value, bool) and 100000 <= value <= 999999 and any(IDENTIFIER_CONTEXT.search(item) for item in contexts):
                    hits.append({"line": None, "value": str(value),
                                 "kind": "NUMERIC_SECURITY_CODE_IN_IDENTIFIER_CONTEXT"})

            if document is not None:
                visit_json(document)
        if suffix == ".sql":
            sql_symbol = re.compile(
                r"(?:CASE\s+WHEN\s+)?[\w.\"`]*?(?:security|symbol|ticker|instrument|stock)[\w.\"`]*(?:code|id)"
                r"\s*(?:=|IN\s*\()\s*['\"]?(\d{6})",
                re.I,
            )
            hits.extend({"line": text.count("\n", 0, match.start()) + 1, "value": match.group(1), "kind": "SQL_SECURITY_FILTER_LITERAL"}
                        for match in sql_symbol.finditer(text))
            sql_case = re.compile(
                r"\bCASE\s+(?:[\w.\"`]*?(?:security|symbol|ticker|instrument|stock)[\w.\"`]*(?:code|id))"
                r"\s+WHEN\s+['\"]?(\d{6})",
                re.I,
            )
            hits.extend({"line": text.count("\n", 0, match.start()) + 1, "value": match.group(1), "kind": "SQL_SECURITY_FILTER_LITERAL"}
                        for match in sql_case.finditer(text))
    result = {"path": rel, "category": category, "hits": hits, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if suffix in {".json", ".yaml", ".yml"}:
        try:
            if suffix == ".json":
                json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            result["parse_error"] = str(exc)
    return result


def _matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _validate_audit_attestation(path, item, root: Path | None):
    required = ("runtime_authorized", "does_not_write_accepted_heads", "does_not_write_runtime_artifacts", "not_called_by_production")
    if not (path.startswith("scripts/")
            and all(item.get(key) is False if key == "runtime_authorized" else item.get(key) is True for key in required)
            and isinstance(item.get("attestation_basis"), str)
            and bool(item.get("attestation_basis", "").strip())
            and root is not None
            and item.get("reviewed_source_sha256")):
        return False
    try:
        actual = hashlib.sha256((root / path).read_bytes()).hexdigest()
    except OSError:
        return False
    return actual == item["reviewed_source_sha256"]


def _script_writes_governance(path: Path) -> bool:
    """Conservatively recognize common writers to accepted and runtime state."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return True
    sensitive_path = re.compile(
        r"(?:data[/\\]v4[/\\](?!source_evidence[/\\])|artifact_store[/\\]|"
        r"reports[/\\]current[/\\](?:CURRENT_RELEASE|CURRENT_STATUS)|"
        r"publication[_/\\-]?heads?|runtime[_/\\-]?state[_/\\-]?heads?)",
        re.I,
    )
    writers = {"atomic_json", "atomic_json_write", "atomic_write_json", "atomic_write_bytes", "atomic_bytes", "atomic_text", "atomic_write", "write_immutable", "write_text", "write_bytes", "open", "replace", "rename", "dump", "publish_generation"}
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

    def scope_of(node):
        current = node
        while current in parents:
            current = parents[current]
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return current
        return tree

    assignments_by_scope = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            assignments_by_scope.setdefault(scope_of(node), []).append(node)

    def propagate(assignments, initially_sensitive):
        names = set(initially_sensitive)
        changed = True
        while changed:
            changed = False
            for node in assignments:
                value = getattr(node, "value", None)
                if value is None:
                    continue
                try:
                    source = ast.unparse(value)
                except (AttributeError, TypeError):
                    source = ""
                referenced_names = {item.id for item in ast.walk(value) if isinstance(item, ast.Name)}
                if sensitive_path.search(source) or referenced_names & names:
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    additions = {name.id for target in targets for name in ast.walk(target) if isinstance(name, ast.Name)}
                    if additions - names:
                        names.update(additions)
                        changed = True
        return names

    global_names = propagate(assignments_by_scope.get(tree, []), set())
    names_by_scope = {tree: global_names}
    for scope, assignments in assignments_by_scope.items():
        if scope is not tree:
            names_by_scope[scope] = propagate(assignments, global_names)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
        if name not in writers:
            continue
        if name in {"write_text", "write_bytes"}:
            destination = node.func.value if isinstance(node.func, ast.Attribute) else None
        elif name in {"replace", "rename"} and len(node.args) >= 2:
            destination = node.args[1]
        elif name in {"atomic_json", "atomic_json_write", "atomic_write_json", "atomic_write_bytes", "atomic_bytes", "atomic_text", "atomic_write", "write_immutable", "publish_generation", "dump", "open"} and node.args:
            destination = node.args[0]
        else:
            destination = None
        if name == "open" and not any(isinstance(arg, ast.Constant) and isinstance(arg.value, str) and any(mode in arg.value for mode in ("w", "a", "+")) for arg in node.args[1:2]):
            continue
        if destination is None:
            continue
        try:
            source = ast.unparse(destination)
        except (AttributeError, TypeError):
            source = ""
        referenced_names = {item.id for item in ast.walk(destination) if isinstance(item, ast.Name)}
        if sensitive_path.search(source) or referenced_names & names_by_scope.get(scope_of(node), global_names):
            return True
    return False


def classify(path: str, policy: dict, *, root: Path | None = None, production_modules=frozenset()):
    path = path.replace("\\", "/")
    roles = policy.get("path_roles", {})
    if path.startswith("tests/") and path.endswith((".py", ".sql")):
        return "TEST_ONLY"
    if _matches(path, policy.get("test_only_globs", [])):
        return "TEST_ONLY"
    if path.startswith("reports/v4_08/audit_inputs/"):
        return "AUDIT_INPUT_ONLY"
    if _matches(path, policy.get("evidence_only_globs", [])):
        return "EVIDENCE_ONLY"
    if path in policy.get("reference_data_paths", []):
        return "REFERENCE_DATA"
    if path in policy.get("production_entrypoints", []) or _matches(path, policy.get("production_runtime_globs", [])):
        return "PRODUCTION_RUNTIME"
    if path.startswith("data/v4/source_evidence/"):
        return "EVIDENCE_ONLY"
    if path.startswith("data/v4/artifact_store/"):
        return "IMMUTABLE_FACT_DATA"
    if path.startswith("data/user/") or path.startswith("data/focus/"):
        return "USER_DATA"
    # Writer detection takes precedence over any script allowlist.
    if path.startswith("scripts/") and (any(_matches(path, [pattern]) for pattern in policy.get("governance_mutation_globs", []))
            or (root is not None and _script_writes_governance(root / path))):
        return "GOVERNANCE_MUTATION"
    if path in roles:
        role = roles[path]
        category = role.get("category")
        valid_categories = HARD_GATED | ALLOWED_DATA | {"AUDIT_ONLY", "REFERENCE_DATA", "UNCLASSIFIED_FAIL_CLOSED"}
        if category == "AUDIT_ONLY" and not _validate_audit_attestation(path, role, root):
            return "UNCLASSIFIED_FAIL_CLOSED"
        return category if category in valid_categories else "UNCLASSIFIED_FAIL_CLOSED"
    if path in policy.get("runtime_configuration_paths", []) or (path.startswith("config/") and Path(path).suffix.lower() in {".json", ".yaml", ".yml"}):
        return "RUNTIME_CONFIGURATION"
    if path in policy.get("reference_data_paths", []):
        return "REFERENCE_DATA"
    if path.startswith("src/") and Path(path).suffix.lower() in {".py", ".sql"}:
        module = _module_for_path(path)
        if module in production_modules or _matches(path, policy.get("production_runtime_globs", [])):
            return "PRODUCTION_RUNTIME"
        if _matches(path, policy.get("system_pipeline_globs", ["src/**/*.py", "src/**/*.sql"])):
            return "SYSTEM_PIPELINE"
        return "UNCLASSIFIED_FAIL_CLOSED"
    if path.startswith("scripts/") and Path(path).suffix.lower() in {".py", ".sql"}:
        return "SYSTEM_PIPELINE"
    if _matches(path, policy.get("immutable_fact_globs", [])):
        return "IMMUTABLE_FACT_DATA"
    if _matches(path, policy.get("user_data_globs", [])):
        return "USER_DATA"
    return "UNCLASSIFIED_FAIL_CLOSED"


def _module_for_path(path: str):
    rel = path.removeprefix("src/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    if rel.endswith("/__init__"):
        rel = rel[:-9]
    return rel.replace("/", ".")


def _module_index(root: Path):
    modules = {}
    base = root / "src"
    if base.exists():
        for file in base.rglob("*.py"):
            rel = file.relative_to(root).as_posix()
            module = _module_for_path(rel)
            modules[module] = rel
            modules.setdefault(module.rsplit(".", 1)[-1], rel)
    for file in root.glob("*.py"):
        modules[file.stem] = file.name
    return modules


def _imports(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(("." * node.level) + node.module)
    return found


def production_call_graph(root: Path, policy: dict):
    module_index = _module_index(root)
    roots = policy.get("production_entrypoints", ["src/production/daily.py", "run_daily.py"])
    root_modules = [(_module_for_path(path) if path.startswith("src/") else Path(path).stem) for path in roots]
    adjacency = {}
    for module, rel in module_index.items():
        canonical = _module_for_path(rel) if rel.startswith("src/") else Path(rel).stem
        if module != canonical:
            continue
        path = root / rel
        edges = []
        for imported in _imports(path):
            imported = imported.lstrip(".")
            resolved = module_index.get(imported)
            if not resolved and "." in imported:
                resolved = module_index.get(imported.split(".", 1)[0])
            if resolved:
                child = _module_for_path(resolved) if resolved.startswith("src/") else Path(resolved).stem
                edges.append(child)
        adjacency.setdefault(module, set()).update(edges)
    reachable = set()
    stack = root_modules[:]
    while stack:
        node = stack.pop()
        if node in reachable:
            continue
        reachable.add(node)
        stack.extend(adjacency.get(node, ()))
    # Modules invoked through production's explicit run chain are part of the contract.
    required_paths = policy.get("production_required_modules", [])
    required_modules = {_module_for_path(path) for path in required_paths}
    reachable.update(required_modules)
    edges = sorted({(source, target) for source, children in adjacency.items() if source in reachable for target in children})
    nodes = [{"module": module, "path": module_index.get(module, next((p for p in required_paths if _module_for_path(p) == module), None)),
              "category": "PRODUCTION_RUNTIME"}
             for module in sorted(reachable)]
    return {"entrypoints": roots, "nodes": nodes, "edges": [{"from": a, "to": b} for a, b in edges],
            "required_paths": required_paths, "unresolved_required_paths": [p for p in required_paths if not (root / p).exists()]}, reachable


def _scan_roots(root: Path, policy: dict):
    found = set()
    excluded = set(policy.get("scan_exclude_paths", []))
    for item in policy.get("scan_roots", []):
        base = root / item
        if base.is_file():
            if base.suffix.lower() in EXTENSIONS and base.relative_to(root).as_posix() not in excluded:
                found.add(base)
        elif base.is_dir():
            found.update(path for path in base.rglob("*") if path.is_file() and path.suffix.lower() in EXTENSIONS
                         and path.relative_to(root).as_posix() not in excluded)
    for pattern in policy.get("scan_globs", []):
        found.update(path for path in root.glob(pattern) if path.is_file() and path.suffix.lower() in EXTENSIONS
                     and path.relative_to(root).as_posix() not in excluded)
    return sorted(found, key=lambda path: path.relative_to(root).as_posix())


def _reference_registry_valid(path: Path):
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    instruments = document.get("instruments", []) if isinstance(document, dict) else []
    return (document.get("classification") == "REFERENCE_DATA"
            and document.get("runtime_authorized") is True
            and bool(instruments)
            and all(isinstance(item, dict) and item.get("instrument_type") == "MARKET_INDEX" for item in instruments))


def run(root: Path):
    root = Path(root).resolve()
    policy_path = root / "config/runtime_path_policy_v1.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    graph, reachable = production_call_graph(root, policy)
    module_to_path = {_module_for_path(x["path"]): x["path"] for x in graph["nodes"] if x.get("path")}
    results = []
    for path in _scan_roots(root, policy):
        rel = path.relative_to(root).as_posix()
        category = classify(rel, policy, root=root, production_modules=reachable)
        result = scan_file(path, root=root, category=category)
        if category == "REFERENCE_DATA" and not _reference_registry_valid(path):
            result["parse_error"] = "REFERENCE_DATA_SCHEMA_INVALID"
            result["category"] = "UNCLASSIFIED_FAIL_CLOSED"
        if result.get("parse_error"):
            result["category"] = "UNCLASSIFIED_FAIL_CLOSED"
        results.append(result)
    hard_hits = [{"path": item["path"], **hit} for item in results if item["category"] in HARD_GATED for hit in item["hits"]]
    unclassified = [item["path"] for item in results if item["category"] == "UNCLASSIFIED_FAIL_CLOSED" or item.get("parse_error")]
    governance_paths = [item["path"] for item in results if item["category"] == "GOVERNANCE_MUTATION"]
    runtime_paths = [item["path"] for item in results if item["category"] == "RUNTIME_CONFIGURATION"]
    all_hits = [{"path": item["path"], "category": item["category"], **hit} for item in results for hit in item["hits"]]
    allowed_hit_indexes = [index for index, hit in enumerate(all_hits) if hit["category"] in ALLOWED_DATA]
    audit_hit_indexes = [index for index, hit in enumerate(all_hits) if hit["category"] == "AUDIT_ONLY"]
    summary = {category: sum(item["category"] == category for item in results) for category in sorted(
        HARD_GATED | ALLOWED_DATA | {"REFERENCE_DATA", "AUDIT_ONLY", "UNCLASSIFIED_FAIL_CLOSED"})}
    return {
        "contract_id": POLICY_ID,
        "contract_version": POLICY_VERSION,
        "status": "PASS" if not hard_hits and not unclassified else "FAIL",
        "hard_gated_equity_symbol_hits": len(hard_hits),
        "hard_gated_hits": hard_hits,
        "unclassified_paths": unclassified,
        "production_call_graph": graph,
        "governance_mutation_paths": governance_paths,
        "runtime_configuration_paths": runtime_paths,
        "category_counts": summary,
        "specific_stock_literal_hits": len(all_hits),
        "all_symbol_literals": all_hits,
        "allowed_evidence_test_user_fact_reference_hits": {
            "encoding": "indexes into all_symbol_literals",
            "count": len(allowed_hit_indexes),
            "indexes": allowed_hit_indexes,
        },
        "audit_only_hits": {
            "encoding": "indexes into all_symbol_literals",
            "count": len(audit_hit_indexes),
            "indexes": audit_hit_indexes,
        },
        "scanned_paths": [item["path"] for item in results],
        "category_per_file": {item["path"]: item["category"] for item in results},
        "file_receipts": [{key: item[key] for key in ("path", "category", "byte_count", "sha256", "parse_error") if key in item} for item in results],
        "results": [{"path": item["path"], "category": item["category"], "hit_count": len(item["hits"]),
                     **({"parse_error": item["parse_error"]} if "parse_error" in item else {})} for item in results],
        "policy_path": policy_path.relative_to(root).as_posix(),
    }


def main():
    root = Path(__file__).resolve().parents[1]
    result = run(root)
    path = root / "reports/v4_08/V4_08_R4_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json"
    from build_v4_08_r2_membership_evidence import atomic_json
    atomic_json(path, result)
    print(json.dumps({key: result[key] for key in ("status", "hard_gated_equity_symbol_hits", "specific_stock_literal_hits", "unclassified_paths")}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
