import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from phase2_runner import bind_phase1
from tdx.gbbq_reader import file_sha256

def test_mixed_generation_rejected(tmp_path):
    r={'generation':'good'}
    for rel,key in [('data/normalized/adjusted_daily.parquet','adjusted_dataset_sha256'),('data/factors/factors_daily.parquet','factor_dataset_sha256')]:
        p=tmp_path/rel;p.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(pa.table({'v':[1]}).replace_schema_metadata({b'generation':b'bad'}),p)
        r[key]=file_sha256(p)
    with pytest.raises(ValueError):bind_phase1(tmp_path,r)
