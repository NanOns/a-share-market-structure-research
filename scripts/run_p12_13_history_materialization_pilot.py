"""P12-13 bounded 8-session historical materialization pilot."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq
from production.release import atomic_write_json
from tdx.gbbq_reader import read_gbbq
from tdx.security_master import current_a_stock_ids, read_industry_assignments
from workbench_analysis.sector_attention import build_sector_current
from workbench_analysis.today_research_factors_v3_3 import CONTRACT_ID as FACTOR_CONTRACT, calculate_today_facts
from workbench_service.universe import is_workbench_statistical_security_id


PARQUET = ROOT / "data/normalized/adjusted_daily.parquet"
GBBQ = Path("D:/new_tdx/T0002/hq_cache/gbbq")
DB = ROOT / "data/database/market_research.duckdb"
SPEC = ROOT / "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md"
DATASET_ROOT = ROOT / "data/research_history_v3_3"
RECEIPT = ROOT / "reports/p12_13/p12_13_stage_gate.json"
STAGE_CONTRACT = "P12-13_HISTORY_MATERIALIZATION_PILOT_V1"
DATASET_CONTRACT = "TODAY_RESEARCH_HISTORY_BASE_V3_3_RECONSTRUCTED_01"
HISTORY_BASIS = "RECONSTRUCTED_CURRENT_MEMBERSHIP"
PILOT_DAYS = 8


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def equal_number(left, right, tolerance=1e-12) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    return not pd.isna(left) and not pd.isna(right) and abs(float(left) - float(right)) <= tolerance


def load_members(connection, publication_id: str) -> tuple[pd.DataFrame, dict]:
    source_scope, revision, attribute_version_id = connection.execute(
        "select source_scope,revision_no,attribute_version_id from relation_publication_bindings where publication_id=?",
        [publication_id],
    ).fetchone()
    members = connection.execute(
        """select e.sector_id,e.security_id,a.name sector_name,a.type sector_type,a.role sector_role
             from relation_edge_intervals e
             join sector_attribute_revisions ar on ar.source_scope=e.source_scope
              and ('attrset-' || substr(ar.attribute_set_hash,1,24))=?
             join sector_attribute_revision_bindings ab on ab.source_scope=e.source_scope and ab.sector_id=e.sector_id
              and ab.from_attribute_revision<=ar.attribute_revision
              and (ab.to_attribute_revision is null or ar.attribute_revision<ab.to_attribute_revision)
             join sector_attribute_versions a on a.source_scope=ab.source_scope and a.sector_id=ab.sector_id
              and a.attribute_version_id=ab.attribute_version_id
            where e.source_scope=? and e.from_revision<=? and (e.to_revision is null or ?<e.to_revision)""",
        [attribute_version_id, source_scope, revision, revision],
    ).fetchdf().drop_duplicates(["sector_id", "security_id"])
    return members, {"source_scope": source_scope, "revision": revision, "attribute_version_id": attribute_version_id}


def main() -> None:
    config = json.loads((ROOT / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))
    events = defaultdict(list)
    for item in read_gbbq(GBBQ):
        if item.category == 1:
            events[item.security_id].append(xrxd_from_gbbq(item))
    with duckdb.connect(str(DB), read_only=True) as connection:
        publication_id, latest_date = connection.execute(
            "select publication_id,trade_date from publications where status='SUCCESS' order by trade_date desc,revision desc limit 1"
        ).fetchone()
        members, membership_identity = load_members(connection, publication_id)
        sessions = [row[0].isoformat() for row in connection.execute(
            "select distinct date from read_parquet(?) where date<=? order by date", [str(PARQUET), latest_date]
        ).fetchall()]
        targets = sessions[-PILOT_DAYS:]
        if len(targets) != PILOT_DAYS:
            raise RuntimeError("P12_13_INSUFFICIENT_TARGET_SESSIONS")
        first_index = sessions.index(targets[0]) - 21
        if first_index < 0:
            raise RuntimeError("P12_13_INSUFFICIENT_WARMUP")
        load_dates = sessions[first_index:sessions.index(targets[-1]) + 1]
        raw = connection.execute(
            """select security_id,date,raw_open,raw_high,raw_low,raw_close,raw_amount,raw_volume,
                      has_actual_bar,is_synthetic_fill,universe_status
                 from read_parquet(?) where date between ? and ? order by security_id,date""",
            [str(PARQUET), load_dates[0], load_dates[-1]],
        ).fetchall()
        production_sector = connection.execute(
            """select s.sector_id,s.current_eligible,s.m1,s.b1,s.rel1,s.p1,s.member_count,s.quote_valid_count
                 from research_runs r join research_sector_states s using(run_id)
                where r.publication_id=? and r.trade_date=? and r.status='COMPLETE'
                order by s.sector_id""", [publication_id, latest_date]
        ).fetchdf()
    metadata = ROOT / f"data/input_staging/metadata/{latest_date:%Y%m%d}/T0002/hq_cache/tdxhy.cfg"
    market_universe = sorted(current_a_stock_ids(read_industry_assignments(metadata)))
    market_universe = [security_id for security_id in market_universe if is_workbench_statistical_security_id(security_id, ROOT)]
    market_universe_set = set(market_universe)
    market_universe_hash = hashlib.sha256("\n".join(market_universe).encode()).hexdigest()
    by_stock = defaultdict(dict)
    for row in raw:
        by_stock[str(row[0])][row[1].isoformat()] = row
    master_index = {day: index for index, day in enumerate(sessions)}
    all_stock_rows = []
    all_sector_rows = []
    daily = []
    for target in targets:
        target_index = sessions.index(target)
        window_dates = sessions[target_index - 21:target_index + 1]
        cutoff = int(target.replace("-", ""))
        stock_rows = []
        for security_id in sorted(by_stock):
            bars = by_stock[security_id]
            available = [int(day.replace("-", "")) for day in window_dates if day in bars and bars[day][8] is True]
            factors = build_affine_factors(available, [event for event in events[security_id] if event.ex_day <= cutoff]) if available else {}
            factor_input = []
            for day in window_dates:
                row = bars.get(day)
                base = {"date": day, "session_index": master_index[day], "anchor_cutoff": target, "price_basis": "TDX_NATIVE_AFFINE_QFQ"}
                if row is None or row[8] is not True:
                    factor_input.append({**base, "has_actual_bar": False})
                    continue
                factor = factors[int(day.replace("-", ""))]
                factor_input.append({
                    **base, "has_actual_bar": True, "is_synthetic_fill": bool(row[9]),
                    "open": float(factor.qfq_price(row[2])), "high": float(factor.qfq_price(row[3])),
                    "low": float(factor.qfq_price(row[4])), "close": float(factor.qfq_price(row[5])),
                    "raw_open": float(row[2]), "raw_close": float(row[5]),
                    "amount": float(row[6]), "volume": float(row[7]),
                })
            facts = calculate_today_facts(factor_input)
            current = bars.get(target)
            previous = bars.get(window_dates[-2])
            quote_ret1 = None
            if current and previous and current[8] is True and previous[8] is True and current[5] and previous[5]:
                quote_ret1 = float(current[5] / previous[5] - 1)
            stock_rows.append({
                "security_id": security_id, "trade_date": target, "history_basis": HISTORY_BASIS,
                "universe_status": current[10] if current else None, "quote_ret1": quote_ret1, **facts,
            })
        stock = pd.DataFrame(stock_rows).sort_values("security_id", kind="mergesort").reset_index(drop=True)
        stock["trade_date"] = pd.to_datetime(stock["trade_date"], errors="raise").dt.date
        stock["date"] = pd.to_datetime(stock["date"], errors="raise").dt.date
        market = stock.loc[stock["security_id"].isin(market_universe_set), ["security_id", "trade_date", "quote_ret1"]].rename(columns={"quote_ret1": "ret1"})
        member_quotes = members.merge(market[["security_id", "ret1"]], on="security_id", how="left", validate="many_to_one")
        member_quotes["trade_date"] = pd.Timestamp(target).date()
        sectors = build_sector_current(member_quotes, market, config)
        sector_rows = []
        for row in sectors.to_dict("records"):
            sector_rows.append({
                "sector_id": row["sector_id"], "trade_date": target, "sector_type": row["sector_type"],
                "history_basis": HISTORY_BASIS, "current": row["current"],
                "member_count": row["total_member_count"], "quote_valid_count": row["quote_valid_count"],
                "quote_coverage": row["quote_coverage"], "market_quote_coverage": row["market_quote_coverage"],
                "market_m1": row["market_m1"], "m1": row["m1"], "b1": row["b1"],
                "rel1": row["rel1"], "p1": row["p1"], "positive_count": row["positive_count"],
                "top1_positive_share": row["top1_positive_share"],
                "checks_json": json.dumps(row["checks"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                "reason_codes_json": json.dumps(row["reason_codes"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            })
        sector = pd.DataFrame(sector_rows).sort_values("sector_id", kind="mergesort").reset_index(drop=True)
        sector["trade_date"] = pd.to_datetime(sector["trade_date"], errors="raise").dt.date
        all_stock_rows.append(stock)
        all_sector_rows.append(sector)
        daily.append({
            "trade_date": target, "stock_rows": len(stock), "normal_universe_rows": len(market),
            "factor_ready_rows": int(stock["quality"].eq("READY").sum()), "sector_rows": len(sector),
            "current_true": int(sector["current"].eq(True).sum()),
        })
    stocks = pd.concat(all_stock_rows, ignore_index=True)
    sectors = pd.concat(all_sector_rows, ignore_index=True)
    latest_sector = sectors.loc[sectors["trade_date"].eq(pd.Timestamp(targets[-1]).date())].copy()
    parity = production_sector.merge(latest_sector, on="sector_id", suffixes=("_production", "_pilot"), validate="one_to_one")
    parity_mismatches = []
    numeric_pairs = (("m1_production", "m1_pilot"), ("b1_production", "b1_pilot"),
                     ("rel1_production", "rel1_pilot"), ("p1_production", "p1_pilot"),
                     ("member_count_production", "member_count_pilot"),
                     ("quote_valid_count_production", "quote_valid_count_pilot"))
    for row in parity.to_dict("records"):
        left = None if pd.isna(row["current_eligible"]) else bool(row["current_eligible"])
        right = None if pd.isna(row["current"]) else bool(row["current"])
        if left != right or any(not equal_number(row[a], row[b]) for a, b in numeric_pairs):
            parity_mismatches.append(row["sector_id"])
    logical_identity = {
        "contract_id": DATASET_CONTRACT, "stage_contract": STAGE_CONTRACT, "dates": targets,
        "history_basis": HISTORY_BASIS, "factor_contract": FACTOR_CONTRACT,
        "sector_contract": config["contracts"]["sector_current"],
        "adjusted_daily_sha256": sha(PARQUET), "gbbq_sha256": sha(GBBQ),
        "spec_sha256": sha(SPEC), "membership": membership_identity,
        "market_universe_contract": "TDXHY_CURRENT_A_STOCK_IDS_V1",
        "market_universe_count": len(market_universe), "market_universe_hash": market_universe_hash,
        "implementation_hashes": {
            "materializer": sha(Path(__file__)),
            "factor": sha(ROOT / "src/workbench_analysis/today_research_factors_v3_3.py"),
            "sector_current": sha(ROOT / "src/workbench_analysis/sector_attention.py"),
            "config": sha(ROOT / "config/research_attention_v3.yaml"),
        },
        "stock_rows": len(stocks), "sector_rows": len(sectors),
    }
    DATASET_ROOT.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".p12_13.", dir=DATASET_ROOT))
    try:
        stocks.to_parquet(stage / "stock_facts.parquet", index=False, compression="zstd")
        sectors.to_parquet(stage / "sector_current.parquet", index=False, compression="zstd")
        file_hashes = {
            "stock_facts.parquet": sha(stage / "stock_facts.parquet"),
            "sector_current.parquet": sha(stage / "sector_current.parquet"),
        }
        digest = hashlib.sha256(canonical({"identity": logical_identity, "files": file_hashes})).hexdigest()
        target_path = DATASET_ROOT / digest
        reused = target_path.is_dir()
        if reused:
            shutil.rmtree(stage)
        else:
            manifest = {**logical_identity, "output_digest": digest, "files": file_hashes}
            (stage / "manifest.json").write_bytes(canonical(manifest))
            os.replace(stage, target_path)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    manifest = json.loads((target_path / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        if sha(target_path / name) != expected:
            raise RuntimeError("P12_13_DATASET_FILE_HASH_MISMATCH:" + name)
    with duckdb.connect(database=":memory:") as connection:
        stored_stock = connection.execute("select count(*),count(distinct trade_date),count(distinct security_id) from read_parquet(?)", [str(target_path / "stock_facts.parquet")]).fetchone()
        stored_sector = connection.execute("select count(*),count(distinct trade_date),count(distinct sector_id) from read_parquet(?)", [str(target_path / "sector_current.parquet")]).fetchone()
        nonfinite = connection.execute("""select count(*) from read_parquet(?) where
            not isfinite(bias20) or not isfinite(sigma20_v3) or not isfinite(amr20_mean_prior)""", [str(target_path / "stock_facts.parquet")]).fetchone()[0]
        stock_types = dict((row[0], row[1]) for row in connection.execute("describe select * from read_parquet(?)", [str(target_path / "stock_facts.parquet")]).fetchall())
        sector_types = dict((row[0], row[1]) for row in connection.execute("describe select * from read_parquet(?)", [str(target_path / "sector_current.parquet")]).fetchall())
    checks = {
        "eight_sessions": len(targets) == PILOT_DAYS,
        "stock_primary_key_unique": not stocks.duplicated(["trade_date", "security_id"]).any(),
        "sector_primary_key_unique": not sectors.duplicated(["trade_date", "sector_id"]).any(),
        "stored_stock_rows_match": stored_stock[0] == len(stocks) and stored_stock[1] == PILOT_DAYS,
        "stored_sector_rows_match": stored_sector[0] == len(sectors) and stored_sector[1] == PILOT_DAYS,
        "all_daily_populations_nonzero": all(row["stock_rows"] > 0 and row["sector_rows"] > 0 for row in daily),
        "latest_production_sector_parity": len(parity) == len(production_sector) == len(latest_sector) and not parity_mismatches,
        "nonfinite_persisted_values": nonfinite == 0,
        "native_date_types": stock_types.get("trade_date") == "DATE" and stock_types.get("date") == "DATE" and sector_types.get("trade_date") == "DATE",
        "file_hashes_verified": True,
        "tdx_read_only": True,
    }
    acceptance = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    receipt = {
        "stage": "P12-13_HISTORY_MATERIALIZATION_PILOT", "stage_contract": STAGE_CONTRACT,
        "acceptance": acceptance, "acceptance_scope": "8-session reconstructed base facts and sector CURRENT materialization; PIT/effect claims excluded",
        "dataset_contract": DATASET_CONTRACT, "dataset_path": str(target_path), "output_digest": digest,
        "history_basis": HISTORY_BASIS, "dates": targets, "daily": daily,
        "latest_production_parity": {"sector_count": len(parity), "mismatch_count": len(parity_mismatches), "mismatch_sector_ids": parity_mismatches[:20]},
        "stock_rows": len(stocks), "sector_rows": len(sectors), "stored_shapes": {"stock": stored_stock, "sector": stored_sector},
        "files": manifest["files"], "checks": checks, "reused": reused,
        "source_identity": logical_identity, "tdx_modified": False,
        "next_stage": "P12-13_170_SESSION_MATERIALIZATION" if acceptance == "FULL_PASS" else "P12-13_REPAIR",
    }
    atomic_write_json(RECEIPT, receipt)
    print(json.dumps({key: receipt[key] for key in ("stage", "acceptance", "dates", "stock_rows", "sector_rows", "output_digest", "reused", "next_stage")}, ensure_ascii=False, indent=2))
    if acceptance != "FULL_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
