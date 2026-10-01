"""Append-only full historical producer repair; no accepted-head publication."""
from contextlib import ExitStack
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
import gzip,hashlib,io,json,os,sys,tempfile,itertools
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.status_st_authority_r1 import load_accepted_dated_evidence,produce_trading_status,produce_st
from workbench_analysis.dm01_extracted_domain_r1 import evaluate_price_base
from workbench_analysis.limit_rules import LimitStateService
from workbench_analysis.price_reference_state import PreviousCloseState

OUTDIR=ROOT/'data/v4/artifact_store/a12_authority_candidate_r1'
PATHS={k:'data/v4/artifact_store/v4_02/'+v for k,v in {
    'status':'V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz','st':'V4_02_DATED_ST_STATUS_R7_20260927.jsonl.gz',
    'price':'V4_02_PRICE_LIMIT_R6_20260927.jsonl.gz','daily':'V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet'}.items()}
PATHS['universe']='data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz'
PATHS['producer']='config/v4_02_status_st_authority_r1.json'
FIELDS=('security_id','source_security_key','trade_date','trading_status','is_st','risk_status','reference_price','reference_basis','rule_id','limit_up_price','limit_down_price','limit_status','reason','special_price_phase')

def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()+b'\n'
def identity(r):return tuple(r[k] for k in ['security_id','source_security_key','trade_date'])
def main():
    governing=read('config/source_authority_governance_r1.json')
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in governing['protected_bindings'])
    inputs={k:bind(p) for k,p in PATHS.items()};contract=read(PATHS['producer']);facts=load_accepted_dated_evidence(ROOT,contract)
    local_inventory=[dict(source=inputs['daily'],can_prove='DATED_ACTUAL_TDX_OHLC_AND_BAR_PRESENCE',cannot_prove=['SUSPENSION_FROM_ABSENCE','ST_STATE','LEGAL_LIFECYCLE'],dated=True,accepted=True),
        dict(source=bind('data/v4/V4_01_ACCEPTED_HEAD.json'),can_prove='ACCEPTED_DATED_SYMBOL_AND_ENTITY_BINDING',cannot_prove=['DATED_ST','SUSPENSION_FROM_PROVIDER'],dated=True,accepted=True),
        dict(source=bind('reports/audits/V4_01_IDENTITY_FIELD_AUTHORITY_MATRIX_R1.json'),can_prove='IDENTITY_FIELD_PROVENANCE_RESULT_C',cannot_prove=['ALL_HISTORICAL_TYPES_LOCAL_CONFIRMED'],dated=True,accepted=False),
        dict(source=bind('src/tdx/security_master.py'),can_prove='CURRENT_TNF_NAMES_AND_CODES',cannot_prove=['HISTORICAL_ST_EFFECTIVE_INTERVAL','DATED_SUSPENSION'],dated=False,mutable_current_only=True,accepted_historical_st=False),
        dict(source=inputs['status'],can_prove='OLD_LOCAL_ACTUAL_PLUS_PROVIDER_CROSSCHECK',cannot_prove=['PROVIDER_FORMAL_OWNER_UNDER_CURRENT_MASTER'],dated=True,source_role_revalidation_required=True),
        dict(source=inputs['st'],can_prove='BAOSTOCK_DATED_PROVIDER_FACT',cannot_prove=['LOCAL_ST_AUTHORITY','AS_RECORDED_AT_TARGET'],dated=True,historical_queryable=True,source_role='SUPPLEMENTAL_CROSSCHECK'),
        dict(source=bind('data/v4/bootstrap/special_price_phase_events_r4.jsonl'),can_prove='BOUNDED_ACCEPTED_SPECIAL_PHASE_NOTICE_FACTS',cannot_prove=['WHOLE_MARKET_DATED_ST_OR_SUSPENSION'],dated=True,accepted=True)]
    evidence_files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size) for p in sorted((ROOT/'data/v4/source_evidence').rglob('*')) if p.is_file() and p.suffix.lower() in ('.json','.jsonl','.pdf','.html','.txt')]
    atomic_json(ROOT/'reports/audits/V4_02_STATUS_ST_AUTHORITY_INVENTORY_R1.json',dict(contract_id='V4_02_STATUS_ST_AUTHORITY_INVENTORY_R1',sources=local_inventory,existing_source_evidence_inventory=evidence_files,
        accepted_dated_authority_files=contract['accepted_dated_evidence'],accepted_dated_authority_fact_count=len(facts),
        conclusion='NO_ACCEPTED_PER_SECURITY_DATED_ST_OR_SUSPENSION_DATASET_RECOVERED; DO_NOT_INFER_NORMAL_OR_SUSPENSION',
        general_risk_ratio_rules_not_dated_security_st=True,current_active_catalogue_not_should_trade_evidence=True,external_acceptance=None))
    atomic_json(ROOT/'reports/audits/A12_STAGE_ENTRY_R1.json',dict(stage_contract='LOCAL_DATED_TRADING_STATUS_V2 + LOCAL_DATED_ST_IDENTITY_V2',authority=bind('docs/evidence/source_authority/V4_A12_V4_02_STATUS_ST_AUTHORITY_AND_CASCADE_REPAIR_TASK_R1_20261001.md'),
        master_amendment=bind('docs/evidence/source_authority/V4_CROSS_STAGE_REMEDIATION_MASTER_AMENDMENT_R2_20261001.md'),inputs=inputs,protected_bindings=governing['protected_bindings'],status='CANDIDATE_ENGINEERING_ONLY',next_stage='V4_04 true replay then dependency-scoped cascade; independent acceptance pending'))
    runtime_bindings=[bind(p) for p in ['src/workbench_analysis/status_st_authority_r1.py','src/workbench_analysis/dm01_extracted_domain_r1.py','src/workbench_analysis/limit_rules.py','config/v4_02_price_limit_rules_r3.json','config/special_price_phase_policy_r6.json','scripts/build_v4_02_price_limits_generic.py']]
    atomic_json(ROOT/'reports/audits/A12_PRODUCER_CONTRACT_FREEZE_R1.json',dict(contract_id='A12_PRODUCER_CONTRACT_FREEZE_R1',status='PASS_ENGINEERING_PRODUCER_CONTRACT_FROZEN',contract=inputs['producer'],runtime_bindings=runtime_bindings,source_role='BAOSTOCK_CROSSCHECK_ONLY',scope='CANDIDATE_NOT_FORMAL_ACCEPTED',external_acceptance=None))
    conn=duckdb.connect();conn.execute('create temp table bars as select canonical_security_id,trade_date,raw_close from read_parquet(?)',[str(ROOT/PATHS['daily'])]);conn.execute('create index bar_date on bars(trade_date)')
    service=LimitStateService(read('config/v4_02_price_limit_rules_r3.json')['rules']);states={}
    transitions={k:Counter() for k in ['status','st','price_reason','price_status']};counts=Counter();samples={};digests={k:hashlib.sha256() for k in ['status','st','price','old_price_business','new_price_business']}
    output_paths={k:OUTDIR/f'V4_02_{name}_AUTHORITY_R1.jsonl.gz' for k,name in [('status','DATED_TRADING_STATUS'),('st','DATED_ST_STATUS'),('price','PRICE_LIMIT')]}
    OUTDIR.mkdir(parents=True,exist_ok=True);temporary={}
    try:
        with ExitStack() as stack:
            streams={k:stack.enter_context(gzip.open(ROOT/PATHS[k],'rt',encoding='utf8')) for k in ['universe','status','st','price']}
            writers={}
            for k,p in output_paths.items():
                fd,temp=tempfile.mkstemp(prefix=p.name+'.',suffix='.tmp',dir=OUTDIR);os.close(fd);temporary[k]=Path(temp)
                raw=stack.enter_context(open(temp,'wb'));writers[k]=stack.enter_context(gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=3))
            bars={};current_day=None
            for ul,sl,il,pl in zip(streams['universe'],streams['status'],streams['st'],streams['price'],strict=True):
                u,s,i,p=map(json.loads,[ul,sl,il,pl]);assert identity(u)==identity(s)==identity(i)==identity(p)
                day=u['trade_date'];sid=u['security_id']
                if day!=current_day:
                    bars={sid:Decimal(str(close)) for sid,close in conn.execute('select canonical_security_id,raw_close from bars where trade_date=?',[int(day.replace('-',''))]).fetchall()}
                    current_day=day
                assert (u.get('source_bar_present') is True)==(sid in bars),identity(u)
                new_s=produce_trading_status(u,facts,s.get('provider_tradestatus'))
                new_i=produce_st(u,facts,i.get('is_st'))
                state=states.setdefault(sid,PreviousCloseState(None))
                result={k:p.get(k) for k in ['security_id','source_security_key','trade_date','board_scope','special_price_phase','phase_policy_id','event_id','event_revision']}
                result.update(contract_id='PRICE_LIMIT_RULE_R6_A12_SOURCE_BOUNDARY_R1',trading_status=new_s['status'],is_st=new_i['is_st'],risk_status=None,reference_price=None,reference_basis='UNKNOWN',rule_id=None,limit_up_price=None,limit_down_price=None,limit_status='UNKNOWN',reason=None,knowledge_lineage='RECONSTRUCTED_CORRECTED',st_owner_contract='LOCAL_DATED_ST_IDENTITY_V2')
                bar=dict(trade_date=day.replace('-',''),raw_close=bars[sid]) if sid in bars else None
                result=evaluate_price_base(result,new_s['status'],bar,new_i['is_st'],state,state.value if hasattr(state,'value') else None,[],service,{},set(),{}, {day.replace('-',''):0})
                if new_s['status']=='ACTUAL_TRADED' and bar is not None:state.observe_actual_close(bar['raw_close'])
                if new_i['is_st'] is None:assert result['limit_status']=='UNKNOWN'
                for k,new in [('status',new_s),('st',new_i),('price',result)]:
                    b=canonical(new);writers[k].write(b);digests[k].update(b)
                transitions['status'][s['status']+' -> '+new_s['status']]+=1
                transitions['st'][str(i.get('is_st'))+' -> '+str(new_i['is_st'])]+=1
                transitions['price_reason'][str(p.get('reason'))+' -> '+str(result['reason'])]+=1
                transitions['price_status'][str(p.get('limit_status'))+' -> '+str(result['limit_status'])]+=1
                counts['rows']+=1;counts['new_status_'+new_s['status']]+=1;counts['new_st_'+str(new_i['is_st'])]+=1
                old_business={k:p.get(k) for k in FIELDS};new_business={k:result.get(k) for k in FIELDS}
                digests['old_price_business'].update(canonical(old_business));digests['new_price_business'].update(canonical(new_business))
                if old_business!=new_business:counts['price_business_rows_changed']+=1
                tag=s['status']+' -> '+new_s['status']
                if tag not in samples:samples[tag]=dict(old=s,new=new_s,old_st=i,new_st=new_i,old_price=old_business,new_price=new_business)
                if counts['rows']%250000==0:print(json.dumps(dict(rows=counts['rows'],new_status={k:v for k,v in counts.items() if k.startswith('new_status')})),flush=True)
        for k,p in output_paths.items():
            if p.exists():
                assert hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(temporary[k].read_bytes()).hexdigest(),'IMMUTABLE_A12_CANDIDATE_COLLISION'
                temporary[k].unlink()
            else:os.replace(temporary[k],p)
    finally:
        conn.close()
        for p in temporary.values():
            if p.exists():p.unlink()
    assert counts['rows']==4035729
    out={k:{**bind(p.relative_to(ROOT).as_posix()),'logical_digest':digests[k].hexdigest()} for k,p in output_paths.items()}
    atomic_json(ROOT/'reports/audits/A12_V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json',dict(contract_id='A12_V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1',status='PASS_APPEND_ONLY_ENGINEERING_SOURCE_BOUNDARY_REPAIR',inputs=inputs,artifacts=out,counts=dict(counts),transitions={k:dict(v) for k,v in transitions.items()},samples=samples,
        old_price_business_digest=digests['old_price_business'].hexdigest(),new_price_business_digest=digests['new_price_business'].hexdigest(),unchanged_kernel_bindings=runtime_bindings,
        arithmetic_policy='UNCHANGED_ACCEPTED_KERNEL; UNKNOWN_FORMAL_ST_FAILS_BEFORE_RATIO_EVALUATION',special_phase_metadata='PRESERVED_ACCEPTED_PHASE_CLASSIFICATION; UNACCEPTED_ST_CANNOT_AUTHORIZE_KNOWN_PRICE_RESULT',
        observation_at=datetime.now(timezone.utc).isoformat(),formal_publication=False,accepted_heads_unchanged=True,external_acceptance=None,next_stage='V4_03 exact consumed-field gate; V4_04 real replay; conditional cascade'))
    print(json.dumps(dict(status='PASS_A12_APPEND_ONLY_FULL_HISTORY',counts=dict(counts),transitions={k:dict(v) for k,v in transitions.items()})),flush=True)

if __name__=='__main__':main()
