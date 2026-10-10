"""Export new bounded source inputs and lineage, without business calculations."""
from immediate_r3_common import *
from collections import Counter
from datetime import datetime,timezone
import csv,random

def main():
    head=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=head['accepted_trade_date'];refs=head['owners'][day]
    protected=[binding('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),binding('data/v4/V4_DATA_ACCEPTED_HEAD.json'),head['day_receipt']]
    task=Path('D:/Users/lps/Desktop/阶段任务/V4_IMMEDIATE_EXECUTION_MASTER_AND_TASK_CARDS_R3_20261010.md')
    contracts=[binding(task),binding('AGENTS.md'),binding('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md'),binding('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md')]
    write(OUT/'STAGE_LEDGER.json',dict(contract='V4-IMMEDIATE-R3-20261010',BASE_SHA=git('rev-parse','HEAD'),remote_SHA=git('rev-parse','origin/codex/v4-fp14-r2-repair'),T0=day,protected=protected,contracts=contracts,started_at=datetime.now(timezone.utc).isoformat(),stages=[dict(stage=s,contract='V4-IMMEDIATE-R3-20261010 '+s,evidence=d,acceptance='IN_PROGRESS',next_stage=n) for s,d,n in [('PRE-00','STAGE_LEDGER.json','P0-ALG'),('P0-ALG','02_P0_ALG','P0-OWNER'),('P0-OWNER','03_P0_OWNER','P0-AMOUNT'),('P0-AMOUNT','04_P0_AMOUNT','P1-COHORT'),('P1-COHORT','05_P1_COHORT','P1-PRODUCT-QA'),('P1-PRODUCT-QA','06_P1_PRODUCT_QA','GIT/DRIVE')]],external_acceptance='NOT_GRANTED'))
    # R2 reused arithmetic is frozen evidence; do not rerun its completed full rank sample.
    r2=load('docs/evidence/core_algo_ui_r2_20261010/oracle/INPUT.json')
    existing={s['security_id'] for s in r2['stocks']}
    states=load(refs['focus'])['rows'];by={r['entity_id']:r for r in states}
    selected=set(existing);rng=random.Random(20261010)
    for field in ('validity','maturity','state_freshness','health'):
        groups={}
        for r in states:groups.setdefault(r[field],[]).append(r['entity_id'])
        for ids in groups.values():selected.update(rng.sample(sorted(ids),min(2,len(ids))))
    snapshot=load(head['membership_snapshot']);identity=load(snapshot['identity_source']);members=load(snapshot['memberships'])
    target=next(r['security_id'] for r in identity['rows'] if r.get('source_security_key')=='SZ.301628');selected.add(target)
    sources=[];d0=[];d2=[];histories={};sectors=[];rotations=[];loo=[]
    sector_current=load(refs['sector'])
    chosen=['INDUSTRY:T0706']
    for typ in ('INDUSTRY','THEME'):
        candidates=sorted([r for r in sector_current if r['sector_type']==typ],key=lambda r:(len(r['member_ids']),r['sector_id']))
        chosen.extend(r['sector_id'] for r in (candidates[0],candidates[len(candidates)//2],candidates[-1]))
    chosen=sorted(set(chosen))
    for date in head['published_sessions']:
        o=head['owners'][date]
        diag=load(o['diagnostic']);history_ref=diag['owner']['history'];sources.extend([o['focus'],o['prewatch'],o['sector'],o['rotation'],o['relative_sector'],history_ref])
        # Compact recursion provenance preserves required/status/quality and exact timestamps.
        for row in load(o['focus'])['rows']:
            if row['entity_id'] not in selected:continue
            d2.append(dict(entity_id=row['entity_id'],trade_date=date,session_index=row['session_index'],facts={k:{a:v for a,v in f.items() if a in ('value','status','quality','required','system_available_at','time_role','source_output_digest','source_field_payload')} for k,f in row['input_provenance'].items()},actual={k:row[k] for k in ('maturity','health','validity','tracking','final_eligibility','state_freshness','downgrade_candidate','downgrade_count','expiry_count','improvement_baseline','market_age','exit_session_index','episode_id','transition_reasons')},prior_state_binding=row['prior_state_binding']))
        for row in load(o['prewatch']):
            if row['security_id'] in selected:d0.append(dict(security_id=row['security_id'],trade_date=date,target_values=row['target_values'],signals=row['signals']))
        sn=[{k:r[k] for k in ('sector_id','trade_date','member_ids','current_member_count','unmapped_count')} | {'fields':{k:{'value':v['value']} for k,v in r['fields'].items() if k in ('sector_rs1','sector_rs5','breadth_ret1','breadth_ret5')}} for r in load(o['sector']) if r['sector_id'] in chosen];sectors.extend(sn)
        rot=[dict(sector_id=r['sector_id'],trade_date=date,rotation={k:v for k,v in r['rotation'].items() if k in ('episode','negative_out_count','output_state','prior_rotation_state','trade_date') } | {'fields':{k:{'value':v['value']} for k,v in r['rotation']['fields'].items() if k in ('dq5','breadth_delta1','basket_cumulative_return','sector_price_retention_core','base_seed_retention','breadth_retention','pulse_age_sessions')}}) for r in load(o['rotation']) if r['sector_id'] in chosen];rotations.extend(rot)
        ids=set(selected)|{m for s in sn for m in s['member_ids']}|{m for r in rot for m in (r['rotation'].get('episode') or {}).get('frozen_basket',[])}
        core={}
        for r in load(o['core']):
            if r['security_id'] in ids:
                core[r['security_id']]=dict(price_basis_id=r['price_basis_id'],**{k:f['value'] if f.get('quality_state') in ('KNOWN','OBSERVED') else None for k,f in r['fields'].items() if k in ('ret1','ret5','rps20','ma20','amount_ratio20','pos60')})
        raw={r['security_id']:r for r in load(o['raw'])};seeds={r['security_id']:{'TRUE':True,'FALSE':False}.get(r['base_seed_state']) for r in load(o['seed'])}
        with gzip.open(checked(history_ref),'rt',encoding='utf8') as f:
            for line in f:
                r=json.loads(line);sid=r['security_id']
                if sid not in ids:continue
                b=next((b for b in r['bars'] if b['trade_date']==date),{})
                c=b.get('qfq_ohlc',[None]*4)[3] if b.get('qfq_ohlc') else None
                if sid in core:core[sid].update(close=c,amount=raw.get(sid,{}).get('amount'),base_seed=seeds.get(sid),close_minus_ma20=c-core[sid]['ma20'] if c is not None and core[sid].get('ma20') is not None else None)
                if sid in selected:
                    # 27 real master sessions, with gaps retained as explicit null slots.
                    cal=load(path(o['core']).parent/'../../FOCUS_CALENDAR.json') if False else None
                    histories[(sid,date)]=r['bars'][-40:]
        for s in sn:s['contributions']={sid:core.get(sid,{}) for sid in s['member_ids']}
        index=head['published_sessions'].index(date);prior_map={};prior_source=None
        if index:
            previous=head['published_sessions'][index-1];rebuilt=path(o['rotation']).parent.parent/previous/'rotation.jsonl.gz'
            if rebuilt.exists():
                prior_source=binding(rebuilt);sources.append(prior_source);prior_map={v['sector_id']:v['rotation'] for v in load(prior_source)}
        for r in rot:
            relevant=set(next(s['member_ids'] for s in sn if s['sector_id']==r['sector_id']))|set((r['rotation'].get('episode') or {}).get('frozen_basket',[]))
            r['contributions']={sid:core.get(sid,{}) for sid in relevant}
            if r['sector_id'] in prior_map:
                pr=prior_map[r['sector_id']]
                r['exact_producer_prior']=dict(episode=pr.get('episode'),output_state=pr['output_state'],negative_out_count=pr['negative_out_count'],trade_date=previous,source=prior_source)
        if date==day:
            for r in load(o['relative_sector']):
                for m in r.get('memberships',[]):
                    if m['sector_id'] in chosen and m.get('relative_substitutions'):loo.append(dict(security_id=r['security_id'],sector_id=m['sector_id'],actual={k:m[k] for k in ('non_target_member_count','relative_substitutions')}))
    calendar=load(path(refs['core']).parent.parent.parent/'FOCUS_CALENDAR.json')['session_dates']
    if calendar and isinstance(calendar[0],dict):calendar=[r['trade_date'] for r in calendar]
    for row in d0:
        sid,date=row['security_id'],row['trade_date'];end=calendar.index(date)+1;dates=calendar[max(0,end-27):end];bars={b['trade_date']:b for b in histories[(sid,date)]}
        row['bars']=[dict(trade_date=d,**{k:v for k,v in bars.get(d,{}).items() if k!='trade_date'}) for d in dates]
    pack=dict(contract='R3_INCREMENTAL_INDEPENDENT_ORACLE_V1',T0=day,calendar=calendar[-150:],d0=d0,d2=d2,sectors=sectors,rotations=rotations,loo=loo,selected_ids=sorted(selected),sector_ids=chosen,sources=sources,parameters=load('config/v4_10_parameter_set_r1_2.json'),reused_R2=dict(input=binding('docs/evidence/core_algo_ui_r2_20261010/oracle/INPUT.json'),script=binding('scripts/audit_core_algo_ui_r2.py'),output=binding('docs/evidence/core_algo_ui_r2_20261010/oracle/OUTPUT.json'),verdict='PASS_KEEP_EXACT_HASH_BOUND_SCOPE'),strict_PIT='NOT_VERIFIABLE_LATEST_MEMBER_RETRO')
    write(OUT/'02_P0_ALG/P0_ALG_ORACLE_INPUT.json',pack)
    write(OUT/'02_P0_ALG/P0_ALG_ALGORITHM_INPUT_LINEAGE.json',dict(sources=sources,producers=[binding(p) for p in ['src/v4/target_fact_producers_r4.py','src/workbench_analysis/today_research_factors_v3_3.py','src/v4/research_state.py','src/sector/rotation_r5.py','src/sector/native_r5.py','src/workbench_analysis/v4_13_loo_runtime.py']],window='27 MASTER_SESSIONS_WITH_GAPS; no calendar-day recursion',PIT_scope='LATEST_MEMBER_RETRO_ONLY',first_available_at='UNKNOWN_FOR_HISTORICAL_AS_RECORDED',output_owners=head['owners']))
    print(json.dumps(dict(selected_stocks=len(selected),d0_rows=len(d0),d2_rows=len(d2),sectors=len(chosen),loo_pairs=len(loo))))

if __name__=='__main__':main()
