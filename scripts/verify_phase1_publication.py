"""Read-only final publication verification, including sealed five-point QFQ values."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import sys
import numpy as np
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from validation.phase0_2b import read_frozen
from factors.registry import NAMES

ROOT=Path(__file__).resolve().parents[1]


def verify():
    r=json.loads((ROOT/'reports/phase1/PHASE1_FINAL_RECEIPT.json').read_text('utf8'))
    for rel,key in [('data/normalized/adjusted_daily.parquet','adjusted_dataset_sha256'),
                    ('data/factors/factors_daily.parquet','factor_dataset_sha256')]:
        h=hashlib.sha256()
        with (ROOT/rel).open('rb') as f:
            for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
        assert h.hexdigest()==r[key],rel
    normalized=ROOT/'data/normalized/adjusted_daily.parquet'
    pf=pq.ParquetFile(normalized)
    assert pf.metadata.num_rows==r['adjusted_dataset_rows']
    assert pf.schema_arrow.metadata[b'generation'].decode()==r['generation']
    five=read_frozen(ROOT/'reports/phase0_2b/run_001','local.json')
    for sample in five:
        sid=sample['security_id']; day=str(sample['date'])
        from datetime import date
        d=date(int(day[:4]),int(day[4:6]),int(day[6:]))
        table=pq.read_table(normalized,filters=[('security_id','=',sid),('date','=',d)])
        assert table.num_rows==1
        row=table.to_pylist()[0]
        for f in ('open','high','low','close'):
            assert row['raw_'+f]==Decimal(str(sample['raw'][f]))
            assert row['adj_'+f]==Decimal(str(sample['qfq'][f]))
        assert Decimal(row['qfq_mul'])==Decimal(sample['local_A'])
        assert Decimal(row['qfq_add'])==Decimal(sample['local_B'])
    factor=pq.read_table(ROOT/'data/factors/factors_daily.parquet').to_pandas()
    assert len(factor)==r['factor_dataset_rows']
    assert not factor.duplicated(['security_id','date']).any()
    assert set(factor.price_basis)=={'TDX_NATIVE_QFQ'}
    assert set(factor.factor_version)=={r['factor_contract_version']}
    assert not np.isinf(factor[NAMES].to_numpy(dtype=float)).any()
    latest=factor[factor.date==factor.date.max()]
    assert latest.universe_status.eq('IN_NORMAL_UNIVERSE').sum()==r['normal_universe_count']
    print('PASS: publication hashes/generation, five sealed RAW/QFQ/A/B points, factor keys and latest universe')

if __name__=='__main__': verify()
