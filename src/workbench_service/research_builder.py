"""Bound end-to-end builder for a V3 local-close research run."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from workbench_analysis.research_features import ResearchFeatureContext, build_stock_research_features
from workbench_analysis.sector_attention import (
    aggregate_early_width, build_sector_current, build_sector_member_roles,
    build_sector_potential, progress_potential_episode,
)
from workbench_analysis.stock_attention import classify_stock_frame
from workbench_analysis.technical import calculate_technical_daily
from workbench_analysis.strength import calculate_strength_daily
from workbench_analysis.sector_cycle import CONTRACT_VERSION as SECTOR_CYCLE_CONTRACT
from workbench_service.research_association import select_associations_and_shortlists
from workbench_service.research_runs import JOB_TYPE, ResearchRunStore
from workbench_service.research_v3_contracts import parameter_hash
from workbench_service.research_signal_evaluation import seal_episode_id
from workbench_service.universe import is_workbench_statistical_security_id
from tdx.security_master import current_a_stock_ids, read_industry_assignments


class ResearchBuildError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _market_universe_metadata_path(root: Path, source_bundle_id: str | None, trade_date: Any) -> Path:
    """Resolve tdxhy.cfg from the immutable source-bundle contract.

    M3 versions metadata by snapshot id, so the old date-only staging path is
    no longer authoritative.  Keep the legacy location as a compatibility
    fallback for publications created before versioned source bundles.
    """
    if source_bundle_id:
        bundle_path = root / "data/source_bundles" / str(source_bundle_id) / "source_bundle.json"
        if bundle_path.is_file():
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            if str(bundle.get("source_bundle_id") or "") != str(source_bundle_id):
                raise ResearchBuildError("SOURCE_BUNDLE_IDENTITY_MISMATCH")
            metadata = bundle.get("metadata") or {}
            metadata_root = metadata.get("root")
            if metadata_root:
                candidate = (root / str(metadata_root)).resolve()
                project_root = root.resolve()
                try:
                    candidate.relative_to(project_root)
                except ValueError as exc:
                    raise ResearchBuildError("MARKET_UNIVERSE_SOURCE_OUTSIDE_PROJECT") from exc
                candidate = candidate / "T0002/hq_cache/tdxhy.cfg"
                expected = ((metadata.get("files") or {}).get("T0002/hq_cache/tdxhy.cfg") or {}).get("sha256")
                if candidate.is_file() and (not expected or _sha256_file(candidate) == str(expected)):
                    return candidate
                if candidate.is_file():
                    raise ResearchBuildError("MARKET_UNIVERSE_SOURCE_HASH_MISMATCH")
    legacy = root / "data/input_staging/metadata" / pd.Timestamp(trade_date).strftime("%Y%m%d") / "T0002/hq_cache/tdxhy.cfg"
    if legacy.is_file():
        return legacy
    raise ResearchBuildError("MARKET_UNIVERSE_SOURCE_MISSING")


def _rank_eligible(frame: pd.DataFrame, eligible: str, columns: list[str]) -> pd.Series:
    """Rank only qualified sectors; unknown and failed rows remain unranked."""
    ranked = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    subset = frame.loc[frame[eligible].eq(True)].copy()
    if subset.empty:
        return ranked
    subset = subset.sort_values(columns + ["sector_id"], ascending=[False] * len(columns) + [True],
                                na_position="last", kind="mergesort")
    ranked.loc[subset.index] = pd.array(range(1, len(subset) + 1), dtype="Int64")
    return ranked


def _common_member_breadth_delta(
    current_members: pd.DataFrame,
    prior_members: pd.DataFrame,
    quotes: pd.DataFrame,
    current_date: Any,
    prior_date: Any,
    min_coverage: float = .70,
) -> pd.DataFrame:
    """Return t versus t-3 breadth on the identical member intersection."""
    current_keys = current_members[["sector_id", "security_id"]].drop_duplicates()
    prior_keys = prior_members[["sector_id", "security_id"]].drop_duplicates()
    common = current_keys.merge(prior_keys, on=["sector_id", "security_id"], how="inner")
    values = quotes.copy()
    values["trade_date"] = pd.to_datetime(values["trade_date"]).dt.date
    current_day, prior_day = pd.Timestamp(current_date).date(), pd.Timestamp(prior_date).date()
    wanted = values[values["trade_date"].isin([current_day, prior_day])]
    pivot = wanted.pivot(index="security_id", columns="trade_date", values="ret1")
    rows = []
    current_counts = current_keys.groupby("sector_id")["security_id"].nunique()
    prior_counts = prior_keys.groupby("sector_id")["security_id"].nunique()
    for sector_id, group in common.groupby("sector_id", sort=True):
        if current_day not in pivot or prior_day not in pivot:
            value = None
        else:
            paired = pivot.reindex(group["security_id"].astype(str))[[current_day, prior_day]].apply(pd.to_numeric, errors="coerce").dropna()
            denominator = max(int(current_counts.get(sector_id, 0)), int(prior_counts.get(sector_id, 0)))
            coverage = len(paired) / denominator if denominator else 0.0
            value = float((paired.iloc[:, 0] > 0).mean() - (paired.iloc[:, 1] > 0).mean()) if len(paired) >= 5 and coverage >= min_coverage else None
        rows.append({"sector_id": str(sector_id), "trade_date": current_day, "b_delta3": value})
    return pd.DataFrame(rows, columns=["sector_id", "trade_date", "b_delta3"])


def _exact_cycle_delta(cycle: pd.DataFrame, today: Any, prior: Any, config: dict[str, Any]) -> pd.DataFrame:
    """Compare calendar-aligned ranks only when both cross sections are stable."""
    today, prior = pd.Timestamp(today).date(), pd.Timestamp(prior).date()
    current = cycle.loc[cycle.trade_date.eq(today), ["sector_id", "sector_type", "q5"]]
    earlier = cycle.loc[cycle.trade_date.eq(prior) & cycle.contract_id.eq(SECTOR_CYCLE_CONTRACT), ["sector_id", "sector_type", "q5"]]
    coverage = config["thresholds"]["coverage"]
    rows = []
    for sector_type, group in current.groupby("sector_type", sort=False):
        old = earlier[earlier.sector_type.eq(sector_type)]
        now_ids = set(group.loc[pd.to_numeric(group.q5, errors="coerce").notna(), "sector_id"])
        old_ids = set(old.loc[pd.to_numeric(old.q5, errors="coerce").notna(), "sector_id"])
        union = now_ids | old_ids
        change = abs(len(now_ids) - len(old_ids)) / max(len(now_ids), len(old_ids)) if union else 1.0
        overlap = len(now_ids & old_ids) / len(union) if union else 0.0
        comparable = change <= coverage["max_rank_universe_change"] and overlap >= coverage["min_rank_intersection_union"]
        old_q5 = old.set_index("sector_id").q5
        for row in group.itertuples(index=False):
            previous = old_q5.get(row.sector_id)
            value = float(row.q5 - previous) if comparable and pd.notna(row.q5) and pd.notna(previous) else None
            rows.append({"sector_id": row.sector_id, "dq5_3": value})
    return pd.DataFrame(rows, columns=["sector_id", "dq5_3"])


def _common_member_ma20_delta(current_members: pd.DataFrame, prior_members: pd.DataFrame,
                               technical: pd.DataFrame, today: Any, prior: Any,
                               min_coverage: float) -> pd.DataFrame:
    """Compare QFQ close/MA20 on the identical two-day valid member set."""
    current_keys = current_members[["sector_id", "security_id"]].drop_duplicates()
    prior_keys = prior_members[["sector_id", "security_id"]].drop_duplicates()
    common = current_keys.merge(prior_keys, on=["sector_id", "security_id"])
    technical = technical.copy()
    technical["date"] = pd.to_datetime(technical["date"]).dt.date
    today, prior = pd.Timestamp(today).date(), pd.Timestamp(prior).date()
    values = technical[technical.date.isin([today, prior])].set_index(["security_id", "date"])
    counts_now = current_keys.groupby("sector_id").security_id.nunique()
    counts_old = prior_keys.groupby("sector_id").security_id.nunique()
    rows = []
    for sector_id, group in common.groupby("sector_id", sort=False):
        paired = []
        for security_id in group.security_id.astype(str):
            if (security_id, today) not in values.index or (security_id, prior) not in values.index:
                continue
            now = values.loc[(security_id, today)]
            old = values.loc[(security_id, prior)]
            numbers = pd.to_numeric(pd.Series([now.adj_close, now.ma20, old.adj_close, old.ma20]), errors="coerce")
            if np.isfinite(numbers).all():
                paired.append((numbers.iloc[0] > numbers.iloc[1], numbers.iloc[2] > numbers.iloc[3]))
        denominator = max(int(counts_now.get(sector_id, 0)), int(counts_old.get(sector_id, 0)))
        delta = float(sum(pair[0] for pair in paired) / len(paired) - sum(pair[1] for pair in paired) / len(paired)) if len(paired) >= 5 and len(paired) / denominator >= min_coverage else None
        rows.append({"sector_id": sector_id, "ma20_delta3": delta})
    return pd.DataFrame(rows, columns=["sector_id", "ma20_delta3"])


def build_latest_research_run(root: str | Path, database_path: str | Path) -> dict[str, Any]:
    """Build the latest publication through every P05-P07 stage and seal it."""
    root = Path(root)
    database_path = Path(database_path)
    config = json.loads((root / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))
    if config.get("parameter_hash") != parameter_hash(config):
        raise ResearchBuildError("PARAMETER_HASH_MISMATCH")
    parquet = root / "data/normalized/adjusted_daily.parquet"
    adjusted_digest = _sha256_file(parquet)
    with duckdb.connect(str(database_path)) as connection:
        publication = connection.execute(
            """select p.publication_id,p.trade_date,
                      coalesce(pm.membership_snapshot_id,'relation-' || rb.observation_id),
                      coalesce(pas.snapshot_id,'UNBOUND') snapshot_id,
                      rb.source_scope,rb.revision_no,rb.attribute_version_id,
                      rb.observation_id source_bundle_id,p.source_path
                 from publications p
                 left join publication_memberships pm using(publication_id)
                 left join relation_publication_bindings rb using(publication_id)
                 left join publication_analysis_snapshots pas on pas.publication_id=p.publication_id and pas.domain='LOCAL_RECONSTRUCTED'
                where p.status='SUCCESS' and (pm.membership_snapshot_id is not null or rb.observation_id is not null)
                order by p.trade_date desc,p.revision desc limit 1"""
        ).fetchone()
        if not publication:
            raise ResearchBuildError("RESEARCH_PUBLICATION_MISSING")
        publication_id, trade_date, membership_snapshot_id, snapshot_id, source_scope, relation_revision, attribute_version_id, source_bundle_id, source_path = publication
        # Legacy membership publications do not have a relation binding, but
        # M4 still records their immutable bundle directory in source_path.
        if not source_bundle_id or not (root / "data/source_bundles" / str(source_bundle_id) / "source_bundle.json").is_file():
            source_bundle_id = Path(str(source_path)).name
        metadata_path = _market_universe_metadata_path(root, source_bundle_id, trade_date)
        universe_ids = sorted(current_a_stock_ids(read_industry_assignments(metadata_path)))
        universe_ids = [value for value in universe_ids if is_workbench_statistical_security_id(value, root)]
        if not universe_ids:
            raise ResearchBuildError("MARKET_UNIVERSE_EMPTY")
        universe_hash = hashlib.sha256("\n".join(universe_ids).encode("utf-8")).hexdigest()
        sessions = [str(row[0]) for row in connection.execute(
            "select distinct date from read_parquet(?) where date<=? order by date desc limit 110",
            [str(parquet), trade_date],
        ).fetchall()][::-1]
        if len(sessions) < 101:
            raise ResearchBuildError("RESEARCH_HISTORY_INSUFFICIENT")
        raw = connection.execute(
            """select security_id,date as trade_date,adj_close,raw_close,raw_amount,raw_volume,
                      price_basis,project_price_basis,adjustment_status,adjustment_version,universe_status,
                      lag(raw_close) over(partition by security_id order by date) as quote_prev_close,
                      has_actual_bar,tradable,data_observed,is_synthetic_fill
                 from read_parquet(?) where date between ? and ?""",
            [str(parquet), sessions[0], sessions[-1]],
        ).fetch_df()
        if source_scope:
            members = connection.execute(
                """select e.sector_id,e.security_id,a.name sector_name,a.type sector_type,a.role sector_role
                     from relation_edge_intervals e
                     join sector_attribute_revisions ar
                       on ar.source_scope=e.source_scope and ('attrset-' || substr(ar.attribute_set_hash,1,24))=?
                     join sector_attribute_revision_bindings ab
                       on ab.source_scope=e.source_scope and ab.sector_id=e.sector_id
                      and ab.from_attribute_revision<=ar.attribute_revision
                      and (ab.to_attribute_revision is null or ar.attribute_revision<ab.to_attribute_revision)
                     join sector_attribute_versions a
                       on a.source_scope=ab.source_scope and a.sector_id=ab.sector_id and a.attribute_version_id=ab.attribute_version_id
                    where e.source_scope=? and e.from_revision<=?
                      and (e.to_revision is null or ?<e.to_revision)""",
                [attribute_version_id, source_scope, relation_revision, relation_revision],
            ).fetch_df().drop_duplicates(["sector_id", "security_id"])
        else:
            members = connection.execute(
                """select sector_id,security_id,
                          json_extract_string(payload_json,'$.sector_name') sector_name,
                          json_extract_string(payload_json,'$.sector_type') sector_type,
                          json_extract_string(payload_json,'$.sector_role') sector_role
                     from membership_entries where membership_snapshot_id=?""",
                [membership_snapshot_id],
            ).fetch_df().drop_duplicates(["sector_id", "security_id"])
        prior_membership = connection.execute(
            """select pm.membership_snapshot_id,rb.source_scope,rb.revision_no
                 from publications p
                 left join publication_memberships pm using(publication_id)
                 left join relation_publication_bindings rb using(publication_id)
                where p.status='SUCCESS' and p.trade_date=?
                  and (pm.membership_snapshot_id is not null or rb.observation_id is not null)
                order by p.revision desc limit 1""",
            [sessions[-4]],
        ).fetchone()
        if prior_membership and prior_membership[1]:
            prior_members = connection.execute(
                """select sector_id,security_id from relation_edge_intervals
                    where source_scope=? and from_revision<=?
                      and (to_revision is null or ?<to_revision)""",
                [prior_membership[1], prior_membership[2], prior_membership[2]],
            ).fetch_df().drop_duplicates(["sector_id", "security_id"])
        elif prior_membership:
            prior_members = connection.execute(
                "select sector_id,security_id from membership_entries where membership_snapshot_id=?",
                [prior_membership[0]],
            ).fetch_df().drop_duplicates(["sector_id", "security_id"])
        else:
            prior_members = members.iloc[0:0][["sector_id", "security_id"]]
        quote_rows = connection.execute(
            """select t.security_id,t.trade_date,t.quote_ret1 ret1
                 from analysis_snapshot_entries e
                 join technical_result_daily t
                   on t.slice_id=e.slice_id and t.trade_date=e.trade_date
                where e.snapshot_id=? and e.domain='technical' and e.trade_date=?""",
            [snapshot_id, trade_date],
        ).fetch_df()
        cycle = connection.execute(
            """select c.sector_id,c.sector_type,c.trade_date,c.contract_id,c.sector_rs5_pct q5,c.sector_rs20_pct q20,
                      c.breadth_ret1_common_change_3d b_delta3,c.breadth_ma20 ma20_width,
                      c.sector_amount_vs_prior20,c.amount_contract_id
                 from analysis_snapshot_entries e join sector_cycle_daily c
                   on c.slice_id=e.slice_id and c.trade_date=e.trade_date
                where e.snapshot_id=? and e.domain='sector_cycle' and e.trade_date between ? and ?""",
            [snapshot_id, sessions[-11], sessions[-1]],
        ).fetch_df()
        today_cycle_contracts = set(cycle.loc[
            pd.to_datetime(cycle["trade_date"]).dt.date.eq(pd.Timestamp(trade_date).date()), "contract_id"
        ].dropna().astype(str))
        if today_cycle_contracts != {SECTOR_CYCLE_CONTRACT}:
            raise ResearchBuildError("SECTOR_CYCLE_CORRECTNESS_REBUILD_REQUIRED")
        slice_rows = connection.execute(
            """select domain,trade_date,slice_id from analysis_snapshot_entries
                where snapshot_id=? and domain in ('technical','strength','sector_cycle')
                order by domain,trade_date,slice_id""", [snapshot_id],
        ).fetchall()

        body = {"job_type": JOB_TYPE, "publication_id": publication_id, "trade_date": str(trade_date),
                "algorithm_version": config["algorithm_version"], "parameter_hash": config["parameter_hash"],
                "snapshot_id": snapshot_id, "membership_snapshot_id": membership_snapshot_id,
                "dependency_bindings": {"features": config["contracts"]["features"], "sector_cycle": SECTOR_CYCLE_CONTRACT, "membership": membership_snapshot_id,
                                        "adjusted_daily_sha256": adjusted_digest, "history_sessions": [sessions[0], sessions[-1]],
                                        "analysis_slices": [(str(domain), str(day), str(slice_id)) for domain, day, slice_id in slice_rows],
                                        "historical_membership": "PIT_PUBLICATION_ONLY" if prior_membership else "UNAVAILABLE",
                                        "market_universe": "TDXHY_CURRENT_A_STOCK_IDS_V1", "market_universe_hash": universe_hash,
                                        "market_universe_count": len(universe_ids)}}
        store = ResearchRunStore(connection)
        started = store.start(body)
        if started["status"] == "COMPLETE":
            return {**started, "publication_id": publication_id, "trade_date": str(trade_date)}
        run_id = started["run_id"]
        try:
            technical = calculate_strength_daily(raw.rename(columns={"trade_date": "date"}), cutoff=sessions[-1])
            features = build_stock_research_features(
                raw, technical[["security_id", "date", "rps5", "rps20"]].rename(columns={"date": "trade_date"}),
                sessions, ResearchFeatureContext(run_id, publication_id, snapshot_id, membership_snapshot_id, "MASTER_CALENDAR", sessions[-1]),
                liquidity20_amount_gte=config["thresholds"]["stock_signals"]["risk"]["liquidity20_amount_gte"],
            )
            signals = classify_stock_frame(features, config)
            stock = signals.merge(features, on="security_id", suffixes=("", "_feature"))
            current_quotes = technical.loc[
                pd.to_datetime(technical["date"]).dt.date.eq(pd.Timestamp(trade_date).date()),
                ["security_id", "date", "quote_ret1"],
            ].rename(columns={"date": "trade_date", "quote_ret1": "ret1"})
            current_quotes = pd.DataFrame({"security_id": universe_ids}).merge(
                current_quotes, on="security_id", how="left", validate="one_to_one")
            current_quotes["trade_date"] = pd.Timestamp(trade_date).date()
            observed_ids = set(raw.loc[
                pd.to_datetime(raw["trade_date"]).dt.date.eq(pd.Timestamp(trade_date).date())
                & raw["data_observed"].fillna(False).astype(bool), "security_id"
            ].astype(str))
            current_quotes.loc[~current_quotes["security_id"].astype(str).isin(observed_ids), "ret1"] = float("nan")
            member_current = members.merge(current_quotes, on="security_id", how="left")
            member_current["trade_date"] = pd.Timestamp(trade_date).date()
            cycle["sector_id"] = cycle["sector_id"].astype(str)
            cycle["trade_date"] = pd.to_datetime(cycle["trade_date"]).dt.date
            cycle = cycle.sort_values("trade_date").drop_duplicates(["sector_id", "trade_date"], keep="last")
            today_cycle = cycle[cycle["trade_date"].eq(pd.Timestamp(trade_date).date())].copy()
            today_cycle = today_cycle.merge(_exact_cycle_delta(cycle, trade_date, sessions[-4], config), on="sector_id", how="left")
            ma20_delta = _common_member_ma20_delta(members, prior_members, technical, trade_date, sessions[-4],
                                                     config["thresholds"]["coverage"]["min_common_member_coverage"])
            today_cycle = today_cycle.merge(ma20_delta, on="sector_id", how="left")
            amount = today_cycle[["sector_id", "trade_date", "sector_amount_vs_prior20", "amount_contract_id"]]
            quote_history = technical.loc[
                pd.to_datetime(technical["date"]).dt.date.isin([pd.Timestamp(trade_date).date(), pd.Timestamp(sessions[-4]).date()]),
                ["security_id", "date", "quote_ret1"],
            ].rename(columns={"date": "trade_date", "quote_ret1": "ret1"})
            comparison = _common_member_breadth_delta(members, prior_members, quote_history, trade_date, sessions[-4],
                                                       config["thresholds"]["coverage"]["min_common_member_coverage"])
            current = build_sector_current(member_current, current_quotes, config, amount_features=amount, comparison_features=comparison)
            signal_members = members.merge(stock[["security_id", "setup", "recovery", "extended", "close", "ma20"]], on="security_id", how="left")
            early = aggregate_early_width(signal_members)
            current = current.merge(early, on="sector_id", how="left")
            current = current.merge(today_cycle[["sector_id", "q5", "q20", "dq5_3", "ma20_width", "ma20_delta3"]], on="sector_id", how="left")
            lookback = int(config["thresholds"]["potential_branches"]["RECOVERY_BUILD"]["prior_current_lookback_sessions"])
            previous_dates = sessions[max(0, len(sessions) - 1 - lookback):-1]
            prior_rows = connection.execute(
                """select r.trade_date,s.sector_id,s.current_eligible
                     from research_runs r join research_sector_states s on s.run_id=r.run_id
                    where r.status='COMPLETE' and r.algorithm_version=? and r.parameter_hash=?
                      and r.trade_date>=? and r.trade_date<?""",
                [config["algorithm_version"], config["parameter_hash"], previous_dates[0], trade_date],
            ).fetchall() if previous_dates else []
            by_date = {(str(day), str(sector_id)): eligible for day, sector_id, eligible in prior_rows}
            current["prior_current_within10"] = current["sector_id"].astype(str).map(
                lambda sector_id: True if any(by_date.get((day, sector_id)) is True for day in previous_dates)
                else False if all((day, sector_id) in by_date for day in previous_dates) else None
            )
            sectors = build_sector_potential(current, config)
            sectors["current_rank"] = _rank_eligible(sectors, "current", ["p1", "b1", "rel1", "amount_A"])
            sectors["branch_hit_count"] = sectors["branch_results"].map(lambda values: sum(value is True for value in values.values()))
            sectors["potential_rank"] = _rank_eligible(sectors, "potential_eligible", ["branch_hit_count", "dq5_3", "ma20_delta3", "early_width", "amount_A"])
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
            previous_run = connection.execute(
                """select run_id from research_runs where status='COMPLETE' and trade_date<?
                     and algorithm_version=? and parameter_hash=? order by trade_date desc limit 1""",
                [trade_date, config["algorithm_version"], config["parameter_hash"]],
            ).fetchone()
            previous_shortlists = connection.execute(
                "select list_type,security_id from research_shortlist where run_id=?", [previous_run[0]]
            ).fetch_df() if previous_run else None
            associations, shortlists = select_associations_and_shortlists(
                role_members, compact_roles, sectors, config,
                signal_date=str(trade_date), previous_shortlists=previous_shortlists,
            )
            stock_rows = [{"security_id": row["security_id"], "setup": row.get("setup"), "breakout": row.get("breakout"), "recovery": row.get("recovery"), "trend_background": row.get("trend_background"), "structure_break": row.get("structure_break"), "quality": row.get("quality", "PARTIAL"), "bias20": row.get("bias20"), "sigma20": row.get("sigma20"), "extension_z20": row.get("extension_z20"), "dist_high20": row.get("dist_high20"), "range5": row.get("range5"), "range20": row.get("range20"), "rps5_delta3": row.get("rps5_delta3"), "liquidity20_amount": row.get("amount_prior20_median"), "risk_codes": row.get("risk_codes", []), "reason_codes": row.get("reason_codes", []), "evidence": {"selection": row.get("checks", {}), "technical": {"contract_id": row.get("contract_id")}}} for row in stock.to_dict("records")]
            sector_rows = [{**row, "current_eligible": row.get("current"), "potential_branch": row.get("primary_branch"), "potential_branches": row.get("branch_results", {}), "member_count": row.get("total_member_count"), "feature_valid_count": row.get("early_evaluable_count"), "amount_a": row.get("amount_A"), "quality": "PARTIAL" if pd.isna(row.get("dq5_3")) or pd.isna(row.get("ma20_delta3")) else ("READY" if row.get("current") is not None else "PARTIAL"), "evidence": {"current_quality": "READY" if row.get("current") is not None else "UNKNOWN", "potential_history_quality": "UNKNOWN" if pd.isna(row.get("dq5_3")) or pd.isna(row.get("ma20_delta3")) else "READY", "branch_checks": row.get("branch_checks", {})}, "input_members_hash": membership_snapshot_id, "rank_universe_hash": config["parameter_hash"]} for row in sectors.to_dict("records")]
            role_rows = compact_roles.to_dict("records")
            shortlist_rows = shortlists.to_dict("records") if not shortlists.empty else []
            completed = store.complete(run_id, stock_states=stock_rows, sector_states=sector_rows, signal_states=episode_rows, member_roles=role_rows, shortlists=shortlist_rows)
            return {**completed, "publication_id": publication_id, "trade_date": str(trade_date), "stock_count": len(stock_rows), "sector_count": len(sector_rows), "role_count": len(role_rows), "shortlist_count": len(shortlist_rows), "association_count": len(associations)}
        except Exception as exc:
            store.fail(run_id, type(exc).__name__)
            raise


__all__ = ["ResearchBuildError", "build_latest_research_run"]
