from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pilot_contract_is_bounded_and_reconstructed():
    source = (ROOT / "scripts/run_p12_13_history_materialization_pilot.py").read_text(encoding="utf-8")
    assert "PILOT_DAYS = 8" in source
    assert 'HISTORY_BASIS = "RECONSTRUCTED_CURRENT_MEMBERSHIP"' in source
    assert "events[security_id] if event.ex_day <= cutoff" in source.replace("for event in ", "")
    assert "D:/new_tdx/T0002/hq_cache/gbbq" in source
    assert "to_parquet" in source and "compression=\"zstd\"" in source


def test_pilot_does_not_enter_170_day_or_production_database_write():
    source = (ROOT / "scripts/run_p12_13_history_materialization_pilot.py").read_text(encoding="utf-8")
    assert "PILOT_DAYS = 170" not in source
    assert "duckdb.connect(str(DB), read_only=True)" in source
    assert "insert into" not in source.lower()
