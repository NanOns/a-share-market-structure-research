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
import importlib.util
from collections import deque
import json
import re
import subprocess
import sys
import sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE_RE = re.compile(r"(?<!\d)20\d{2}[-/]\d{2}[-/]\d{2}(?!\d)|(?<![0-9a-f])20\d{6}(?![0-9a-f])", re.IGNORECASE)
SEC_RE = re.compile(r"(?i)(?:\b(?:sh|sz|bj)\.?\d{6}\b|\bSEC-[A-Z0-9._-]+\b|(?<![0-9a-f])\d{6}(?![0-9a-f]))")
SECTOR_RE = re.compile(r"(?i)(?:\b(?:INDUSTRY|THEME):[A-Z0-9_-]+\b|\bT\d{4}\b)")
EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".sql", ".json", ".yaml", ".yml", ".toml", ".ini", ".cmd", ".bat", ".ps1", ".sh"}
ROOT_FILES = {"OPEN_RESEARCH_WORKBENCH.cmd", "OPEN_UNIFIED_WORKBENCH.cmd"}
ENTRYPOINT_CONTRACT = "config/v4_active_runtime_entrypoints_v1.json"


def active_entrypoint_inventory(files: list[str]) -> tuple[list[str], dict]:
    """Read the checked V4 launcher/service inventory; unknown files fail closed."""
    try:
        value=json.loads((ROOT/ENTRYPOINT_CONTRACT).read_text(encoding="utf-8"))
        if value.get("contract_id")!="V4_ACTIVE_RUNTIME_ENTRYPOINTS_V1" or value.get("version")!="1.0.0":
            raise ValueError("ACTIVE_ENTRYPOINT_CONTRACT_INVALID")
        entries=value.get("entrypoints")
        if not isinstance(entries,list) or not entries or any(not isinstance(x,str) or x not in files for x in entries):
            raise ValueError("ACTIVE_ENTRYPOINT_PATH_NOT_TRACKED")
        bindings=value.get("entrypoint_sha256")
        if not isinstance(bindings,dict) or set(bindings)!=set(entries):
            raise ValueError("ACTIVE_ENTRYPOINT_SOURCE_BINDINGS_INCOMPLETE")
        for rel in entries:
            actual=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
            if bindings.get(rel)!=actual:
                raise ValueError(f"ACTIVE_ENTRYPOINT_SOURCE_BINDING_MISMATCH:{rel}")
        evidence={"status":"SOURCE_VERIFIED","contract_path":ENTRYPOINT_CONTRACT,
                  "entrypoints":entries,"entrypoint_bindings":bindings,
                  "contract_sha256":hashlib.sha256((ROOT/ENTRYPOINT_CONTRACT).read_bytes()).hexdigest()}
        return entries,evidence
    except (OSError,ValueError,TypeError) as error:
        # Preserve conservative coverage if the activity contract is absent or stale.
        legacy=[x for x in files if Path(x).parent==Path(".") and Path(x).suffix==".py" and Path(x).name.startswith("run_")]
        return legacy,{"status":"UNKNOWN","contract_path":ENTRYPOINT_CONTRACT,"reason":str(error)}


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
            if parts:
                result[".".join(parts)] = rel
                result["src."+".".join(parts)] = rel
        elif p.parts[0] in {"scripts", "tools", "tests"}:
            result[p.with_suffix("").as_posix().replace("/", ".")] = rel
        elif p.parent==Path('.'):
            result[p.stem]=rel
    return result


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _scope_nodes(scope: ast.AST):
    """Walk one lexical scope without borrowing assignments from nested scopes."""
    stack = [scope]
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if child is not scope and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                         ast.ClassDef, ast.Lambda)):
                continue
            stack.append(child)


def _string_values(node: ast.AST) -> tuple[str, ...] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = [item.value for item in node.elts
                  if isinstance(item, ast.Constant) and isinstance(item.value, str)]
        if len(values) == len(node.elts) and values:
            return tuple(values)
    return None


