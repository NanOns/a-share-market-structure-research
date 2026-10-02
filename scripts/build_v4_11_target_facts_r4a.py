"""Accepted source -> full market target producer candidates, no TDX access."""
from scripts.next_round_execution_r4 import *
from src.v4.target_fact_producers_r4 import *
from src.v4.adjustment_basis_r4 import parent_bar,incremental_bar,basis_id,admission
from collections import defaultdict,Counter
import gzip,json,math
import pandas as pd
import pyarrow.parquet as pq
from decimal import Decimal,InvalidOperation
from workbench_analysis.research_features import build_stock_research_features,ResearchFeatureContext
from normalize.universe_recent import qualifies_normal_universe
from market_calendar.trading_calendar import StockTimeline
from src.v4.a02_a05_external_acceptance_r1 import read_accepted_rps

OUT='reports/v4_11_r4a/'
DATA='data/v4/confirmation_candidates_r4/'
REV='_R2'
def coordinate_value(value):
    try:
        number=Decimal(str(value))
        return str(number.normalize()) if number.is_finite() else None
    except (InvalidOperation,ValueError,TypeError):return None
def normalized(value):
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
    if isinstance(value,list):return [normalized(v) for v in value]
    if value is pd.NA or isinstance(value,float) and not math.isfinite(value):return None
    if hasattr(value,'item'):return normalized(value.item())
    return value
def compressed(path,value):
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    atomic_bytes(path,gzip.compress(raw,mtime=0));return bind(path)
def load_sources(target_day='2026-09-30'):
    entry=verify_protected();h=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');chain=read(exact(h['accepted_chain']).relative_to(ROOT).as_posix())
    ctx=read(exact(chain['source_context']).relative_to(ROOT).as_posix());sessions=ctx['calendar']['session_dates'];day=h['accepted_trade_date']
    target=sessions.index(day);window=sessions[max(0,target-129):target+1]
    parent=read(exact(ctx['parent']['components']['ADJUSTED_DAILY']).relative_to(ROOT).as_posix());hist=parent['accepted_source_bindings'][0];path=exact(hist)
    # Aggregate lifetime observed record count and all observed session dates from
    # accepted raw columns. No provider or current TDX filesystem inference.
    table=pq.read_table(path,columns=['canonical_security_id','raw_close'],filters=[('trade_date','<=',20260924)])
    lifetime={r['canonical_security_id']:r['raw_close_count'] for r in table.group_by('canonical_security_id').aggregate([('raw_close','count')]).to_pylist()}
    del table
    observed=defaultdict(set)
    columns=['canonical_security_id','source_security_key','trade_date','raw_open','raw_high','raw_low','raw_close','qfq_open','qfq_high','qfq_low','qfq_close','qfq_mul','qfq_add','volume','amount','adjusted_quality','trading_status','adjustment_source_revision','price_basis']
    history=pq.read_table(path,columns=columns,filters=[('trade_date','>=',int(window[0].replace('-',''))),('trade_date','<=',20260924)]).to_pylist()
    bars={};refs=[bind('data/v4/V4_DATA_ACCEPTED_HEAD.json'),h['accepted_chain'],chain['source_context'],hist,h['calendar'],h['identity']]
    for r in history:
        d=str(r['trade_date']);d=d[:4]+'-'+d[4:6]+'-'+d[6:];sid=r['canonical_security_id']
        if r['raw_close'] is not None:observed[sid].add(r['trade_date'])
        bars[sid,d]=parent_bar(r)
    identity={};status={};isst={};raw={}
    historical_status=bind('data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz');refs.append(historical_status)
    for line in gzip.open(exact(historical_status),'rt',encoding='utf8'):
        record=json.loads(line);d=record['trade_date']
        if window[0]<=d<='2026-09-24':status.setdefault(d,{})[record['security_id']]=record

    for node in chain['nodes']:
        d=node['trade_date']
        if d>target_day:continue
        for cap in ('RAW_DAILY','ADJUSTED_DAILY','IDENTITY_UNIVERSE','TRADING_STATUS','ISST'):
            rec=node['components'][cap];ref=dict(path=rec['artifact_path'],sha256=rec['artifact_sha256'],bytes=rec['artifact_bytes']);refs.append(ref)
            records=read(exact(ref).relative_to(ROOT).as_posix())['rows'];by={r['security_id']:r for r in records}
            if cap=='RAW_DAILY':
                for sid,r in by.items():
                    observed[sid].add(int(d.replace('-','')))
                    if d>'2026-09-24':lifetime[sid]=lifetime.get(sid,0)+1
                    bars.setdefault((sid,d),dict(date=d,security_id=sid)).update(source_security_key=r['source_security_key'],
                        **{'raw_'+k:float(r[k]) for k in ('open','high','low','close')},amount=r['amount'],volume=r['volume'])
                raw[d]=by
            elif cap=='ADJUSTED_DAILY':
                for sid,r in by.items():bars.setdefault((sid,d),dict(date=d,security_id=sid)).update(incremental_bar(r))
            elif cap=='IDENTITY_UNIVERSE':identity[d]=by
            elif cap=='TRADING_STATUS':status[d]=by
            else:isst[d]=by
    refs=list({r['path']:r for r in refs}.values())
    return entry,h,ctx,sessions,window,bars,observed,lifetime,identity,status,isst,raw,refs

