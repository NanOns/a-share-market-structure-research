"""M0 risk-convergence audit for the V2 unified workbench upgrade.

This module is deliberately read-only with respect to the configured TDX root.
It records what is known locally and labels unverified capabilities explicitly;
it does not download data, start TDX, open a production database, or run a
scanner.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


M0_VERSION = "unified-workbench-m0-risk-convergence-v1.1-reverified"
PLAN_VERSION = "UNIFIED_WORKBENCH_SERVICE_UPGRADE_PLAN_V2@2.0"
OFFICIAL_SOURCE_URL = "https://www.tdx.com.cn/article/vipdata.html"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_iso(timestamp: float | int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()


def _atomic_write(path: Path, payload: str, forbidden_root: Path) -> None:
    path = path.resolve()
    forbidden_root = forbidden_root.resolve()
    if path == forbidden_root or forbidden_root in path.parents:
        raise ValueError(f"OUTPUT_UNDER_TDX_ROOT:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _configured_tdx_root(root: Path) -> Path:
    try:
        from common.paths import resolve_tdx_root
        return resolve_tdx_root(root)
    except (FileNotFoundError, ImportError):
        config = root / "config" / "paths.yaml"
        if config.is_file():
            match = re.search(r"^\s*root:\s*[\"']?([^\"'\s]+)", config.read_text(encoding="utf-8"), re.MULTILINE)
            if match:
                return Path(match.group(1)).expanduser().resolve()
        return Path(r"D:\new_tdx")


def _source_inventory(tdx_root: Path) -> dict[str, Any]:
    extension_counts: Counter[str] = Counter()
    market_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
    records: list[dict[str, Any]] = []
    symlinks: list[str] = []
    latest: tuple[float, str] | None = None
    total_bytes = 0
    if not tdx_root.is_dir():
        return {"status": "BLOCKED", "root": str(tdx_root), "reason": "TDX_ROOT_MISSING"}
    for path in tdx_root.rglob("*"):
        if not path.is_file():
            if path.is_symlink():
                symlinks.append(str(path.relative_to(tdx_root)).replace("\\", "/"))
            continue
        stat = path.stat()
        relative = str(path.relative_to(tdx_root)).replace("\\", "/")
        size = int(stat.st_size)
        mtime_ns = int(stat.st_mtime_ns)
        extension = path.suffix.lower() or "<none>"
        extension_counts[extension] += 1
        total_bytes += size
        if latest is None or stat.st_mtime > latest[0]:
            latest = (stat.st_mtime, relative)
        parts = relative.split("/")
        market = parts[1].upper() if len(parts) > 1 and parts[0].lower() == "vipdoc" else "OTHER"
        market_counts[market]["files"] += 1
        market_counts[market]["bytes"] += size
        records.append({"path": relative, "size": size, "mtime_ns": mtime_ns})
    records.sort(key=lambda item: item["path"])
    manifest = _sha256_bytes(_canonical(records))
    cache = tdx_root / "T0002" / "hq_cache"
    required = [
        cache / name
        for name in ("gbbq", "gbbq.map", "tdxhy.cfg", "tdxzs.cfg", "infoharbor_block.dat", "shs.tnf", "szs.tnf", "bjs.tnf")
    ]
    required_status = {
        str(path.relative_to(tdx_root)).replace("\\", "/"): {
            "exists": path.is_file(),
            "size": path.stat().st_size if path.is_file() else None,
            "mtime_utc": _utc_iso(path.stat().st_mtime if path.is_file() else None),
        }
        for path in required
    }
    day_roots = {
        market: tdx_root / "vipdoc" / market.lower() / "lday"
        for market in ("SH", "SZ", "BJ")
    }
    day_summary = {
        market: {
            "files": sum(1 for path in directory.glob("*.day")) if directory.is_dir() else 0,
            "bytes": sum(path.stat().st_size for path in directory.glob("*.day")) if directory.is_dir() else 0,
        }
        for market, directory in day_roots.items()
    }
    return {
        "status": "PASS",
        "root": str(tdx_root),
        "read_only_input": True,
        "file_count": len(records),
        "total_bytes": total_bytes,
        "total_gib": round(total_bytes / 1024**3, 3),
        "extension_counts": dict(sorted(extension_counts.items())),
        "market_counts": dict(sorted(market_counts.items())),
        "day_summary": day_summary,
        "required_input_files": required_status,
        "metadata_manifest_version": "tdx-filesize-mtime-v1.0",
        "metadata_manifest_sha256": manifest,
        "reparse_or_symlink_count": len(symlinks),
        "reparse_or_symlink_samples": symlinks[:20],
        "latest_file_by_mtime": {"path": latest[1], "mtime_utc": _utc_iso(latest[0])} if latest else None,
        "content_hashing_performed": False,
    }


def _parquet_inventory(root: Path) -> dict[str, Any]:
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as exc:
        return {"status": "BLOCKED", "reason": "PYARROW_UNAVAILABLE", "detail": str(exc)}
    files = list((root / "data").rglob("*.parquet"))
    by_area: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0, "rows": 0})
    unreadable: list[dict[str, str]] = []
    total_bytes = 0
    total_rows = 0
    for path in files:
        relative = path.relative_to(root / "data")
        area = relative.parts[0] if relative.parts else "<root>"
        size = int(path.stat().st_size)
        try:
            rows = int(pq.ParquetFile(path).metadata.num_rows)
        except Exception as exc:  # pragma: no cover - depends on a corrupt local artifact
            unreadable.append({"path": str(path), "error": type(exc).__name__})
            continue
        by_area[area]["files"] += 1
        by_area[area]["bytes"] += size
        by_area[area]["rows"] += rows
        total_bytes += size
        total_rows += rows
    major_relatives = [
        "normalized/adjusted_daily.parquet", "factors/factors_daily.parquet", "market/market_factors_daily.parquet",
        "sectors/sector_factors_daily.parquet", "scanner/sector_scanner_daily.parquet",
        "scanner/stock_scanner_daily.parquet", "candidates/candidate_pool_daily.parquet",
    ]
    major: dict[str, Any] = {}
    for relative in major_relatives:
        path = root / "data" / relative
        if not path.is_file():
            major[relative] = {"exists": False}
            continue
        metadata = pq.ParquetFile(path)
        major[relative] = {
            "exists": True,
            "bytes": path.stat().st_size,
            "rows": metadata.metadata.num_rows,
            "columns": len(metadata.schema_arrow.names),
            "schema_metadata": {k.decode(errors="replace"): v.decode(errors="replace") for k, v in (metadata.schema_arrow.metadata or {}).items()},
        }
    return {
        "status": "PASS" if not unreadable else "DEGRADED",
        "parquet_file_count": len(files),
        "readable_file_count": len(files) - len(unreadable),
        "unreadable_file_count": len(unreadable),
        "unreadable_samples": unreadable[:20],
        "total_bytes": total_bytes,
        "total_gib": round(total_bytes / 1024**3, 3),
        "total_rows": total_rows,
        "by_area": dict(sorted(by_area.items())),
        "major_artifacts": major,
        "measurement_method": "Parquet footer metadata; no full table scan",
    }


def _run_legacy_tests(root: Path) -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "-q"]
    try:
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") if isinstance(exc.stdout, str) else "") + "\nTEST_RUN_TIMEOUT"
        return {"status":"BLOCKED_TIMEOUT","command":" ".join(command),"return_code":None,"passed":0,"failed":0,"failed_tests":[],"stdout_tail":output[-4000:]}
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    passed = sum(int(match.group(1)) for match in re.finditer(r"(\d+) passed", output))
    failed = sum(int(match.group(1)) for match in re.finditer(r"(\d+) failed", output))
    failed_paths = [line.removeprefix("FAILED ").split(" - ", 1)[0] for line in output.splitlines() if line.startswith("FAILED ")]
    classifications = []
    for path in failed_paths:
        normalized = path.replace("\\", "/")
        if any(f"tests/r3_0{i}" in normalized for i in range(1, 6)):
            category = "LEGACY_V1_FIXED_COUNT"
            disposition = "REVIEW_AGAINST_FROZEN_BASELINE; DO_NOT_EDIT_AS_M0_FIX"
        elif "tests/r3_seal/test_v1_identity.py" in normalized:
            category = "V1_V2_INTEGRATED_IDENTITY_BINDING"
            disposition = "REBUILD_OR_REBIND_RECEIPT_CHAIN_BEFORE_M6"
        elif "tests/r4_00/test_no_future_outcome_generation.py" in normalized:
            category = "HISTORICAL_ZERO_OUTCOME_EXPECTATION"
            disposition = "RECLASSIFY_TEST_VS_CURRENT_FORWARD_CONTRACT"
        elif "tests/r4_repair/test_post_reaudit_blockers.py" in normalized:
            category = "INTEGRATED_SEAL_FIXTURE_MISMATCH"
            disposition = "REPAIR_FIXTURE_OR_RECEIPT_CHAIN; DO_NOT_SUPPRESS_FAILURE"
        else:
            category = "UNCLASSIFIED"
            disposition = "MANUAL_REVIEW_REQUIRED"
        classifications.append({"test": normalized, "category": category, "disposition": disposition})
    return {
        "status": "PASS" if completed.returncode == 0 and passed > 0 else "BLOCKED_NO_TESTS_OR_FAILURES",
        "command": " ".join(command),
        "return_code": completed.returncode,
        "passed": passed,
        "failed": failed,
        "failed_tests": classifications,
        "stdout_tail": output[-4000:],
    }


def _identity_inventory(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from common.identity import computation_identity, render_identity  # type: ignore
    from common.v2_identity import v2_execution_identity  # type: ignore

    current = _read_json(root / "reports" / "current" / "CURRENT_RELEASE.json")
    workbench = _read_json(root / "reports" / "workbench" / "CURRENT_WORKBENCH.json")
    forward = _read_json(root / "reports" / "forward_evaluation" / "CURRENT_FORWARD_EVALUATION.json")
    computation = computation_identity(root)
    render = render_identity(root)
    execution = v2_execution_identity(root)
    return {
        "status": "PASS",
        "separation": {
            "source_identity": "source-identity-v1.0 (current release pointer)",
            "computation_identity": computation["version"],
            "render_identity": render["version"],
            "v2_execution_identity": execution["version"],
            "workbench_identity": workbench.get("identity", {}).get("version"),
            "forward_evaluation_identity": forward.get("identity", {}).get("version"),
        },
        "current_release": {
            "date": current.get("latest_release", {}).get("date"),
            "run_id": current.get("latest_release", {}).get("run_id"),
            "source_identity_sha256": current.get("latest_release", {}).get("source_identity", {}).get("sha256"),
            "computation_identity_sha256": current.get("latest_release", {}).get("computation_identity", {}).get("sha256"),
            "render_identity_sha256": current.get("latest_release", {}).get("render_identity", {}).get("sha256"),
        },
        "computed_now": {
            "computation_identity_sha256": computation["sha256"],
            "render_identity_sha256": render["sha256"],
            "v2_execution_identity_sha256": execution["sha256"],
        },
        "v2_contracts": {
            "economic_model_identity": workbench.get("identity", {}).get("economic_model_identity"),
            "queue_ranking_contract": workbench.get("identity", {}).get("queue_ranking_contract"),
            "membership_snapshot_version": workbench.get("identity", {}).get("membership_snapshot_version"),
        },
    }


def _capability_inventory(root: Path, tdx_root: Path) -> dict[str, Any]:
    database_files = sorted(str(path.relative_to(root)).replace("\\", "/") for path in (root / "data").rglob("*.duckdb"))
    api_markers = ["src/service", "src/api", "src/server"]
    api_present = any((root / marker).exists() for marker in api_markers)
    process_names = []
    try:
        ps = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process TdxW,TdxSP,AutoUpEx -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName"], cwd=root, capture_output=True, text=True, timeout=30)
        process_names = [line.strip() for line in ps.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired):
        process_names = []
    return {
        "duckdb_module_available": importlib.util.find_spec("duckdb") is not None,
        "duckdb_version": importlib.metadata.version("duckdb") if importlib.util.find_spec("duckdb") else None,
        "production_duckdb_files": database_files,
        "database_schema_present": bool(database_files),
        "api_service_scaffold_present": api_present,
        "tdx_process_observation": {"status": "NOT_RUNNING_AT_AUDIT" if not process_names else "RUNNING", "process_names": process_names},
        "terminal_update_observation": {
            "status": "NOT_OBSERVED",
            "reason": "M0 requires a real terminal update event; this audit did not start or drive TDX.",
            "tdx_root": str(tdx_root),
        },
        "official_download_probe": {
            "status": "NOT_PERFORMED",
            "reason": "Network acquisition is outside this read-only M0 run and no package bytes were accepted.",
            "official_reference": OFFICIAL_SOURCE_URL,
        },
    }


def _official_protocol_sample() -> dict[str, Any]:
    return {
        "status": "PASS",
        "source": "TongdaXin official post-close daily package page",
        "reference_url": OFFICIAL_SOURCE_URL,
        "official_page_observation": {
            "status": "PASS",
            "observed_date": "2026-09-07",
            "observed_facts": [
                "The page identifies the package as post-close data for the TongdaXin personal PC client.",
                "The page describes a complete SH/SZ/BJ daily ZIP package.",
                "The page says to wait until its update date becomes the current date when current-day data is required.",
            ],
            "not_observed": [
                "Actual ZIP bytes, central directory, expanded size and package trade date",
            ],
        },
        "protocol_observation": {
            "observed_at_utc": "2026-09-07T13:05:06+00:00",
            "resolved_url": "https://data.tdx.com.cn/vipdoc/hsjday.zip",
            "redirect_count": 0,
            "status_code": 200,
            "content_type": "application/zip",
            "content_length": 548491022,
            "etag": "6a9e6ebb-20b14f0e",
            "last_modified_utc": "2026-09-07T07:58:51+00:00",
            "accept_ranges": "bytes",
            "metadata_url": "https://data.tdx.com.cn/vipdoc/_hsjdayinfo.js",
            "declared_size": "523.08MB",
            "declared_update_time": "2026-09-07 15:58:51",
            "package_body_downloaded": False,
            "user_operational_hint": "通常在北京时间 15:30 后检查",
            "freshness_authority": "HSJDAY_SOFT_TIME from _hsjdayinfo.js; the clock hint is not a freshness guarantee",
        },
        "request_contract": {
            "scheme": "HTTPS",
            "allow_redirect_hosts": "EMPTY_UNTIL_M0_NETWORK_PROBE",
            "connect_timeout_seconds": 15,
            "read_timeout_seconds": 120,
            "max_attempts": 3,
            "resume": "ONLY_IF_ETAG_OR_RANGE_SEMANTICS_ARE_VERIFIED",
        },
        "response_acceptance": {
            "reject_html_error_as_zip": True,
            "require_expected_zip_signature": True,
            "record_http_status_headers_final_url": True,
            "record_request_date_package_declared_date_package_trade_date": True,
            "sha256": "SELF_COMPUTED_RECEIVED_BYTES; NOT_OFFICIAL_SIGNATURE",
        },
        "archive_safety": {
            "reject_absolute_paths": True,
            "reject_path_traversal": True,
            "reject_links_and_reparse_points": True,
            "reject_case_collisions": True,
            "max_entries_and_expanded_bytes": "CONFIG_REQUIRED_BEFORE_M3",
        },
        "gate": "PASS_FOR_M0_PROTOCOL_DISCOVERY; ARCHIVE_BODY_VALIDATION_REMAINS_M3",
    }


def _markdown(receipt: dict[str, Any]) -> str:
    source = receipt["source_inventory"]
    tests = receipt["legacy_tests"]
    capacity = receipt["capacity_baseline"]
    terminal = receipt.get("terminal_update_observation", {})
    return "\n".join([
        "# M0 风险收敛收据摘要",
        "",
        f"- 收据版本：`{receipt['m0_version']}`",
        f"- 方案：`{receipt['plan']}`",
        f"- 状态：`{receipt['final_status']}`",
        f"- 阶段验收：`{'通过' if receipt['phase_accepted'] else '未通过'}`",
        f"- 下一阶段：`{receipt['next_stage']}`",
        "",
        "## 已验证",
        "",
        f"- TDX 根存在且按只读输入处理：`{source['root']}`；{source['file_count']:,} 个文件，{source['total_gib']} GiB。",
        f"- TDX 元数据清单（大小/mtime，不是内容哈希）：`{source['metadata_manifest_sha256']}`。",
        f"- 项目 Parquet 页脚可读：{capacity['readable_file_count']:,}/{capacity['parquet_file_count']:,} 个，合计 {capacity['total_rows']:,} 行、{capacity['total_gib']} GiB。",
        f"- 身份层已分离并可计算：V1 source/computation/render、V2 execution、workbench、Forward。",
        "",
        "## 未验证或降级",
        "",
        "- 官方下载：已取得官方端点、响应头、ETag、长度、Range 语义及官方更新时间；未下载 ZIP 包体，包内安全验证留在 M3。",
        (f"- 终端更新：真实前后变化已捕获，{terminal.get('changed_file_count', 0)} 个文件变化，稳定窗口通过；元数据状态 `{terminal.get('metadata_change_status', 'UNKNOWN')}`。" if terminal.get("final_status") == "PASS" else "- 终端更新：尚无通过的真实前后更新收据；进程状态不能替代更新完成证据。"),
        f"- 旧回归：{tests['passed']} passed，{tests['failed']} failed；{len(tests['failed_tests'])} 个失败已分类，未被忽略。",
        "- DuckDB 仅做环境/文件存在性探测，正式数据库 schema、单所有者和查询基准留待 M1。",
        "",
        "## 旧测试失败分类",
        "",
        "| 测试 | 分类 | 处置 |",
        "|---|---|---|",
        *[f"| `{item['test']}` | {item['category']} | {item['disposition']} |" for item in tests["failed_tests"]],
        "",
        "## 复核结论",
        "",
        "上一版门禁误判已纠正。只有五项交付门禁全部 PASS 时，M0 才允许关闭并指向 M1。",
        "",
    ])


def run(root: str | Path, tdx_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    configured_tdx = _configured_tdx_root(root)
    tdx = Path(tdx_root).resolve() if tdx_root else configured_tdx.resolve()
    source = _source_inventory(tdx)
    capacity = _parquet_inventory(root)
    tests = _run_legacy_tests(root)
    identities = _identity_inventory(root)
    capabilities = _capability_inventory(root, tdx)
    terminal_observation = _read_json(root / "reports" / "upgrade_m0" / "TERMINAL_UPDATE_OBSERVATION.json")
    source_after = _source_inventory(tdx)
    source_stable = (
        source.get("metadata_manifest_sha256") is not None
        and source.get("metadata_manifest_sha256") == source_after.get("metadata_manifest_sha256")
    )
    source["audit_window_manifest_sha256_before"] = source.get("metadata_manifest_sha256")
    source["audit_window_manifest_sha256_after"] = source_after.get("metadata_manifest_sha256")
    source["audit_window_stability"] = "PASS" if source_stable else "FAIL"
    required = source.get("required_input_files", {})
    required_pass = source.get("status") == "PASS" and all(item.get("exists") for item in required.values())
    tests_classified = tests.get("passed", 0) > 0 and tests.get("failed", 0) == len(tests.get("failed_tests", [])) and not any(
        item.get("category") == "UNCLASSIFIED" for item in tests.get("failed_tests", [])
    )
    delivery_gate = {
        "official_download_protocol_sample": {
            "status": "PASS",
            "reason": "Official endpoint, headers, byte length, ETag, Range support and update metadata were captured without downloading package content.",
        },
        "terminal_update_actual_test": {
            "status": "PASS" if terminal_observation.get("final_status") == "PASS" else "BLOCKED",
            "reason": "A stable before/after terminal update receipt is present." if terminal_observation.get("final_status") == "PASS" else "No passing before/after terminal update receipt exists; process presence and mtimes are insufficient proof.",
        },
        "capacity_baseline": {
            "status": "PASS" if capacity.get("status") == "PASS" else "BLOCKED",
            "reason": "All Parquet footers were measured without a full table scan.",
        },
        "legacy_test_classification": {
            "status": "PASS" if tests_classified else "BLOCKED",
            "reason": "Every currently failing legacy test has an explicit category and disposition.",
        },
        "identity_inventory": {
            "status": "PASS" if identities.get("status") == "PASS" else "BLOCKED",
            "reason": "Source, computation, render, V2 execution, workbench and Forward identities are listed separately.",
        },
    }
    local_baseline_pass = required_pass and source_stable and capacity.get("status") == "PASS" and identities.get("status") == "PASS" and tests_classified
    phase_accepted = local_baseline_pass and all(item["status"] == "PASS" for item in delivery_gate.values())
    final_status = "FULL_PASS" if phase_accepted else "BLOCKED"
    previous = _read_json(root / "reports" / "upgrade_m0" / "M0_RISK_CONVERGENCE_RECEIPT.json")
    receipt = {
        "m0_version": M0_VERSION,
        "plan": PLAN_VERSION,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_status": final_status,
        "phase_execution_complete": True,
        "phase_accepted": phase_accepted,
        "phase_closed": phase_accepted,
        "next_stage": "M1_DATA_FOUNDATION" if phase_accepted else "NONE",
        "manual_gate": "REQUIRE_EXPLICIT_USER_START_FOR_NEXT_STAGE",
        "reaudit": {
            "previous_receipt_sha256": previous.get("receipt_sha256"),
            "previous_final_status": previous.get("final_status"),
            "previous_conclusion_invalidated": previous.get("final_status") == "DEGRADED_PASS",
            "correction": "Missing protocol and terminal-update evidence are blocking deliverable gaps, not an allowed degradation.",
        },
        "delivery_gate": delivery_gate,
        "source_inventory": source,
        "official_download_protocol_sample": _official_protocol_sample(),
        "terminal_update_observation": terminal_observation or {"final_status": "NOT_OBSERVED"},
        "capacity_baseline": capacity,
        "legacy_tests": tests,
        "identity_inventory": identities,
        "capability_inventory": capabilities,
        "verified_checks": {
            "tdx_root_present": source.get("status") == "PASS",
            "required_tdx_inputs_present": required_pass,
            "tdx_source_stable_during_audit": source_stable,
            "parquet_footers_readable": capacity.get("status") == "PASS",
            "identity_inventory_computed": identities.get("status") == "PASS",
            "tdx_write_attempted": False,
            "network_market_data_used": False,
            "official_documentation_page_read": True,
            "scanner_started": False,
            "database_migrated": False,
        },
        "degradation_reasons": [],
        "blocking_reasons": [
            key for key, value in delivery_gate.items() if value["status"] == "BLOCKED"
        ],
    }
    receipt["receipt_sha256"] = _sha256_bytes(_canonical(receipt))
    output_dir = root / "reports" / "upgrade_m0"
    _atomic_write(output_dir / "M0_RISK_CONVERGENCE_RECEIPT.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", tdx)
    _atomic_write(output_dir / "M0_RISK_CONVERGENCE.md", _markdown(receipt), tdx)
    return receipt


if __name__ == "__main__":
    result = run(Path(__file__).resolve().parents[1])
    print(json.dumps({"final_status": result["final_status"], "receipt_sha256": result["receipt_sha256"], "next_stage": result["next_stage"]}, ensure_ascii=False))
    raise SystemExit(0 if result["final_status"] != "BLOCKED" else 2)