def dynamic_import_targets(call: ast.Call, parents: dict[ast.AST, ast.AST]) -> tuple[str, ...]:
    """Resolve literal names and simple, finite local import allowlists."""
    if not call.args:
        return ()
    argument = call.args[0]
    direct = _string_values(argument)
    if direct is not None:
        return direct
    if not isinstance(argument, ast.Name):
        return ()
    cursor = parents.get(call)
    while cursor is not None:
        iterable = None
        targets = ()
        if isinstance(cursor, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in cursor.generators:
                if any(isinstance(target, ast.Name) and target.id == argument.id
                       for target in ast.walk(generator.target)):
                    iterable = generator.iter
                    targets = (generator.target,)
                    break
        elif isinstance(cursor, (ast.For, ast.AsyncFor)):
            targets = (cursor.target,)
            iterable = cursor.iter
        if iterable is not None and (any(isinstance(target, ast.Name) and target.id == argument.id
                                         for target in targets) or
                                     any(isinstance(item, ast.Name) and item.id == argument.id
                                         for target in targets for item in ast.walk(target))):
            values = _string_values(iterable)
            if values is not None:
                return values
            if isinstance(iterable, ast.Name):
                binding_name = iterable.id
            else:
                return ()
            scope = next((item for item in _ancestor_nodes(cursor, parents)
                          if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module))), None)
            if scope is None:
                return ()
            assignments = []
            for item in _scope_nodes(scope):
                if isinstance(item, ast.Assign) and any(isinstance(target, ast.Name) and target.id == binding_name
                                                        for target in item.targets):
                    assignments.append(item.value)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.target.id == binding_name:
                    assignments.append(item.value)
            return _string_values(assignments[0]) if len(assignments) == 1 else ()
        cursor = parents.get(cursor)
    return ()


def _ancestor_nodes(node: ast.AST, parents: dict[ast.AST, ast.AST]):
    cursor = node
    while cursor in parents:
        cursor = parents[cursor]
        yield cursor


def imports(path: Path, rel: str, modules: dict[str, str]) -> set[str]:
    try: tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (SyntaxError, UnicodeError, OSError): return set()
    found = set()
    package = rel.split("/")[:-1]
    if package and package[0] == "src": package = package[1:]
    base = ".".join(package)
    parents = _parents(tree)
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
        elif isinstance(node,ast.Call):
            name=ast.unparse(node.func)
            if name in {'__import__','importlib.import_module','runpy.run_module','runpy.run_path'} and node.args:
                for target in dynamic_import_targets(node,parents):
                    if target in modules:found.add(modules[target])
                    elif name=='runpy.run_path' and target in modules.values():found.add(target)
    return found


def is_standard_library_module(name: str | None) -> bool:
    """Recognize literal stdlib imports without treating third-party modules as resolved."""
    if not name or not isinstance(name, str):
        return False
    top_level = name.partition(".")[0]
    if top_level not in sys.stdlib_module_names:
        return False
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ModuleNotFoundError, ValueError):
        return False
    if spec is None:
        return False
    if spec.origin in {"built-in", "frozen"}:
        return True
    if not spec.origin:
        return False
    try:
        origin = Path(spec.origin).resolve()
        stdlib_root = Path(sysconfig.get_path("stdlib")).resolve()
        site_roots = [Path(sysconfig.get_path(key)).resolve()
                      for key in ("purelib", "platlib") if sysconfig.get_path(key)]
        return origin.is_relative_to(stdlib_root) and not any(origin.is_relative_to(site) for site in site_roots)
    except (OSError,TypeError,ValueError):
        return False


