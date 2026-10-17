"""Shared staged-blob and commit-diff admission policy for this repository."""
from __future__ import annotations

import argparse
import ast
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath

MAX_BLOB_BYTES = 1024 * 1024
STAGE_REPORT = re.compile(
    r"reports/stage/V4_[A-Za-z0-9_-]+_COMPREHENSIVE_TEST_REPORT_\d{8}_R\d+\.md$"
)
ALLOWED_ROOT_FILES = {
    ".gitignore", ".gitattributes", "AGENTS.md", "README.md", "PROJECT_SPEC.md",
    ".env.example", "pytest.ini", "pyproject.toml", "requirements.txt", "THIRD_PARTY_NOTICES.md",
}
ALLOWED_ROOT_PREFIXES = ("requirements-",)
ALLOWED_DIRS = (
    "src/", "scripts/", "tools/", "tests/", "migrations/", "config/",
    "docs/requirements/", "docs/design/", "docs/spec/", "docs/upgrade/",
    ".githooks/", ".github/workflows/",
)
ALLOWED_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".sql",
    ".sh", ".ps1", ".cmd", ".bat", ".md", ".txt", ".json", ".toml", ".ini",
    ".yaml", ".yml", ".xml", ".svg",
}
DENIED_ROOTS = (
    "data/", "artifacts/", "runtime/", "logs/", "references/", "docs/evidence/",
    "reports/audits/",
)
DENIED_SUFFIXES = (".zip", ".parquet", ".sqlite", ".sqlite3", ".db", ".jsonl", ".gz", ".log", ".csv", ".tsv", ".arrow", ".feather", ".exe", ".dll", ".pyc")
PROCESS_NAME = re.compile(
    r"(?i)(?:task[-_]?(?:card|handoff)|execution[-_]plan|repair[-_]receipt|"
    r"audit[-_]?pass|evidence[-_]?bundle|acceptance[-_]?receipt|run[-_]?receipt)"
)
PROCESS_UPGRADE_DOC = re.compile(r"(?i)(?:^|[_-])(?:task|execution|continuation|receipt|evidence)(?:[_-]|\.)")
ROOT_LAUNCHER = re.compile(r"^(?:run_[A-Za-z0-9_.-]+\.py|(?:OPEN|START)_[A-Za-z0-9_.-]+\.cmd)$")
MACHINE_PATH = re.compile(
    r"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/](?:[^\\/\s'\"`]+[\\/])*[^\s'\"`]*|\\\\[^\\\s]+\\[^\\\s]+"
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?<![A-Za-z0-9_.])(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|"
    r"private[_-]?key|client[_-]?secret)\b['\"]?\s*[=:]\s*['\"]?([^\s'\"#,;]{4,})"
)
PLACEHOLDER = re.compile(r"(?i)^(?:change[-_ ]?me|example|sample|placeholder|your[-_ ].*|<.*>|\$\{.*\}|\*+|null|none|redacted)$")
DSN_CREDENTIAL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s'\"`]+:[^\s@'\"`]+@")
SENSITIVE_FILE = re.compile(r"(?i)(?:^|/)(?:\.env(?:\..*)?|id_rsa|id_ed25519|credentials(?:\..*)?|secrets?\.(?:json|ya?ml|toml)|.*\.(?:pem|p12|pfx|key))$")
REPORT_PAYLOAD = re.compile(r"(?im)^\s*\{\s*\"(?:task_id|run_id|evidence_bundle|artifact_manifest|input_manifest|execution_id)\"\s*:")
FORBIDDEN_PROD_PATH = re.compile(r"(?i)(?:docs/evidence/|reports/audits/|reports/(?:r\d+|v4_[^/]+)/)")
READ_CALL = re.compile(r"(?i)(?:read_text|read_bytes|json\.load|yaml\.safe_load|open\s*\([^\n]{0,100}(?:['\"]r['\"]|mode\s*=\s*['\"]r))")
TARGET_BRANCH = re.compile(
    r"(?i)(?:\b(?:SH|SZ)\.(?:\d{6})\b|\b(?:code|symbol|stock_code|security_code)\s*==\s*['\"]\d{6}['\"]|"
    r"\b(?:sector_id|industry_id)\s*==\s*['\"](?:INDUSTRY|CONCEPT):[^'\"]+['\"]|"
    r"\b(?:code|symbol|stock_code)\s+in\s*\{[^}]*['\"]\d{6}['\"])")
