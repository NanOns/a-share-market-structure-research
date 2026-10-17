"""V4_NONCONFIG_EXTERNAL_FILE_REFERENCE_AUDIT_R1: read-only Git-tracked file reference inventory."""
from __future__ import annotations
import argparse, ast, hashlib, json, os, re, subprocess, sys
from pathlib import Path, PureWindowsPath
from typing import Any

CONTRACT_ID = "V4_NONCONFIG_EXTERNAL_FILE_REFERENCE_AUDIT_R2"
CONTRACT_VERSION = "2.0.0"
NONCONFIG_EXTS = {".py", ".sh", ".ps1", ".bat", ".cmd", ".sql", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".css", ".csv", ".jsonl", ".ndjson", ".parquet", ".zip", ".gz", ".bin", ".dat", ".db", ".sqlite", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".dll", ".exe", ".so", ".dylib", ".wasm"}
CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
PATH_KEYS = {"path", "filepath", "file_path", "file", "archive_path", "artifact_path", "source_path", "script_path", "sql_path", "asset_path", "uri", "locator", "source_locator", "record_locator"}
IO_CALLS = {"open", "os.open", "Path.open", "Path.read_bytes", "Path.read_text", "Path.write_bytes", "Path.write_text", "read_bytes", "read_text", "write_bytes", "write_text", "read_csv", "read_parquet", "read_json", "read_sql", "json.load", "json.loads", "csv.reader", "gzip.open", "zipfile.ZipFile", "ZipFile", "glob.glob", "Path.glob", "Path.rglob", "runpy.run_path", "importlib.util.spec_from_file_location", "subprocess.run", "subprocess.Popen", "subprocess.check_call", "subprocess.check_output", "os.system"}
LITERAL_PATH_RE = re.compile(r"(?<![\w.])(?:[A-Za-z]:[\\/][^\s\"'<>|,]+|(?:[\\/]|\.\.?[\\/])?[\w@+-]+(?:[\\/][\w@+-]+)*\.(?:jsonl?\.gz|jsonl|ndjson|parquet|sqlite|json|ya?ml|toml|py|sh|ps1|bat|cmd|sql|js|mjs|ts|tsx|html|css|csv|zip|gz|bin|dat|png|jpg|jpeg|gif|ico|pdf|dll|exe|wasm))(?![\w])", re.I)


def _sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def _atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_bytes(raw); os.replace(tmp, path)
def _git(root: Path, *args: str) -> bytes: return subprocess.check_output(["git", "-C", str(root), *args])
def _tracked(root: Path) -> list[str]:
    return [x.decode("utf-8", "surrogateescape").replace("\\", "/") for x in _git(root, "ls-files", "-z").split(b"\0") if x]
def _reachable(path: str) -> bool:
    p=path.lower()
    if p.startswith(("tests/upgrade_v1/", "tests/upgrade_v2/", "tests/upgrade_v3/")) or "m14" in p: return False
    return (p.startswith(("src/workbench_db/", "src/workbench_analysis/", "src/workbench_service/", "src/sector/", "scripts/", "config/", "data/v4/", "sql/", ".github/workflows/"))
            or p.startswith(("tests/", "frontend/", "web/", "ui/", "client/")))
def _entry(path: str) -> str:
    p=path.lower()
    if p.startswith(".github/workflows/"): return ".github/workflows"
    if p.startswith("tests/"): return "tests"
    if p.startswith("scripts/"): return "scripts/"+Path(path).name
    if p.startswith("src/workbench_service/"): return "v4_service"
    if p.startswith("src/workbench_db/"): return "v4_database"
    if p.startswith("src/workbench_analysis/"): return "v4_analysis"
    if p.startswith(("frontend/", "web/", "ui/", "client/")): return "v4_frontend"
    if p.startswith("data/v4/"): return "accepted_head_or_v4_data"
    return "v4_repo_scan"

def _kind(path: str) -> str:
    ext=Path(path).suffix.lower()
    return "CONFIG_ONLY" if ext in CONFIG_EXTS else ("NONCONFIG_FILE" if ext in NONCONFIG_EXTS else "OTHER_FILE")
