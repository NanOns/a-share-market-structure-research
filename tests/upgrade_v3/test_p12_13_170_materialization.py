from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_170_contract_is_explicit_and_separate_from_pilot():
    source = (ROOT / "scripts/run_p12_13_170_materialization.py").read_text(encoding="utf-8")
    assert "PILOT_DAYS = 170" in source
    assert 'DATASET_ROOT = ROOT / "data/research_history_v3_3_170"' in source
    assert 'HISTORY_BASIS = "RECONSTRUCTED_CURRENT_MEMBERSHIP"' in source
    assert 'DATASET_CONTRACT = "TODAY_RESEARCH_HISTORY_BASE_170_V3_3_RECONSTRUCTED_01"' in source
    assert "P12-14_OPTIONAL_TURNOVER_SOURCE" in source


def test_170_contract_keeps_sources_read_only_and_binds_implementation():
    source = (ROOT / "scripts/run_p12_13_170_materialization.py").read_text(encoding="utf-8")
    assert "duckdb.connect(str(DB), read_only=True)" in source
    assert "implementation_hashes" in source
    assert "file_hashes" in source
    assert "latest_production_sector_parity" in source
    assert "insert into" not in source.lower()
