"""Read-only P06-02 potential distribution from the V3 stock signal chain."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.research_features import ResearchFeatureContext, build_stock_research_features
from workbench_analysis.sector_attention import aggregate_early_width, build_sector_current, build_sector_potential
from workbench_analysis.stock_attention import classify_stock_frame
from workbench_analysis.technical import calculate_technical_daily


def _atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(name)
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    config_path = ROOT / "config/research_attention_v3.yaml"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    parquet = ROOT / "data/normalized/adjusted_daily.parquet"
    db = ROOT / "data/database/market_research.duckdb"
    with duckdb.connect(str(db), read_only=True) as connection:
        publication = connection.execute(
            """select p.publication_id,p.trade_date,pm.membership_snapshot_id
                 from publications p join publication_memberships pm using(publication_id)
                where p.status='SUCCESS' order by p.trade_date desc,p.revision desc limit 1"""
        ).fetchone()
        if not publication:
            raise RuntimeError("P06_02_PUBLICATION_BINDING_MISSING")
        publication_id, trade_date, snapshot_id = publication
        sessions = [str(row[0]) for row in connection.execute(
            "select distinct date from read_parquet(?) where date <= ? order by date desc limit 110", [str(parquet), trade_date]
        ).fetchall()][::-1]
        raw = connection.execute(
            """select security_id,date as trade_date,adj_close,raw_close,raw_amount,raw_volume,
                      has_actual_bar,tradable,data_observed,is_synthetic_fill
                 from read_parquet(?) where date between ? and ?""", [str(parquet), sessions[0], sessions[-1]]
        ).fetch_df()
        members = connection.execute(
            """select sector_id,security_id,
                      json_extract_string(payload_json,'$.sector_name') sector_name,
                      json_extract_string(payload_json,'$.sector_type') sector_type,
                      json_extract_string(payload_json,'$.sector_role') sector_role
                 from membership_entries where membership_snapshot_id=?""", [snapshot_id]
        ).fetch_df()
        cycle = connection.execute(
            """select sector_id,trade_date,sector_rs5_pct q5,sector_rs20_pct q20,breadth_ret1_common_change_3d b_delta3,
                      breadth_ma20 ma20_width,sector_type
                 from sector_cycle_daily where trade_date between ? and ?""", [sessions[-4], sessions[-1]]
        ).fetch_df()
        amount = connection.execute(
            """select sector_id,trade_date,sector_amount_vs_prior20,amount_contract_id
                 from sector_cycle_daily where trade_date=?""", [trade_date]
        ).fetch_df()
    raw["price_basis"] = "TDX_NATIVE_QFQ"
    technical = calculate_technical_daily(raw.rename(columns={"trade_date": "date"}), cutoff=sessions[-1])
    for window in (5, 20):
        technical[f"rps{window}"] = technical.groupby("date")[f"ret{window}"].rank(method="average", pct=True)
    features = build_stock_research_features(
        raw, technical[["security_id", "date", "rps5", "rps20"]].rename(columns={"date": "trade_date"}), sessions,
        ResearchFeatureContext("P06-02-READONLY", publication_id, snapshot_id, "UNBOUND", "MASTER_CALENDAR", sessions[-1]),
    )
    signals = classify_stock_frame(features, config)
    signals = signals.merge(features[["security_id", "close", "ma20"]], on="security_id", how="left")
    members = members.drop_duplicates(["sector_id", "security_id"])
    stock_input = members.merge(signals[["security_id", "setup", "recovery", "extended", "close", "ma20"]], on="security_id", how="left")
    early = aggregate_early_width(stock_input)
    member_current = members.merge(signals[["security_id", "trade_date"]], on="security_id", how="left")
    member_current["trade_date"] = pd.Timestamp(trade_date).date()
    member_current = member_current.merge(technical[["security_id", "date", "quote_ret1"]].rename(columns={"date": "trade_date", "quote_ret1": "ret1"}), on=["security_id", "trade_date"], how="left")
    market = technical[["security_id", "date", "quote_ret1"]].rename(columns={"date": "trade_date", "quote_ret1": "ret1"})
    cycle["sector_id"] = cycle["sector_id"].astype(str)
    cycle["trade_date"] = pd.to_datetime(cycle["trade_date"]).dt.date
    cycle = cycle.sort_values("trade_date").drop_duplicates(["sector_id", "trade_date"], keep="last")
    cycle["dq5_3"] = cycle.groupby("sector_id")["q5"].diff(3)
    cycle["ma20_delta3"] = cycle.groupby("sector_id")["ma20_width"].diff(3)
    current_comparison = cycle[cycle["trade_date"].eq(pd.Timestamp(trade_date).date())][["sector_id", "trade_date", "b_delta3"]]
    current = build_sector_current(member_current, market, config, amount_features=amount, comparison_features=current_comparison)
    current = current.merge(early, on="sector_id", how="left")
    current["trade_date"] = pd.to_datetime(current["trade_date"]).dt.date
    current = current.merge(
        cycle[cycle["trade_date"].eq(trade_date)][["sector_id", "q5", "q20", "dq5_3", "ma20_width", "ma20_delta3"]],
        on="sector_id", how="left", suffixes=("", "_history")
    )
    if "ma20_width_history" in current:
        current["ma20_width"] = current["ma20_width_history"]
        current = current.drop(columns=["ma20_width_history"])
    current["prior_current_within10"] = None
    potential = build_sector_potential(current, config)
    output = ROOT / "reports/upgrade_v3/P06-02_POTENTIAL_DISTRIBUTION.json"
    report = {
        "contract_id": "v3-p06-02-potential-distribution-v1.0",
        "sector_potential_contract_id": "SECTOR_POTENTIAL_PREVIEW_1",
        "trade_date": str(trade_date),
        "input": {"publication_id": publication_id, "membership_snapshot_id": snapshot_id, "membership_row_count": int(len(members)), "stock_signal_count": int(len(signals)), "normalized_sha256": _sha256(parquet), "database_sha256": _sha256(db), "read_only": True},
        "parameter": {"schema_version": config["schema_version"], "parameter_hash": config["parameter_hash"]},
        "distribution": {"sector_count": int(len(potential)), "potential_true": int(potential["potential_eligible"].eq(True).sum()), "potential_false": int(potential["potential_eligible"].eq(False).sum()), "potential_unknown": int(potential["potential_eligible"].isna().sum()), "branch_true": {name: int(potential["branch_results"].map(lambda value, key=name: value[key] is True).sum()) for name in ("BREADTH_BUILD", "BASE_BUILD", "RECOVERY_BUILD")}, "early_width_available": int(early["early_width"].notna().sum()), "examples": potential[potential["potential_eligible"].eq(True)][["sector_id", "primary_branch", "early_width", "q20", "amount_A"]].head(10).to_dict("records")},
        "policy": {"database_written": False, "tdx_modified": False, "legacy_candidate_used": False, "effectiveness_claim": False},
    }
    _atomic(output, report)
    print(json.dumps({"status": "PASS", "output": str(output), "potential_true": report["distribution"]["potential_true"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
