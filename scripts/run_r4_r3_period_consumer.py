"""Actual unchanged current period consumers over independent exact candidate bars."""
from pathlib import Path
import sys,json,os,hashlib
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.run_r4_r3_exact_http import oracle_price
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_service.core_product_bff_r1 import dated_product_manifest,CoreProductBFFR1
from workbench_analysis.r43_owner_replay import checked,transform_window
from workbench_analysis.operational_daily_periods_v1 import derive_periods
from workbench_analysis.exact_period_consumer_r3 import derive_exact_periods
from workbench_analysis.market_source_acquisition import official_sessions
from workbench_db.v4_history_pg_r1 import read
from adjustment.tdx_adjustment_v0_3 import build_affine_factors,xrxd_from_gbbq
from adjustment.exact_factor_transport_r1 import ExactFactorTransport
from adjustment.exact_ohlc_consumer_r1 import consume_exact_ohlc
from tdx.gbbq_reader import read_gbbq

def main():
    root=Path('G:/codex_tmp/r4_r3_ui_candidate');out=ROOT/'docs/audits/r4_r3_semantics_http_20261011'
    api=accepted_api(root);day='2026-10-09';authority=json.loads((root/'config/core_product_read_authority_r1.json').read_bytes())
    manifest=dated_product_manifest(root,authority,day);calendar=official_sessions(root)
    source=api.candidate['source_registry'][day]['gbbq'];path=checked(root,source);blob=path.read_bytes();events=read_gbbq(path)
    dispositions=json.loads((root/'config/v4_02_gbbq_price_impact_classification_v1.json').read_bytes())['dispositions']
    sid='SEC-3A5B40C6141461B88CA555E0BB852BDF';symbol='SH.688553';series=read(root,manifest['history_index'],day,sid)
    chosen=[e for e in events if e.security_id.upper()==symbol];dates=[int(row['trade_date'].replace('-','')) for row in series]
    factors=build_affine_factors(dates+[20261009],[xrxd_from_gbbq(e) for e in chosen if e.category==1 and e.event_date<=20261009])
    exact=[];raw_tuples=[];difference=[]
    for row,date in zip(series,dates):
        raw=dict(security_id=symbol,trade_date=date,**dict(zip(('open','high','low','close'),map(str,row['raw_ohlc']))))
        wire=ExactFactorTransport(symbol,20261009,source['sha256'],factors[date]).to_dict()
        result=consume_exact_ohlc(raw,wire,source_bytes=blob,security_id=symbol,basis_date=20261009)
        qfq=[float(result['prices'][key]) for key in ('open','high','low','close')]
        assert qfq==[oracle_price(value,date,chosen,20261009) for value in row['raw_ohlc']]
        exact.append(dict(row,qfq_ohlc=qfq))
        cents=[int(Decimal(str(value))*100) for value in row['raw_ohlc']]
        assert [Decimal(value)/100 for value in cents]==list(map(lambda v:Decimal(str(v)),row['raw_ohlc']))
        raw_tuples.append((date,*cents,row['amount'],row['volume'],0))
    # Existing real daily producer remains untouched; expose every value delta.
    old=transform_window(raw_tuples,chosen,dispositions,day)
    for oldrow,newrow in zip(old,exact):
        if oldrow['qfq_ohlc']!=newrow['qfq_ohlc']:difference.append(dict(trade_date=newrow['trade_date'],old=oldrow['qfq_ohlc'],new=newrow['qfq_ohlc']))
    member=dict(security_id=sid,source_security_key=symbol)
    periods=derive_exact_periods(member,exact,{},calendar,day,calendar[-1])
    numerical=0
    for basis in ('PERIOD_RAW','PERIOD_ADJUSTED'):
        for period in periods[basis]:
            known=[row for row in exact if period['first_source_date'] and period['first_source_date']<=row['trade_date']<=period['max_source_date']]
            if not known:continue
            prices=[row['raw_ohlc'] if basis=='PERIOD_RAW' else row['qfq_ohlc'] for row in known]
            expected=[prices[0][0],max(p[1] for p in prices),min(p[2] for p in prices),prices[-1][3]]
            assert list(map(float,(period[p] for p in ('open','high','low','close'))))==expected
            assert period['volume']==sum(row['volume'] for row in known)
            assert abs(period['amount']-sum(row['amount'] for row in known))<1e-6
            numerical+=6
    negatives=[]
    for name,args in [('future_target',(member,exact,{},calendar,'2099-01-01',calendar[-1])),
            ('duplicate_bar',(member,exact+[exact[-1]],{},calendar,day,calendar[-1]))]:
        try:derive_periods(*args)
        except ValueError as exc:negatives.append(dict(name=name,result='REFUSED',reason=str(exc)))
        else:raise AssertionError(name)
    # A source calendar gap remains blocked, not silently a suspension.
    missing=exact[:-2]+exact[-1:]
    gap=derive_exact_periods(member,missing,{},calendar,day,calendar[-1])
    gapfile=out/'REAL_PERIOD_GAP_RAW.json';gaptmp=gapfile.with_suffix('.json.tmp');gaptmp.write_text(json.dumps(dict(removed=exact[-2],periods=gap),indent=2),encoding='utf8');os.replace(gaptmp,gapfile)
    assert any(row['period_status']=='BLOCKED_BY_UNKNOWN_STATUS' for row in gap['PERIOD_ADJUSTED'])
    files=['scripts/run_r4_r3_period_consumer.py','src/workbench_analysis/exact_period_consumer_r3.py','src/workbench_analysis/operational_daily_periods_v1.py','src/workbench_analysis/dm01_incremental_component_builders_r3_3.py','src/workbench_analysis/r43_owner_replay.py']
    result=dict(contract_id='R4_R3_TYPED_EXACT_DAILY_PERIOD_PRODUCER_CONSUMER_R1',source_bindings={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
        source_gbbq=source,history_index=manifest['history_index'],security_id=sid,symbol=symbol,
        exact_ohlc_oracle_cells=len(exact)*4,period_oracle_cells=numerical,old_real_producer_deltas=difference,
        period_rows=periods,negative_vectors=negatives,gap='BLOCKED_BY_UNKNOWN_STATUS',
        status='SCOPED_PASS',production_loaded=False,knowledge_lineage='RECONSTRUCTED',PIT_ELIGIBLE=False)
    dest=out/'REAL_DAILY_PERIOD_CONSUMER_ORACLE.json';tmp=dest.with_suffix('.json.tmp');tmp.write_text(json.dumps(result,indent=2),encoding='utf8');os.replace(tmp,dest)
    print(json.dumps(dict(exact_cells=len(exact)*4,period_cells=numerical,producer_changed_rows=len(difference),status='SCOPED_PASS')))

if __name__=='__main__':main()