def build(day='2026-09-30'):
    entry,h,ctx,sessions,window,bars,observed,lifetime,identity,status,isst,raw,refs=load_sources(day)
    window=[d for d in window if d<=day];universe=sorted(identity[day]);cutoff=entry['observed_at_utc']
    rps=read_accepted_rps(ROOT,day);rphead=bind('data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json');refs.append(rphead)
    pub=rps['scores'] if 'scores' in rps else rps['publication']
    score_rows=pub['rows'] if isinstance(pub,dict) else pub
    score={r['security_id']:r for r in score_rows};deltas={r['security_id']:r for r in rps['deltas'][3]}
    cfg=read('config/research_attention_v3.yaml')
    rs=[]
    for d in (day,sessions[sessions.index(day)-3]):
        rp=read_accepted_rps(ROOT,d);q=rp.get('scores',rp.get('publication'))
        for r in q['rows'] if isinstance(q,dict) else q:rs.append(dict(security_id=r['security_id'],trade_date=d,rps5=None if r['rps5']['value'] is None else r['rps5']['value']/100,rps20=None if r['rps20']['value'] is None else r['rps20']['value']/100))
    raw_features=[];windows={};normal={};normal_evidence={};reason={}
    for sid in universe:
        target=bars.get((sid,day),{});slots=[]
        for d in window:
            original=bars.get((sid,d),{});error=admission(original,target)
            ready=error is None
            state=status.get(d,{}).get(sid,{}).get('status',original.get('trading_status'))
            r=dict(original,date=d,session_index=sessions.index(d),anchor_cutoff=day,has_actual_bar=ready,
                adjustment_basis_id=basis_id(original),basis_admission_reason=error,accepted_trading_status=state,
                raw_actual_bar=all(original.get('raw_'+k) is not None for k in ('open','high','low','close')),is_synthetic_fill=False)
            slots.append(r)
            raw_features.append(dict(security_id=sid,trade_date=d,adj_close=r.get('close') if ready else None,raw_amount=r.get('amount'),
                has_actual_bar=r['raw_actual_bar'],price_basis='TDX_NATIVE_QFQ',adjustment_status='VERIFIED_REPRODUCIBLE_TDX_NATIVE' if ready else 'UNKNOWN',
                project_price_basis='FORWARD_ADJUSTED',adjustment_version=basis_id(original),is_synthetic_fill=False))
        windows[sid]=slots
        dates=observed[sid];timeline=StockTimeline(sid,min(dates) if dates else None,max(dates) if dates else None,lifetime.get(sid,0),frozenset(dates),
            file_exists=bool(dates),structurally_valid=bool(dates),current_member=identity[day][sid]['identity_status']=='IDENTITY_BOUND')
        normal[sid],normal_evidence[sid]=qualifies_normal_universe(timeline,[int(d.replace('-','')) for d in window[-120:]])
        reason[sid]=window_reason(slots[-27:])
    features=build_stock_research_features(pd.DataFrame(raw_features),pd.DataFrame(rs),window,
        ResearchFeatureContext(CONTRACT,CONTRACT+':'+day,h['source_revision'],'NO_SECTOR_INPUT',ctx['calendar']['publication_id'],day),
        liquidity20_amount_gte=cfg['thresholds']['stock_signals']['risk']['liquidity20_amount_gte'])
    features={r['security_id']:normalized(r) for r in features.to_dict('records')}
    manifest=read('config/v4_11_legacy_extraction_manifest_r2.json');rows=[];calculations=[];source_digest=digest(refs)
    for sid in universe:
        feature=features[sid];sd=score.get(sid,{});dd=deltas.get(sid,{}).get('fields',{}).get('rps5_delta3',{})
        feature['rps20']=sd.get('rps20',{}).get('value');feature['rps20']=feature['rps20']/100 if feature['rps20'] is not None else None
        feature['rps5_delta3']=dd.get('value');feature['rps5_delta3']=feature['rps5_delta3']/100 if feature['rps5_delta3'] is not None else None
        compatible=all(identity[day][sid]['source_security_key']==r.get('source_security_key') for r in (raw[day].get(sid,{}),status[day].get(sid,{})) if r)
        values,signals=produce(windows[sid][-27:],feature,normal_universe=normal[sid],identity_compatible=compatible,parameters=cfg)
        facts={};window_digest=digest(windows[sid][-27:])
        for f in manifest['input_fields']:
            value=normalized(values.get(f));why=None if value is not None else DIAGNOSTIC.get(f,dd.get('unknown_reason') if f=='rps5_delta3' else sd.get('rps20',{}).get('unknown_reason') if f=='rps20' else field_reason(f,windows[sid],feature,sd,dd))
            facts[f]=dict(value=value,quality='KNOWN' if value is not None else 'UNKNOWN',reason=why or ('ZERO_DENOMINATOR' if value is None else None),
                unit=manifest['input_units'][f],time_role='DIAGNOSTIC_EXCLUDED' if f in DIAGNOSTIC else manifest['input_time_roles'][f],
                producer_contract_id=CONTRACT,parameter_set_id=PARAMETERS,system_available_at=cutoff,
                window_identity=window_digest,source_digest=source_digest,
                knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
        rows.append(dict(security_id=sid,trade_date=day,facts=facts))
        calculations.append(normalized(dict(security_id=sid,trade_date=day,window=windows[sid],values=values,feature=feature,signals=signals,normal_evidence=normal_evidence[sid])))
    publication=seal(dict(contract_id=CONTRACT,producer_contract_id=CONTRACT,parameter_set_id=PARAMETERS,trade_date=day,
        knowledge_cutoff=cutoff,scope='REAL_ACCEPTED_SOURCE_CANDIDATE',accepted=False,AS_RECORDED=False,
        knowledge_lineage='RECONSTRUCTED_CORRECTED',source_bindings=refs,source_digest=digest(refs),rows=rows,permissions=PERMISSIONS))
    validate(publication,ROOT,expected_sources=refs)
    return publication,calculations


def window_reason(slots):
    if slots[-1].get('accepted_trading_status')=='SUSPENDED':return 'CURRENT_BAR_SUSPENDED'
    if not slots[-1].get('raw_actual_bar'):return 'UNEXPLAINED_DATA_GAP'
    for r in slots:
        if r.get('accepted_trading_status')=='SUSPENDED':return 'CONFIRMED_SUSPENSION_IN_LEGACY_MASTER_WINDOW'
        if not r.get('raw_actual_bar'):return 'UNEXPLAINED_DATA_GAP'
        if r.get('basis_admission_reason'):return r['basis_admission_reason']
    return 'INSUFFICIENT_HISTORY'

def field_reason(field,slots,feature=None,rps=None,delta=None):
    feature=feature or {};rps=rps or {};delta=delta or {}
    if field=='clv' and slots[-1].get('has_actual_bar') and slots[-1].get('high')==slots[-1].get('low'):return 'ZERO_DENOMINATOR'
    if field=='trend_background_v3' and feature.get('rps20') is None:return 'ACCEPTED_RPS_UNAVAILABLE:'+str(rps.get('rps20',{}).get('unknown_reason'))
    if field in ('setup_v3','recovery_v3') and feature.get('rps5_delta3') is None:return 'ACCEPTED_RPS_UNAVAILABLE:'+str(delta.get('unknown_reason'))
    if field.endswith('_v3') and feature.get('price_basis') is None:return window_reason(slots[-101:])
    lengths={'structure_break_v3':60,'extended_v3':60,'trend_background_v3':60,'ma20_nondeclining_3':24,'prior5_below_ma20_count':25,'break_high20':21,'ma5_rising_3':8,'ret5':6,'close_above_prior_high':2,'close_to_ma5':5}
    return window_reason(slots[-lengths.get(field,27):])
