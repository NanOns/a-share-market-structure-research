import pandas as pd
import pytest

from workbench_analysis.structures import (
    CONTRACT_VERSION,
    STRUCTURE_BASIS,
    StructureAdapterError,
    build_historical_structure_rows,
    calculate_historical_structures,
)


def _frame():
    return pd.DataFrame(
        [
            {
                "security_id": "SH.600001",
                "trade_date": "2026-09-08",
                "v1_steady_trend": True,
                "continuity_value": 0.65,
                "continuity_valid_count": 20,
                "continuity_valid_ratio": 0.80,
                "pulse_value": 0.20,
                "v1_strong_pullback": False,
                "v1_breakout_prep": False,
                "v1_sector_leader": False,
                "v1_early_mover": False,
                "up_day_ratio20": 0.70,
            },
            {
                "security_id": "SH.600002",
                "trade_date": "2026-09-08",
                "v1_steady_trend": True,
                "v1_strong_pullback": False,
                "v1_breakout_prep": False,
                "v1_sector_leader": False,
                "v1_early_mover": False,
            },
        ]
    )


def test_historical_structure_rows_reuse_mappings_and_keep_unknown_distinct_from_false():
    rows = build_historical_structure_rows(_frame(), cutoff="2026-09-08")
    first = rows[(rows.security_id == "SH.600001") & (rows.queue_name == "STEADY_QUEUE")].iloc[0]
    unknown = rows[(rows.security_id == "SH.600002") & (rows.queue_name == "STEADY_QUEUE")].iloc[0]
    outside = rows[(rows.security_id == "SH.600001") & (rows.queue_name == "PULLBACK_QUEUE")].iloc[0]
    assert first.source_class == "STEADY_CORE" and first.hit is True and first.tier == "CORE"
    assert unknown.source_class == "DATA_INSUFFICIENT" and pd.isna(unknown.hit) and pd.isna(unknown.tier)
    assert outside.source_class == "OUTSIDE_V1_STRONG_PULLBACK" and outside.hit is False
    assert set(rows.structure_basis) == {STRUCTURE_BASIS}
    assert rows.queue_rank.notna().any()


def test_summary_counts_unique_hits_and_marks_unknown_quality():
    result = calculate_historical_structures(_frame(), cutoff="2026-09-08")
    assert result["contract_id"] == CONTRACT_VERSION
    summary = result["summary"].set_index("security_id")
    assert summary.loc["SH.600001", "unique_hit_count"] == 1
    assert summary.loc["SH.600002", "research_band_quality"] == "DATA_INSUFFICIENT"
    assert result["audit"]["formal_observations_written"] is False
    assert result["audit"]["formal_outcomes_written"] is False


def test_future_and_duplicate_structure_inputs_are_rejected():
    with pytest.raises(StructureAdapterError, match="FUTURE_STRUCTURE_INPUT"):
        build_historical_structure_rows(_frame(), cutoff="2026-09-07")
    duplicate = pd.concat([_frame(), _frame().iloc[[0]]], ignore_index=True)
    with pytest.raises(StructureAdapterError, match="STRUCTURE_DUPLICATE_SECURITY_DATE"):
        build_historical_structure_rows(duplicate, cutoff="2026-09-08")


def test_unrecognized_string_flags_remain_unknown():
    frame = pd.DataFrame([{"security_id": "SH.600009", "trade_date": "2026-09-08", "v1_steady_trend": "unknown"}])
    rows = build_historical_structure_rows(frame, cutoff="2026-09-08")
    steady = rows[rows.queue_name == "STEADY_QUEUE"].iloc[0]
    assert steady.source_class == "DATA_INSUFFICIENT" and pd.isna(steady.hit)