def _risk(target: str|None, root: Path, caller: str, expected_sha: str|None, expected_bytes: int|None) -> tuple[str,str,str|None,int|None,str|None,bool|None]:
    if not target: return "DYNAMIC_UNRESOLVED","P2",None,None,None,None
    # A string longer than the OS path-component limit cannot be a file path.
    # Keep the edge in the inventory, but do not pass document/code payloads to stat().
    path_parts=target.replace("\\", "/").split("/")
    if len(target.encode("utf-8", "surrogatepass")) > 4096 or any(len(part.encode("utf-8", "surrogatepass")) > 255 for part in path_parts):
        return "NON_PATH_LITERAL","INFO",None,None,None,None
    historical_tool=caller.startswith("scripts/") and any(k in Path(caller).name.lower() for k in ("r4_next", "next_stage_delivery", "v41011", "r43_r2_cloud_archive"))
    if target.startswith(("/api/", "api/")):
        return "API_ROUTE_NOT_LOCAL_FILE","INFO",None,None,None,None
    static_root=root/"src/workbench_service/static"
    if caller.startswith("src/workbench_service/static/") and target.startswith("/"):
        if target.startswith("/v2/"):
            resolved=(static_root/target.lstrip("/")).resolve(strict=False)
        elif target=="/v4/daily-update.js":
            resolved=static_root/"daily-update/app.js"
        elif target.startswith("/v4/assets/"):
            name=Path(target).name
            resolved=static_root/"research"/name
        elif target=="/v4/workbench.js":
            resolved=static_root/"v4-workbench.js"
        elif target=="/v4/shadow.js":
            resolved=static_root/"shadow-v4.js"
        else:
            resolved=(static_root/Path(caller).parent.relative_to("src/workbench_service/static")/target.lstrip("/")).resolve(strict=False)
        if not resolved.is_relative_to(static_root.resolve()): return "UNTRUSTED_PATH_TRAVERSAL","P1",str(resolved),None,None,False
        if not resolved.is_file(): return "MISSING_FILE","P1" if caller.startswith("src/") else "P2",str(resolved),None,None,False
        raw=resolved.read_bytes()
        if expected_sha and (_sha(raw)!=expected_sha or expected_bytes is not None and len(raw)!=expected_bytes): return "ACTUAL_MISMATCH","P1",str(resolved),_sha(raw),len(raw),True
        return "KNOWN_VALID_CURRENT_REFERENCE","INFO",str(resolved),_sha(raw),len(raw),True
    # Windows drive-rooted literals remain absolute/stale when the audit runs
    # on Linux CI. pathlib.Path on POSIX treats ``E:/...`` as a relative name.
    if PureWindowsPath(target).is_absolute() and os.name != "nt":
        priority="P2" if historical_tool or caller in {"scripts/v4_closeout_v41011_sql_fixture.py","scripts/workbench_tray.ps1"} else "P1" if caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/",".github/","data/v4/V4_")) else "P2"
        return "ABSOLUTE_STALE_ROOT",priority,target,None,None,False
    candidate=Path(target)
    candidate=Path(target)
    if not candidate.is_absolute() and "/" not in target and "\\" not in target and candidate.suffix.lower() in {".exe", ".com", ".bat", ".cmd"}:
        return "EXTERNAL_TOOL_LOOKUP","P2",None,None,None,None
    if candidate.is_absolute():
        resolved=candidate.resolve(strict=False)
        if not resolved.is_relative_to(root): return "ABSOLUTE_STALE_ROOT","P2" if historical_tool or caller in {"scripts/v4_closeout_v41011_sql_fixture.py","scripts/workbench_tray.ps1"} else "P1" if caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/",".github/","data/v4/V4_")) else "P2",str(resolved),None,None,False
    else:
        ui_caller=caller.startswith(("frontend/","web/","ui/","client/")) or caller.startswith("src/workbench_service/static/") and Path(caller).suffix.lower() in {".html", ".css"}
        if caller.startswith(("src/workbench_service/static/r43-compat/","src/workbench_service/static/r43-control-v2/")) and target.startswith("./"):
            base=static_root/"research"
        else:
            base=(root/Path(caller).parent) if target.startswith(("./","../")) or ui_caller else root
        resolved=(base/candidate).resolve(strict=False)
        if not resolved.is_relative_to(root): return "UNTRUSTED_PATH_TRAVERSAL","P1" if caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/",".github/")) else "P2",str(resolved),None,None,False
    exists=resolved.is_file()
    if not exists:
        active_caller=caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/",".github/","data/v4/V4_"))
        return "MISSING_FILE","P1" if active_caller else "P2",str(resolved),None,None,False
    try: raw=resolved.read_bytes()
    except OSError: return "UNVERIFIABLE_BYTES","P1" if caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/",".github/","data/v4/V4_")) else "P2",str(resolved),None,None,True
    if raw.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        return "GIT_LFS_POINTER_ONLY","P1" if caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/",".github/","data/v4/V4_")) else "P2",str(resolved),_sha(raw),len(raw),True
    if expected_sha and (_sha(raw)!=expected_sha or expected_bytes is not None and len(raw)!=expected_bytes):
        priority="P0" if caller in {"data/v4/V4_STAGE_ACCEPTED_HEAD.json","data/v4/V4_DATA_ACCEPTED_HEAD.json"} else "P1" if caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/",".github/","data/v4/V4_")) else "P2"
        return "ACTUAL_MISMATCH",priority,str(resolved),_sha(raw),len(raw),True
    if expected_sha and _sha(raw)==expected_sha and (expected_bytes is None or len(raw)==expected_bytes):
        return "KNOWN_VALID_CURRENT_REFERENCE","INFO",str(resolved),_sha(raw),len(raw),True
    if caller.startswith(("docs/", "reports/")):
        return "DOC_ONLY","INFO",str(resolved),_sha(raw),len(raw),True
    if caller.startswith("tests/"):
        return "TEST_ONLY","INFO",str(resolved),_sha(raw),len(raw),True
    if Path(target).suffix.lower() in CONFIG_EXTS:
        if target.replace("\\","/").lower().startswith(("data/v4/","reports/","docs/")):
            return "BUSINESS_ARTIFACT_REFERENCE_REQUIRES_CLASSIFICATION","P2",str(resolved),_sha(raw),len(raw),True
        return "CONFIG_SCOPE_REVIEW_REQUIRED","P2",str(resolved),_sha(raw),len(raw),True
    return "KNOWN_VALID_CURRENT_REFERENCE","INFO",str(resolved),_sha(raw),len(raw),True

def _call_name(node: ast.AST) -> str:
    parts=[]; cur=node
    while isinstance(cur,(ast.Attribute,ast.Name)):
        parts.append(cur.attr if isinstance(cur,ast.Attribute) else cur.id);cur=cur.value if isinstance(cur,ast.Attribute) else None
    return ".".join(reversed(parts))
