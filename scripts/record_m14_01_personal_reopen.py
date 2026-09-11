"""Record the explicit, personal-only reopening of the M14 local branch."""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/M14_PERSONAL_RESEARCH_REOPEN_CONTRACT_V1.md"
PREVIOUS = ROOT / "reports/upgrade_m14/m14_01_review_receipt_20260911.json"
REGISTRY = ROOT / "config/m14_source_registry_v1.json"
RECEIPT = ROOT / "reports/upgrade_m14/m14_01_personal_reopen_receipt_20260911.json"


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    production_rejected = all(item["enabled"] is False and item["status"] == "REJECTED" for item in registry["source_candidates"])
    receipt = {
        "receipt_id": "M14-01-REOPEN-PERSONAL-20260911",
        "stage": "M14-01-REOPEN-PERSONAL",
        "contract_id": "M14_PERSONAL_RESEARCH_REOPEN_V1_0",
        "contract": "docs/M14_PERSONAL_RESEARCH_REOPEN_CONTRACT_V1.md",
        "previous_receipt": "reports/upgrade_m14/m14_01_review_receipt_20260911.json",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DEGRADED_PASS" if production_rejected else "BLOCKED",
        "release_ready": False,
        "decision_basis": "USER_EXPLICIT_PERSONAL_RESEARCH_ONLY_20260911",
        "scope": "仅个人研究隔离分支复开 M14-02 批次/视图验证，不复开生产来源",
        "evidence": {
            "previous_review_status": json.loads(PREVIOUS.read_text(encoding="utf-8"))["status"],
            "production_sources_remain_rejected": production_rejected,
            "registry": "config/m14_source_registry_v1.json",
            "api37_to_40_enabled": False,
            "publication_enabled": False,
            "production_adapters_enabled": False,
            "local_snapshot_mutated": False,
        },
        "acceptance": "DEGRADED_PASS: 仅个人隔离分支复开；生产来源仍REJECTED，M14-02不得进入API/UI/发布或本地模型消费",
        "next_stage": "M14-02",
        "next_stage_contract": "docs/M14_BATCH_FOUNDATION_CONTRACT_V1.md",
        "next_stage_requires_manual_start": True,
        "bound_hashes": {
            "contract": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
            "previous_receipt": hashlib.sha256(PREVIOUS.read_bytes()).hexdigest(),
            "registry": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        },
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(RECEIPT)}, ensure_ascii=False))
    return 0 if receipt["status"] == "DEGRADED_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