DYNAMIC_SQL = re.compile(
    r"(?is)(?:f['\"]\s*(?:select|insert|update|delete)\b[^'\"]*\{|"
    r"(?:^|[=(:,])\s*['\"]\s*(?:select|insert|update|delete)\b[^\n]{0,100}\s*\+\s*(?:str\(|[A-Za-z_][\w.]*)|"
    r"['\"]\s*(?:select|insert|update|delete)\b[^'\"]{0,100}['\"]\s*\.format(?:_map)?\s*\()")
LFS_POINTER = re.compile(
    rb"\Aversion https://git-lfs\.github\.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n?\Z"
)


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    detail: str


def run_git(args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args], input=input_bytes, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip() or "git command failed")
    return result.stdout


def parse_name_status(raw: bytes) -> list[tuple[str, str]]:
    fields = raw.split(b"\0")
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i].decode("ascii", "replace")
        i += 1
        if status.startswith(("R", "C")):
            if i + 1 >= len(fields):
                raise ValueError("malformed git name-status output")
            _old_path = fields[i]
            new_path = fields[i + 1]
            i += 2
            out.append((status, new_path.decode("utf-8", "surrogateescape")))
        else:
            if i >= len(fields):
                raise ValueError("malformed git name-status output")
            path = fields[i]
            i += 1
            if status[:1] != "D":
                out.append((status, path.decode("utf-8", "surrogateescape")))
    return out


def classify_path(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    lower = normalized.lower()
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized) or "../" in f"/{normalized}/":
        return "PATH_TRAVERSAL"
    if SENSITIVE_FILE.search(normalized) and normalized != ".env.example":
        return "SENSITIVE_FILENAME"
    if lower.startswith("reports/"):
        return None if STAGE_REPORT.fullmatch(normalized) else "FORBIDDEN_REPORT_PATH"
    if any(lower.startswith(root) for root in DENIED_ROOTS):
        return "FORBIDDEN_OUTPUT_PATH"
    if not (
        normalized in ALLOWED_ROOT_FILES
        or ROOT_LAUNCHER.fullmatch(normalized)
        or any(normalized.startswith(prefix) for prefix in ALLOWED_ROOT_PREFIXES)
        or any(normalized.startswith(prefix) for prefix in ALLOWED_DIRS)
    ):
        return "PATH_NOT_ALLOWLISTED"
    suffix = PurePosixPath(normalized).suffix.lower()
    if lower.endswith(".jsonl.gz") or any(lower.endswith(ext) for ext in DENIED_SUFFIXES):
        # Small text fixtures are permitted only beneath tests/fixtures and are still size checked.
        if not (normalized.startswith("tests/fixtures/") and suffix in {".csv", ".tsv", ".jsonl", ".gz"}):
            return "FORBIDDEN_FILE_TYPE"
    if suffix not in ALLOWED_SUFFIXES and normalized not in ALLOWED_ROOT_FILES and not (
        (normalized.startswith("tests/fixtures/") and suffix in {".csv", ".tsv", ".jsonl", ".gz"})
        or (normalized.startswith(".githooks/") and suffix == "")
    ):
        return "FILE_TYPE_NOT_ALLOWLISTED"
    if PROCESS_NAME.search(PurePosixPath(normalized).name) and not normalized.startswith("tests/"):
        return "PROCESS_ARTIFACT_NAME"
    if normalized.startswith("docs/upgrade/") and PROCESS_UPGRADE_DOC.search(PurePosixPath(normalized).name):
        return "PROCESS_UPGRADE_DOCUMENT"
    return None


