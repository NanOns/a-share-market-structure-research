from pathlib import Path
from workbench_analysis.history_170_v3_3 import load_stock_facts,resolve_dataset
ROOT=Path(__file__).resolve().parents[2]
def test_checked_in_170_dataset_is_verified_and_consumable():
 path,manifest=resolve_dataset(ROOT);rows,identity=load_stock_facts(ROOT,"2026-09-15")
 assert path.is_dir() and manifest["output_digest"]==identity["dataset_digest"]
 assert len(rows)==6182 and identity["rows"]==6182
 assert str(rows["SH.600023"]["trade_date"])[:10]=="2026-09-15"
def test_daily_funnel_binds_170_identity_and_consumes_facts():
 source=(ROOT/"scripts/p12_03_current_funnel.py").read_text(encoding="utf-8")
 assert "load_stock_facts(ROOT,TARGET)" in source and "'history_170':history_identity" in source
