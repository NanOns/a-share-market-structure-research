import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from phase3_runner import bind_phase2
from tdx.gbbq_reader import file_sha256

def test_mixed_generation_rejected(tmp_path):
    r={'generation':'expected','output_sha256':{}}
    for rel in ('data/sectors/sector_factors_daily.parquet','data/market/market_regime_daily.parquet'):
      p=tmp_path/rel;p.parent.mkdir(parents=True,exist_ok=True)
      pq.write_table(pa.table({'v':[1]}).replace_schema_metadata({b'generation':b'wrong'}),p)
      r['output_sha256'][rel]=file_sha256(p)
    with pytest.raises(ValueError): bind_phase2(tmp_path,r)
