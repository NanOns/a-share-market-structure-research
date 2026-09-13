"""Build a read-only P07-01 member-role distribution report."""
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
from workbench_analysis.sector_attention import build_sector_current, build_sector_member_roles
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
    config = json.loads((ROOT / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))
    parquet = ROOT / "data/normalized/adjusted_daily.parquet"
    database = ROOT / "data/database/market_research.duckdb"
    with duckdb.connect(str(database), read_only=True) as connection:
        publication = connection.execute(
            """select p.publication_id,p.trade_date,pm.membership_snapshot_id
                 from publications p join publication_memberships pm using(publication_id)
                where p.status='SUCCESS' order by p.trade_date desc,p.revision desc limit 1"""
        ).fetchone()
        publication_id, trade_date, snapshot_id = publication
        members = connection.execute(
            """select sector_id,security_id,
                      json_extract_string(payload_json,'$.sector_name') sector_name,
                      json_extract_string(payload_json,'$.sector_type') sector_type,
                      json_extract_string(payload_json,'$.sector_role') sector_role
                 from membership_entries where membership_snapshot_id=?""", [snapshot_id]
        ).fetch_df()
        technical_db = connection.execute(
            """select security_id,quote_ret1 ret1,raw_amount amount_vs_prior20
                 from technical_result_daily where trade_date=?""", [trade_date]
        ).fetch_df()
        sessions = [str(row[0]) for row in connection.execute(
            "select distinct date from read_parquet(?) where date <= ? order by date desc limit 110", [str(parquet), trade_date]
        ).fetchall()][::-1]
        raw = connection.execute(
            """select security_id,date as trade_date,adj_close,raw_close,raw_amount,raw_volume,
                      has_actual_bar,tradable,data_observed,is_synthetic_fill
                 from read_parquet(?) where date between ? and ?""", [str(parquet), sessions[0], sessions[-1]]
        ).fetch_df()
    raw["price_basis"] = "TDX_NATIVE_QFQ"
    technical = calculate_technical_daily(raw.rename(columns={"trade_date": "date"}), cutoff=sessions[-1])
    for window in (5, 20):
        technical[f"rps{window}"] = technical.groupby("date")[f"ret{window}"].rank(method="average", pct=True)
    features = build_stock_research_features(
        raw, technical[["security_id", "date", "rps5", "rps20"]].rename(columns={"date": "trade_date"}), sessions,
        ResearchFeatureContext("P07-01-READONLY", publication_id, snapshot_id, "UNBOUND", "MASTER_CALENDAR", sessions[-1]),
    )
    signals = classify_stock_frame(features, config).merge(features[["security_id", "close", "ma20", "dist_high20", "liquidity20"]], on="security_id", how="left")
    signals["position_complete"] = signals[["close", "ma20", "dist_high20"]].notna().all(axis=1)
    signals["amount_vs_prior20"] = features["amount_vs_prior20"].values
    signals["rps5_delta3"] = features["rps5_delta3"].values
    signals["bias20"] = features["bias20"].values
    member_rows = members.merge(technical_db, on="security_id", how="left").merge(signals[["security_id", "breakout", "recovery", "setup", "extended", "structure_break", "position_complete", "liquidity20", "amount_vs_prior20", "rps5_delta3", "bias20"]], on="security_id", how="left", suffixes=("_db", ""))
    member_rows["amount_vs_prior20"] = member_rows["amount_vs_prior20"].combine_first(member_rows["amount_vs_prior20_db"])
    sector_states = pd.DataFrame({"sector_id": members["sector_id"].drop_duplicates().astype(str), "current": None, "potential_eligible": False})
    roles = build_sector_member_roles(member_rows, sector_states, config)
    role_counts = roles["role"].value_counts().to_dict()
    report = {
        "contract_id": "v3-p07-01-member-roles-v1.0",
        "member_role_contract_id": "SECTOR_MEMBER_ROLES_PREVIEW_1",
        "trade_date": str(trade_date),
        "input": {"publication_id": publication_id, "membership_snapshot_id": snapshot_id, "membership_row_count": int(len(members)), "stock_signal_count": int(len(signals)), "normalized_sha256": _sha256(parquet), "database_sha256": _sha256(database), "read_only": True},
        "roles": {"counts": {str(key): int(value) for key, value in role_counts.items()}, "sector_count": int(members.sector_id.nunique()), "today_leader_sector_count": int(roles.loc[roles.role.eq("TODAY_LEADER"), "sector_id"].nunique()), "current_research_count": int((roles.role == "CURRENT_RESEARCH").sum()), "early_watch_count": int((roles.role == "EARLY_WATCH").sum()), "samples": {role: roles[roles.role.eq(role)][["sector_id", "security_id", "role_rank", "today_rank"]].head(5).to_dict("records") for role in ("TODAY_LEADER", "CURRENT_RESEARCH", "EARLY_WATCH")}},
        "policy": {"database_written": False, "tdx_modified": False, "legacy_ret20_used_for_today_leader": False, "effectiveness_claim": False},
    }
    output = ROOT / "reports/upgrade_v3/P07-01_MEMBER_ROLES_DISTRIBUTION.json"
    _atomic(output, report)
    print(json.dumps({"status": "PASS", "output": str(output), "role_counts": report["roles"]["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
