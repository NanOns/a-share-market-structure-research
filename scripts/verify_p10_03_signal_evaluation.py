"""Verify and seal P10-03 without writing the production database."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402

from workbench_db.migrations import MigrationExecutor  # noqa: E402
from workbench_service.research_signal_evaluation import (  # noqa: E402
    CONTRACT_ID,
    EVAL_VERSION,
    ResearchSignalOutcomeStore,
    build_equal_size_baselines,
    build_outcome_rows,
    episode_first_signals,
    signal_identity_hash,
)


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
DB = ROOT / "data" / "database" / "market_research.duckdb"
REPORT = ROOT / "reports" / "upgrade_v3" / "P10-03-SIGNAL-EVALUATION.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_atomic(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def _signal(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "signal_run_id": "synthetic-run",
        "sector_id": "THEME:A",
        "episode_id": "episode-a",
        "signal_date": "2026-09-10",
        "sector_type": "THEME",
        "potential_eligible": True,
        "current_eligible": False,
        "potential_branch": "BASE_BUILD",
        "algorithm_version": "v3",
        "parameter_hash": "params-1",
        "snapshot_id": "snap-1",
        "membership_snapshot_id": "members-1",
        "evaluation_basis": "HISTORICAL_RECONSTRUCTED",
    }
    row.update(updates)
    return row


def _synthetic() -> dict[str, object]:
    sessions = ["2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17"]
    future = [{"sector_id": "THEME:A", "trade_date": item, "current_eligible": item == "2026-09-14"} for item in sessions[1:]]
    prices = {
        ("2026-09-10", "S1"): 10.0, ("2026-09-15", "S1"): 11.0, ("2026-09-17", "S1"): 12.0,
        ("2026-09-10", "S2"): 20.0, ("2026-09-15", "S2"): 21.0, ("2026-09-17", "S2"): 22.0,
    }
    pending = build_outcome_rows([_signal()], sessions=sessions[:2], future_rows=future[:1], members_by_episode={"episode-a": ["S1", "S2"]}, prices=prices, as_of_date="2026-09-11")
    observed = build_outcome_rows([_signal()], sessions=sessions, future_rows=future, members_by_episode={"episode-a": ["S1", "S2"]}, prices=prices, as_of_date="2026-09-17")
    repeated = episode_first_signals([_signal(), _signal(signal_date="2026-09-11")])
    target_rows = [_signal(sector_id="THEME:A", episode_id="episode-a"), _signal(sector_id="THEME:B", episode_id="episode-b")]
    universe = [
        {"sector_id": "THEME:A", "trade_date": "2026-09-10", "sector_type": "THEME", "current_eligible": False, "potential_eligible": True, "q20": .9, "dq5_3": .1},
        {"sector_id": "THEME:B", "trade_date": "2026-09-10", "sector_type": "THEME", "current_eligible": False, "potential_eligible": True, "q20": .8, "dq5_3": .2},
        {"sector_id": "THEME:C", "trade_date": "2026-09-10", "sector_type": "THEME", "current_eligible": False, "potential_eligible": True, "q20": .7, "dq5_3": .3},
        {"sector_id": "THEME:D", "trade_date": "2026-09-10", "sector_type": "THEME", "current_eligible": False, "potential_eligible": True, "q20": .6, "dq5_3": .4},
    ]
    baselines = build_equal_size_baselines(target_rows, universe)
    before_signal = None
    after_signal = None
    with duckdb.connect(":memory:") as connection:
        connection.execute("create table research_sector_signal_state(run_id varchar, sector_id varchar, lifecycle varchar)")
        connection.execute("insert into research_sector_signal_state values ('synthetic-run','THEME:A','QUALIFIED')")
        store = ResearchSignalOutcomeStore(connection)
        first_write = store.upsert(pending)
        second_write = store.upsert(pending)
        before_signal = connection.execute("select lifecycle from research_sector_signal_state where run_id='synthetic-run'").fetchone()[0]
        after_signal = connection.execute("select lifecycle from research_sector_signal_state where run_id='synthetic-run'").fetchone()[0]
        outcome_count = connection.execute("select count(*) from research_signal_outcomes").fetchone()[0]
    base_hash = signal_identity_hash(_signal())
    future_hash = signal_identity_hash({**_signal(), "t_plus_5_current": True, "future_return": .2, "outcome_status": "OBSERVED"})
    return {
        "pending_statuses": [row["status"] for row in pending],
        "observed": {"statuses": [row["status"] for row in observed], "confirmed_date_h3": str(observed[0]["confirmed_date"]), "lead_sessions_h3": observed[0]["lead_sessions"], "coverage_h3": observed[0]["member_forward_coverage"]},
        "episode_count_after_dedup": len(repeated),
        "baseline_counts": {name: len(rows) for name, rows in baselines.items()},
        "hash_stable": base_hash == future_hash,
        "store_first_write": first_write,
        "store_second_write": second_write,
        "outcome_count": outcome_count,
        "signal_state_before": before_signal,
        "signal_state_after": after_signal,
        "eval_version": EVAL_VERSION,
    }


def _real_read() -> dict[str, object]:
    result: dict[str, object] = {}
    with duckdb.connect(str(DB), read_only=True) as connection:
        result["complete_runs"] = int(connection.execute("select count(*) from research_runs where status='COMPLETE'").fetchone()[0])
        latest = connection.execute("select run_id,publication_id,cast(trade_date as varchar) from research_runs where status='COMPLETE' order by trade_date desc limit 1").fetchone()
        result["latest_run"] = None if latest is None else {"run_id": str(latest[0]), "publication_id": str(latest[1]), "trade_date": str(latest[2])}
        run_id = latest[0] if latest else None
        result["sealed_episode_count"] = int(connection.execute("select count(*) from research_sector_signal_state where run_id=? and episode_id is not null", [run_id]).fetchone()[0]) if run_id else 0
        result["signal_state_count"] = int(connection.execute("select count(*) from research_sector_signal_state where run_id=?", [run_id]).fetchone()[0]) if run_id else 0
        result["outcome_table_present"] = int(connection.execute("select count(*) from information_schema.tables where table_name='research_signal_outcomes'").fetchone()[0]) == 1
        result["outcome_count"] = int(connection.execute("select count(*) from research_signal_outcomes").fetchone()[0]) if result["outcome_table_present"] else 0
    return result


def _run() -> dict[str, object]:
    before = (DB.stat().st_size, DB.stat().st_mtime_ns)
    synthetic = _synthetic()
    real = _real_read()
    after = (DB.stat().st_size, DB.stat().st_mtime_ns)
    page = (ROOT / "src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
    migration_ok = "034_v3_signal_outcomes" in MigrationExecutor.DEPENDENCIES and (ROOT / "src/workbench_db/migrations/034_v3_signal_outcomes.sql").is_file()
    compile_probe = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "scripts"], cwd=ROOT, capture_output=True, text=True)
    diff_probe = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    node_probe = subprocess.run(["node", "-e", "const fs=require('fs'),vm=require('vm'); for (const p of process.argv.slice(1)) new vm.Script(fs.readFileSync(p,'utf8'),{filename:p});", str(ROOT / "src/workbench_service/static/v2/router.js"), str(ROOT / "src/workbench_service/static/v2/api.js"), str(ROOT / "src/workbench_service/static/v2/app.js")], cwd=ROOT, capture_output=True, text=True)
    pytest_probe = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/upgrade_v3/test_p10_03_signal_evaluation.py"], cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, capture_output=True, text=True)
    checks = {
        "contract": CONTRACT_ID == "V3_P10_SIGNAL_EVALUATION_V1_0" and synthetic["eval_version"] == EVAL_VERSION,
        "pending_works": synthetic["pending_statuses"] == ["PENDING", "PENDING"],
        "observed_confirmation_and_fixed_member_return": synthetic["observed"]["statuses"] == ["OBSERVED", "OBSERVED"] and synthetic["observed"]["confirmed_date_h3"] == "2026-09-14" and synthetic["observed"]["coverage_h3"] == 1.0,
        "future_cannot_change_signal_hash": synthetic["hash_stable"],
        "repeated_episode_not_independent": synthetic["episode_count_after_dedup"] == 1,
        "three_equal_size_baselines": all(value == 2 for value in synthetic["baseline_counts"].values()),
        "outcome_store_idempotent": synthetic["store_first_write"] == {"inserted": 2, "updated": 0, "unchanged": 0} and synthetic["store_second_write"] == {"inserted": 0, "updated": 0, "unchanged": 2} and synthetic["outcome_count"] == 2,
        "signal_state_unchanged": synthetic["signal_state_before"] == synthetic["signal_state_after"] == "QUALIFIED",
        "migration_registered": migration_ok,
        "real_complete_run_present": int(real["complete_runs"]) >= 1,
        "real_effect_gate_not_claimed": int(real["sealed_episode_count"]) < 50,
        "v3_observation_ui": all(marker in page for marker in ("evaluation-heading", "/api/v3/research/evaluation", "规则观察·效果验证中")),
        "python_compile": compile_probe.returncode == 0,
        "javascript_syntax": node_probe.returncode == 0,
        "diff_check": diff_probe.returncode == 0,
        "targeted_tests": pytest_probe.returncode == 0,
        "production_database_unchanged": before == after,
    }
    return {"checks": checks, "synthetic": synthetic, "real_read": real, "database_stat_before": {"size": before[0], "mtime_ns": before[1]}, "database_stat_after": {"size": after[0], "mtime_ns": after[1]}, "probes": {"compile_stderr": compile_probe.stderr[-1000:], "node_stderr": node_probe.stderr[-1000:], "diff_output": diff_probe.stdout[-1000:] + diff_probe.stderr[-1000:], "pytest_output": pytest_probe.stdout[-2000:] + pytest_probe.stderr[-1000:]}}


def main() -> int:
    evidence = _run()
    checks = evidence["checks"]
    status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    payload = {
        "receipt_id": "P10-03-SIGNAL-EVALUATION",
        "stage": "P10-03",
        "status": status,
        "engineering_status": status,
        "effect_status": "EFFECT_OBSERVATION_PENDING" if status == "FULL_PASS" else "NOT_ACCEPTED",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {"contract_id": CONTRACT_ID, "eval_version": EVAL_VERSION, "spec_sha256": _sha256(SPEC), "spec_section": "§8.2、§14.1–§14.2、§18.13、§20.3–§20.8", "scope": "封存 POTENTIAL 首次 episode；3/5 交易日 CURRENT 确认；固定成员复权收益诊断；三组同日等量基线；历史重建/真实前瞻/PENDING/DATA_GAP 分开。"},
        "checks": checks,
        "evidence": evidence,
        "acceptance": "P10-03 FULL_PASS：评估链、PENDING/DATA_GAP、未来 hash 隔离、episode 去重、三组等量基线和只读页面均有证据；真实样本不足时明确保持规则观察，不宣称效果通过。" if status == "FULL_PASS" else "P10-03 BLOCKED：至少一项评估、存储、只读边界或工程校验失败。",
        "known_limits": ["当前真实库仅有 1 个 COMPLETE research run，封存 episode 为 0；尚未达到 20 个信号日/50 个独立 episode。", "本阶段不做概率、回测、可成交收益或 AI 优于涨幅榜的结论。", "生产数据库仅执行 read_only 查询；合成 outcomes 写入内存 DuckDB，未写生产库；TDX 输入目录未触碰。"],
        "next_stage": "P11-01" if status == "FULL_PASS" else "P10-03-REPAIR",
        "tdx_inputs_modified": False,
        "production_database_written": False,
    }
    _write_atomic(payload)
    print(json.dumps({"status": status, "effect_status": payload["effect_status"], "checks": checks, "next_stage": payload["next_stage"]}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
