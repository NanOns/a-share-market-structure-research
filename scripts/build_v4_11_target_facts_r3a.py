"""Accepted source -> full market target producer candidates, no TDX access."""
from scripts.next_round_execution_r3 import *
from src.v4.target_fact_producers_r3 import *
from collections import defaultdict,Counter
import gzip,json,math
import pandas as pd
import pyarrow.parquet as pq
from decimal import Decimal,InvalidOperation
from workbench_analysis.research_features import build_stock_research_features,ResearchFeatureContext
from normalize.universe_recent import qualifies_normal_universe
from market_calendar.trading_calendar import StockTimeline
from src.v4.a02_a05_external_acceptance_r1 import read_accepted_rps

OUT='reports/v4_11_r3a/'
DATA='data/v4/confirmation_candidates_r3/'
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
    columns=['canonical_security_id','source_security_key','trade_date','raw_open','raw_high','raw_low','raw_close','qfq_open','qfq_high','qfq_low','qfq_close','qfq_mul','qfq_add','volume','amount','adjusted_quality','trading_status','adjustment_source_revision']
    history=pq.read_table(path,columns=columns,filters=[('trade_date','>=',int(window[0].replace('-',''))),('trade_date','<=',20260924)]).to_pylist()
    bars={};refs=[bind('data/v4/V4_DATA_ACCEPTED_HEAD.json'),h['accepted_chain'],chain['source_context'],hist,h['calendar'],h['identity']]
    for r in history:
        d=str(r['trade_date']);d=d[:4]+'-'+d[4:6]+'-'+d[6:];sid=r['canonical_security_id']
        if r['raw_close'] is not None:observed[sid].add(r['trade_date'])
        bars[sid,d]=dict(date=d,security_id=sid,source_security_key=r['source_security_key'],
            **{k:float(r['qfq_'+k]) if r['qfq_'+k] is not None else None for k in ('open','high','low','close')},
            **{'raw_'+k:float(r['raw_'+k]) if r['raw_'+k] is not None else None for k in ('open','high','low','close')},
            amount=r['amount'],volume=r['volume'],quality=r['adjusted_quality'],mul=str(r['qfq_mul']),add=str(r['qfq_add']))
    identity={};status={};isst={};raw={}
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
                for sid,r in by.items():bars.setdefault((sid,d),dict(date=d,security_id=sid)).update(
                    **{k:float(r[k]) if r[k] is not None else None for k in ('open','high','low','close')},quality=r['adjustment_readiness'],mul=r['qfq_mul'],add=r['qfq_add'])
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
        target=bars.get((sid,day),{});coordinate=[coordinate_value(target.get(k)) for k in ('mul','add')];slots=[]
        for d in window:
            original=bars.get((sid,d),{});row_coordinate=[coordinate_value(original.get(k)) for k in ('mul','add')]
            ready=original.get('quality')=='READY' and all(x is not None for x in coordinate) and coordinate==row_coordinate and all(original.get(k) is not None for k in ('open','high','low','close'))
            r=dict(original,date=d,session_index=sessions.index(d),anchor_cutoff=day,price_basis='TDX_NATIVE_AFFINE_QFQ',has_actual_bar=ready,
                raw_actual_bar=all(original.get('raw_'+k) is not None for k in ('open','high','low','close')),is_synthetic_fill=False)
            slots.append(r)
            raw_features.append(dict(security_id=sid,trade_date=d,adj_close=r.get('close') if ready else None,raw_amount=r.get('amount'),
                has_actual_bar=r['raw_actual_bar'],price_basis='TDX_NATIVE_QFQ',adjustment_status='VERIFIED_REPRODUCIBLE_TDX_NATIVE' if ready else 'UNKNOWN',
                project_price_basis='FORWARD_ADJUSTED',adjustment_version=digest(list(coordinate)),is_synthetic_fill=False))
        windows[sid]=slots
        dates=observed[sid];timeline=StockTimeline(sid,min(dates) if dates else None,max(dates) if dates else None,lifetime.get(sid,0),frozenset(dates),
            file_exists=bool(dates),structurally_valid=bool(dates),current_member=identity[day][sid]['identity_status']=='IDENTITY_BOUND')
        normal[sid],normal_evidence[sid]=qualifies_normal_universe(timeline,[int(d.replace('-','')) for d in window[-120:]])
        reason[sid]='CURRENT_BAR_SUSPENDED' if sid not in raw[day] else 'ADJUSTMENT_UNKNOWN' if target.get('quality')!='READY' else 'MISSING_OR_MIXED_COORDINATE_MASTER_SESSION'
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
            value=normalized(values.get(f));why=None if value is not None else DIAGNOSTIC.get(f,dd.get('unknown_reason') if f=='rps5_delta3' else sd.get('rps20',{}).get('unknown_reason') if f=='rps20' else reason[sid])
            facts[f]=dict(value=value,quality='KNOWN' if value is not None else 'UNKNOWN',reason=why or ('ZERO_DENOMINATOR' if value is None else None),
                unit=manifest['input_units'][f],time_role='DIAGNOSTIC_EXCLUDED' if f in DIAGNOSTIC else manifest['input_time_roles'][f],
                producer_contract_id=CONTRACT,parameter_set_id=PARAMETERS,system_available_at=cutoff,
                window_identity=window_digest,source_digest=source_digest,
                knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
        rows.append(dict(security_id=sid,trade_date=day,facts=facts))
        calculations.append(normalized(dict(security_id=sid,trade_date=day,window=windows[sid][-27:],values=values,feature=feature,signals=signals,normal_evidence=normal_evidence[sid])))
    publication=seal(dict(contract_id=CONTRACT,producer_contract_id=CONTRACT,parameter_set_id=PARAMETERS,trade_date=day,
        knowledge_cutoff=cutoff,scope='REAL_ACCEPTED_SOURCE_CANDIDATE',accepted=False,AS_RECORDED=False,
        knowledge_lineage='RECONSTRUCTED_CORRECTED',source_bindings=refs,source_digest=digest(refs),rows=rows,permissions=PERMISSIONS))
    validate(publication,ROOT,expected_sources=refs)
    return publication,calculations

def main():
    entry=verify_protected();manifest=read('config/v4_11_legacy_extraction_manifest_r2.json')
    stage=write(OUT+'R3A_STAGE_CONTRACT.json',dict(stage_contract=bind(DOCROOT+TASKS[0]),master=bind(MASTER),authority=bind(AUDIT),phase0=entry['phase0'],
        exact_legacy_sources=[bind(p) for p in ('src/workbench_analysis/today_research_factors_v3_3.py','src/workbench_analysis/research_features.py','src/workbench_analysis/stock_attention.py','src/normalize/universe_recent.py','scripts/p12_03_current_funnel.py')],permissions=PERMISSIONS,
        acceptance='CANDIDATE_ONLY',next_stage='SEAL_R3A_PLUS_R3B_BEFORE_R3C'))
    contract=write('config/v4_11_target_fact_producers_r3a_v1.json',dict(contract_id=CONTRACT,parameter_set_id=PARAMETERS,stage=stage,
        parameters=bind('config/research_attention_v3.yaml'),source_bindings=read('data/v4/V4_DATA_ACCEPTED_HEAD.json'),
        price_coordinate='TARGET_AFFINE_IDENTITY_MUST_MATCH_EVERY_PRICE_SLOT; otherwise UNKNOWN',
        raw_amount_unit='CNY (TDX native float amount; no unit scaling)',amount_factor_source='calculate_today_facts; identity-affine raw window, only AMR20/LIQ20 outputs consumed',
        normal_universe='Exact qualifies_normal_universe: accepted historical record count>=120, recent120 coverage>=.75, latest raw actual required; accepted RAW source replaces filesystem lookup',
        window_valid='True when legacy factor quality READY, otherwise UNKNOWN; missing is never false',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
        provider_status='NOT_QUERIED_THIS_TASK; all sources locally bound accepted artifacts',diagnostic=DIAGNOSTIC,permissions=PERMISSIONS))
    pubs={};calcs={};summary={}
    for day in ('2026-09-29','2026-09-30'):
        pub,calc=build(day);pubs[day]=compressed(DATA+'TARGET_FACTS_'+day+'_R3A'+REV+'.json.gz',pub);calcs[day]=compressed(DATA+'CALCULATIONS_'+day+'_R3A'+REV+'.json.gz',calc)
        summary[day]={f:dict(known=sum(r['facts'][f]['value'] is not None for r in pub['rows']),unknown=sum(r['facts'][f]['value'] is None for r in pub['rows']),
            unknown_reasons=dict(Counter(r['facts'][f]['reason'] for r in pub['rows'] if r['facts'][f]['value'] is None))) for f in manifest['input_fields']}
    matrix=[]
    for f in manifest['input_fields']:
        source='stock_attention.classify_stock_attention' if f.endswith('_v3') else 'qualifies_normal_universe' if f=='normal_universe' else 'A02 accepted RPS explicit date publication' if f.startswith('rps') else 'calculate_today_facts / exact P12-03 projection'
        matrix.append(dict(field=f,legacy_source_symbol=source,formula_AST=manifest['exact_function_AST'].get('scan_today_research'),unit=manifest['input_units'][f],time_role=manifest['input_time_roles'][f],
            target_prior_window=manifest.get('input_window_roles',{}).get(f,'EXPLICIT_MASTER_WINDOW_TARGET_AND_PRIOR_SLOTS'),accepted_upstream_source=pub['source_bindings'],producer_contract=CONTRACT,
            parameter_set=PARAMETERS,publication_namespace='V4_11_R3_FACTS',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
            current_capability='DIAGNOSTIC_ONLY' if f in DIAGNOSTIC else 'EXISTING_ACCEPTED_PRODUCER' if f.startswith('rps') or f in ('actual_bar','input_identity_compatible') else 'FORMAL_CANDIDATE_PRODUCER',
            capability_reason=DIAGNOSTIC.get(f),target_counts=summary['2026-09-30'][f]))
    matrixref=write(OUT+'REQUIRED_FIELD_CAPABILITY_MATRIX'+REV+'.json',dict(contract_id='V4_11_REQUIRED_FIELD_CAPABILITY_MATRIX_R3A',fields=matrix))
    sr=write(OUT+'TARGET_FIELD_COVERAGE'+REV+'.json',dict(universe_20260930=5224,by_date=summary,publications=pubs,source_digest=pub['source_digest'],publication_digest=pub['logical_digest'],contract=contract))
    sealed=write(OUT+'R3A_SEALED_PRODUCER_SET'+REV+'.json',dict(status='V4_11_R3A_TARGET_FACT_PRODUCERS_CANDIDATE_READY',sealed=True,accepted=False,contract=contract,
        runtime=bind('src/v4/target_fact_producers_r3.py'),builder=bind('scripts/build_v4_11_target_facts_r3a.py'),publications=pubs,calculations=calcs,matrix=matrixref,coverage=sr,
        permissions=PERMISSIONS,next_stage='R3C_ONLY_AFTER_R3B_SEALED'))
    verify_protected();print(json.dumps(dict(sealed=sealed,status='CANDIDATE_READY',coverage=summary['2026-09-30'])))
if __name__=='__main__':main()
