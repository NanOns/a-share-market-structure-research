"""Independent V3 P09 re-audit; preserves historical audit receipts."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
EXPECTED_SPEC_SHA256 = "52536035f82d4754eda13241181f2aa8563b9d37e280e2ae39bfbd3a5a6c9d5b"
EXPECTED_ROUTES = (
    "/api/v3/events/overview",
    "/api/v3/events/pools",
    "/api/v3/events/topics",
    "/api/v3/events/distribution",
    "/api/v3/events/topics/",
    "/api/v3/events/stocks/",
    "/api/v3/hot-rankings",
    "/api/v3/hot-plates",
    "/api/v3/hot-topics",
    "/api/v3/research/sectors/",
    "/v3/online",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    findings: list[dict[str, str]] = []
    p09 = (ROOT / "src" / "workbench_online" / "p09_products.py").read_text(encoding="utf-8")
    app = (ROOT / "src" / "workbench_service" / "app.py").read_text(encoding="utf-8")
    page = ROOT / "src" / "workbench_service" / "static" / "online-p09-v3.html"
    receipt_path = ROOT / "reports" / "upgrade_v3" / "P09-REMAINING-PRODUCTS.json"
    probe_path = ROOT / "reports" / "upgrade_v3" / "P09-01-B-REMAINING-REPROBE-20260913.json"

    if _sha(SPEC) != EXPECTED_SPEC_SHA256:
        findings.append({"severity": "BLOCKER", "code": "SPEC_HASH_DRIFT", "detail": "V3 文档哈希与阶段合同不一致"})
    for route in EXPECTED_ROUTES:
        if route not in (app if route.startswith("/api") else page.read_text(encoding="utf-8")):
            findings.append({"severity": "HIGH", "code": "ROUTE_OR_PAGE_MISSING", "detail": route})
    for forbidden in ("duckdb", "open(", "write_text", "online_batches", "online_pool_entries"):
        if forbidden in p09:
            findings.append({"severity": "HIGH", "code": "P09_MODULE_PERSISTENCE_PATH", "detail": forbidden})
    if "EXT10" in p09 or "EXT11" in p09:
        findings.append({"severity": "HIGH", "code": "RETIRED_SOURCE_IN_ADAPTER", "detail": "EXT10/EXT11"})
    if "P09_MAX_CONCURRENT = 4" not in p09 or "P09_MAX_TOTAL_SECONDS = 12.0" not in p09:
        findings.append({"severity": "HIGH", "code": "REQUEST_BUDGET_DRIFT", "detail": "P09 bounded request constants"})
    if '"raw_payload_persisted": False' not in p09 or '"rows_persisted": False' not in p09 or '"batch_persisted": False' not in p09:
        findings.append({"severity": "HIGH", "code": "NO_PERSISTENCE_EVIDENCE_MISSING", "detail": "request-time DTO persistence flags"})
    if not page.is_file():
        findings.append({"severity": "HIGH", "code": "PAGE_MISSING", "detail": str(page)})
    if not receipt_path.is_file() or not probe_path.is_file():
        findings.append({"severity": "HIGH", "code": "RECEIPT_MISSING", "detail": "P09 product/probe receipt"})

    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else {}
    probe = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path.is_file() else {}
    if receipt.get("status") != "FULL_PASS":
        findings.append({"severity": "HIGH", "code": "ENGINEERING_STATUS_NOT_FULL_PASS", "detail": str(receipt.get("status"))})
    if receipt.get("source_status") not in {"FULL_PASS", "DEGRADED_PASS"}:
        findings.append({"severity": "HIGH", "code": "SOURCE_STATUS_INVALID", "detail": str(receipt.get("source_status"))})
    requests = probe.get("requests", [])
    if any(item.get("raw_payload_persisted") or item.get("rows_persisted") or item.get("batch_persisted") for item in requests):
        findings.append({"severity": "BLOCKER", "code": "FORBIDDEN_PERSISTENCE_RECEIPTED", "detail": "probe says source data persisted"})
    if "EXT06" not in receipt.get("unavailable_sources", []) and probe.get("source_summary", {}).get("EXT06") and all(status == "UNAVAILABLE" for status in probe["source_summary"]["EXT06"]):
        findings.append({"severity": "MEDIUM", "code": "SOURCE_STATUS_SUMMARY_MISMATCH", "detail": "EXT06"})
    if re.search(r"EXT11.*https?://", app):
        # The app may mention the retired source only as an explicit status;
        # an adapter URL or network call would be a finding.
        if "no unsupported quote URL is substituted" not in app:
            findings.append({"severity": "HIGH", "code": "RETIRED_SOURCE_NETWORK_SUBSTITUTION", "detail": "EXT11"})

    # Functional evidence gates: the old route/string audit did not inspect
    # whether cross-source joins and source completeness were actually proven.
    runtime_path = ROOT / "config/p09_runtime_capabilities_v1.json"
    mapping_path = ROOT / "config/p09_topic_sector_mapping_v1.json"
    if not runtime_path.is_file():
        findings.append({"severity": "HIGH", "code": "RUNTIME_CAPABILITY_CONTRACT_MISSING", "detail": str(runtime_path)})
    else:
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        if runtime.get("contract_id") != "v3-p09-runtime-capabilities-v1.0":
            findings.append({"severity": "HIGH", "code": "RUNTIME_CAPABILITY_CONTRACT_INVALID", "detail": str(runtime.get("contract_id"))})
    mapping_receipt_path = ROOT / "reports/upgrade_v3/P09-TOPIC-SECTOR-MAPPING-20260913.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.is_file() else {}
    mapping_receipt = json.loads(mapping_receipt_path.read_text(encoding="utf-8")) if mapping_receipt_path.is_file() else {}
    if not mapping.get("entries") or mapping_receipt.get("status") != "FULL_PASS" or mapping_receipt.get("mapping_sha256") != _sha(mapping_path) or not all(item.get("pass") for item in mapping_receipt.get("checks", [])):
        findings.append({"severity": "HIGH", "code": "TOPIC_SECTOR_MAPPING_UNVERIFIED", "detail": "Versioned RELATED pairs require current source and fixed local-run overlap evidence."})
    metadata_path = probe_path
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    known_limits = []
    if not metadata.get("requests") or any(item.get("status") != "AVAILABLE" for item in metadata.get("requests", [])):
        findings.append({"severity": "HIGH", "code": "CORE_SOURCE_REPROBE_NOT_FULL", "detail": "EXT02-09 Longzijue datasets must pass the bounded reprobe."})
    for token in ("dragon_estimated_amount_yi", "CIRCULATION_VALUE_YUAN_TIMES_TURNOVER_RATIO", "def promotion", "SOURCE_YESTERDAY_LIMIT_UP_TRANSITION_POOL"):
        if token not in p09:
            findings.append({"severity": "HIGH", "code": "LONGZIJUE_PATH_MISSING", "detail": token})
    for token in ("EXT05:yesterday_limit_up", "market_overview", "v3-p09-events-overview-v1.3"):
        if token not in app:
            findings.append({"severity": "HIGH", "code": "OVERVIEW_CHAIN_MISSING", "detail": token})
    deferred_enhancements = ["Strict synchronized per-stock live quote reranking remains deferred.", "Additional topic-to-local-sector mappings remain evidence-gated RELATED links."]
    if 'href="/api/v3/events/distribution"' in page.read_text(encoding="utf-8"):
        findings.append({"severity": "MEDIUM", "code": "DISTRIBUTION_PAGE_DETAIL_INCOMPLETE", "detail": "Distribution has a raw API link, not a complete in-page drilldown."})

    status = "BLOCKED" if any(item["severity"] in {"BLOCKER", "HIGH"} for item in findings) else "FULL_PASS"
    audit = {
        "receipt_id": "P09-REAUDIT-CURRENT-20260913",
        "stage": "P09-REAUDIT-CURRENT",
        "status": status,
        "findings": findings,
        "known_limits": known_limits,
        "deferred_enhancements": deferred_enhancements,
        "engineering_status": "FULL_PASS" if not findings else "BLOCKED",
        "scope": {"spec_sha256": EXPECTED_SPEC_SHA256, "routes_checked": list(EXPECTED_ROUTES), "tdx_inputs_modified": False},
        "evidence": {"implementation": "src/workbench_online/p09_products.py + src/workbench_service/app.py", "probe": str(probe_path), "product_receipt": str(receipt_path), "page": str(page)},
        "acceptance": "FULL_PASS: Longzijue core online products, source contracts, API and page evidence gates closed." if not findings else "Open engineering findings require repair.",
        "next_stage": "P09-G09-CLOSE-OUT" if not findings else "P09-MAPPING-COVERAGE-UI-REPAIR",
    }
    out = ROOT / "reports" / "upgrade_v3" / "P09-REAUDIT-CURRENT-20260913.json"
    out_tmp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
    out_tmp.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(out_tmp, out)
    report = ROOT / "docs" / "V3_P09_REAUDIT_CURRENT_20260913.md"
    report_tmp = report.with_suffix(report.suffix + f".{os.getpid()}.tmp")
    report_tmp.write_text("# V3 P09 当前复审\n\n" + json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(report_tmp, report)
    print(json.dumps({"status": status, "finding_count": len(findings), "findings": findings}, ensure_ascii=False))
    return 0 if status in {"FULL_PASS", "DEGRADED_PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