def _lfs_object_path(oid: str) -> str:
    from pathlib import Path

    path = Path(run_git(["rev-parse", "--git-path", "lfs/objects"]).decode().strip())
    return str(path / oid[:2] / oid[2:4] / oid)


def _read_lfs_object(oid: str) -> bytes | None:
    from pathlib import Path

    path = Path(_lfs_object_path(oid))
    return path.read_bytes() if path.is_file() else None


def inspect_blob(path: str, blob: bytes) -> list[Finding]:
    findings: list[Finding] = []
    kind = classify_path(path)
    if kind:
        findings.append(Finding(kind, path, "path is outside the repository content contract"))

    pointer = LFS_POINTER.fullmatch(blob)
    raw_size = len(blob)
    content = blob
    if pointer:
        oid = pointer.group(1).decode("ascii")
        declared_size = int(pointer.group(2))
        obj = _read_lfs_object(oid)
        if obj is None:
            findings.append(Finding("LFS_OBJECT_MISSING", path, "referenced local LFS object is unavailable"))
        elif len(obj) != declared_size or hashlib.sha256(obj).hexdigest() != oid:
            findings.append(Finding("LFS_OBJECT_MISMATCH", path, "local LFS object size or SHA-256 does not match pointer"))
        else:
            content, raw_size = obj, len(obj)
    elif blob.startswith(b"version https://git-lfs.github.com/spec/v1"):
        findings.append(Finding("LFS_POINTER_INVALID", path, "LFS pointer format is invalid"))

    if raw_size > MAX_BLOB_BYTES:
        code = "MANUAL_REVIEW_REQUIRED" if path.startswith(("docs/requirements/", "docs/design/", "docs/spec/", "reports/stage/")) else "BLOB_TOO_LARGE"
        findings.append(Finding(code, path, f"raw blob is {raw_size} bytes; limit is {MAX_BLOB_BYTES}"))

    text = content.decode("utf-8", "replace")
    low = text.lower()
    if DSN_CREDENTIAL.search(text):
        findings.append(Finding("CREDENTIAL_PATTERN", path, "credential-bearing connection string pattern detected"))
    for match in SECRET_ASSIGNMENT.finditer(text):
        value = match.group(1).strip().strip("'\"")
        # A token field assigned from the identically named SQL/Python field
        # is an identifier binding, not a credential literal. Literal and
        # named-secret values remain subject to the checks below.
        left = re.split(r"[=:]", match.group(0), maxsplit=1)[0].strip().strip("'\"")
        left = left.rsplit(".", 1)[-1].lower()
        right = value.rsplit(".", 1)[-1].lower()
        if left and right == left and re.fullmatch(r"[A-Za-z_]\w*", value.rsplit(".", 1)[-1]):
            continue
        if value and not PLACEHOLDER.fullmatch(value) and not re.match(
            r"(?i)^(?:os\.(?:getenv|environ)|settings\.|config\.|secretmanager\.|"
            r"get_secret\(|read_secret\(|process\.env\b|env\(|[A-Za-z_]\w*\.[A-Za-z_]\w*\()", value
        ) and not re.fullmatch(r"(?i)(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*\([^)]*\)", value):
            findings.append(Finding("CREDENTIAL_PATTERN", path, "non-placeholder credential assignment pattern detected"))
            break

    # These two exact-path offline validators must inspect report/Head evidence
    # by design. The scanner exception also permits machine-path syntax; the
    # promotion validator retains all other code-path checks.
    read_only_report_tools = {
        "scripts/audit_v4_nonconfig_file_references_r1.py",
        "scripts/validate_v4_12_promotion_r14.py",
    }
    code_path = path.startswith(("src/", "scripts/", "tools/")) or path.lower().endswith((".js", ".ts", ".tsx", ".sql", ".cmd", ".bat"))
    if code_path and path != "tools/git_repository_policy.py":
        if MACHINE_PATH.search(text) and path != "scripts/audit_v4_nonconfig_file_references_r1.py":
            findings.append(Finding("MACHINE_PATH", path, "machine-specific absolute path detected"))
        if _direct_forbidden_path_read(text) and path not in read_only_report_tools:
            findings.append(Finding("PROCESS_DATA_DEPENDENCY", path, "production/tool code reads a task, evidence, or historical report path"))
        if path.startswith("src/") and TARGET_BRANCH.search(text):
            findings.append(Finding("TARGET_SPECIFIC_BRANCH", path, "production code contains a fixed security or sector branch candidate"))
        if path.endswith((".sql", ".py", ".js", ".ts", ".tsx")) and DYNAMIC_SQL.search(text):
            findings.append(Finding("DYNAMIC_SQL", path, "SQL appears to interpolate or concatenate a dynamic query"))

    if not path.startswith("tests/") and REPORT_PAYLOAD.search(text):
        findings.append(Finding("PROCESS_PAYLOAD_MASQUERADE", path, "task/run/evidence payload is not a formal source or configuration"))

    if path.startswith("reports/stage/"):
        required = ("stage_id:", "code_sha:", "test_scope:", "conclusion:", "approval_status:")
        absent = [field[:-1] for field in required if field not in low]
        if absent:
            findings.append(Finding("STAGE_REPORT_SCHEMA", path, "missing required fields: " + ", ".join(absent)))
        if not text.lstrip().startswith("---"):
            findings.append(Finding("STAGE_REPORT_TEMPLATE", path, "formal stage report must use the versioned front matter template"))
    return findings


