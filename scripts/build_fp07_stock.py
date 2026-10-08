"""Publish a read-only actual OHLC index and dated Core/Profile bindings."""
import gzip,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import enter,operational_path
from scripts.build_fp05_market import verified
from workbench_service.current_v4_context import canonical,digest

def main():
    out=enter(7);market=json.loads((operational_path('v4_market_operational_authority_v1.json')).read_bytes());sector=json.loads((operational_path('v4_sector_operational_authority_v1.json')).read_bytes());assert market['input_data_head']==sector['input_data_head']
    assert market['trade_date']==sector['trade_date'],'STOCK_OWNER_DATE_MIX'
    sources=dict(history=market['history'],factors=sector['factors'],profiles=sector['profiles'],unit_contract=ref('src/tdx/tdx_audit.py'),projection_adapter=ref('scripts/build_fp07_stock.py'))
    folder=ROOT/'data/v4/fp07_stocks'/digest(canonical(sources));folder.mkdir(parents=True,exist_ok=True);path=folder/'series.sqlite';tmp=path.with_suffix('.tmp');assert not tmp.exists()
    db=sqlite3.connect(tmp);db.execute('CREATE TABLE bars(security TEXT,day TEXT,payload TEXT,PRIMARY KEY(security,day)) WITHOUT ROWID');count=0;entities=0
    with gzip.open(verified(market['history']),'rt',encoding='utf8') as f:
        for line in f:
            row=json.loads(line);entities+=1
            for b in row['bars']:
                assert b['trade_date']<=market['trade_date'];assert b['volume']>=0 and b['amount']>=0
            db.executemany('INSERT INTO bars VALUES(?,?,?)',[(row['security_id'],b['trade_date'],canonical(b).decode()) for b in row['bars']]);count+=len(row['bars'])
    db.commit();db.close();tmp.replace(path)
    authority=dict(contract_id='FP07_STOCK_OPERATIONAL_AUTHORITY_V1',trade_date=market['trade_date'],input_data_head=market['input_data_head'],factors=sector['factors'],profiles=sector['profiles'],series=ref(path),sources=sources,price_basis='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,volume_unit='SHARES',amount_unit='CNY',intraday='NOT_AVAILABLE_NO_FAKE_MINUTE_BARS')
    write(operational_path('v4_stock_operational_authority_v1.json',for_write=True),authority);write(out/'REAL_MATERIALIZATION.json',dict(authority=authority,bars=count,entities=entities,status='READY_REAL_SOURCE_INDEX'))
    print(json.dumps(dict(status='READY',bars=count,entities=entities)))
if __name__=='__main__':main()
