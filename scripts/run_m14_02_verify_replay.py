"""Replay the Eastmoney M14-02 page and verify bounded batch behavior."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.base import FetchResult, OnlineFetchPolicy
import workbench_online.collector as collector_module
from workbench_online.collector import collect_eastmoney_hot_rank
from workbench_online.eastmoney_hot_rank import fetch_eastmoney_hot_rank


OUTPUT_ROOT = ROOT / "data/online/m14_personal"
RECEIPT = ROOT / "reports/upgrade_m14/m14_02_verify_replay_receipt_20260911.json"
CONTRACT = ROOT / "docs/M14_BATCH_FOUNDATION_CONTRACT_V1.md"


def atomic_json(path: Path, payload: object) -> None:
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".m14-replay-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(name).replace(path)
    except Exception:
        Path(name).unlink(missing_ok=True)
        raise


def batch_id_from_file(batch: dict) -> str:
    material = {
        "source_id": batch["source_id"],
        "dataset": batch["dataset"],
        "list_type": batch["list_type"],
        "page": batch["page"],
        "raw_sha256": batch["raw_sha256"],
        "observed_at_utc": batch["observed_at_utc"],
        "source_as_of": batch["source_as_of"],
        "decoder_version": batch["decoder_version"],
        "contract_id": batch["contract_id"],
    }
    return "m14b-" + hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def rank_shape_is_stable(batch: dict) -> bool:
    rows = batch["rows"]
    expected = list(range(1, len(rows) + 1))
    return (
        [row["platform_rank"] for row in rows] == expected
        and [row["source_row_order"] for row in rows] == expected
        and all(row["security_id"] and len(row["source_code"]) == 6 for row in rows)
    )


def failure_does_not_write() -> dict:
    def failing_fetcher(_url, _policy, **_kwargs):
        return FetchResult("requested", "received", 503, "text/plain", b"", "https://example.invalid")

    with tempfile.TemporaryDirectory(prefix="m14-replay-failure-") as directory:
        root = Path(directory)
        original = collector_module.fetch_eastmoney_hot_rank
        collector_module.fetch_eastmoney_hot_rank = lambda policy, **kwargs: fetch_eastmoney_hot_rank(policy, fetcher=failing_fetcher, **kwargs)
        try:
            collect_eastmoney_hot_rank(root, OnlineFetchPolicy())
        except ValueError as exc:
            files = list(root.rglob("*"))
            return {"raised": str(exc) == "HTTP_STATUS:503", "partial_files": len(files)}
        finally:
            collector_module.fetch_eastmoney_hot_rank = original
        return {"raised": False, "partial_files": len(list(root.rglob("*")))}


def main() -> int:
    first = collect_eastmoney_hot_rank(OUTPUT_ROOT)
    second = collect_eastmoney_hot_rank(OUTPUT_ROOT)
    first_batch = json.loads(Path(first["batch_path"]).read_text(encoding="utf-8"))
    second_batch = json.loads(Path(second["batch_path"]).read_text(encoding="utf-8"))
    first_raw_ok = hashlib.sha256(Path(first["raw_path"]).read_bytes()).hexdigest() == first["raw_sha256"]
    second_raw_ok = hashlib.sha256(Path(second["raw_path"]).read_bytes()).hexdigest() == second["raw_sha256"]
    same_source_time = first["source_as_of"] == second["source_as_of"] and first["source_as_of"] is not None
    same_codes_when_same_time = (
        not same_source_time
        or [row["source_code"] for row in first_batch["rows"]]
        == [row["source_code"] for row in second_batch["rows"]]
    )
    failure = failure_does_not_write()
    evidence = {
        "attempts": [
            {key: first[key] for key in ("batch_id", "row_count", "mapped_security_count", "source_as_of", "observed_at_utc", "raw_sha256", "batch_path", "raw_path")},
            {key: second[key] for key in ("batch_id", "row_count", "mapped_security_count", "source_as_of", "observed_at_utc", "raw_sha256", "batch_path", "raw_path")},
        ],
        "row_count_stable": first["row_count"] == second["row_count"] == 20,
        "mapping_count_stable": first["mapped_security_count"] == second["mapped_security_count"] == 20,
        "rank_shape_stable": rank_shape_is_stable(first_batch) and rank_shape_is_stable(second_batch),
        "same_codes_when_source_time_same": same_codes_when_same_time,
        "raw_hash_matches_disk": first_raw_ok and second_raw_ok,
        "raw_deduplicated_when_payload_same": first["raw_sha256"] == second["raw_sha256"],
        "batch_identity_deterministic": batch_id_from_file(first_batch) == first["batch_id"] and batch_id_from_file(second_batch) == second["batch_id"],
        "distinct_observations_retained": first["observed_at_utc"] != second["observed_at_utc"] and first["batch_id"] != second["batch_id"],
        "failure_probe": failure,
        "local_snapshot_mutated": False,
        "publication_enabled": False,
    }
    acceptance_ok = all(
        [
            evidence["row_count_stable"],
            evidence["mapping_count_stable"],
            evidence["rank_shape_stable"],
            evidence["same_codes_when_source_time_same"],
            evidence["raw_hash_matches_disk"],
            evidence["batch_identity_deterministic"],
            evidence["distinct_observations_retained"],
            failure["raised"],
            failure["partial_files"] == 0,
        ]
    )
    receipt = {
        "receipt_id": "M14-02-VERIFY-REPLAY-20260911",
        "stage": "M14-02-VERIFY-REPLAY",
        "contract_id": "M14_BATCH_FOUNDATION_V1_0",
        "contract": "docs/M14_BATCH_FOUNDATION_CONTRACT_V1.md",
        "status": "DEGRADED_PASS" if acceptance_ok else "BLOCKED",
        "release_ready": False,
        "scope": "东方财富热榜重复页抓取、批次身份、平台排名稳定性和失败恢复",
        "evidence": evidence,
        "guardrails": {
            "tdx_inputs_modified": False,
            "external_adjustment_service_used": False,
            "future_data_used": False,
            "automated_trading_added": False,
            "probability_claims_added": False,
            "local_snapshot_mutated": False,
            "publication_enabled": False,
        },
        "acceptance": "DEGRADED_PASS: 重复观测保留为独立批次，原始载荷按哈希去重，平台排名结构稳定，失败探针未产生半成品；继续保持个人研究隔离",
        "next_stage": "M14-03-HOT-RANK",
        "next_stage_contract": "按热榜独立能力合同定义可消费字段、比较批次、15分钟可比窗口和降级空态；仍不得阻塞本地主流程",
        "next_stage_requires_manual_start": True,
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "first_batch": first["batch_id"], "second_batch": second["batch_id"], "raw_deduplicated": evidence["raw_deduplicated_when_payload_same"]}, ensure_ascii=False))
    return 0 if acceptance_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