def _const_string(node: ast.AST|None) -> str|None:
    return node.value if isinstance(node,ast.Constant) and isinstance(node.value,str) else None

def _eval_path_expr(node: ast.AST|None, assignments: dict[str, ast.AST], seen: set[str]|None=None) -> tuple[str|None, list[str]]:
    """Resolve a conservative subset of Python path expressions without reading env values."""
    seen=set() if seen is None else seen
    if node is None: return None,["missing expression"]
    if isinstance(node,ast.Constant) and isinstance(node.value,(str,int,float)):
        return str(node.value),[]
    if isinstance(node,ast.Name):
        if node.id in seen: return None,[f"recursive binding {node.id}"]
        value=assignments.get(node.id)
        if value is None: return None,[f"unbound name {node.id}"]
        return _eval_path_expr(value,assignments,seen|{node.id})
    if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Div)):
        left,lb=_eval_path_expr(node.left,assignments,seen);right,rb=_eval_path_expr(node.right,assignments,seen)
        if left is None or right is None: return None,lb+rb
        return (str(PureWindowsPath(left)/right) if "\\" in left else str(Path(left)/right)) if isinstance(node.op,ast.Div) else left+right,[]
    if isinstance(node,ast.JoinedStr):
        chunks=[];blockers=[]
        for part in node.values:
            if isinstance(part,ast.Constant): chunks.append(str(part.value));continue
            value,why=_eval_path_expr(part.value,assignments,seen) if isinstance(part,ast.FormattedValue) else (None,["unsupported f-string part"])
            if value is None: blockers.extend(why)
            else: chunks.append(value)
        return ("".join(chunks),[]) if not blockers else (None,blockers)
    if isinstance(node,ast.Call):
        name=_call_name(node.func)
        if name in {"Path","PurePath","PurePosixPath","PureWindowsPath"} and node.args:
            return _eval_path_expr(node.args[0],assignments,seen)
        if name.endswith(".joinpath") or name=="joinpath":
            values=[];blockers=[]
            receiver=node.func.value if isinstance(node.func,ast.Attribute) else None
            if receiver is not None:
                v,b=_eval_path_expr(receiver,assignments,seen);values.append(v) if v is not None else None;blockers.extend(b)
            for arg in node.args:
                v,b=_eval_path_expr(arg,assignments,seen);values.append(v) if v is not None else None;blockers.extend(b)
            return (str(Path(values[0]).joinpath(*values[1:])),[]) if not blockers and values else (None,blockers)
        if name in {"os.getenv","getenv","os.environ.get","environ.get"} and node.args:
            key=_const_string(node.args[0])
            return None,[f"environment variable {key or ast.unparse(node.args[0])} value not read"]
        return None,[f"dynamic call {name or ast.unparse(node.func)}"]
    return None,[f"unresolved expression {ast.unparse(node)}"]

def _scope_assignments(statements: list[ast.stmt]) -> dict[str, ast.AST]:
    """Collect assignments in one lexical scope, excluding nested scopes."""
    result={}
    pending=list(statements)
    while pending:
        node=pending.pop()
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)): continue
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name): result[target.id]=node.value
        elif isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) and node.value is not None:
            result[node.target.id]=node.value
        pending.extend(ast.iter_child_nodes(node))
    return result

def _module_assignments(tree: ast.Module) -> dict[str, ast.AST]:
    return _scope_assignments(tree.body)

def _expr_text(node: ast.AST|None) -> str|None:
    try: return ast.unparse(node) if node is not None else None
    except Exception: return None

def _reachability_index(root: Path, tracked: list[str], authority_docs: set[str]) -> dict[str,dict[str,Any]]:
    """Conservative Python import/script graph rooted at V4 launch and CI entries."""
    source_ext={".py",".sh",".ps1",".bat",".cmd",".sql",".js",".mjs",".ts",".tsx",".jsx",".html",".css"}
    code=[p for p in tracked if Path(p).suffix.lower() in source_ext]
    code_set=set(code); module_to_path={}
    for rel in code:
        if not rel.endswith(".py"): continue
        stem=rel[:-3].replace("/",".")
        if stem.endswith(".__init__"): stem=stem[:-9]
        module_to_path[stem]=rel
        if stem.startswith("src."): module_to_path[stem[4:]]=rel
    graph={p:set() for p in code}; roots=set()
    roots.update(p for p in code if p in {"run_desktop.py","src/workbench_service/server.py","src/workbench_service/app.py","src/workbench_service/__main__.py","src/v4/app.py","src/v4/server.py"})
    for rel in tracked:
        if rel.startswith(".github/workflows/"):
            roots.add(rel)
            try: text=(root/rel).read_text(encoding="utf-8-sig",errors="replace")
            except OSError: continue
            for match in re.finditer(r"(?:python|py|bash|pwsh)?\s*(scripts/[A-Za-z0-9_./-]+\.(?:py|sh|ps1|sql))",text,re.I):
                if match.group(1) in code_set: roots.add(match.group(1))
        if rel in code_set and not rel.endswith(".py"): continue
        if rel not in code_set or not rel.endswith(".py"): continue
        try: tree=ast.parse((root/rel).read_text(encoding="utf-8-sig"),filename=rel)
        except (OSError,SyntaxError,UnicodeDecodeError): continue
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                module=node.module or ""
                if node.level and rel.startswith("src/"):
                    parts=rel[:-3].split("/")[:-1]; base=parts[:max(0,len(parts)-node.level+1)]; module=".".join(base+([module] if module else []))
                names=[module]+[module+"."+a.name for a in node.names if a.name!="*"]
            else: names=[]
            for name in names:
                path=module_to_path.get(name)
                if path: graph[rel].add(path)
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                value=node.value.replace("\\","/")
                match=re.search(r"(?:^|\b)(scripts/[A-Za-z0-9_./-]+\.py)(?:$|\b)",value)
                if match and match.group(1) in code_set: graph[rel].add(match.group(1))
    chains={}; queue=[]
    for entry in sorted(roots):
        if entry in code_set: chains[entry]=[entry];queue.append(entry)
    while queue:
        caller=queue.pop(0)
        for child in sorted(graph.get(caller,())):
            if child not in chains: chains[child]=chains[caller]+[child];queue.append(child)
    result={}
    for rel in tracked:
        low=rel.lower()
        if rel in chains:
            result[rel]={"class":"CONFIRMED_STATIC_CHAIN","chain":chains[rel]}
        elif rel in authority_docs:
            result[rel]={"class":"CONFIRMED_AUTHORITY_CLOSURE","chain":[rel]}
        elif low.startswith(("tests/upgrade_v1/","tests/upgrade_v2/","tests/upgrade_v3/")) or "m14" in low or low.startswith("archive/"):
            result[rel]={"class":"DETERMINED_RETIRED_OR_FIXTURE","chain":[]}
        elif _reachable(rel):
            result[rel]={"class":"POSSIBLE_CURRENT_SCOPE","chain":[]}
        else:
            result[rel]={"class":"OUTSIDE_V4_SCOPE","chain":[]}
    return result

