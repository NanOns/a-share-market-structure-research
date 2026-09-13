"""Generate the P05-03 initial signal-distribution evidence atomically."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.research_features import ResearchFeatureContext, build_stock_research_features
from workbench_analysis.stock_attention import CONTRACT_ID, PREDICATE_CONTRACT, classify_stock_frame, signal_distribution
from workbench_analysis.technical import calculate_technical_daily
from workbench_service.research_v3_contracts import parameter_hash


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    config_path = ROOT / "config/research_attention_v3.yaml"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    normalized_path = ROOT / "data/normalized/adjusted_daily.parquet"
    with duckdb.connect() as connection:
        sessions = [str(row[0]) for row in connection.execute(
            "SELECT DISTINCT date FROM read_parquet(?) ORDER BY date DESC LIMIT 110", [str(normalized_path)]
        ).fetchall()][::-1]
        raw = connection.execute(
            """
            SELECT security_id,date AS trade_date,adj_close,raw_close,raw_amount,raw_volume,
                   has_actual_bar,tradable,data_observed,is_synthetic_fill
              FROM read_parquet(?) WHERE date BETWEEN ? AND ?
            """,
            [str(normalized_path), sessions[0], sessions[-1]],
        ).fetch_df()
    raw["price_basis"] = "TDX_NATIVE_QFQ"
    technical = calculate_technical_daily(raw.rename(columns={"trade_date": "date"}), cutoff=sessions[-1])
    for window in (5, 20):
        technical[f"rps{window}"] = technical.groupby("date")[f"ret{window}"].rank(method="average", pct=True)
    features = build_stock_research_features(
        raw,
        technical[["security_id", "date", "rps5", "rps20"]].rename(columns={"date": "trade_date"}),
        sessions,
        ResearchFeatureContext("P05-03-READONLY", "UNBOUND", "UNBOUND", "UNBOUND", "MASTER_CALENDAR", sessions[-1]),
    )
    signals = classify_stock_frame(features, config)
    report = {
        "contract_id": "v3-p05-03-signal-distribution-v1.0",
        "stock_attention_contract_id": CONTRACT_ID,
        "feature_contract_id": str(features.iloc[0]["contract_id"]) if len(features) else None,
        "trade_date": sessions[-1],
        "input": {
            "normalized_path": str(normalized_path),
            "normalized_sha256": _sha256_file(normalized_path),
            "master_session_count": len(sessions),
            "input_row_count": int(len(raw)),
            "output_stock_count": int(len(signals)),
        },
        "parameter": {
            "schema_version": config["schema_version"],
            "parameter_hash": parameter_hash(config),
            "recorded_parameter_hash": config["parameter_hash"],
            "predicate_contract": PREDICATE_CONTRACT,
        },
        "quality": {
            "feature_ready": int(features["quality"].eq("READY").sum()),
            "feature_partial": int(features["quality"].eq("PARTIAL").sum()),
            "liquidity_true": int(features["liquidity20"].eq(True).sum()),
            "liquidity_false": int(features["liquidity20"].eq(False).sum()),
            "liquidity_unknown": int(features["liquidity20"].isna().sum()),
            "extended_true": int(signals["extended"].eq(True).sum()),
            "extended_unknown": int(signals["extended"].isna().sum()),
        },
        "signals": signal_distribution(signals),
        "policy": {
            "thresholds_changed_during_distribution": False,
            "effectiveness_claim": False,
            "database_written": False,
            "tdx_modified": False,
        },
    }
    if report["parameter"]["parameter_hash"] != report["parameter"]["recorded_parameter_hash"]:
        raise RuntimeError("PARAMETER_HASH_MISMATCH")
    output = ROOT / "reports/upgrade_v3/P05-03_SIGNAL_DISTRIBUTION.json"
    _atomic_json(output, report)
    print(json.dumps({"status": "PASS", "output": str(output), "trade_date": sessions[-1]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