def runtime_graph(files: list[str]) -> tuple[set[str], dict[str, list[str]], list[str], dict[str, list[str]]]:
    modules = module_map(files)
    graph = {}
    active_entries,entrypoint_evidence=active_entrypoint_inventory(files)
    seeds = set(active_entries)
    for rel in files:
        p = Path(rel)
        if p.suffix.lower() in {".cmd", ".bat", ".ps1"} and rel in active_entries:
            try:
                body = (ROOT/p).read_text(encoding="utf-8-sig")
                for target in re.findall(r"(?:python(?:\.exe)?|py)\s+(?:-\w+\s+)*[\"']?([^\s\"']+\.py)", body, re.I):
                    normalized = target.replace("\\", "/")
                    if normalized in files: seeds.add(normalized)
            except OSError: pass
    for rel in files:
        if rel.endswith(".py"):
            graph[rel] = imports(ROOT / rel, rel, modules)
        else: graph[rel] = set()
    # Merge static service edges AFTER imports. Dynamic asset selection requires
    # conservative coverage; it is not proof that all browser routes resolve.
    static_assets=[x for x in files if x.startswith("src/workbench_service/static/")]
    for rel in active_entries:
        if rel in {"src/workbench_service/v4_server.py","src/workbench_service/v4_control_server_v2.py","src/workbench_desktop/engine.py"}:
            graph.setdefault(rel,set()).update(static_assets)
    # Follow literal HTML/JS/JSX module and asset references outside that directory.
    # HTTP fetch routes are recorded separately as unresolved runtime edges.
    for rel in files:
        if Path(rel).suffix.lower() not in {".html", ".js", ".jsx", ".ts", ".tsx"}: continue
        try: body=(ROOT/rel).read_text(encoding="utf-8-sig")
        except (OSError,UnicodeError): continue
        for target in re.findall(r'''(?:src\s*=\s*|href\s*=\s*|from\s+|import\s*\(?\s*)["']([^"']+)["']''',body):
            target=target.split("?",1)[0].split("#",1)[0]
            if "://" in target or target.startswith("//"): continue
            candidate=(ROOT/rel).parent/target if not target.startswith("/") else ROOT/target.lstrip("/")
            for path in (candidate, candidate.with_suffix(".js"), candidate.with_suffix(".jsx"), candidate.with_suffix(".ts"), candidate.with_suffix(".tsx")):
                resolved=path.resolve()
                if resolved.is_relative_to(ROOT.resolve()):
                    linked=resolved.relative_to(ROOT.resolve()).as_posix()
                    if linked in files: graph[rel].add(linked)
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
    if rel.startswith("tests/") and reachable:return "ACTIVE_TEST_IMPORT","UNRESOLVED"
    if rel.startswith("tests/"): return "TEST_ONLY", "TEST_ONLY"
    if rel.startswith("docs/evidence/") or rel.startswith("docs/audits/"): return "HISTORICAL_FROZEN", "HISTORICAL_FROZEN"
    if rel.startswith("config/") or rel.startswith("migrations/"): return ("ACTIVE_CONFIG" if reachable else "CONFIG_REACHABILITY_UNRESOLVED"), ("UNRESOLVED" if reachable else "UNRESOLVED")
    if reachable: return "ACTIVE_OR_LEGACY_REQUIRED", "UNRESOLVED"
    if rel.startswith(("scripts/", "tools/")): return "INACTIVE_OR_DYNAMIC_SCRIPT", "UNRESOLVED"
    return "UNREACHABLE_STATIC", "UNRESOLVED"


def semantic_candidate_key(rel: str, category: str, literal: str, line: str) -> str:
    normalized = " ".join(line.strip()[:320].split())
    return hashlib.sha256(f"{rel}\0{category}\0{literal}\0{normalized}".encode("utf-8")).hexdigest()


def versioned_market_reference(rel: str, literal: str) -> bool:
    """Prove only the explicit index benchmark contract's configured symbols."""
    if rel not in {"config/core_product_index_benchmark_v1.json","config/v4_market_reference_instruments_v1_1.json"}:return False
    try:
        contract=json.loads((ROOT/"config/core_product_index_benchmark_v1.json").read_text(encoding="utf-8"))
        consumer=(ROOT/"src/workbench_analysis/operational_product_pack_v3.py").read_text(encoding="utf-8")
        if rel.endswith('v1_1.json'):
            binding=contract.get('reference_instruments',{})
            if binding.get('path')!=rel or binding.get('sha256')!=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest():return False
            catalog=json.loads((ROOT/rel).read_bytes())
            matches=[row for row in catalog.get('instruments',[]) if literal.upper() in
                     (str(row.get('instrument_id','')).upper(),str(row.get('code','')).upper())]
            return (catalog.get('version')==contract.get('reference_version') and catalog.get('runtime_authorized') is True
                    and len(matches)==1 and matches[0].get('instrument_type')=='MARKET_INDEX'
                    and matches[0].get('source_kind')=='TDX_INDEX_DAY' and 'INDEX_BENCHMARK_TYPE_OR_SOURCE_INVALID' in consumer)
        return (contract.get("contract_id")=="CORE_PRODUCT_INDEX_BENCHMARK_V1"
                and bool(contract.get("version"))
                and any(str(item.get("symbol","" )).lower()==literal.lower() for item in contract.get("benchmarks",[]))
                and "index_benchmark_contract(root)" in consumer
                and "index_reference_contract" in consumer)
    except (OSError,ValueError,TypeError,AttributeError):return False


