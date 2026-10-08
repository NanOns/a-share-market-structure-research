"""Scoped corrected Core producer: exact target QFQ, original CORE_FACTOR_V1.

Artifacts are isolated; no operational authority is changed.
"""
import collections
import gzip
import json
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from statistics import fmean

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.audit_three_day_repair_r1 import OUT,DAYS,load
from scripts.build_fp06_sector import compress
from adjustment.tdx_adjustment import build_affine_factors,xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq
from v4.factors.core import Bar,Observation,compute_core
from workbench_service.current_v4_context import canonical,digest

SOURCE_OUT=OUT
OUT=SOURCE_OUT/'core_owner_r2'


def main():
    if (OUT/'OWNER_REPLAY_PER_DAY.json').exists():raise RuntimeError('OWNER_REPLAY_FROZEN')
    assert load(str((SOURCE_OUT/'A_STAGE_DISPOSITION.json').relative_to(ROOT)))['result']=='DEGRADED_PASS'
    frozen_producer=OUT/'implementations'/digest(Path(__file__).read_bytes())/Path(__file__).name
    write(frozen_producer,Path(__file__).read_bytes())
    write(OUT/'ENTRY.json',dict(stage='B_CORRECTED_CORE_R2',task=ref(SOURCE_OUT/'TASK.md'),
        stage_contract='CORE_FACTOR_V1_WITH_ACCEPTED_ADJUSTMENT_CAPABILITY_GATE',acceptance='IN_PROGRESS',
        previous_attempt=ref(SOURCE_OUT/'B_FIRST_ATTEMPT_REJECTION.json'),next_stage='SCOPED_ORACLE_NO_RELEASE'))
    head=load('data/v4/V4_DATA_ACCEPTED_HEAD.json');chain=load(head['accepted_chain']['path'])
    stock=load('config/v4_stock_operational_authority_v1.json')
    market=load(load('config/v4_market_operational_authority_v1.json')['market']['path'])
    execution=load(market['sources']['execution']['path'])
    sessions=load(head['calendar']['path'])['session_dates']
    nodes={n['trade_date']:n for n in chain['nodes']}
    raw_history=collections.defaultdict(dict)
    # Existing frozen history contains real RAW bars; discard its later QFQ coordinate.
    history=stock['sources']['history']
    assert ref(history['path'])['sha256']==history['sha256']
    with gzip.open(ROOT/history['path'],'rt',encoding='utf8') as f:
        for line in f:
            row=json.loads(line)
            for b in row['bars']:
                raw_history[row['security_id']][b['trade_date']]=b
    statuses=collections.defaultdict(dict)
    status_source=load('config/v4_sector_operational_authority_v1.json')['sources']['historical_status']
    with gzip.open(ROOT/status_source['path'],'rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line)
            if r['status']=='SUSPENDED':statuses[r['security_id']][r['trade_date']]='SUSPENDED'
    for day,node in nodes.items():
        for r in load(node['components']['TRADING_STATUS']['artifact_path'])['rows']:statuses[r['security_id']][day]=r['status']
    dispositions=load('config/v4_02_gbbq_price_impact_classification_v1.json')['dispositions']
    receipts=[];oracle=[]
    for target in DAYS:
        node=nodes[target];identity=load(node['components']['IDENTITY_UNIVERSE']['artifact_path'])['rows']
        gbbq=execution['inputs'][target]['inputs']['GBBQ']
        assert ref(gbbq['path'])['sha256']==gbbq['sha256']
        events=collections.defaultdict(list)
        for e in read_gbbq(ROOT/gbbq['path']):
            if e.event_date<=int(target.replace('-','')):events[e.security_id].append(e)
        sources=dict(history=history,gbbq=gbbq,calendar=head['calendar'],identity=ref(node['components']['IDENTITY_UNIVERSE']['artifact_path']),
            raw=ref(node['components']['RAW_DAILY']['artifact_path']),status=ref(node['components']['TRADING_STATUS']['artifact_path']),
            historical_status=status_source,kernel=ref('src/v4/factors/core.py'),
            parameters=ref('config/v4_03_parameter_set_v1.json'),parameter_registry=ref('config/v4_03_parameter_registry_v1.json'),
            classification=ref('config/v4_02_gbbq_price_impact_classification_v1.json'),producer=ref(frozen_producer),
            adjusted=ref(node['components']['ADJUSTED_DAILY']['artifact_path']))
        accepted_adjusted={r['security_id']:r for r in load(node['components']['ADJUSTED_DAILY']['artifact_path'])['rows']}
        input_digest=digest(canonical(sources));rows=[];prior_rows=[];coordinate=[];checks=collections.Counter();errors=[]
        prior=sessions[sessions.index(target)-1]
        for i in identity:
            sid=i['security_id'];symbol=i['source_security_key']
            bars=[b for d,b in sorted(raw_history[sid].items()) if d<=target]
            if not bars:continue
            relevant=[e for e in events[symbol] if int(bars[0]['trade_date'].replace('-',''))<e.event_date]
            blocked=[e.category for e in relevant if dispositions.get(str(e.category),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT')]
            accepted_ready=accepted_adjusted.get(sid,{}).get('adjustment_readiness')=='READY'
            factors=build_affine_factors([int(b['trade_date'].replace('-','')) for b in bars]+[int(target.replace('-',''))],[xrxd_from_gbbq(e) for e in relevant if e.category==1]) if not blocked and accepted_ready else {}
            basis=digest(canonical(dict(target=target,gbbq=gbbq['sha256'],symbol=symbol)))
            by={};qs=[]
            for b in bars:
                factor=factors.get(int(b['trade_date'].replace('-','')))
                q=[float(factor.qfq_price(Decimal(v))) for v in b['raw_ohlc']] if factor else None
                by[b['trade_date']]=(b,q)
                qs.append(dict(trade_date=b['trade_date'],qfq_ohlc=q))
            observations=[]
            for day in sessions:
                if day<bars[0]['trade_date'] or day>target:continue
                b,q=by.get(day,(None,None))
                state='ACTUAL' if q else 'ADJUSTMENT_UNKNOWN' if b else 'CONFIRMED_SUSPENSION' if statuses[sid].get(day)=='SUSPENDED' else 'UNKNOWN'
                observations.append(Observation(day,state,Bar(*q,float(b['amount']),float(b['volume']),basis,input_digest) if q else None))
            if not observations or observations[-1].trade_date!=target:continue
            values={k:asdict(v) for k,v in compute_core(observations,sid,asof=target).items()}
            row=dict(security_id=sid,symbol=symbol,trade_date=target,price_basis_id=basis,fields=values,
                owner_contract='CORE_FACTOR_V1',input_digest=input_digest,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
            rows.append(row)
            # Exact previous-session dependency expressed in the TARGET coordinate.
            if any(o.trade_date==prior for o in observations):
                pv={k:asdict(v) for k,v in compute_core(observations,sid,asof=prior).items()}
                prior_rows.append(dict(security_id=sid,trade_date=prior,coordinate_target=target,price_basis_id=basis,fields=pv,
                    owner_contract='CORE_FACTOR_V1',knowledge_lineage='RECONSTRUCTED_CORRECTED',input_digest=input_digest))
            actual=[o for o in observations if o.state=='ACTUAL']
            for name in ('ma20','ret5','atr20'):
                cell=values[name]
                if cell['value'] is None:checks[name+':UNKNOWN']+=1;continue
                if name=='ma20':v=fmean(o.bar.close for o in actual[-20:])
                elif name=='atr20':
                    bs=[o.bar for o in actual[-21:]]
                    v=fmean(max(b.high-b.low,abs(b.high-a.close),abs(b.low-a.close)) for a,b in zip(bs,bs[1:]))
                else:
                    start=sessions[sessions.index(target)-5]
                    v=by[target][1][3]/by[start][1][3]-1
                checks[name+':CHECKED']+=1
                if abs(v-cell['value'])>1e-9:errors.append(dict(security_id=sid,field=name,expected=v,actual=cell['value']))
            coordinate.append(dict(security_id=sid,trade_date=target,price_basis_id=basis,bars=qs[-22:],blocked_event_categories=blocked,
                accepted_adjustment_ready=accepted_ready,capability_reason=None if accepted_ready else 'NO_ACCEPTED_TARGET_ADJUSTMENT_CAPABILITY'))
        directory=OUT/'owners'/target
        owner=compress(directory/'core.jsonl.gz',rows);prior_binding=compress(directory/'prior_core_in_target_coordinate.jsonl.gz',prior_rows)
        raw_inputs=compress(directory/'oracle_inputs.jsonl.gz',coordinate)
        receipts.append(dict(trade_date=target,input_digest=input_digest,sources=sources,owner=owner,
            prior_core_in_target_coordinate=prior_binding,rows=len(rows),prior_rows=len(prior_rows),
            owner_contract='CORE_FACTOR_V1',parameter_digest=sources['parameters']['sha256'],
            price_basis_policy='PER_TARGET_NATIVE_AFFINE_QFQ',knowledge_lineage='RECONSTRUCTED_CORRECTED',
            publication_state='ISOLATED_STAGING_NOT_ACCEPTED',not_rebuilt=['RPS','CORE_PROFILE','STRUCTURE','SECTOR_BASE_SEED_NATIVE_ROTATION']))
        oracle.append(dict(trade_date=target,checks=dict(checks),errors=errors,result='PASS' if not errors else 'FAIL',raw_inputs=raw_inputs,
            method='Independent arithmetic over saved QFQ inputs; QFQ coefficients use original accepted adjustment implementation, not independent coefficient acceptance'))
        print(json.dumps(dict(day=target,rows=len(rows),checks=dict(checks),errors=len(errors))),flush=True)
    write(OUT/'OWNER_REPLAY_PER_DAY.json',receipts)
    write(OUT/'C_SECTOR_STOCK_CORE_NUMERICAL_ORACLE.json',dict(stock_scoped_oracle=oracle,sector='NOT_VERIFIABLE_HISTORICAL_MEMBERSHIP_UNBOUND',full_core_semantics_acceptance=False))
    write(OUT/'B_WINDOW_REQUIREMENTS.json',dict(contract='CORE_FACTOR_V1',source=ref('src/v4/factors/core.py'),
        requirements=dict(ma20='20 actual technical bars',atr20='21 actual technical bars',ret5='exact 5 calendar-session endpoints',
            prior_atr20='21 actual technical bars ending no later than previous session in target coordinate'),
        three_days_sufficient=False,history_reused_not_redownloaded=True))


if __name__=='__main__':main()
