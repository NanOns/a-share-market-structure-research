import pyarrow as pa
import pyarrow.parquet as pq
from phase1_runner import write_parquet

def test_windows_atomic_parquet_write_and_source_guard(tmp_path):
    import pytest
    p=tmp_path/'out'/'data.parquet'; tdx=tmp_path/'tdx'
    write_parquet(p,pa.table({'v':[1,2]}),tdx)
    assert pq.read_table(p)['v'].to_pylist()==[1,2]
    with pytest.raises(ValueError): write_parquet(tdx/'bad.parquet',pa.table({'v':[1]}),tdx)
