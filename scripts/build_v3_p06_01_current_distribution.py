"""Build the read-only P06-01 CURRENT evidence report from V3-bound inputs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.sector_attention import CONTRACT_ID, build_sector_current

DB_PATH = ROOT / "data" / "database" / "market_research.duckdb"
CONFIG_PATH = ROOT / "config" / "research_attention_v3.yaml"
OUTPUT_PATH = ROOT / "reports" / "upgrade_v3" / "P06-01_CURRENT_DISTRIBUTION.json"


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    publication = connection.execute(
        """select p.publication_id,p.trade_date,pm.membership_snapshot_id
             from publications p join publication_memberships pm using(publication_id)
            where p.status='SUCCESS' order by p.trade_date desc,p.revision desc limit 1"""
    ).fetchone()
    if not publication:
        raise RuntimeError("P06_01_PUBLICATION_BINDING_MISSING")
    publication_id, trade_date, membership_snapshot_id = publication
    members = connection.execute(
        """select e.sector_id,e.security_id,?::date trade_date,
                  json_extract_string(e.payload_json,'$.sector_name') sector_name,
                  json_extract_string(e.payload_json,'$.sector_type') sector_type,
                  json_extract_string(e.payload_json,'$.sector_role') sector_role,
                  t.quote_ret1 ret1
             from membership_entries e
             left join technical_result_daily t
               on t.security_id=e.security_id and t.trade_date=?
            where e.membership_snapshot_id=?""",
        [trade_date, trade_date, membership_snapshot_id],
    ).fetchdf()
    market = connection.execute(
        """select security_id,trade_date,quote_ret1 ret1
             from technical_result_daily where trade_date=?""", [trade_date]
    ).fetchdf()
    amount = connection.execute(
        """select sector_id,trade_date,sector_amount_vs_prior20,amount_contract_id
             from sector_cycle_daily where trade_date=?""", [trade_date]
    ).fetchdf()
    comparison = connection.execute(
        """select sector_id,trade_date,breadth_ret1_common_change_3d b_delta3
             from sector_cycle_daily where trade_date=?""", [trade_date]
    ).fetchdf()
    output = build_sector_current(members, market, config, amount_features=amount, comparison_features=comparison)
    current = output[output["current"].eq(True)]
    weak = output[output["weak"].eq(True)]
    payload = {
        "contract_id": "v3-p06-01-current-distribution-v1.0",
        "sector_current_contract_id": CONTRACT_ID,
        "trade_date": str(trade_date),
        "input": {
            "publication_id": publication_id,
            "membership_snapshot_id": membership_snapshot_id,
            "membership_row_count": int(len(members)),
            "market_quote_row_count": int(len(market)),
            "database_sha256": _sha256(DB_PATH),
            "read_only": True,
        },
        "parameter": {"schema_version": config["schema_version"], "parameter_hash": config["parameter_hash"]},
        "distribution": {
            "sector_count": int(len(output)),
            "current_true": int(len(current)),
            "current_false": int(output["current"].eq(False).sum()),
            "current_unknown": int(output["current"].isna().sum()),
            "weak_true": int(len(weak)),
            "normal_rank_eligible": int(output["normal_rank_eligible"].sum()),
            "amount_A_available": int(output["amount_A"].notna().sum()),
            "top_current": current[["sector_id", "sector_type", "m1", "b1", "rel1", "p1", "amount_A"]].head(10).to_dict("records"),
            "top_rejections": pd.Series([code for codes in output["reason_codes"] for code in codes]).value_counts().head(10).to_dict(),
        },
        "policy": {"database_written": False, "tdx_modified": False, "legacy_rank_used_for_current": False, "effectiveness_claim": False},
    }
    _atomic_json(OUTPUT_PATH, payload)
    print(json.dumps({"status": "PASS", "output": str(OUTPUT_PATH), "current_true": len(current)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
