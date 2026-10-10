"""Bound real rank oracle using statistics only, no cycle/rank producer calls."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import gzip
import json
import math
from collections import defaultdict
from statistics import median
from workbench_analysis.v4_14_replay_io import exact,publish,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

OUT='docs/evidence/next_stage_after_audit_r1_20261010'


def load(binding):
    return json.loads(exact(ROOT,binding))


def rows(binding):
    raw=exact(ROOT,binding)
    if binding['path'].endswith('.gz'):raw=gzip.decompress(raw)
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def main():
    matrix=json.loads((ROOT/'docs/evidence/pre_next_t0_execution_r1_20261010/final/D2_PRODUCER_SOURCE_MATRIX.json').read_bytes())
    source=matrix['rows'][0]['fields']['CONFIRMED']['source'];candidate=load(source)
    rank=load(candidate['rows'][0]['inputs']['q20']['source'])
    technical,members,calendar=(load(b) for b in rank['sources'])
    day=candidate['T0'];sessions=calendar['session_dates'];prior=sessions[sessions.index(day)-3]
    dates=sorted({r['trade_date'] for r in technical['rows']})
    errors=[];strength_checked=0
    index={(r['trade_date'],r['security_id']):r for r in technical['rows']}
    # Independent source-level extraction from bound Core/prewatch, not RET alias.
    for pos,date in enumerate(dates):
        core=rows(technical['sources'][pos*2]);states=rows(technical['sources'][pos*2+1])
        normal={r['security_id'] for r in states if r['target_values'].get('normal_universe') is True}
        for horizon in (5,20):
            values={r['security_id']:r['fields']['ret'+str(horizon)]['value'] for r in core
                if r['security_id'] in normal and r['fields']['ret'+str(horizon)].get('quality_state')=='OBSERVED'
                and r['fields']['ret'+str(horizon)].get('value') is not None}
            baseline=median(values.values()) if len(values)>=100 else None
            for r in core:
                value=values.get(r['security_id']);expected=value-baseline if value is not None and baseline is not None else None
                actual=index[(date,r['security_id'])]['rs'+str(horizon)]
                strength_checked+=1
                if actual!=expected:errors.append(dict(stage='RS_EXTRACTION',date=date,security_id=r['security_id'],horizon=horizon))
    group=defaultdict(list);types={}
    for r in members['rows']:
        types[r['sector_id']]=r['sector_type']
        for n in (5,20):
            v=index.get((r['trade_date'],r['security_id']),{}).get('rs'+str(n))
            if v is not None and math.isfinite(v):group[(r['trade_date'],r['sector_id'],n)].append(v)
    med={key:median(v) for key,v in group.items()}
    ranks={}
    for date in (prior,day):
        for typ in set(types.values()):
            for n in (5,20):
                pool={sid:v for (d,sid,h),v in med.items() if d==date and h==n and types[sid]==typ}
                for sid,v in pool.items():
                    ranks[(date,sid,n)]=(sum(x<v for x in pool.values())+(sum(x==v for x in pool.values())+1)/2)/len(pool)
    cfg=json.loads((ROOT/'config/research_attention_v3.yaml').read_bytes())['thresholds']['coverage']
    observations=[]
    for r in candidate['rows']:
        sid=r['sector_id'];typ=types[sid]
        now_ids={s for (d,s,h) in ranks if d==day and h==5 and types[s]==typ}
        old_ids={s for (d,s,h) in ranks if d==prior and h==5 and types[s]==typ}
        union=now_ids|old_ids
        comparable=bool(union) and abs(len(now_ids)-len(old_ids))/max(len(now_ids),len(old_ids))<=cfg['max_rank_universe_change'] and len(now_ids&old_ids)/len(union)>=cfg['min_rank_intersection_union']
        before=ranks.get((prior,sid,5));current=ranks.get((day,sid,5))
        expected=dict(q20=ranks.get((day,sid,20)),dq5_3=current-before if comparable and current is not None and before is not None else None)
        for field,value in expected.items():
            receipt=r['inputs'][field]['source'];actual=load(receipt)
            if actual['value']!=value:errors.append(dict(stage='SECTOR_RANK',sector_id=sid,field=field,expected=value,actual=actual['value']))
            observations.append(dict(sector_id=sid,field=field,expected=value,actual=actual['value'],source=receipt))
    publish(ROOT,OUT+'/C_RANK_NON_AMOUNT_INDEPENDENT_ORACLE.json',dict(
        contract_id='C_BOUND_CORE_RS_MEDIAN_AVERAGE_RANK_ORACLE_V1',T0=day,source=source,
        sources=rank['sources'],source_level_RS_values_checked=strength_checked,
        sector_rank_fields_checked=len(observations),observations=observations,mismatches=errors,
        status='PASS_SCOPED' if not errors else 'FAIL',history_basis='LATEST_MEMBER_RECONSTRUCTED_NOT_PIT',
        amount_A_dependency=False,formal_D2='NOT_GRANTED'))
    bindings={p:ref(ROOT,p) for p in [
        'config/v4_08_b2_machine_ast_r5.json','config/v4_11_r5b_candidate_d2_contract_v1.json',
        'config/v4_10_input_provenance_r1_2.json','src/sector/legacy_b2_r5.py',
        'src/sector/episode_genesis_candidate_v2.py','src/workbench_analysis/v4_15_settlement.py',
        'docs/evidence/pre_next_t0_execution_r1_20261010/final/D2_LEGACY_GOLDEN_FIELD_READBACK.json']}
    fields=[]
    for field in ('CONFIRMED','WARM','frozen_invalidation','episode_invalidation_contract_id','followup_complete','scenario'):
        current=field in ('CONFIRMED','WARM')
        producer='src/sector/operational_candidate_v2.py::build -> operational_candidate_v1.compute -> legacy_b2_r5.evaluate_b2' if current else 'src/sector/episode_genesis_candidate_v2.py::create' if field in ('episode_invalidation_contract_id','scenario') else 'src/sector/episode_genesis_candidate_v2.py::observe -> operational_candidate_v1.'+('evaluate_invalidation' if field=='frozen_invalidation' else 'followup')
        fields.append(dict(field=field,producer=producer,production_owner_status='SOURCE_PRODUCER_NOT_ADMITTED',
            actual_original=source if current else None,current_status='RECONSTRUCTED_RESEARCH_ONLY' if current else 'NO_PRIOR_EPISODE',
            legal_birth='actual same-day first availability before cutoff, AS_RECORDED exact sector member version and field scoped independent authority' if current else 'immutable actual genesis captures membership/conditions/scenario/calendar; T+1/3/5 settlements only when due' if field=='followup_complete' else 'immutable actual current-day genesis original; no retrospective creation',
            next_acquisition='2026-10-12 after real capture; date alone confers no authority' if current else 'first admitted actual future genesis, followed by due sessions' if field=='followup_complete' else 'first actual future genesis with source review',
            allowed_states=['TRUE','FALSE','UNKNOWN'] if current else ['NO_PRIOR_EPISODE','PENDING','UNKNOWN','COMPLETE_CANDIDATE'] if field=='followup_complete' else ['NO_PRIOR_EPISODE','UNKNOWN','INHERITED_CANDIDATE'],
            contract_id='SECTOR_OPERATIONAL_RESEARCH_CANDIDATE_V2' if current else 'SECTOR_EPISODE_GENESIS_CANDIDATE_V2',version='V2',cutoff='actual aware field clock, never historical synthesized clock'))
    atomic_json(ROOT,ROOT/OUT/'C_D2_SOURCE_AND_EPISODE_GENESIS_MAP.json',dict(contract_id='C_D2_GENESIS_OWNER_MAP_V1',
        exact_BASE='c0b9903fe596c1884c04f5529d6699034548850e',fields=fields,bindings=bindings,
        golden_scope=dict(date='2026-09-24',members=3553,qualification_observations=6188,sectors=541,
                          evidence_basis='existing frozen golden readback; not rerun here',cross_date_authorization=False),
        formal_D2='NOT_GRANTED',stage_acceptance='ENGINEERING_PASS_SCOPED_PENDING_INDEPENDENT_REVIEW',
        next_stage='REAL_FUTURE_GENESIS_FIELD_SOURCE_REVIEW'))
    print(json.dumps(dict(RS_values=strength_checked,rank_fields=len(observations),mismatches=len(errors))))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