def _walk_json(value: Any, pointer: str=""):
    if isinstance(value,dict):
        for k,v in value.items():
            ptr=pointer+"/"+str(k).replace("~","~0").replace("/","~1")
            if str(k).lower() in PATH_KEYS and isinstance(v,str):
                yield ptr,v,value
            yield from _walk_json(v,ptr)
    elif isinstance(value,list):
        for i,v in enumerate(value): yield from _walk_json(v,pointer+f"/{i}")

def _json_pointer_line(raw: bytes, pointer: str) -> int:
    """Best-effort physical line for a JSON pointer (the key is unique only locally)."""
    tokens=[x.replace("~1","/").replace("~0","~") for x in pointer.split("/") if x]
    if not tokens: return 1
    key=json.dumps(tokens[-1],ensure_ascii=False).encode("utf-8")
    offset=raw.find(key)
    return raw[:offset].count(b"\n")+1 if offset>=0 else 1

def _reachable_json_documents(root: Path, tracked: list[str]) -> tuple[set[str],int,int,bool]:
    """Bounded path-dependency closure from current V4 authority documents.

    Only current Head/authority JSON documents seed the walk. Their explicit
    path bindings may lead into reports/docs evidence; those documents are
    scanned only when they are tracked and reached through a recorded edge.
    The byte and document limits prevent large historical report trees from
    turning a targeted audit into an unbounded repository dump.
    """
    tracked_set=set(tracked); found=set(); pending=[]; total_bytes=0
    for rel in tracked:
        low=rel.lower()
        if Path(rel).suffix.lower()!=".json": continue
        authority_name=any(k in Path(low).name for k in ("accepted_head", "head_", "_head", "manifest", "registry", "receipt", "contract", "authority", "migration", "owner", "rps", "publication", "universe", "source_pit", "lineage", "binding"))
        if (low.startswith("data/v4/") and "head" in low
                or low.startswith("config/") and authority_name):
            pending.append(rel)
    while pending and len(found)<16384 and total_bytes<512_000_000:
        rel=pending.pop(0)
        if rel in found or rel not in tracked_set: continue
        path=root/rel
        try:
            size=path.stat().st_size
            if size>1_000_000 or total_bytes+size>512_000_000: continue
            raw=path.read_bytes()
        except OSError: continue
        found.add(rel);total_bytes+=len(raw);low=rel.lower();targets=[]
        if path.suffix.lower()==".json":
            try: obj=json.loads(raw.decode("utf-8-sig"))
            except (UnicodeDecodeError,json.JSONDecodeError): obj=None
            if obj is not None: targets.extend(target for _,target,_ in _walk_json(obj))
        elif path.suffix.lower() in {".md",".mdx",".html",".txt"}:
            text=raw.decode("utf-8-sig","replace")
            targets.extend(m.group(0).strip("<>()[]{}.,;'") for m in re.finditer(r"(?:reports|docs|data/v4|config)/[A-Za-z0-9_./@+-]+\.(?:jsonl?|jsonl\.gz|ya?ml|toml|py|sql|csv|parquet|zip|md|mdx|html|txt)",text,re.I))
            targets.extend(m.group(1) for m in re.finditer(r"\[[^\]]*\]\((?:\.\.?/)?([^\s)#]+)",text))
        for target in targets:
            if not target or re.match(r"^(?:https?:|/api/|\$|%|\{)",target,re.I): continue
            normalized=target.split("#",1)[0].split("?",1)[0].replace("\\","/")
            candidates=[normalized]
            if not normalized.startswith(("reports/","docs/","data/v4/","config/")):
                candidates.insert(0,(Path(rel).parent/normalized).as_posix())
            for candidate in candidates:
                try: resolved=(root/candidate).resolve(strict=False)
                except OSError: continue
                if resolved.is_relative_to(root) and candidate in tracked_set:
                    if candidate.lower().startswith(("reports/","docs/","data/v4/","config/")) and candidate not in found:
                        pending.append(candidate)
                    break
    return found,len(pending),total_bytes,bool(pending and (len(found)>=16384 or total_bytes>=512_000_000))