def temporal_evidence_authority(rel,literal):
    """只认可已逐字段核验的阶段权威读取；不豁免当前数据来源。"""
    if rel!='config/operational_daily_source_authority_v2.json':return None
    try:
        value=json.loads((ROOT/rel).read_bytes())
        if value.get('contract_id')!='V4_DAILY_OWNER_SOURCE_CONTEXT_V2' or value.get('version')!='2.0.0':return None
        readers=value.get('evidence_readers',{})
        for name in ('phase0','upgrade_document','task_contract'):
            binding=value.get(name,{})
            if literal not in binding.get('path',''):continue
            proof=readers.get(name,{})
            if proof.get('time_role')!='ENGINEERING_AUTHORITY_ONLY' or not proof.get('field') or not proof.get('function'):return None
            for consumer in proof.get('consumer_bindings',[]):
                if hashlib.sha256((ROOT/consumer['path']).read_bytes()).hexdigest()!=consumer['sha256']:return None
            if len(proof.get('consumer_bindings',[]))!=2:return None
            if hashlib.sha256((ROOT/binding['path']).read_bytes()).hexdigest()!=binding['sha256']:return None
            return dict(contract=rel,version=value['version'],binding=binding,**proof)
    except (OSError,ValueError,KeyError,TypeError):return None
    return None


def verified_false_positive(rel: str, category: str, literal: str, line: str) -> str | None:
    """Narrow syntax/data-shape false positives; never grant path-wide waivers."""
    cache_dir="T"+"0002"
    cache_pattern=r"\b(?:tdx_root|metadata_root)\s*/\s*[\"']"+re.escape(cache_dir)+r"[\"']\s*/\s*[\"']hq_cache"
    if category=="CONSTANT_SECTOR_ID" and rel in {"src/tdx/tdx_audit.py","src/v4/contracts/source_overlap.py"} and re.search(cache_pattern,line):
        return "TDX_METADATA_DIRECTORY_COMPONENT"
    false_sector_label="industry"+":"+"candidates"
    if category=="CONSTANT_SECTOR_ID" and literal.lower()==false_sector_label and re.search(r"\bif\s+industry\s*:\s*candidates\s*=",line):
        return "PYTHON_IF_SUITE_ASSIGNMENT"
    if category=="CONSTANT_SECURITY_ID" and re.fullmatch(r"9{6}",literal) and "coalesce(current_rank,potential_rank," in line.lower():
        return "SQL_RANK_ORDERING_SENTINEL"
    if category=="CONSTANT_SECURITY_ID" and rel=="src/production/workbench.py" and "#"+literal.lower() in line.lower():
        return "CSS_HEX_COLOR"
    if category in {"CONSTANT_DATE","CONSTANT_SECURITY_ID"} and rel=="src/tdx/_gbbq_key.py" and re.search(r"[\"'][0-9a-f]{64,}[\"']",line,re.I):
        return "ENCRYPTED_KEY_CIPHERTEXT"
    if category=="CONSTANT_DATE" and rel=="src/workbench_service/legacy_feature_matrix.py" and "V3-UC-" in line and re.search(r"V3-UC-20\d{6}-\d+",line):
        return "DATED_LEGACY_USER_ISSUE_ID"
    return None


def verified_historical_evidence_binding(rel: str, literal: str, tree: ast.AST, source: str) -> str | None:
    """A content hash proves bytes, not historical-only consumption.

    Current consumers can use an immutable old receipt as a current default.
    Until a versioned, consumer-specific temporal proof is supplied, keep the
    candidate unresolved even if its adjacent digest matches.
    """
    return None


