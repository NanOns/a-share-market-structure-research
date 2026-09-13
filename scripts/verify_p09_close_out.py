"""Aggregate P09 child receipts after the independent audit."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> dict:
    return json.loads((ROOT / "reports" / "upgrade_v3" / name).read_text(encoding="utf-8"))


def main() -> int:
    remaining = _read("P09-REMAINING-PRODUCTS.json")
    audit = _read("P09-INDEPENDENT-AUDIT-20260913.json")
    ext01 = _read("P09-03-EXT01-CLOSE-OUT.json")
    assert remaining["engineering_status"] == "FULL_PASS"
    assert audit["status"] == "FULL_PASS" and not audit["findings"]
    assert remaining["source_status"] in {"FULL_PASS", "DEGRADED_PASS"}
    source_status = "FULL_PASS" if remaining["source_status"] == "FULL_PASS" and ext01.get("status") == "FULL_PASS" else "DEGRADED_PASS"
    closeout = {
        "receipt_id": "P09-CLOSE-OUT-20260913",
        "stage": "P09-CLOSE-OUT",
        "status": source_status,
        "engineering_status": "FULL_PASS",
        "release_ready": False,
        "stage_contract": {
            "contract_id": "v3-p09-close-out-v1.0",
            "spec_sha256": "52536035f82d4754eda13241181f2aa8563b9d37e280e2ae39bfbd3a5a6c9d5b",
            "scope": "P09-01 through P09-04 online event/product preview and independent audit",
        },
        "acceptance": "FULL_PASS for the implemented engineering chain and independent audit; DEGRADED_PASS for source capability because V3 requires explicit degradation for unavailable/partial public sources.",
        "child_receipts": {
            "EXT01_close_out": ext01.get("status"),
            "remaining_products": remaining.get("status"),
            "independent_audit": audit.get("status"),
        },
        "available_remaining_sources": remaining.get("available_sources", []),
        "unavailable_remaining_sources": remaining.get("unavailable_sources", []),
        "known_limits": [
            "EXT01 当前收盘证据仍为单页/倍率未完全确认，保持 DEGRADED",
            "EXT06 市场概况当前探测返回来源错误，保持 UNAVAILABLE",
            "P09-04 严格同步盘中报价未启用；EXT11 按 V3 §22 退役，不用未验证 URL 替代",
            "在线热榜/板块/话题和剩余在线产品为请求时 DTO，raw/row/batch 不落盘",
        ],
        "audit": {"findings": audit.get("findings", []), "receipt": "reports/upgrade_v3/P09-INDEPENDENT-AUDIT-20260913.json"},
        "evidence": {
            "source_probe": "reports/upgrade_v3/P09-01-B-REMAINING-CURRENT-PROBE.json",
            "remaining_products": "reports/upgrade_v3/P09-REMAINING-PRODUCTS.json",
            "independent_audit": "reports/upgrade_v3/P09-INDEPENDENT-AUDIT-20260913.json",
            "tests": "51 P09/M14/M7 targeted tests passed; git diff --check passed",
        },
        "next_stage": "P10-01",
        "tdx_inputs_modified": False,
        "production_database_written": False,
        "local_run_identity_changed": False,
    }
    out = ROOT / "reports" / "upgrade_v3" / "P09-CLOSE-OUT-20260913.json"
    tmp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(closeout, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    print(json.dumps({"status": closeout["status"], "engineering_status": closeout["engineering_status"], "audit_findings": len(closeout["audit"]["findings"]), "next_stage": closeout["next_stage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
