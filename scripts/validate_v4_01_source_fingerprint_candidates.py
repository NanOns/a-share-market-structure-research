from __future__ import annotations

"""Run a label-blinded offline validation of V4-01 source fingerprints."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v4_01.source_fingerprint_candidate import analyze_source_fingerprint  # noqa: E402


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    payload = gzip.decompress(raw) if path.suffix == ".gz" else raw
    return json.loads(payload.decode("utf-8")), payload


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["evaluation"]
    lines = [
        "# V4-01 通用源级指纹候选器｜标签盲测 R1",
        "",
        f"- 阶段合同：`{report['contract_id']} v{report['contract_version']}`",
        f"- 阶段验收：`{report['acceptance_result']}`",
        f"- 样本：正样本 {metrics['positive_count']}，合并后继反例 {metrics['negative_count']}",
        f"- 候选检测：TP={metrics['true_positive']}，FN={metrics['false_negative']}，FP={metrics['false_positive']}，TN={metrics['true_negative']}",
        "- 适用边界：本结果只验证冻结的小样本候选信号；不验证通用 SAME_ENTITY 规则，不清除 V4-01 Gate A。",
        "- 生产 identity 变更授权：`false`",
        "",
        "## 冻结的盲测结果",
        "",
        "| Case | 代码对 | 有效日 | 新代码含旧史 | Bao 有效日严格一致率 | 完全相同的同日 bar | 检测输出 | 揭盲标签 |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for case in report["cases"]:
        outcome = "命中" if case["evaluation_match"] else "未命中"
        features = case["features"]
        active_ratio = features["baostock_active_exact_ratio"]
        active_match = (
            f"{features['baostock_active_exact_business_days']}/"
            f"{features['baostock_pre_effective_active_both_days']} "
            f"({active_ratio:.2%})"
            if active_ratio is not None else "N/A"
        )
        lines.append(
            f"| {case['case_id']} | `{case['old_code']} → {case['new_code']}` | "
            f"{case['effective_date']} | old TDX={features['old_tdx_file_present']}; "
            f"new TDX backfill={features['new_tdx_pre_effective_history']}; "
            f"BaoStock backfill={features['baostock_new_query_backfills_pre_effective_history']} | "
            f"{active_match} | {features['duplicate_identical_bar_days']} | `{case['disposition']}` | "
            f"`{case['expected_outcome']}` ({outcome}) |"
        )
    lines.extend([
        "",
        "## 判别规则",
        "",
        "- TDX 语义重叠比较 OHLC、amount、volume；`reserved` 和 raw 32-byte prefix 仅保留作描述，不能单独否定业务历史连续性。",
        "- BaoStock 只在两边 `tradestatus=0` 时，将 volume/amount 的空值与数值零作为表示差异归一；真实交易日金额仍严格比较，不设置金额容差。",
        "- 满足有效日之前的新代码回填、至少 20 个双边有效交易历史日且严格业务字段匹配率不低于 99%，并同时具备 TDX 历史信号及无实质冲突时，产生强候选。阈值仅为研究参数。",
        "- 双代码同日返回逐字段相同的真实交易 bar 记作 provider alias duplicate；只有业务字段不同的双边真实 bar 才触发冲突。",
        "- 输出永不自动合并 identity。正式 SAME_ENTITY 仍要求独立官方或经版本化接受的证据。",
        "- 原始输入报告的旧 classifier 结果仅用于追溯；本轮 detector 不读取该字段，而是从冻结的原始 TDX/BaoStock 证据重新计算。",
        "",
        "## 解释与限制",
        "",
        report["limitations"],
        "",
        "## 证据摘要",
        "",
        f"- Contract SHA-256：`{report['contract_sha256']}`",
        f"- 候选器模块 SHA-256：`{report['candidate_detector_module_sha256']}`；评估器 SHA-256：`{report['validation_script_sha256']}`。",
        f"- 样本清单 SHA-256：`{report['case_manifest_sha256']}`",
        f"- 揭盲标签 SHA-256：`{report['label_manifest_sha256']}`",
        f"- 最新 V4-01 owner receipt：`{report['baseline']['latest_v4_01_owner_receipt_status']}`；SHA-256 `{report['baseline']['latest_v4_01_owner_receipt_sha256']}`。",
        f"- 外部验收文件 SHA-256：`{report['baseline']['external_acceptance_review_sha256']}`。",
        f"- BaoStock request ledger SHA-256：`{report['request_ledger']['sha256']}`；2026-09-29 请求计数 {report['request_ledger']['shanghai_day_count']}。",
        "- 完整冻结 BaoStock 原始行位于压缩 JSON 输入；每个输入的压缩与解压后 SHA-256 见 JSON 收据。",
        f"- 下一阶段：`{report['next_stage']}`",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "config/v4_01_source_fingerprint_blind_cases_v1.json")
    parser.add_argument("--labels", type=Path, default=ROOT / "config/v4_01_source_fingerprint_blind_labels_v1.json")
    parser.add_argument("--contract", type=Path, default=ROOT / "config/v4_01_source_fingerprint_candidate_v1.json")
    parser.add_argument("--json-output", type=Path, default=ROOT / "reports/v4_01/V4_01_SOURCE_FINGERPRINT_CANDIDATE_BLIND_VALIDATION_R1.json")
    parser.add_argument("--markdown-output", type=Path, default=ROOT / "docs/audits/V4_01_SOURCE_FINGERPRINT_CANDIDATE_BLIND_VALIDATION_R1.md")
    args = parser.parse_args()
    cases_path = args.cases.resolve()
    labels_path = args.labels.resolve()
    contract_path = args.contract.resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    case_manifest = json.loads(cases_path.read_text(encoding="utf-8"))
    r8_receipt_path = ROOT / "reports/v4_01/v4_01_final_stage_receipt_R8_3_20260928.json"
    r8_receipt = json.loads(r8_receipt_path.read_text(encoding="utf-8"))
    upgrade_path = ROOT / "docs/evidence/V4_PRE03_JOINT_FINAL_SEAL_TASK_R1_20260927.md"
    external_review_path = ROOT / "docs/evidence/V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_EXTERNAL_ACCEPTANCE_20260929.md"

    # Detector pass: expected labels are not opened until all case outputs are frozen in memory.
    predictions: list[dict[str, Any]] = []
    for item in case_manifest["cases"]:
        report_path = (ROOT / item["diagnostic_report"]).resolve()
        diagnostic, raw_json = load_json(report_path)
        detector = analyze_source_fingerprint(diagnostic, contract)
        predictions.append({
            "case_id": item["case_id"],
            "diagnostic_report": str(report_path.relative_to(ROOT)).replace("\\", "/"),
            "diagnostic_report_compressed_sha256": sha256_file(report_path),
            "diagnostic_report_json_sha256": sha256_bytes(raw_json),
            "source_tdx_unchanged": diagnostic.get("execution_identity", {}).get("tdx_sources_unchanged") is True,
            "request_count_delta": diagnostic.get("baostock", {}).get("request_budget", {}).get("request_count_delta"),
            "old_code": detector["old_code"],
            "new_code": detector["new_code"],
            "effective_date": detector["effective_date"],
            "captured_report_classifier_output": diagnostic.get("conclusion", {}).get("pattern_class"),
            "captured_report_classifier_used_by_detector": False,
            **detector,
        })

    labels_doc = json.loads(labels_path.read_text(encoding="utf-8"))
    labels = {item["case_id"]: item for item in labels_doc["labels"]}
    if set(labels) != {item["case_id"] for item in predictions}:
        raise SystemExit("BLIND_CASE_LABEL_SET_MISMATCH")

    true_positive = false_negative = false_positive = true_negative = 0
    cases: list[dict[str, Any]] = []
    for prediction in predictions:
        label = labels[prediction["case_id"]]
        predicted = prediction["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"
        expected = bool(label["positive_for_fingerprint_candidate"])
        if predicted and expected:
            true_positive += 1
        elif not predicted and expected:
            false_negative += 1
        elif predicted and not expected:
            false_positive += 1
        else:
            true_negative += 1
        source_evidence = []
        for evidence in label.get("source_evidence", []):
            capture = (ROOT / evidence["repository_capture_path"]).resolve()
            actual_sha = sha256_file(capture) if capture.is_file() else None
            source_evidence.append({
                **evidence,
                "capture_exists": capture.is_file(),
                "capture_hash_matches": actual_sha == evidence["sha256"],
            })
        cases.append({
            **prediction,
            "expected_outcome": label["expected_outcome"],
            "positive_for_fingerprint_candidate": expected,
            "predicted_positive": predicted,
            "evaluation_match": predicted == expected,
            "source_evidence": source_evidence,
        })

    positive_count = sum(bool(label["positive_for_fingerprint_candidate"]) for label in labels.values())
    negative_count = len(labels) - positive_count
    sources_verified = all(
        evidence["capture_exists"] and evidence["capture_hash_matches"]
        for case in cases for evidence in case["source_evidence"]
    )
    source_immutable = all(case["source_tdx_unchanged"] for case in cases)
    blind_match = false_negative == 0 and false_positive == 0
    bounded_set_complete = positive_count >= 2 and negative_count >= 2 and sources_verified and source_immutable
    acceptance = "PASS_BOUNDED_BLIND_VALIDATION" if blind_match and bounded_set_complete else "BLOCKED_VALIDATION_OR_EVIDENCE_GAP"

    ledger_path = ROOT / "reports/v4_baostock/request_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    shanghai_day = ledger.get("by_shanghai_date", {}).get("2026-09-29", {})
    report: dict[str, Any] = {
        "contract_id": contract["contract_id"],
        "contract_version": contract["version"],
        "stage": contract["stage"],
        "acceptance_result": acceptance,
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "input_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "baseline": {
            "latest_v4_01_owner_receipt_path": str(r8_receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "latest_v4_01_owner_receipt_sha256": sha256_file(r8_receipt_path),
            "latest_v4_01_owner_receipt_status": r8_receipt.get("status"),
            "latest_applicable_upgrade_document_path": str(upgrade_path.relative_to(ROOT)).replace("\\", "/"),
            "latest_applicable_upgrade_document_sha256": sha256_file(upgrade_path),
            "external_acceptance_review_path": str(external_review_path.relative_to(ROOT)).replace("\\", "/") if external_review_path.is_file() else None,
            "external_acceptance_review_sha256": sha256_file(external_review_path) if external_review_path.is_file() else None,
        },
        "contract_path": str(contract_path.relative_to(ROOT)).replace("\\", "/"),
        "contract_sha256": sha256_file(contract_path),
        "candidate_detector_module_path": "src/v4_01/source_fingerprint_candidate.py",
        "candidate_detector_module_sha256": sha256_file(ROOT / "src/v4_01/source_fingerprint_candidate.py"),
        "validation_script_path": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "validation_script_sha256": sha256_file(Path(__file__).resolve()),
        "case_manifest_path": str(cases_path.relative_to(ROOT)).replace("\\", "/"),
        "case_manifest_sha256": sha256_file(cases_path),
        "label_manifest_path": str(labels_path.relative_to(ROOT)).replace("\\", "/"),
        "label_manifest_sha256": sha256_file(labels_path),
        "label_blinding": {
            "detector_function_called_before_label_file_open": True,
            "labels_used_by_detector": False,
            "independent_external_reviewer_blinding": False
        },
        "cases": cases,
        "evaluation": {
            "case_count": len(cases),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "true_positive": true_positive,
            "false_negative": false_negative,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "all_cases_match": blind_match,
            "all_source_captures_hash_verified": sources_verified,
            "tdx_sources_unchanged_for_all_cases": source_immutable,
        },
        "stage_contract": {
            "identity_mutation": False,
            "historical_universe_mutation": False,
            "production_integration": False,
            "TDX_read_only": True,
            "BaoStock_raw_payload_retained": True,
            "candidate_only": True,
            "independent_confirmation_required": True,
            "current_v4_01_owner_gate_cleared": False,
            "current_v4_01_owner_gate_status": r8_receipt.get("status"),
        },
        "request_ledger": {
            "path": "reports/v4_baostock/request_ledger.json",
            "sha256": sha256_file(ledger_path),
            "shanghai_day_count": int(shanghai_day.get("count", 0)),
            "operations": shanghai_day.get("operations", {}),
            "case_request_count_delta": sum(int(case["request_count_delta"] or 0) for case in cases),
        },
        "limitations": (
            "The four-case set contains two officially documented pure code-renumbering positives and two merger-successor negative controls. "
            "It is label-separated from detector execution but not independently blinded to an external reviewer. "
            "Only one positive has both local old/new TDX files for paired semantic overlap; the 0.95 TDX volume research threshold is therefore not calibrated. "
            "The result does not estimate market-wide false-positive/false-negative rates and does not establish a SAME_ENTITY confirmation rule."
        ),
        "next_stage": "EXPAND_INDEPENDENT_BLIND_SET_WITH_MORE_PAIRED_TDX_CASES_AND_REASSESS_RESEARCH_THRESHOLDS; KEEP_PRODUCTION_IDENTITY_UNCHANGED",
    }
    markdown = render_markdown(report).encode("utf-8")
    report["validation_summary_path"] = str(args.markdown_output.resolve().relative_to(ROOT)).replace("\\", "/")
    report["validation_summary_sha256"] = sha256_bytes(markdown)
    atomic_json(args.json_output.resolve(), report)
    atomic_bytes(args.markdown_output.resolve(), markdown)
    print(json.dumps({
        "acceptance_result": acceptance,
        "evaluation": report["evaluation"],
        "request_ledger": report["request_ledger"],
        "json_output": str(args.json_output.resolve()),
        "markdown_output": str(args.markdown_output.resolve()),
    }, ensure_ascii=False, indent=2))
    return 0 if acceptance == "PASS_BOUNDED_BLIND_VALIDATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