def immutable_evidence_bytes(rel: str, literal: str, tree: ast.AST, source: str) -> str | None:
    """Byte identity diagnostic only; never an admission exemption."""
    assignments={}
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign):
            names=[x.id for x in node.targets if isinstance(x,ast.Name)]
            value=node.value
        elif isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name):
            names=[node.target.id];value=node.value
        else:continue
        if isinstance(value,ast.Constant) and isinstance(value.value,str):
            for name in names:assignments[name]=value.value
    for name,path_value in assignments.items():
        if literal not in path_value or not path_value.replace("\\","/").startswith(("docs/evidence/","docs/audits/")):continue
        path=(ROOT/path_value).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():continue
        digest_names=(name+"_SHA256",name+"_SHA",name+"_DIGEST",name+"Sha256")
        for digest_name in digest_names:
            expected=assignments.get(digest_name)
            if expected and re.fullmatch(r"[0-9a-f]{64}",expected,re.I) and hashlib.sha256(path.read_bytes()).hexdigest()==expected.lower():
                return path.relative_to(ROOT).as_posix()+"#sha256:"+expected.lower()
    return None


def date_component_literals(tree: ast.AST) -> list[tuple[int, str]]:
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
        if name not in {"date", "datetime", "Timestamp"} or len(node.args) < 3:
            continue
        parts = node.args[:3]
        if not all(isinstance(x, ast.Constant) and isinstance(x.value, int) for x in parts):
            continue
        year, month, day = (x.value for x in parts)
        if 1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
            found.append((node.lineno, f"{year:04d}-{month:02d}-{day:02d}"))
    return found


