from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[2]
def test_long_schema():assert {"security_id","queue_name","queue_tier","source_v2_class"}==set(pq.read_table(ROOT/"reports/shadow/v2/20260904/priority/V2_QUEUE_MEMBERSHIP.parquet").column_names)
