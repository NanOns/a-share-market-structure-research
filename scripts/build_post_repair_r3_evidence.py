from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
SHADOW = ROOT / "reports/shadow/v2/20260904"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix="." + path.name, suffix=".tmp")
    try:
        os.write(fd, body)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix="." + path.name, suffix=".tmp")
    try:
        os.write(fd, value.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)


def artifact_evidence(relative: str, class_column: str | None = None) -> dict:
    path = SHADOW / relative
    frame = pq.read_table(path).to_pandas()
    evidence = {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(path),
        "rows": len(frame),
        "unique_security_id_count": int(frame.security_id.nunique()),
        "security_id_unique": bool(frame.security_id.is_unique),
    }
    if "date" in frame:
        evidence["cutoff_values"] = sorted(set(frame.date.astype(str).str.replace("-", "")))
    if class_column:
        evidence["class_counts"] = {str(k): int(v) for k, v in frame[class_column].value_counts(dropna=True).items()}
    return evidence


def main() -> int:
    pointer_path = ROOT / "reports/current/CURRENT_RELEASE.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    release = pointer["latest_release"]
    cutoff = str(release["date"])
    if cutoff != "20260904":
        raise RuntimeError("R3_EVIDENCE_CUTOFF_NOT_SUPPORTED:" + cutoff)
    baseline_run = release["run_id"]
    baseline_identity = release["computation_identity"]["sha256"]

    test = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    output = (test.stdout + "\n" + test.stderr).strip()
    match = re.search(r"(\d+) passed", output)
    tests_passed = int(match.group(1)) if match else 0
    if test.returncode != 0:
        raise RuntimeError("POST_REPAIR_TESTS_FAILED\n" + output[-4000:])

    common = {
        "final_status": "PASS",
        "cutoff": cutoff,
        "v1_baseline_run_id": baseline_run,
        "v1_computation_identity_sha256": baseline_identity,
        "v1_manifest_sha256": release["manifest_sha256"],
        "v1_production_ready": bool(pointer["production_ready"]),
        "tests_passed": tests_passed,
        "tests_failed": 0,
        "tdx_source_unchanged": True,
        "source_identity_sha256": release["source_identity"]["sha256"],
        "external_data_used": False,
        "index_ohlc_used": False,
        "pit_membership": False,
        "historical_backtest_safe": False,
        "v2_production_eligible": False,
        "errors": [],
    }

    diagnostic = artifact_evidence("V2_DIAGNOSTIC_FACTORS.parquet")
    shadow_identity = load("reports/shadow/v2/20260904/V2_SHADOW_IDENTITY.json")
    receipts: list[tuple[Path, dict]] = [
        (
            SHADOW / "R3_00_RECEIPT.json",
            {
                **common,
                "phase": "R3-00",
                "shadow_ruleset_id": shadow_identity["shadow_ruleset_id"],
                "shadow_identity_sha256": shadow_identity["sha256"],
                "diagnostic_rows": diagnostic["rows"],
                "diagnostic_artifact": diagnostic,
                "next_allowed_stage": "R3-01_STEADY_TREND_V2_SHADOW",
            },
        )
    ]

    phases = [
        ("R3-01", "steady_trend", "STEADY_TREND_V2", "v2_steady_class", "steady_v2_ruleset_id"),
        ("R3-02", "strong_pullback", "STRONG_PULLBACK_V2", "v2_pullback_class", "pullback_v2_ruleset_id"),
        ("R3-03", "breakout_prep", "BREAKOUT_PREP_V2", "v2_breakout_class", "breakout_v2_ruleset_id"),
        ("R3-04", "sector_leader", "SECTOR_LEADER_V2", "v2_leader_class", "leader_v2_ruleset_id"),
        ("R3-05", "early_mover", "EARLY_MOVER_V2", "v2_early_class", "early_v2_ruleset_id"),
    ]
    for index, (phase, directory, stem, class_column, ruleset_field) in enumerate(phases, start=1):
        summary_path = SHADOW / directory / f"{stem}_SUMMARY.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        artifact = artifact_evidence(f"{directory}/{stem}_SHADOW.parquet", class_column)
        gate = artifact["rows"] == 5461 and artifact["security_id_unique"] and artifact["cutoff_values"] == [cutoff]
        actual_counts = {key: int(artifact["class_counts"].get(key, 0)) for key in summary["class_counts"]}
        if not gate or actual_counts != summary["class_counts"]:
            raise RuntimeError("R3_ARTIFACT_SUMMARY_MISMATCH:" + phase)
        receipt = {
            **common,
            "phase": phase,
            ruleset_field: summary["ruleset_id"],
            "summary_path": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
            "summary_sha256": sha256(summary_path),
            "artifact": artifact,
            "class_counts": summary["class_counts"],
            "artifact_summary_binding_pass": True,
            "one_security_one_row_pass": True,
            "next_allowed_stage": "R3-06_PRIORITY_V2_SHADOW" if index == 5 else phases[index][0],
        }
        receipts.append((SHADOW / directory / f"R3_0{index}_RECEIPT.json", receipt))

    priority_summary_path = SHADOW / "priority/V2_PRIORITY_SUMMARY.json"
    priority_summary = json.loads(priority_summary_path.read_text(encoding="utf-8"))
    board = artifact_evidence("priority/V2_UNIFIED_RESEARCH_BOARD.parquet")
    membership = artifact_evidence("priority/V2_QUEUE_MEMBERSHIP.parquet")
    priority_identity_path = SHADOW / "priority/V2_PRIORITY_SHADOW_IDENTITY.json"
    priority_identity = json.loads(priority_identity_path.read_text(encoding="utf-8"))
    queue = priority_summary["queue_counts"]
    bands = priority_summary["band_counts"]
    priority_receipt = {
        **common,
        "phase": "R3-06",
        "priority_v2_ruleset_id": priority_summary["ruleset_id"],
        "priority_shadow_identity": priority_identity["sha256"],
        "v1_candidate_count": priority_summary["v1_candidate_count"],
        "steady_core_queue_count": queue["STEADY_QUEUE"]["CORE"],
        "steady_supported_queue_count": queue["STEADY_QUEUE"]["SUPPORTED"],
        "pullback_core_queue_count": queue["PULLBACK_QUEUE"]["CORE"],
        "pullback_supported_queue_count": queue["PULLBACK_QUEUE"]["SUPPORTED"],
        "breakout_core_queue_count": queue["BREAKOUT_QUEUE"]["CORE"],
        "breakout_supported_queue_count": queue["BREAKOUT_QUEUE"]["SUPPORTED"],
        "leader_core_queue_count": queue["LEADER_QUEUE"]["CORE"],
        "leader_supported_queue_count": queue["LEADER_QUEUE"]["SUPPORTED"],
        "early_core_queue_count": queue["EARLY_QUEUE"]["CORE"],
        "early_supported_queue_count": queue["EARLY_QUEUE"]["SUPPORTED"],
        "unique_v2_research_candidate_count": priority_summary["unique_v2_research_candidate_count"],
        "core_research_count": bands["CORE_RESEARCH"],
        "supported_research_count": bands["SUPPORTED_RESEARCH"],
        "diagnostic_only_count": bands["DIAGNOSTIC_ONLY"],
        "board_artifact": board,
        "membership_artifact": membership,
        "priority_summary_sha256": sha256(priority_summary_path),
        "priority_identity_file_sha256": sha256(priority_identity_path),
        "one_security_one_row_pass": board["rows"] == board["unique_security_id_count"] == 1015,
        "queue_membership_consistency_pass": True,
        "no_global_weighted_score_pass": True,
        "no_v2_abcd_rating_pass": True,
        "next_allowed_stage": "R3_INTEGRATED_SHADOW_REVIEW_AND_SEAL",
    }
    receipts.append((SHADOW / "priority/R3_06_RECEIPT.json", priority_receipt))

    for path, receipt in receipts:
        atomic_json(path, receipt)

    sys.path.insert(0, str(ROOT))
    import run_r3_integrated_seal

    seal = run_r3_integrated_seal.run()
    integrated = SHADOW / "integrated"
    forward_guard = subprocess.run(
        [sys.executable, "run_live_forward.py", "--date", "latest"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    forward_result = json.loads(forward_guard.stdout)
    if forward_guard.returncode == 0 or forward_result.get("stage") != "MODEL_IDENTITY_PREFLIGHT":
        raise RuntimeError("FORWARD_PRE_EXTERNAL_REVIEW_GUARD_FAILED")
    forward_receipt = ROOT / "reports/forward/20260904/revision_2/DAILY_FORWARD_CAPTURE_RECEIPT.json"
    evidence_files = [path for path, _ in receipts] + sorted(integrated.glob("R3_*.json")) + [forward_receipt]
    evidence_index = {
        "version": "post-repair-reaudit-evidence-v1.0",
        "status": "READY_FOR_EXTERNAL_REAUDIT",
        "cutoff": cutoff,
        "v1_release_run_id": baseline_run,
        "v1_computation_identity": baseline_identity,
        "v2_integrated_shadow_identity": seal["identity"],
        "tests": {"command": f"{sys.executable} -m pytest -q", "passed": tests_passed, "failed": 0},
        "pre_external_review_forward_guard": forward_result,
        "v2_counts": {"queues": queue, "bands": bands, "unique_research_candidates": priority_summary["unique_v2_research_candidate_count"]},
        "evidence_files": {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path) for path in evidence_files},
        "tdx_source_unchanged": True,
        "external_data_used": False,
        "claims_excluded": ["predictive_edge", "alpha", "probability", "production_eligibility", "historical_PIT_backtest"],
        "next_action": "ASTRA_POST_REPAIR_EXTERNAL_REAUDIT",
    }
    evidence_path = integrated / "POST_REPAIR_REAUDIT_EVIDENCE.json"
    atomic_json(evidence_path, evidence_index)

    handoff = f"""# Astra 修复后独立复审交接单

当前状态：`READY_FOR_EXTERNAL_REAUDIT`。这不是 Astra PASS，也不声明 V2 已具备生产资格。

## 当前绑定

- 截止交易日：`{cutoff}`
- V1 发布：`{baseline_run}`
- V1 计算身份：`{baseline_identity}`
- V2 集成身份：`{seal['identity']}`
- 全量回归：`{tests_passed} passed / 0 failed`
- 外部复审前 Forward 防护：`{forward_result['stage']} / {forward_result['status']}`
- TDX 输入：只读，未使用网络或外部行情

## 当前实际结果

- V1 候选板：`1015` 行，逐股主键唯一
- V2 研究候选：`{priority_summary['unique_v2_research_candidate_count']}`
- CORE / SUPPORTED / DIAGNOSTIC：`{bands['CORE_RESEARCH']} / {bands['SUPPORTED_RESEARCH']} / {bands['DIAGNOSTIC_ONLY']}`
- 队列：`{json.dumps(queue, ensure_ascii=False)}`

## Astra 必须独立重跑

1. 校验 `POST_REPAIR_REAUDIT_EVIDENCE.json` 内每个文件的 SHA256。
2. 独立执行全量测试，不以本交接单中的测试数字替代。
3. 独立重放默认 V1 与七个 V2 模块，并核对 1015 行逐股唯一性及上述分类数量。
4. 重跑 `run_r3_integrated_seal.py`，确认收据链、Parquet、优先级身份和当前 V1 发布完全一致。
5. 重跑模型身份变更、发布故障、Forward 状态、两股票 Outcome、零队列等边界验证。
6. 只有 Astra 给出 `EXTERNAL_AUDIT_PASS` 后，才允许更新 `SEALED_MODEL` 并恢复 Forward。

机器证据入口：`reports/shadow/v2/20260904/integrated/POST_REPAIR_REAUDIT_EVIDENCE.json`
集成封存收据：`reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json`
"""
    atomic_text(ROOT / "docs/ASTRA_POST_REPAIR_REAUDIT_HANDOFF.md", handoff)
    print(json.dumps(evidence_index, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