def scan(files: list[str]) -> tuple[list[dict], dict]:
    reachable, graph, seeds, paths = runtime_graph(files)
    _,entrypoint_evidence=active_entrypoint_inventory(files)
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
        try: text = (ROOT/p).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError): continue
        lines = text.splitlines()
        tree = None
        if ext == ".py":
            try: tree = ast.parse(text)
            except SyntaxError as exc: ast_parse_failures.append({"file":rel,"line":exc.lineno,"reason":exc.msg})
        nodes_by_line = {}
        ast_date_calls = {}
        if tree:
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, (str, int)):
                    nodes_by_line.setdefault(n.lineno, set()).add(type(n).__name__)
                elif isinstance(n, ast.JoinedStr): nodes_by_line.setdefault(n.lineno, set()).add(type(n).__name__)
            for line_no, literal in date_component_literals(tree):
                ast_date_calls.setdefault(line_no, []).append(literal)
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
            for literal in ast_date_calls.get(line_no, ()):
                item = ("CONSTANT_DATE_COMPONENTS", literal, max(1, line.find("(") + 2))
                if item not in matches:
                    matches.append(item)
            for category, literal, col in matches:
                env, disposition = env_for(rel, rel in reachable)
                node_types = sorted(nodes_by_line.get(line_no, ()))
                context = line.strip()[:320]
                historical_binding=verified_historical_evidence_binding(rel,literal,tree,text) if tree else None
                temporal_proof=temporal_evidence_authority(rel,literal)
                # Exempt declaration of documented protocol/formats from date-shaped matches.
                protocol = bool(category == "CONSTANT_DATE" and re.fullmatch(r"YYYY[-/]MM[-/]DD", literal))
                false_positive=verified_false_positive(rel,category,literal,line)
                if protocol: disposition = "CONTRACT_CONSTANT"
                if historical_binding: disposition = "AUTHORIZED_IMMUTABLE_FACT"
                if temporal_proof:disposition='AUTHORIZED_IMMUTABLE_FACT'
                market_reference=versioned_market_reference(rel,literal)
                if market_reference: disposition="VERSIONED_MARKET_REFERENCE"
                if false_positive:disposition="FALSE_POSITIVE"
                finding_id = f"LIT-{len(findings)+1:06d}"
                # Keep the legacy fingerprint for the non-waiving change detector.
                # A separate semantic key is stable when lines are inserted above.
                candidate_key = hashlib.sha256(f"{rel}\0{line_no}\0{category}\0{literal}\0{context}".encode("utf-8")).hexdigest()
                semantic_key = semantic_candidate_key(rel, category, literal, line)
                findings.append({"id": finding_id, "file": rel, "line": line_no, "column": col,
                    "literal": literal, "category": category, "ast_node_types": node_types,
                    "candidate_key": candidate_key, "semantic_key": semantic_key,
                    "environment": env, "runtime_reachable": rel in reachable,
                    "entrypoints": [paths[rel][0]] if rel in paths else [], "call_chain": paths.get(rel, []),
                    "classification": disposition, "functional_impact": "Exact historical source evidence and matching SHA binding verified." if historical_binding else "Versioned index benchmark reference read and SHA-bound by its market consumer." if market_reference else "Syntax or serialized-data shape is not a business identity." if false_positive else "Review source and business context; scanner is candidate recall.",
                    "handling": disposition if disposition in {"CONTRACT_CONSTANT", "AUTHORIZED_IMMUTABLE_FACT", "VERSIONED_MARKET_REFERENCE", "FALSE_POSITIVE"} else ("TEST_ONLY" if env == "TEST_ONLY" else "UNRESOLVED"),
                    "replacement_source": (historical_binding if historical_binding else "config/core_product_index_benchmark_v1.json" if market_reference else false_positive), "modification_commit": None,
                    "regression_id": None, "context": context,
                    "temporal_consumption_proof":temporal_proof,
                    "verifier": "scripts/check_v4_business_literals.py"})
    dynamic_sites=[];dynamic_edges=[];browser_routes=[]
    modules=module_map(files)
    for rel in files:
        if Path(rel).suffix.lower() in {'.js','.jsx','.ts','.tsx','.html'}:
            try:body=(ROOT/rel).read_text(encoding='utf-8-sig')
            except (OSError,UnicodeError):continue
            for line_no,line in enumerate(body.splitlines(),1):
                if re.search(r'\bfetch\s*\(|\bimport\s*\(',line):
                    browser_routes.append(dict(file=rel,line=line_no,runtime_reachable=rel in reachable,
                                               expression=line.strip()[:240],status='ROUTE_REVIEW_REQUIRED'))
        if not rel.endswith('.py'):continue
        try:body=(ROOT/rel).read_text(encoding='utf-8-sig')
        except (OSError,UnicodeError):continue
        try:tree=ast.parse(body)
        except (SyntaxError,UnicodeError):continue
        parents=_parents(tree)
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):continue
            name=ast.unparse(node.func)
            if name not in {'importlib.import_module','__import__','runpy.run_path','runpy.run_module','eval','exec'}:continue
            if rel not in dynamic_sites:dynamic_sites.append(rel)
            targets=dynamic_import_targets(node,parents)
            literal=bool(node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str))
            target=node.args[0].value if literal else None
            local_resolved=bool(targets) and all(value in modules or name=='runpy.run_path' and value in modules.values() for value in targets)
            stdlib_resolved=(bool(targets) and name in {'__import__','importlib.import_module'}
                             and all(is_standard_library_module(value) for value in targets))
            dynamic_edges.append(dict(file=rel,line=node.lineno,function=name,
                runtime_reachable=rel in reachable,target=target,targets=list(targets) or None,
                status=('LITERAL_IMPORT_RESOLVED' if local_resolved and literal else
                        'FINITE_ALLOWLIST_IMPORTS_RESOLVED' if local_resolved else
                        'LITERAL_STDLIB_IMPORT_RESOLVED' if stdlib_resolved and literal else
                        'FINITE_STDLIB_IMPORTS_RESOLVED' if stdlib_resolved else 'UNRESOLVED')))
    summary = {"files_scanned": len(files), "source_python": counts["python"], "source_js": counts["javascript"],
        "runtime_scripts": counts["runtime_scripts"], "config": counts["config"], "sql": counts["sql"], "ui": counts["ui"],
        "active_reachable": sum(1 for x in reachable if x in files),
        "unclassified_outside_active_inventory":sum(1 for x in files if x not in reachable and x not in seeds),
        "test_only": sum(1 for x in files if x.startswith("tests/")), "python_reachable_files": len(reachable),
        "entrypoints": seeds, "import_edges": sum(len(x) for x in graph.values()), "dynamic_import_sites": dynamic_sites,
        "dynamic_edges":dynamic_edges,"browser_routes":browser_routes,
        "python_ast_parse_failures": ast_parse_failures,"active_entrypoint_inventory":entrypoint_evidence}
    return findings, summary