def _direct_forbidden_path_read(text: str) -> bool:
    """Reject filesystem reads of evidence/report paths while allowing PG adapters.

    The previous file-wide check combined any path literal with any read call in
    a module. It incorrectly rejected PG materializer calls and output paths.
    Inspect actual Python file-read expressions and simple string path aliases.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return bool(FORBIDDEN_PROD_PATH.search(text) and READ_CALL.search(text))
    forbidden_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            segment = ast.get_source_segment(text, node.value) or ""
            if FORBIDDEN_PROD_PATH.search(segment):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                forbidden_names.update(t.id for t in targets if isinstance(t, ast.Name))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
        if name not in {"open", "read_text", "read_bytes", "load", "safe_load"}:
            continue
        segment = ast.get_source_segment(text, node) or ""
        if FORBIDDEN_PROD_PATH.search(segment):
            return True
        if any(isinstance(child, ast.Name) and child.id in forbidden_names
               for arg in node.args for child in ast.walk(arg)):
            return True
    return False


def staged_blobs() -> list[tuple[str, bytes]]:
    entries = parse_name_status(run_git(["diff", "--cached", "--name-status", "-z", "--find-renames"]))
    return [(path, run_git(["show", f":{path}"])) for _, path in entries]


def diff_blobs(base: str, head: str) -> list[tuple[str, bytes]]:
    entries = parse_name_status(run_git(["diff", "--name-status", "-z", "--find-renames", base, head]))
    return [(path, run_git(["show", f"{head}:{path}"])) for _, path in entries]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true", help="scan staged Git blobs for pre-commit")
    group.add_argument("--diff-base", metavar="OID", help="scan commit diff from BASE to HEAD")
    parser.add_argument("--diff-head", metavar="OID", help="HEAD commit for --diff-base (defaults to HEAD)")
    args = parser.parse_args(argv)
    try:
        blobs = staged_blobs() if args.staged else diff_blobs(args.diff_base, args.diff_head or "HEAD")
        findings = [finding for path, blob in blobs for finding in inspect_blob(path, blob)]
    except (RuntimeError, ValueError) as exc:
        print(f"repository policy could not complete: {exc}", file=sys.stderr)
        return 2
    if not findings:
        print(f"repository policy passed ({len(blobs)} changed blob(s))")
        return 0
    for finding in findings:
        print(f"{finding.code}: {finding.path}: {finding.detail}")
    print(f"repository policy blocked ({len(findings)} finding(s), {len(blobs)} changed blob(s))")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
