"""Full enrollment read projection and actual bounded due plans; no invented returns."""
import json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import enter
from workbench_service.production_v4 import frozen_current_reader
from workbench_service.current_v4_context import canonical,digest
from workbench_analysis.v4_15_settlement import due_plan

def main():
    out=enter(10);reader,_=frozen_current_reader(ROOT);contract,_=reader._contract();ctx=reader.load_context()['context'];rows=[];plans=[];sources={};published=list(reader._rows(contract,'outcomes')) if 'outcomes' in contract['row_bindings'] else []
    for row,binding in reader._rows(contract,'cohort'):
        sources['enrollment_'+row['enrollment_id']]=binding;calendar=reader._read(row['calendar_identity']);sessions=calendar.get('session_dates',calendar.get('sessions'))
        if sessions is None:raise ValueError('CALENDAR_SESSIONS_NOT_FOUND')
        if sessions and isinstance(sessions[0],dict):sessions=[r['trade_date'] for r in sessions]
        plan=due_plan(sessions,row['T0'],ctx['accepted_trade_date'])
        for p in plan:
            p.update(enrollment_id=row['enrollment_id'],entity_id=row['entity_id'],T0=row['T0'],due_reason='FUTURE_SESSION_OUTSIDE_FROZEN_CALENDAR' if p['due_date'] is None else 'NOT_YET_DUE' if p['outcome_status']=='PENDING' else 'AWAIT_ACTUAL_OWNER_SETTLEMENT',kind='DUE_PLAN_ONLY_NOT_OUTCOME',source=binding)
        plans.extend(plan);rows.append(dict(row,source=binding));sources['calendar']=row['calendar_identity']
    actual=[dict(row,source=binding) for row,binding in reader._rows(contract,'outcomes')];assert len({r['enrollment_id'] for r in rows})==len(rows)
    statuses=Counter(r['outcome_status'] for r in actual);fepref=ref('reports/fep_e5_final_external_acceptance_r1/STAGE_ACCEPTANCE_AND_NEXT.json');fep=reader._read(fepref)
    result=dict(contract_id='FP10_FORWARD_READ_PROJECTION_V1',trade_date=ctx['accepted_trade_date'],enrollments=rows,plans=plans,outcomes=actual,statistics=dict(enrollment_denominator=len(rows),planned_horizon_denominator=len(plans),published_outcomes=len(actual),published_enrollment_count=len({r['enrollment_id'] for r in actual}),state_counts=dict(statuses),mature_eligible_count=0,win_rate=None,return_quantiles=None,reason='NO_MATURE_VALIDATION_ELIGIBLE_OUTCOMES',failure_and_censored_not_dropped=True),sources=sources,fep=dict(source=fepref,engineering_state=fep['FEP_ENGINEERING_BRANCH'],production=fep['FEP_PRODUCTION'],champion=fep['CHAMPION'],scope='HISTORICAL_ENGINEERING_EVIDENCE_ONLY'),knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
    path=ROOT/'data/v4/fp10_forward'/digest(canonical(result))/'forward.json';write(path,result);write(ROOT/'config/v4_forward_operational_authority_v1.json',dict(contract_id='FP10_FORWARD_READ_AUTHORITY_V1',trade_date=result['trade_date'],input_data_head=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json'),publication=ref(path)));write(out/'REAL_SOURCE_READBACK.json',dict(statistics=result['statistics'],plans=len(plans),source_count=len(sources),fep=result['fep']));print(json.dumps(result['statistics']))
if __name__=='__main__':main()