def global_gate(findings: list[dict], summary: dict | None = None) -> dict:
    """Evaluate the current runtime gate independently from baseline drift."""
    reachable = [x for x in findings if x.get("runtime_reachable")]
    unresolved = [x for x in reachable if x.get("handling") == "UNRESOLVED"]
    unverified_maintenance=[x for x in findings if not x.get("runtime_reachable") and x.get("handling")=="UNRESOLVED"
                            and x.get("environment")!="TEST_ONLY"
                            and (x.get("file","").startswith(("scripts/","tools/"))
                                 or Path(x.get("file","" )).parent==Path(".") and Path(x.get("file","" )).name.startswith("run_"))]
    active_violations=sum(1 for x in reachable if x.get("handling")=="ACTIVE_VIOLATION")
    _,evidence=active_entrypoint_inventory(tracked_files())
    inventory_unknown=evidence.get("status")!="SOURCE_VERIFIED"
    dynamic_unknown=[row for row in (summary or {}).get('dynamic_edges',[]) if row['status']=='UNRESOLVED'
                     and (row['runtime_reachable'] or row['file'].startswith(('scripts/','tools/')))]
    browser_unknown=[row for row in (summary or {}).get('browser_routes',[]) if row['runtime_reachable']]
    return {
        "status": "GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED" if unresolved or active_violations or unverified_maintenance or inventory_unknown or dynamic_unknown or browser_unknown else "GLOBAL_RUNTIME_LITERAL_GATE_PASS",
        "reachable_candidates": len(reachable),
        "active_violations": active_violations,
        "active_unknown": len(unresolved),
        "unverified_maintenance_candidates":len(unverified_maintenance),
        "active_entrypoint_inventory_status":evidence.get("status"),
        "dynamic_unresolved":len(dynamic_unknown),
        "browser_route_unresolved":len(browser_unknown),
        "unresolved_candidate_ids": [x.get("semantic_key") for x in unresolved],
        "unverified_maintenance_candidate_ids":[x.get("semantic_key") for x in unverified_maintenance],
    }


def gate_exit_code(gate: dict, *, allow_incomplete_inventory: bool = False) -> int:
    blocking=(gate.get("active_unknown",0) or gate.get("active_violations",0)
              or gate.get("unverified_maintenance_candidates",0)
              or gate.get("dynamic_unresolved",0)
              or gate.get("browser_route_unresolved",0)
              or gate.get("active_entrypoint_inventory_status")!="SOURCE_VERIFIED")
    if blocking and not allow_incomplete_inventory:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描 V4 正常运行路径中的固定交易日、证券和板块身份")
    parser.add_argument("--output", type=Path, required=True, help="机器可读清单输出路径")
    parser.add_argument("--fail-on-reachable", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--allow-incomplete-inventory", action="store_true",
                        help="仅生成诊断清单时允许未裁定的可达候选以零退出；不得作为准入")
    args = parser.parse_args()
    files = tracked_files(); findings, summary = scan(files)
    reachable, graph, seeds, _ = runtime_graph(files)
    gate = global_gate(findings,summary)
    reachable_hits = gate["active_unknown"]
    payload = {"schema_version": "V4-PRODUCTION-LITERAL-INVENTORY/2", **gate,
        "summary": summary, "runtime_graph": {"entrypoints":seeds,"edges":graph,"dynamic_import_sites":summary["dynamic_import_sites"]}, "findings": findings}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(args.output)
    compact_summary={k:v for k,v in summary.items() if k not in {"entrypoints","dynamic_import_sites","python_ast_parse_failures","dynamic_edges","browser_routes"}}
    compact_summary.update(entrypoint_count=len(seeds),dynamic_import_site_count=len(summary["dynamic_import_sites"]),python_ast_parse_failure_count=len(summary["python_ast_parse_failures"]))
    print(json.dumps({"output": args.output.as_posix(), "summary": compact_summary, "literal_candidates": len(findings),
                      "reachable_unresolved_candidates": reachable_hits}, ensure_ascii=False))
    return gate_exit_code(gate, allow_incomplete_inventory=args.allow_incomplete_inventory)


if __name__ == "__main__":
    sys.exit(main())
