"""Publish a read-only actual OHLC index and dated Core/Profile bindings."""
import gzip,json,sys
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
    folder=ROOT/'data/v4/fp07_stocks_pg_r1'/digest(canonical(sources));folder.mkdir(parents=True,exist_ok=True);path=folder/'series.pg.json'
    from workbench_db.v4_series_pg_r1 import build
    def rows():
        with gzip.open(verified(market['history']),'rt',encoding='utf8') as f:
            for line in f:
                row=json.loads(line)
                for b in row['bars']:
                    if b['volume']<0 or b['amount']<0:raise ValueError('STOCK_NEGATIVE_TURNOVER')
                    yield row['security_id'],b['trade_date'],b
    index=build(ROOT,path,rows(),t0=market['trade_date'],source_digest=market['history']['sha256'])
    # The stock chart route reads immutable PG history by the accepted data
    # Head and exact history artifact digest.  Keep that version alongside
    # the stock authority so the snapshot consumer can prove the same scope.
    from workbench_db.v4_history_pg_r1 import build as build_history
    def history_rows():
        with gzip.open(verified(market['history']),'rt',encoding='utf8') as f:
            for line in f:
                yield json.loads(line)
    history_index=build_history(ROOT,history_rows(),head_token=market['input_data_head']['sha256'],
        t0=market['trade_date'],source_digest=market['history']['sha256'])
    count=index['bar_count'];entities=index['symbol_count']
    authority=dict(contract_id='FP07_STOCK_OPERATIONAL_AUTHORITY_V1',trade_date=market['trade_date'],input_data_head=market['input_data_head'],factors=sector['factors'],profiles=sector['profiles'],series=ref(path),history_index=history_index,sources=sources,price_basis='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,volume_unit='SHARES',amount_unit='CNY',intraday='NOT_AVAILABLE_NO_FAKE_MINUTE_BARS')
    write(operational_path('v4_stock_operational_authority_v1.json',for_write=True),authority);write(out/'REAL_MATERIALIZATION.json',dict(authority=authority,bars=count,entities=entities,status='READY_REAL_SOURCE_INDEX'))
    print(json.dumps(dict(status='READY',bars=count,entities=entities)))
if __name__=='__main__':main()
