"""Inventory file access and absolute-path literals in current V4 business code."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PureWindowsPath

CONTRACT = "V4_BUSINESS_CODE_FILE_ACCESS_AUDIT_R1"
CODE_ROOTS = ("src/", "scripts/")
CODE_EXTS = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".css", ".sh", ".ps1", ".bat", ".cmd", ".sql"}
READ_CALLS = {
    "open", "io.open", "os.open", "Path.open", "Path.read_bytes", "Path.read_text",
    "read_bytes", "read_text", "read_csv", "read_parquet", "read_json",
    "gzip.open", "zipfile.ZipFile", "ZipFile",
    "glob.glob", "Path.glob", "Path.rglob", "Path.iterdir", "os.listdir", "os.scandir",
    "self.read", "authority.read", "self.authority.read",
}
EXEC_CALLS = {"runpy.run_path", "importlib.util.spec_from_file_location", "subprocess.run", "subprocess.Popen", "subprocess.check_call", "subprocess.check_output", "os.system"}
ENV_LOOKUP_CALLS = {"os.getenv", "os.environ.get"}
WRITE_CALLS = {"Path.write_bytes", "Path.write_text", "write_bytes", "write_text", "mkdir", "os.makedirs", "shutil.copy", "shutil.copy2", "os.replace", "os.rename"}
WRITE_WRAPPERS = {"atomic", "_atomic_write", "atomic_write"}
ABSOLUTE = re.compile(r"(?<![\w])/(?:[^\s\"'<>|,;)]*/)*[^\s\"'<>|,;)]*")


def filesystem_absolute(value: str | None) -> bool:
    if not value or value.startswith(("http://", "https://", "ftp://", "//")):
        return False
    if PureWindowsPath(value).drive and PureWindowsPath(value).root:
        return True
    if value.startswith("\\\\") and len([part for part in value.split("\\") if part]) >= 2:
        return True
    if not value.startswith("/"):
        return False
    # Leading-slash URL/API routes are not filesystem paths.
    if value.startswith(("/api/", "/v4/", "/assets/", "/static/", "/research/", "/health", "/metrics")):
        return False
    return value.startswith(("/mnt/", "/tmp/", "/home/", "/Users/", "/var/", "/opt/", "/etc/", "/srv/", "/workspace/", "/root/", "/app/", "/data/", "/usr/"))


def is_codex_temp_path(value: str | None) -> bool:
    path = PureWindowsPath(value or "")
    return bool(path.drive) and ord(path.drive[0].upper()) == 71 and "codex_tmp" in {part.lower() for part in path.parts}


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def tracked(root: Path) -> list[str]:
    return [p.decode("utf-8", "surrogateescape").replace("\\", "/") for p in git(root, "ls-files", "-z").split(b"\0") if p]


def active_code_paths(root: Path, all_paths: list[str]) -> tuple[list[str], list[str]]:
    """Include src, runtime launchers, and scripts referenced by those sources."""
    current_prefixes = ("src/workbench_", "src/v4/", "src/focus_tracker/", "src/common/", "src/adjustment/", "src/market_calendar/")
    src = {p for p in all_paths if p.startswith(current_prefixes) and Path(p).suffix.lower() in CODE_EXTS}
    launchers = {p for p in all_paths if p in {"run_desktop.py", "run_server.py", "run_v4.py"}}
    active_scripts: set[str] = set()
    queue: list[str] = []
    refs = re.compile(r"scripts/[A-Za-z0-9_./-]+\.py")
    for path in sorted(src | launchers):
        try:
            queue.extend(refs.findall((root / path).read_text(encoding="utf-8-sig")))
        except (OSError, UnicodeDecodeError):
            pass
    # Workflow-owned scripts are also active CI entrypoints.
    for path in all_paths:
        if path.startswith(".github/workflows/"):
            try:
                queue.extend(refs.findall((root / path).read_text(encoding="utf-8-sig")))
            except (OSError, UnicodeDecodeError):
                pass
    while queue:
        script = queue.pop()
        if script in active_scripts or script not in all_paths:
            continue
        if Path(script).name.startswith(("audit_v4_", "validate_v4_", "review_v4_")):
            continue
        active_scripts.add(script)
        try:
            queue.extend(refs.findall((root / script).read_text(encoding="utf-8-sig")))
        except (OSError, UnicodeDecodeError):
            pass
    return sorted(src | launchers | active_scripts), sorted(set(all_paths) - src - launchers - active_scripts)


def call_name(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, (ast.Attribute, ast.Name)):
        parts.append(node.attr if isinstance(node, ast.Attribute) else node.id)
        node = node.value if isinstance(node, ast.Attribute) else None
    return ".".join(reversed(parts))


def expr(node: ast.AST | None, source: str) -> str:
    if node is None:
        return "<no-path-argument>"
    return ast.get_source_segment(source, node) or ast.dump(node, include_attributes=False)


def containing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str | None:
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return parent.name
        parent = parents.get(parent)
    return None


def classify(caller: str, name: str, argument: str, literal: str | None, operation: str) -> tuple[str, str]:
    low = (argument + " " + (literal or "")).lower().replace("\\", "/")
    win_path = PureWindowsPath(literal or "")
    if caller.startswith("src/workbench_desktop/qa"):
        return "QA_TEST_ARTIFACT", "Isolated QA/test-only artifact; it does not represent persisted business state."
    if name in {"authority.read", "self.authority.read", "self.read"} and ("authority" in caller or "owner" in caller or re.search(r"\b(?:binding|ref|owner)\b", argument)) or re.search(r"\b(?:checked|exact)\s*\(", argument):
        return ("BUSINESS_OWNER_FILE_WRITE_REQUIRES_DB" if operation == "WRITE" else "BUSINESS_OWNER_FILE_READ_REQUIRES_DB",
                "Owner/exact binding identifies a business artifact stored in files; business state must use the database, not file-read authorization.")
    if "/config/" in low or low.startswith("config/") or "config/" in low:
        return "CONFIG_CLASS_INPUT_REVIEW", "Potential DB/environment/invariant configuration; allow only when its configuration role is documented and it contains no business state."
    if "environ" in low or "getenv" in low:
        return "ENVIRONMENT_INPUT", "Environment-supplied configuration; validate name, scope, and fail-closed behavior."
    if "runtime/desktop/" in low or "instance.json" in low or "session_end.json" in low:
        return "NONBUSINESS_PROCESS_STATE_REVIEW", "Desktop process/lease metadata; verify it contains no business state and remains local operational state."
    if is_codex_temp_path(literal):
        return "TEMPORARY_PATH_CONFIGURATION", "Temporary engineering/runtime path on the user-approved G: temporary root; ensure it is not a business data store."
    if operation == "READ" and any(token in (low + " " + caller.lower()) for token in ("tdx", "vipdoc", "hq_cache")):
        return "EXTERNAL_BUSINESS_DATA_FILE_READ_REQUIRES_DB", "External/local market-data file is business input; ingest/store/query through the database under the approved source contract."
    if "runtime/" in low or "reports/" in low or "data/" in low:
        return ("BUSINESS_FILE_WRITE_REQUIRES_DB" if operation == "WRITE" else "BUSINESS_FILE_READ_REQUIRES_DB",
                "Business artifact is read or written through workspace files; migrate business state to database. Exempt only nonbusiness OS/process state with evidence.")
    if filesystem_absolute(literal):
        return ("ABSOLUTE_PATH_WRITE_REVIEW" if operation == "WRITE" else "ABSOLUTE_PATH_READ_REVIEW",
                "Absolute filesystem path in business code; only DB/environment/invariant configuration may justify it; remove otherwise.")
    if literal is None:
        return "DYNAMIC_PATH_READ", "Path is dynamic; trace caller inputs and ensure it is constrained by configuration or Owner."
    if caller.startswith("scripts/"):
        return "SCRIPT_FILE_ACCESS", "Script access; verify the script is an approved entrypoint and path is explicit."
    return "RELATIVE_FILE_ACCESS", "Relative file access; verify it is required and bounded to the workspace or an Owner."


def scan(root: Path) -> dict:
    root = root.resolve()
    all_paths = tracked(root)
    paths, excluded_paths = active_code_paths(root, all_paths)
    rows: list[dict] = []
    scanned_files: list[dict[str, str]] = []
    for relative in paths:
        raw = (root / relative).read_bytes()
        scanned_files.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
        try:
            source = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            source = raw.decode("utf-8", "replace")
        if Path(relative).suffix.lower() == ".py":
            try:
                tree = ast.parse(source, filename=relative)
            except SyntaxError as error:
                rows.append({"kind": "PARSE_ERROR", "file": relative, "line": error.lineno, "detail": str(error)})
                continue
            parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
            constants: dict[str, str] = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        for target in targets:
                            if isinstance(target, ast.Name):
                                constants[target.id] = value.value
            seen_absolute: set[tuple[int, str]] = set()
            for node in ast.walk(tree):
                if (isinstance(node, ast.Subscript) and call_name(node.value) == "os.environ"
                        and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
                    key = node.slice.value
                    rows.append({"kind": "ENVIRONMENT_CONFIGURATION_LOOKUP", "file": relative, "line": node.lineno,
                                 "environment_key": key,
                                 "category": "DATABASE_ENV_CONFIGURATION" if any(token in key.upper() for token in ("DSN", "DATABASE", "PGHOST", "PGPORT", "DB_")) else "OTHER_ENVIRONMENT_CONFIGURATION",
                                 "priority": "INFO", "source_sha256": hashlib.sha256(raw).hexdigest(),
                                 "rationale": "Environment lookup is configuration access, not a business-file read; never record the environment value."})
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if node.value.startswith("/") and filesystem_absolute(node.value):
                        seen_absolute.add((node.lineno, node.value))
                    if PureWindowsPath(node.value).is_absolute() and filesystem_absolute(node.value):
                        seen_absolute.add((node.lineno, node.value))
                    else:
                        for match in ABSOLUTE.finditer(node.value):
                            literal = match.group(0).rstrip(".,;:")
                            if len(literal) > 3 and filesystem_absolute(literal):
                                seen_absolute.add((node.lineno, literal))
                if not isinstance(node, ast.Call):
                    continue
                name = call_name(node.func)
                if name in ENV_LOOKUP_CALLS and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    key = node.args[0].value
                    rows.append({"kind": "ENVIRONMENT_CONFIGURATION_LOOKUP", "file": relative, "line": node.lineno,
                                 "environment_key": key,
                                 "category": "DATABASE_ENV_CONFIGURATION" if any(token in key.upper() for token in ("DSN", "DATABASE", "PGHOST", "PGPORT", "DB_")) else "OTHER_ENVIRONMENT_CONFIGURATION",
                                 "priority": "INFO", "source_sha256": hashlib.sha256(raw).hexdigest(),
                                 "rationale": "Environment lookup is configuration access, not a business-file read; never record the environment value."})
                short_name = name.rsplit(".", 1)[-1]
                access_name = name if name in READ_CALLS | WRITE_CALLS | EXEC_CALLS else short_name
                if access_name not in READ_CALLS | WRITE_CALLS | WRITE_WRAPPERS | EXEC_CALLS:
                    continue
                method_access = short_name in {"open", "read_bytes", "read_text", "write_bytes", "write_text", "iterdir", "glob", "rglob"} and isinstance(node.func, ast.Attribute)
                path_arg = node.args[0] if node.args else next((kw.value for kw in node.keywords if kw.arg in {"file", "path", "database", "uri"}), None)
                if access_name in WRITE_WRAPPERS and len(node.args) >= 2 and (name.endswith(".atomic") or short_name == "atomic" and relative.startswith("src/workbench_analysis/dm01_")):
                    path_arg = node.args[1]
                if method_access:
                    receiver = node.func.value
                    if short_name in {"glob", "rglob"} and path_arg is not None:
                        path_arg = ast.BinOp(left=receiver, op=ast.Div(), right=path_arg)
                    else:
                        path_arg = receiver
                if access_name in EXEC_CALLS and path_arg is not None:
                    candidates = [child.value for child in ast.walk(path_arg) if isinstance(child, ast.Constant) and isinstance(child.value, str)]
                    script_candidate = next((v for v in candidates if re.search(r"(?:^|/)[^/]+\.(?:py|sql|sh|ps1|bat)$", v, re.I)), None)
                    if script_candidate is not None:
                        path_arg = ast.Constant(value=script_candidate)
                arg_text = expr(path_arg, source)
                literal = None
                if isinstance(path_arg, ast.Constant) and isinstance(path_arg.value, str):
                    literal = path_arg.value
                elif isinstance(path_arg, ast.Name):
                    literal = constants.get(path_arg.id)
                open_mode = node.args[0] if method_access and short_name == "open" and node.args else node.args[1] if short_name == "open" and len(node.args) > 1 else None
                operation = "EXECUTE" if access_name in EXEC_CALLS else "WRITE" if access_name in WRITE_CALLS | WRITE_WRAPPERS or (short_name == "open" and isinstance(open_mode, ast.Constant) and isinstance(open_mode.value, str) and any(c in open_mode.value for c in "wax+")) else "READ"
                category, rationale = ("SCRIPT_EXECUTION", "Business code invokes an external script or SQL command; verify the executable and script path are approved.") if operation == "EXECUTE" else classify(relative, name, arg_text, literal, operation)
                priority = "P1" if category in {"BUSINESS_OWNER_FILE_READ_REQUIRES_DB", "BUSINESS_OWNER_FILE_WRITE_REQUIRES_DB", "BUSINESS_FILE_READ_REQUIRES_DB", "BUSINESS_FILE_WRITE_REQUIRES_DB", "EXTERNAL_BUSINESS_DATA_FILE_READ_REQUIRES_DB", "ABSOLUTE_PATH_READ_REVIEW", "ABSOLUTE_PATH_WRITE_REVIEW"} else "P2" if category in {"DYNAMIC_PATH_READ", "CONFIG_CLASS_INPUT_REVIEW", "NONBUSINESS_PROCESS_STATE_REVIEW"} else "INFO"
                if is_codex_temp_path(literal):
                    priority = "INFO"
                rows.append({"kind": "FILE_ACCESS", "operation": operation, "category": category, "file": relative,
                             "line": node.lineno, "function": containing_function(node, parents), "api": name,
                             "path_expression": arg_text, "resolved_literal": literal,
                             "absolute_path": filesystem_absolute(literal),
                             "priority": priority, "rationale": rationale, "source_sha256": hashlib.sha256(raw).hexdigest()})
            for line, literal in sorted(seen_absolute):
                if any(row.get("file") == relative and row.get("line") == line and row.get("resolved_literal") == literal for row in rows):
                    continue
                normalized = literal.lower().replace("\\", "/")
                win_literal = PureWindowsPath(literal)
                win_parts = {part.lower() for part in win_literal.parts}
                if (win_literal.drive and ord(win_literal.drive[0].upper()) == 71 and "codex_tmp" in win_parts) or "windows" in win_parts:
                    priority = "INFO"
                elif "new_tdx" in win_parts or "codex work" in " ".join(win_literal.parts).lower():
                    priority = "P2"
                else:
                    priority = "P1"
                rows.append({"kind": "ABSOLUTE_PATH_LITERAL", "file": relative, "line": line, "resolved_literal": literal,
                             "absolute_path": filesystem_absolute(literal), "category": "ABSOLUTE_PATH_LITERAL_REVIEW",
                             "priority": priority,
                             "rationale": "Absolute path literal in business code; review whether it is configuration, test/temp, or an unnecessary dependency.",
                             "source_sha256": hashlib.sha256(raw).hexdigest()})
        else:
            for line_no, line in enumerate(source.splitlines(), 1):
                if not line.strip() or len(line) > 5000 or line.lstrip().startswith(("#", "//", "--", "*")):
                    continue
                if re.search(r"\b(?:open|readFile|readFileSync|createReadStream|read_csv|read_parquet|read_json|read_sql|fetch|import|require)\s*\(", line):
                    matches = [m.group(0).rstrip(".,;:") for m in ABSOLUTE.finditer(line) if filesystem_absolute(m.group(0).rstrip(".,;:"))]
                    for quoted in re.findall(r"['\"]([^'\"]{3,})['\"]", line):
                        if filesystem_absolute(quoted):
                            matches.append(quoted)
                    rows.append({"kind": "NON_PYTHON_ACCESS_CANDIDATE", "file": relative, "line": line_no,
                                 "path_expression": line.strip()[:1000], "absolute_literals": matches,
                                 "category": "DYNAMIC_PATH_READ" if not matches else "ABSOLUTE_PATH_READ",
                                 "priority": "P2" if not matches else "P1",
                                 "rationale": "Non-Python source candidate; review call chain and runtime path resolution.",
                                 "source_sha256": hashlib.sha256(raw).hexdigest()})
    git_head = git(root, "rev-parse", "HEAD").decode().strip()
    accesses = [r for r in rows if r.get("kind") == "FILE_ACCESS"]
    return {"contract_id": CONTRACT, "contract_version": "1.0.0", "git_head": git_head,
            "scope": "tracked current V4 business code: workbench, V4, focus tracker, shared runtime utility modules, runtime launcher, scripts called by those modules or workflows; excludes legacy phase code, tests, config/manifests, reports, documentation, archived data, and uncalled scripts",
            "tracked_code_file_count": len(paths), "excluded_uncalled_or_nonbusiness_file_count": len(excluded_paths),
            "excluded_uncalled_scripts": [p for p in excluded_paths if p.startswith("scripts/")], "file_access_call_count": len(accesses),
            "read_call_count": sum(r["operation"] == "READ" for r in accesses),
            "write_call_count": sum(r["operation"] == "WRITE" for r in accesses),
            "script_or_command_invocation_count": sum(r["operation"] == "EXECUTE" for r in accesses),
            "absolute_path_literal_count": sum(r.get("absolute_path") is True for r in rows),
            "database_environment_configuration_count": sum(r.get("category") == "DATABASE_ENV_CONFIGURATION" for r in rows),
            "other_environment_configuration_count": sum(r.get("category") == "OTHER_ENVIRONMENT_CONFIGURATION" for r in rows),
            "p1_finding_count": sum(r.get("priority") == "P1" for r in rows),
            "p2_review_count": sum(r.get("priority") == "P2" for r in rows),
            "dynamic_path_access_count": sum(r.get("category") == "DYNAMIC_PATH_READ" for r in accesses),
            "business_owner_file_read_requires_db_count": sum(r.get("category") == "BUSINESS_OWNER_FILE_READ_REQUIRES_DB" for r in accesses),
            "business_file_read_requires_db_count": sum(r.get("category") == "BUSINESS_FILE_READ_REQUIRES_DB" for r in accesses),
            "business_file_write_requires_db_count": sum(r.get("category") == "BUSINESS_FILE_WRITE_REQUIRES_DB" for r in accesses),
            "external_business_data_file_read_requires_db_count": sum(r.get("category") == "EXTERNAL_BUSINESS_DATA_FILE_READ_REQUIRES_DB" for r in accesses),
            "scanned_files": scanned_files,
            "rows": sorted(rows, key=lambda r: (r.get("file", ""), r.get("line", 0), r.get("kind", "")))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output")
    args = parser.parse_args()
    result = scan(Path(args.root))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name("." + path.name + ".tmp")
        temporary.write_text(rendered, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
