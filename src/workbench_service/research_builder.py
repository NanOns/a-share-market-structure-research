"""Bound end-to-end builder for a V3 local-close research run."""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import duckdb
import pandas as pd

from workbench_analysis.research_features import ResearchFeatureContext, build_stock_research_features
from workbench_analysis.sector_attention import (
    aggregate_early_width, build_sector_current, build_sector_member_roles,
    build_sector_potential, progress_potential_episode,
)
from workbench_analysis.stock_attention import classify_stock_frame
from workbench_analysis.technical import calculate_technical_daily
from workbench_service.research_association import select_associations_and_shortlists
from workbench_service.research_runs import JOB_TYPE, ResearchRunStore
from workbench_service.research_signal_evaluation import seal_episode_id


class ResearchBuildError(RuntimeError):
    pass


def build_latest_research_run(root: str | Path, database_path: str | Path) -> dict[str, Any]:
    """Build the latest publication through every P05-P07 stage and seal it."""
    root = Path(root)
    database_path = Path(database_path)
    config = json.loads((root / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))
    parquet = root / "data/normalized/adjusted_daily.parquet"
    with duckdb.connect(str(database_path)) as connection:
        publication = connection.execute(
            """select p.publication_id,p.trade_date,pm.membership_snapshot_id,
                      coalesce(pas.snapshot_id,'UNBOUND') snapshot_id
                 from publications p join publication_memberships pm using(publication_id)
                 left join publication_analysis_snapshots pas on pas.publication_id=p.publication_id and pas.domain='LOCAL_RECONSTRUCTED'
                where p.status='SUCCESS' order by p.trade_date desc,p.revision desc limit 1"""
        ).fetchone()
        if not publication:
            raise ResearchBuildError("RESEARCH_PUBLICATION_MISSING")
        publication_id, trade_date, membership_snapshot_id, snapshot_id = publication
        sessions = [str(row[0]) for row in connection.execute(
            "select distinct date from read_parquet(?) where date<=? order by date desc limit 110",
            [str(parquet), trade_date],
        ).fetchall()][::-1]
        if len(sessions) < 101:
            raise ResearchBuildError("RESEARCH_HISTORY_INSUFFICIENT")
        raw = connection.execute(
            """select security_id,date as trade_date,adj_close,raw_close,raw_amount,raw_volume,
                      has_actual_bar,tradable,data_observed,is_synthetic_fill
                 from read_parquet(?) where date between ? and ?""",
            [str(parquet), sessions[0], sessions[-1]],
        ).fetch_df()
        members = connection.execute(
            """select sector_id,security_id,
                      json_extract_string(payload_json,'$.sector_name') sector_name,
                      json_extract_string(payload_json,'$.sector_type') sector_type,
                      json_extract_string(payload_json,'$.sector_role') sector_role
                 from membership_entries where membership_snapshot_id=?""",
            [membership_snapshot_id],
        ).fetch_df().drop_duplicates(["sector_id", "security_id"])
        quote_rows = connection.execute(
            """select security_id,trade_date,quote_ret1 ret1
                 from technical_result_daily where trade_date=?""", [trade_date]
        ).fetch_df()
        cycle = connection.execute(
            """select sector_id,trade_date,sector_rs5_pct q5,sector_rs20_pct q20,
                      breadth_ret1_common_change_3d b_delta3,breadth_ma20 ma20_width,
                      sector_amount_vs_prior20,amount_contract_id
                 from sector_cycle_daily where trade_date between ? and ?""",
            [sessions[-11], sessions[-1]],
        ).fetch_df()

        body = {"job_type": JOB_TYPE, "publication_id": publication_id, "trade_date": str(trade_date),
                "algorithm_version": config["algorithm_version"], "parameter_hash": config["parameter_hash"],
                "snapshot_id": snapshot_id, "membership_snapshot_id": membership_snapshot_id,
                "dependency_bindings": {"features": config["contracts"]["features"], "membership": membership_snapshot_id}}
        store = ResearchRunStore(connection)
        started = store.start(body)
        if started["status"] == "COMPLETE":
            return {**started, "publication_id": publication_id, "trade_date": str(trade_date)}
        run_id = started["run_id"]
        try:
            raw["price_basis"] = "TDX_NATIVE_QFQ"
            technical = calculate_technical_daily(raw.rename(columns={"trade_date": "date"}), cutoff=sessions[-1])
            for window in (5, 20):
                technical[f"rps{window}"] = technical.groupby("date")[f"ret{window}"].rank(method="average", pct=True)
            features = build_stock_research_features(
                raw, technical[["security_id", "date", "rps5", "rps20"]].rename(columns={"date": "trade_date"}),
                sessions, ResearchFeatureContext(run_id, publication_id, snapshot_id, membership_snapshot_id, "MASTER_CALENDAR", sessions[-1]),
            )
            signals = classify_stock_frame(features, config)
            stock = signals.merge(features, on="security_id", suffixes=("", "_feature"))
            current_quotes = quote_rows.copy()
            member_current = members.merge(current_quotes, on="security_id", how="left")
            member_current["trade_date"] = pd.Timestamp(trade_date).date()
            cycle["sector_id"] = cycle["sector_id"].astype(str)
            cycle["trade_date"] = pd.to_datetime(cycle["trade_date"]).dt.date
            cycle = cycle.sort_values("trade_date").drop_duplicates(["sector_id", "trade_date"], keep="last")
            cycle["dq5_3"] = cycle.groupby("sector_id")["q5"].diff(3)
            cycle["ma20_delta3"] = cycle.groupby("sector_id")["ma20_width"].diff(3)
            today_cycle = cycle[cycle["trade_date"].eq(pd.Timestamp(trade_date).date())]
            amount = today_cycle[["sector_id", "trade_date", "sector_amount_vs_prior20", "amount_contract_id"]]
            comparison = today_cycle[["sector_id", "trade_date", "b_delta3"]]
            current = build_sector_current(member_current, current_quotes, config, amount_features=amount, comparison_features=comparison)
            signal_members = members.merge(stock[["security_id", "setup", "recovery", "extended", "close", "ma20"]], on="security_id", how="left")
            early = aggregate_early_width(signal_members)
            current = current.merge(early, on="sector_id", how="left")
            current = current.merge(today_cycle[["sector_id", "q5", "q20", "dq5_3", "ma20_width", "ma20_delta3"]], on="sector_id", how="left")
            current["prior_current_within10"] = None
            sectors = build_sector_potential(current, config)
            sectors["current_rank"] = sectors["current"].eq(True).where(sectors["current"].notna()).rank(method="first").astype("Int64")
            sectors["potential_rank"] = sectors["potential_eligible"].eq(True).where(sectors["potential_eligible"].notna()).rank(method="first").astype("Int64")
            episode_rows = []
            for row in sectors.to_dict("records"):
                seq = pd.DataFrame([{"trade_date": trade_date, "potential_eligible": row.get("potential_eligible"), "current": row.get("current"), "weak": row.get("weak"), "ma20_width": row.get("ma20_width"), "extended_share": row.get("extended_share"), "risk_coverage": row.get("risk_coverage")}])
                episode = progress_potential_episode(seq, config).iloc[0].to_dict()
                first_seen = episode.get("first_seen_date")
                episode_id = seal_episode_id(sector_id=row["sector_id"], first_seen_date=first_seen) if first_seen else None
                episode_rows.append({"sector_id": row["sector_id"], **episode, "episode_id": episode_id, "lifecycle": episode.get("state"), "prior_run_id": None, "history_complete": False})
            role_stock = stock.copy()
            role_stock["position_complete"] = role_stock[["close", "ma20", "dist_high20"]].notna().all(axis=1)
            role_members = members.merge(current_quotes[["security_id", "ret1"]], on="security_id", how="left").merge(
                role_stock[["security_id", "breakout", "recovery", "setup", "extended", "structure_break", "position_complete", "liquidity20", "amount_vs_prior20", "rps5_delta3", "bias20"]],
                on="security_id", how="left",
            )
            roles = build_sector_member_roles(role_members, sectors, config)
            compact_roles = roles[roles["role"].ne("ALL_MEMBERS")]
            associations, shortlists = select_associations_and_shortlists(role_members, compact_roles, sectors, config)
            stock_rows = [{"security_id": row["security_id"], "setup": row.get("setup"), "breakout": row.get("breakout"), "recovery": row.get("recovery"), "trend_background": row.get("trend_background"), "structure_break": row.get("structure_break"), "quality": row.get("quality", "PARTIAL"), "bias20": row.get("bias20"), "sigma20": row.get("sigma20"), "extension_z20": row.get("extension_z20"), "dist_high20": row.get("dist_high20"), "range5": row.get("range5"), "range20": row.get("range20"), "rps5_delta3": row.get("rps5_delta3"), "liquidity20_amount": row.get("amount_prior20_median"), "risk_codes": row.get("risk_codes", []), "reason_codes": row.get("reason_codes", []), "evidence": {"selection": row.get("checks", {}), "technical": {"contract_id": row.get("contract_id")}}} for row in stock.to_dict("records")]
            sector_rows = [{**row, "current_eligible": row.get("current"), "potential_branch": row.get("primary_branch"), "potential_branches": row.get("branch_results", {}), "member_count": row.get("total_member_count"), "feature_valid_count": row.get("early_evaluable_count"), "amount_a": row.get("amount_A"), "quality": "READY" if row.get("current") is not None else "PARTIAL", "evidence": row.get("branch_checks", {}), "input_members_hash": membership_snapshot_id, "rank_universe_hash": config["parameter_hash"]} for row in sectors.to_dict("records")]
            role_rows = compact_roles.to_dict("records")
            shortlist_rows = shortlists.to_dict("records") if not shortlists.empty else []
            completed = store.complete(run_id, stock_states=stock_rows, sector_states=sector_rows, signal_states=episode_rows, member_roles=role_rows, shortlists=shortlist_rows)
            return {**completed, "publication_id": publication_id, "trade_date": str(trade_date), "stock_count": len(stock_rows), "sector_count": len(sector_rows), "role_count": len(role_rows), "shortlist_count": len(shortlist_rows), "association_count": len(associations)}
        except Exception as exc:
            store.fail(run_id, type(exc).__name__)
            raise


__all__ = ["ResearchBuildError", "build_latest_research_run"]