def scan_repository(root: Path, edges_spool: Path|None=None) -> dict[str,Any]:
    root=root.resolve(); tracked=_tracked(root); entries=[]; edge_no=0; identity_cache={}; excluded=[]
    reachable_json,closure_pending_count,closure_bytes,closure_truncated=_reachable_json_documents(root,tracked)
    reachability=_reachability_index(root,tracked,reachable_json)
    reachability_chains={}
    try:
        historical_registry=json.loads((root/"config/v4_historical_moving_head_registry_r17_v1.json").read_bytes())
        historical_rows={}
        for group in ("static_byte_archives","entries","source_archives"):
            for row in historical_registry.get(group,[]):
                original=row.get("original_namespace",{})
                if original.get("path") and original.get("sha256"):
                    historical_rows[(original["path"],original["sha256"])]=row
    except (OSError,UnicodeDecodeError,json.JSONDecodeError):
        historical_rows={}
    try:
        lfs_root=Path(_git(root,"rev-parse","--git-path","lfs/objects").decode().strip())
        if not lfs_root.is_absolute(): lfs_root=(root/lfs_root).resolve()
    except subprocess.CalledProcessError: lfs_root=root/".git/lfs/objects"
    edge_counts={"runtime_verified":0,"dynamic_unresolved":0,"historical":0,"hash_success":0,"lfs":0,"lfs_verified":0,"p0":0,"p1":0}
    spool_handle=edges_spool.open("w",encoding="utf-8",newline="\n") if edges_spool else None
    def emit(caller:str,line:int,symbol:str,entrypoint:str,mode:str,target:str|None,path_source:str,
             purpose:str,expected_sha:str|None=None,expected_bytes:int|None=None,historical:str="CURRENT",
             path_expression:str|None=None,unresolved_steps:list[str]|None=None):
        nonlocal edge_no
        edge_no+=1;kind=_kind(target or "")
        cache_key=(caller,target,expected_sha,expected_bytes)
        if cache_key not in identity_cache: identity_cache[cache_key]=_risk(target,root,caller,expected_sha,expected_bytes)
        risk,priority,resolved,actual_sha,actual_bytes,exists=identity_cache[cache_key]
        lfs_object_path=None;lfs_verified=False
        if risk=="GIT_LFS_POINTER_ONLY" and resolved:
            try:
                pointer=Path(resolved).read_text(encoding="ascii")
                match=re.search(r"(?m)^oid sha256:([0-9a-f]{64})$",pointer)
                size_match=re.search(r"(?m)^size (\d+)$",pointer)
                if match and size_match:
                    oid=match.group(1);content_size=int(size_match.group(1))
                    obj=lfs_root/oid[:2]/oid[2:4]/oid
                    if obj.is_file():
                        object_sha=_sha(obj.read_bytes())
                        lfs_verified=object_sha==oid and obj.stat().st_size==content_size
                        if lfs_verified:
                            lfs_object_path=str(obj);actual_sha=object_sha;actual_bytes=content_size
                            if expected_sha and (expected_sha!=object_sha or expected_bytes is not None and expected_bytes!=content_size):
                                risk="ACTUAL_MISMATCH";priority="P1" if caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/",".github/","data/v4/V4_")) else "P2"
                            else:risk="KNOWN_VALID_CURRENT_REFERENCE";priority="INFO"
            except (OSError,UnicodeDecodeError): pass
        if purpose in {"browser-generated download filename", "runtime output path"}:
            risk,priority,resolved,actual_sha,actual_bytes,exists="OUTPUT_PATH_DECLARATION","INFO",None,None,None,None
        elif purpose=="file read or executable invocation" and target and risk not in {"UNTRUSTED_PATH_TRAVERSAL","ACTUAL_MISMATCH","MISSING_FILE","GIT_LFS_POINTER_ONLY"} and not symbol.startswith(("subprocess.","runpy.","importlib.")) and caller.startswith(("src/","scripts/","frontend/","web/","ui/","client/")):
            target_norm=target.replace("\\","/").lower()
            config_env = Path(target_norm).name in {".env", ".env.local", ".env.production"} and "/config/" in f"/{target_norm.strip('/')}"
            if config_env:
                risk,priority="ENVIRONMENT_CONFIGURATION_READ","INFO"
            elif not target_norm.startswith("config/"):
                reach_class=reachability.get(caller,{}).get("class")
                risk,priority="BUSINESS_FILE_READ_REQUIRES_DB","P1" if reach_class=="CONFIRMED_STATIC_CHAIN" else "P2"
            elif risk not in {"ACTUAL_MISMATCH","MISSING_FILE","GIT_LFS_POINTER_ONLY"}:
                risk,priority="CONFIG_SCOPE_REVIEW_REQUIRED","P2"
        origin=None; identity=None; archive_path=None; archive_sha=None; archive_bytes=None; archive_ok=False
        row=historical_rows.get((target,expected_sha)) if historical=="HISTORICAL" and target and expected_sha else None
        if row:
            original=row["original_namespace"];archive=row.get("archive",{})
            try:
                archived=(root/archive["path"]).resolve(); archived_raw=archived.read_bytes()
                git_raw=subprocess.check_output(["git","-C",str(root),"show",row["source_commit"]+":"+target],stderr=subprocess.DEVNULL)
                representation=row.get("representation")
                origin_match=(archived_raw==git_raw if representation=="EXACT_ACCEPTED_GIT_BLOB_ARCHIVE_CURRENT_MAY_EVOLVE" else archived_raw.replace(b"\r\n",b"\n")==git_raw)
                archive_ok=(archived.is_relative_to(root) and _sha(archived_raw)==expected_sha and len(archived_raw)==original.get("bytes") and origin_match)
                if archive_ok:
                    origin=row.get("source_commit");archive_path=archive["path"];archive_sha=_sha(archived_raw);archive_bytes=len(archived_raw)
                    identity="HISTORICAL_ARCHIVE_VALID_CURRENT_CHANGED" if actual_sha!=expected_sha else "SAME_BYTES"
                    risk="HISTORICAL_ARCHIVE_VALID_CURRENT_CHANGED" if actual_sha!=expected_sha else "KNOWN_VALID_HISTORICAL_ARCHIVE"
                    priority="INFO"
            except (OSError,KeyError,subprocess.CalledProcessError): pass
        reach=reachability.get(caller,{})
        chain=reach.get("chain",[])
        chain_id=_sha("\n".join(chain).encode("utf-8")) if chain else None
        if chain_id: reachability_chains[chain_id]=chain
        edge={
          "reference_id":f"V4-NCFR-{edge_no:07d}","caller_path":caller,"line":line,"symbol":symbol,
          "entrypoint":entrypoint,"reachable":reach.get("class") in {"CONFIRMED_STATIC_CHAIN","CONFIRMED_AUTHORITY_CLOSURE","POSSIBLE_CURRENT_SCOPE"},
          "reachability_class":reach.get("class","OUTSIDE_V4_SCOPE"),"reachability_chain_id":chain_id,"static_or_dynamic":mode,
          "literal_or_resolved_target":target,"root/source_of_path":path_source,"file_type":kind,
          "path_expression":path_expression or (f"<expression unavailable at {caller}:{line}>" if mode=="DYNAMIC" else None),"dynamic_resolution_steps":unresolved_steps or (["runtime CLI/environment/user input or configured root not available to static scan"] if mode=="DYNAMIC" else []),
          "purpose":purpose,"historical_or_current":historical,"accepted_head/manifest_identity":caller+"#"+symbol if historical=="HISTORICAL" else None,
          "origin_commit":origin,"expected_sha256":expected_sha,"expected_bytes":expected_bytes,
          "actual_sha256":actual_sha,"actual_bytes":actual_bytes,"resolved_path":resolved,"exists":exists,
          "archive_path":archive_path,"archive_sha256":archive_sha,"archive_bytes":archive_bytes,"archive_hash_verified":archive_ok,
          "lfs_object_path":lfs_object_path,"lfs_object_hash_verified":lfs_verified,
          "T0":None,"publication_id":None,"namespace":None,"risk_type":risk,"priority":priority,
          "proof":{"scanner_contract":CONTRACT_ID,"path_exists":exists,"hash_verified":bool(expected_sha and actual_sha==expected_sha),"identity_classification":identity},
          "fix_commit":None,"regression_test":None,"unresolved_reason":"dynamic target unavailable at scan time" if risk=="DYNAMIC_UNRESOLVED" else None
        }
        edge_counts["runtime_verified"]+=int(edge["proof"].get("runtime_trace") is True)
        edge_counts["dynamic_unresolved"]+=int(risk=="DYNAMIC_UNRESOLVED")
        edge_counts["historical"]+=int(historical=="HISTORICAL")
        edge_counts["hash_success"]+=int(bool(edge["proof"].get("hash_verified")))
        edge_counts["lfs"]+=int(risk=="GIT_LFS_POINTER_ONLY")
        edge_counts["lfs_verified"]+=int(lfs_verified)
        edge_counts["p0"]+=int(priority=="P0");edge_counts["p1"]+=int(priority=="P1")
        if spool_handle: spool_handle.write(json.dumps(edge,ensure_ascii=False,separators=(",",":"))+"\n")
        else: entries.append(edge)
    module_coverage={}
    for file_index,rel in enumerate(tracked,1):
        if file_index % 10000 == 0: print(f"scanned tracked paths: {file_index}/{len(tracked)}; edges={edge_no}",file=sys.stderr)
        p=root/rel;ext=p.suffix.lower();module=rel.split("/",1)[0];module_coverage[module]=module_coverage.get(module,0)+1
        low=rel.lower()
        is_code_or_v4_data=(low.startswith(("src/", "scripts/", "config/", "data/v4/", ".github/workflows/", "sql/", "frontend/", "web/", "ui/", "client/"))
                            or (low.startswith(("reports/","docs/")) and rel in reachable_json))
        if not is_code_or_v4_data:
            excluded.append({"path":rel,"reason":"OUTSIDE_CURRENT_V4_EXECUTABLE_OR_AUTHORITY_PATHS; referenced bytes are independently checked from active code/config/Accepted Heads"})
            continue
        if low.startswith(("reports/","docs/")) and rel not in reachable_json:
            excluded.append({"path":rel,"reason":"REPORT_DOC_NOT_IN_BOUNDED_ACCEPTED_HEAD_OR_AUTHORITY_DEPENDENCY_CLOSURE"})
            continue
        if ext not in {".py", ".sh", ".ps1", ".bat", ".cmd", ".sql", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".jsonl", ".ndjson", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}:
            excluded.append({"path":rel,"reason":"NON_TEXT_PAYLOAD; bytes are independently hashed when a scanned manifest or code edge references this target"})
            continue
        if low.startswith("data/v4/") and "head" not in low and ext not in {".json", ".jsonl", ".ndjson"}:
            excluded.append({"path":rel,"reason":"V4_SOURCE_OR_BUSINESS_PAYLOAD; whole bytes are hashed when referenced by an Accepted Head, manifest, or executable path"})
            continue
        if (rel.startswith("data/v4/") and ext in {".json", ".jsonl", ".ndjson"}
                and rel not in reachable_json and not (rel.startswith("data/v4/") and "head" in low)):
            excluded.append({"path":rel,"reason":"JSON_RESULT_OR_DATA_NOT_REACHABLE_FROM_A_V4_ACCEPTED_HEAD_OR_CONFIG_AUTHORITY; path and byte identity are still captured when another active reference targets it"})
            continue
        if low.startswith("reports/") and ext in {".json", ".jsonl", ".ndjson"} and rel not in reachable_json and not any(x in low for x in ("manifest", "head", "receipt", "registry", "contract", "owner", "source", "migration", "rps", "publication", "universe", "profile", "sector", "focus", "forward", "settlement", "cohort", "authority", "audit", "inventory", "handoff", "gate", "binding", "lineage")):
            excluded.append({"path":rel,"reason":"REPORT_RESULT_OR_FIXTURE_DATASET; identity references are followed from scanned Accepted Heads and manifests"})
            continue
        try: size=p.stat().st_size
        except OSError: size=0
        if size>1_000_000 and not (low.startswith("data/v4/") and "head" in low):
            excluded.append({"path":rel,"reason":f"OVERSIZED_RESULT_OR_AUTHORITY_DOCUMENT_{size}_BYTES; full SHA and byte count are checked when directly referenced, content is not expanded into path rows"})
            continue
        if not p.is_file(): continue
        raw=p.read_bytes()
        # Manifest/Accepted Head identity edges; skip ordinary config pointer keys.
        if ext==".json" or rel.endswith((".json5",".jsonl")):
            try: obj=json.loads(raw.decode("utf-8-sig")) if ext==".json" else None
            except (UnicodeDecodeError,json.JSONDecodeError): obj=None
            if obj is not None:
                for ptr,target,record in _walk_json(obj):
                    suffix=Path(target.split("#",1)[0].split("?",1)[0]).suffix.lower()
                    if suffix not in NONCONFIG_EXTS and suffix not in CONFIG_EXTS and not re.search(r"[\\/]|^[A-Za-z]:",target): continue
                    sh=record.get("sha256") or record.get("sha_256")
                    size=record.get("bytes",record.get("byte_count"))
                    exp_size=size if isinstance(size,int) and not isinstance(size,bool) else None
                    hist="HISTORICAL" if rel.startswith(("data/v4/", "reports/", "docs/")) and ("accepted" in rel.lower() or "head" in rel.lower() or "archive" in rel.lower()) else "CURRENT"
                    dynamic=target.startswith(("$","%","${")) or "${" in target
                    emit(rel,_json_pointer_line(raw,ptr),ptr,_entry(rel),"DYNAMIC" if dynamic else "STATIC",None if dynamic else target,ptr,"manifest/config path binding",sh if isinstance(sh,str) else None,exp_size,hist,target if dynamic else None,["runtime JSON substitution not evaluated"] if dynamic else [])
        # Python AST: file I/O and executed external paths.
        if ext==".py":
            try: tree=ast.parse(raw.decode("utf-8-sig"),filename=rel)
            except (SyntaxError,UnicodeDecodeError): tree=None
            if tree:
                assignments=_module_assignments(tree)
                parents={child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
                function_assignments={id(scope):_scope_assignments(scope.body) for scope in ast.walk(tree) if isinstance(scope,(ast.FunctionDef,ast.AsyncFunctionDef))}
                for node in ast.walk(tree):
                    if not isinstance(node,ast.Call): continue
                    name=_call_name(node.func)
                    if name not in IO_CALLS: continue
                    arg=node.args[0] if node.args else next((kw.value for kw in node.keywords if kw.arg in {"file","path","args"}),None)
                    path_arg=arg
                    method_name=node.func.attr if isinstance(node.func,ast.Attribute) else ""
                    if isinstance(node.func,ast.Attribute) and method_name in {"open","read_bytes","read_text","write_bytes","write_text","glob","rglob"}:
                        path_arg=node.func.value
                    if name in {"subprocess.run","subprocess.Popen","subprocess.check_call","subprocess.check_output"} and isinstance(arg,(ast.List,ast.Tuple)) and arg.elts: path_arg=arg.elts[0]
                    scope=node
                    while scope in parents and not isinstance(scope,(ast.FunctionDef,ast.AsyncFunctionDef)):
                        scope=parents[scope]
                    path_bindings={**assignments,**function_assignments.get(id(scope),{})}
                    value,blockers=_eval_path_expr(path_arg,path_bindings)
                    if value and (Path(value).suffix.lower() in NONCONFIG_EXTS|CONFIG_EXTS or "/" in value or "\\" in value):
                        mode=_const_string(node.args[0]) if method_name=="open" and node.args else next((_const_string(arg) for arg in node.args[1:2]),None) if name=="open" else None
                        output=method_name in {"write_bytes","write_text"} or name in {"Path.write_bytes","Path.write_text","write_bytes","write_text"} or bool(mode and any(c in mode for c in "wax"))
                        emit(rel,node.lineno,name,_entry(rel),"STATIC",value,"source literal/command argument","runtime output path" if output else "file read or executable invocation",path_expression=_expr_text(path_arg))
                    elif not value:
                        emit(rel,node.lineno,name,_entry(rel),"DYNAMIC",None,"runtime argument/environment/database/glob","file operation target unresolved",path_expression=_expr_text(path_arg),unresolved_steps=blockers)
        # Other code/document formats: file-valued UI attributes and command/path literals.
        if ext in {".js",".mjs",".cjs",".ts",".tsx",".jsx",".html",".css",".sql",".sh",".ps1",".bat",".cmd",".yml",".yaml"}:
            text=raw.decode("utf-8-sig","replace")
            for line_no,line in enumerate(text.splitlines(),1):
                if len(line)>5000: continue
                if ext in {".js",".mjs",".cjs",".ts",".tsx",".jsx"} and not re.search(r"\b(?:fetch|import|require|src|href|download|screenshot|writeFile|createWriteStream)\b|\burl\s*\(",line,re.I): continue
                for match in LITERAL_PATH_RE.finditer(line):
                    target=match.group(0).rstrip(".,;:)")
                    if target.lower().endswith(".json") and re.search(r"\b"+re.escape(Path(target).stem)+r"\.json\s*\(",line,re.I): continue
                    output_name=bool(re.search(r"\bdownload\s*=|\.download\s*=|screenshot|writeFile|createWriteStream",line,re.I))
                    runner_output=rel.startswith(".github/workflows/") and ("--output" in line or "runner.temp" in line)
                    emit(rel,line_no,"path_literal",_entry(rel),"STATIC",target,"source/UI/SQL/shell literal","browser-generated download filename" if output_name else "runtime output path" if runner_output else "external file or asset path literal")
                if ext in {".js",".mjs",".ts",".tsx",".jsx",".html"} and re.search(r"\b(?:fetch|import|require)\s*\([^)]*(?:\+|\$\{|\bprocess\.env\b)",line):
                    emit(rel,line_no,"dynamic_asset_or_fetch",_entry(rel),"DYNAMIC",None,"runtime/UI loader","dynamic frontend asset or request path",path_expression=line.strip(),unresolved_steps=["runtime request construction depends on nonliteral expression"])
    if spool_handle: spool_handle.close()
    return {"contract_id":CONTRACT_ID,"contract_version":CONTRACT_VERSION,"scan_mode":"READ_ONLY_TRACKED_CODE_CONFIG_AUTHORITY_AND_BOUNDED_HEAD_DEPENDENCY_CLOSURE","repository_root":str(root),"git_head":_git(root,"rev-parse","HEAD").decode().strip(),"tracked_file_count":len(tracked),"source_file_count":sum(1 for p in tracked if Path(p).suffix.lower() in {".py",".sh",".ps1",".bat",".cmd",".sql",".js",".mjs",".ts",".tsx",".jsx",".html",".css"}),"module_coverage":module_coverage,"authority_dependency_closure_count":len(reachable_json),"authority_dependency_closure_files":sorted(reachable_json),"authority_dependency_closure_bytes":closure_bytes,"authority_dependency_closure_truncated":closure_truncated,"authority_dependency_closure_pending_count":closure_pending_count,"reachability_class_counts":dict(__import__('collections').Counter(x.get("class") for x in reachability.values())),"reachability_chains":reachability_chains,"reference_edges_total":edge_no,"runtime_verified_count":edge_counts["runtime_verified"],"dynamic_unresolved_count":edge_counts["dynamic_unresolved"],"historical_frozen_reference_count":edge_counts["historical"],"independent_hash_success_count":edge_counts["hash_success"],"lfs_pointer_only_count":edge_counts["lfs"],"lfs_object_verified_count":edge_counts["lfs_verified"],"p0_open":edge_counts["p0"],"p1_open":edge_counts["p1"],"excluded_with_reason_count":len(excluded),"excluded_files":excluded,"reference_edges":entries if not edges_spool else None}

def main() -> int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));ap.add_argument("--output");a=ap.parse_args();root=Path(a.root).resolve()
    spool=Path(a.output).with_suffix(".edges.jsonl") if a.output else None
    result=scan_repository(root,spool);raw=(json.dumps(result,ensure_ascii=False,indent=2)+"\n").encode()
    if a.output:
        payload=json.loads(raw);payload.pop("reference_edges",None)
        prefix=json.dumps(payload,ensure_ascii=False,indent=2)
        # Stream the complete edge array into an atomic final inventory.
        temp=Path(a.output).with_name("."+Path(a.output).name+".tmp")
        with temp.open("w",encoding="utf-8",newline="\n") as out:
            out.write(prefix[:-2]+',\n  "reference_edges": [\n')
            with spool.open(encoding="utf-8") as edges:
                first=True
                for edge_line in edges:
                    if not first: out.write(",\n")
                    out.write("    "+edge_line.rstrip());first=False
            out.write("\n  ]\n}\n")
        os.replace(temp,Path(a.output));spool.unlink()
    else:sys.stdout.buffer.write(raw)
    return 0
if __name__=="__main__":raise SystemExit(main())
