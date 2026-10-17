import json
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_v4_nonconfig_file_references_r1 as audit


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

def _commit(root):
    _git(root, "-c", "user.name=Audit Test", "-c", "user.email=audit@example.invalid", "commit", "-qm", "fixture")


def test_scanner_emits_full_identity_schema_and_classifies_valid_vs_missing(tmp_path):
    root = tmp_path
    _git(root, "init", "-q")
    (root / "scripts").mkdir()
    (root / "data/v4").mkdir(parents=True)
    target = root / "data/v4/frozen.csv"
    target.write_bytes(b"date,close\n2026-10-16,10\n")
    identity = {"path": "data/v4/frozen.csv", "sha256": audit._sha(target.read_bytes()), "bytes": target.stat().st_size}
    (root / "data/v4/V4_ACCEPTED_HEAD.json").write_text(json.dumps({"artifact": identity, "missing": {"path": "data/v4/absent.sql", "sha256": "0" * 64, "bytes": 9}}), encoding="utf-8")
    (root / "scripts/entry.py").write_text("from pathlib import Path\nPath(os.getenv('RUNTIME_ROOT')).read_bytes()\n", encoding="utf-8")
    _git(root, "add", ".")
    _commit(root)
    result = audit.scan_repository(root)
    assert audit.scan_repository(root) == result
    assert result["contract_id"] == audit.CONTRACT_ID
    assert result["tracked_file_count"] == 3
    assert result["reference_edges_total"] >= 3
    edge = next(item for item in result["reference_edges"] if item["literal_or_resolved_target"] == "data/v4/frozen.csv")
    assert edge["expected_sha256"] == identity["sha256"] and edge["actual_sha256"] == identity["sha256"]
    missing = next(item for item in result["reference_edges"] if item["literal_or_resolved_target"] == "data/v4/absent.sql")
    assert missing["risk_type"] == "MISSING_FILE"
    assert any(item["risk_type"] == "DYNAMIC_UNRESOLVED" for item in result["reference_edges"])
    required = {"reference_id", "caller_path", "line", "symbol", "entrypoint", "reachable", "static_or_dynamic",
        "literal_or_resolved_target", "root/source_of_path", "file_type", "purpose", "historical_or_current",
        "accepted_head/manifest_identity", "origin_commit", "expected_sha256", "expected_bytes", "actual_sha256",
        "actual_bytes", "exists", "T0", "publication_id", "namespace", "risk_type", "priority", "proof",
        "fix_commit", "regression_test", "unresolved_reason"}
    assert required <= edge.keys()


def test_scanner_rejects_path_traversal_and_detects_lfs_pointer(tmp_path):
    root = tmp_path
    _git(root, "init", "-q")
    (root / "src").mkdir()
    (root / "src/entry.py").write_text("open('../../outside.csv')\n", encoding="utf-8")
    lfs = root / "large.parquet"
    lfs.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"a" * 64 + b"\nsize 10\n")
    (root / "config").mkdir()
    (root / "config/v4_registry.json").write_text(json.dumps({"payload": {"path": "large.parquet"}}), encoding="utf-8")
    _git(root, "add", ".")
    _commit(root)
    result = audit.scan_repository(root)
    assert any(edge["risk_type"] == "UNTRUSTED_PATH_TRAVERSAL" for edge in result["reference_edges"])
    assert any(edge["risk_type"] == "GIT_LFS_POINTER_ONLY" for edge in result["reference_edges"])


def test_frontend_relative_assets_api_routes_and_download_names_are_not_false_missing_files(tmp_path):
    root = tmp_path
    _git(root, "init", "-q")
    (root / "src/ui").mkdir(parents=True)
    (root / "src/ui/chunk.js").write_text("export const ok = true;\n", encoding="utf-8")
    (root / "src/ui/app.js").write_text("import './chunk.js';\nasync function load(){const r=await fetch('/api/v4/rows.csv');return r.json()}\nlink.download='export.csv';\n", encoding="utf-8")
    static = root / "src/workbench_service/static"
    (static / "v2").mkdir(parents=True)
    (static / "daily-update").mkdir(parents=True)
    (static / "v2/styles.css").write_text("body{}\n", encoding="utf-8")
    (static / "daily-update/app.js").write_text("window.ready=true;\n", encoding="utf-8")
    (static / "v2/index.html").write_text('<link href="/v2/styles.css"><script src="/v4/daily-update.js"></script>\n', encoding="utf-8")
    _git(root, "add", ".")
    _commit(root)
    result = audit.scan_repository(root)
    rel = next(x for x in result["reference_edges"] if x["literal_or_resolved_target"] == "./chunk.js")
    api = next(x for x in result["reference_edges"] if x["literal_or_resolved_target"].endswith("api/v4/rows.csv"))
    name = next(x for x in result["reference_edges"] if x["literal_or_resolved_target"] == "export.csv")
    assert rel["risk_type"] == "KNOWN_VALID_CURRENT_REFERENCE" and rel["actual_sha256"] == audit._sha((root / "src/ui/chunk.js").read_bytes())
    assert api["risk_type"] == "API_ROUTE_NOT_LOCAL_FILE"
    assert name["risk_type"] == "OUTPUT_PATH_DECLARATION"
    css = next(x for x in result["reference_edges"] if x["literal_or_resolved_target"] == "/v2/styles.css")
    alias = next(x for x in result["reference_edges"] if x["literal_or_resolved_target"] == "/v4/daily-update.js")
    assert css["risk_type"] == alias["risk_type"] == "KNOWN_VALID_CURRENT_REFERENCE"


def test_runtime_writes_are_output_paths_not_missing_inputs(tmp_path):
    root = tmp_path
    _git(root, "init", "-q")
    (root / "src").mkdir()
    (root / "src/writer.py").write_text("open('generated.csv', 'w').write('x')\n", encoding="utf-8")
    _git(root, "add", ".")
    _commit(root)
    result = audit.scan_repository(root)
    output = next(x for x in result["reference_edges"] if x["literal_or_resolved_target"] == "generated.csv")
    assert output["risk_type"] == "OUTPUT_PATH_DECLARATION" and output["priority"] == "INFO"


def test_optional_tray_python_override_is_not_a_blocking_stale_root():
    risk, priority, *_ = audit._risk("E:/python/python.exe", ROOT, "scripts/workbench_tray.ps1", None, None)
    assert risk == "ABSOLUTE_STALE_ROOT" and priority == "P2"


def test_oversized_document_literal_is_retained_without_filesystem_stat():
    risk, priority, resolved, *_ = audit._risk("# " + "x" * 300, ROOT, "scripts/example.py", None, None)
    assert risk == "NON_PATH_LITERAL" and priority == "INFO" and resolved is None
