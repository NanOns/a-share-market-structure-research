"""Evidence-only final readback; never fits, tunes or rescoring seen outcomes."""
from datetime import datetime
from scripts import run_fep_e4_r1 as e4
from workbench_analysis.fep_e4 import challenger as c
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e1.feature_owner import verify_file


def timestamp(value):return datetime.fromisoformat(value.replace('Z','+00:00'))

def main():
    cp=e4.contract();report=e4.REPORT;load=e4.load
    candidate=load(report/'FEP_E4_R1_CANDIDATE_SEAL.json')
    if candidate['status']!='PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT':raise ValueError('E4_LOCAL_GATE_NOT_READY')
    for ref in candidate['code_bindings']+candidate['evidence_bindings']:verify_file(e4.ROOT,ref)
    registry=load(report/'MODEL_REGISTRY_GATE.json')['registry']
    selected=load(report/'SELECTED_DEPENDENCIES.json')
    ledger=load(report/'TRAINING_TRIAL_LEDGER.json');trials=[]
    for item in ledger['trials']:
        verify_file(e4.ROOT,item['artifact']);trial=load(e4.ROOT/item['artifact']['path']);trials.append(trial)
        if timestamp(item['attempted_at'])<timestamp(cp['frozen_at']):raise ValueError('E4_FIT_BEFORE_FREEZE')
        if trial['dependencies']['protocol_logical_digest']!=cp['logical_digest']:raise ValueError('E4_MODEL_PROTOCOL_MISMATCH')
        attempt=load(e4.REGISTRY/('attempt_'+str(item['index'])+'.json'))
        c.exact(attempt['parameters'],trial['parameters'],'TRIAL_START_PARAMETERS')
        if trial['status']=='SUCCESS':
            model=trial['model']
            c.exact(model['fixed_parameters'],{k:v for k,v in cp['fixed_parameters'].items() if k!='threads'},'FIXED_PARAMETERS')
            if model['TRAIN_serialization_max_abs_delta']>1e-12:raise ValueError('E4_SERIALIZATION_PARITY')
            for tree in model['TRAIN_leaf_support']:
                if sum(leaf['routed_rows'] for leaf in tree['leaves'])!=3893 or any(leaf['routed_rows']!=leaf['node_count'] for leaf in tree['leaves']):
                    raise ValueError('E4_LEAF_SUPPORT_READBACK')
    for family,q,name in [('HGB_ABSOLUTE_ERROR',None,'point'),('HGB_QUANTILE',.25,'q25'),('HGB_QUANTILE',.5,'q50'),('HGB_QUANTILE',.75,'q75')]:
        winner=c.select(trials,'INTERNAL_TUNE',family,q)
        if selected['selected'][name]['trial_index']!=winner['index']:raise ValueError('E4_SELECTION_READBACK')
        model=load(e4.ROOT/selected['selected'][name]['artifact']['path'])
        clean={k:v for k,v in model.items() if k not in ('created_at','logical_digest','artifact_id','artifact_type','kind')}
        c.exact(clean,winner['model'],'SELECTED_MODEL_PAYLOAD')
    calibration=load(report/'CALIBRATION_DIAGNOSTIC_GATE.json');oldcal=load(e4.e3.REPORT/'CALIBRATION_DIAGNOSTIC_GATE.json')
    e4.emit('CALIBRATION_E3_E4_DIAGNOSTIC_COMPARISON',dict(status='PASS_EXACT_CALIBRATION_COMPARISON',
        E3=oldcal['diagnostics'],E4=calibration['diagnostics'],population='EXACT_E3_213',selection=False,model_adjustment=False,
        probability_calibration='NOT_APPLICABLE_REGRESSION',E3_artifact=oldcal['artifact'],E4_artifact=calibration['artifact']))
    opening=load(report/'SEEN_OUTER_DIAGNOSTIC_OPEN.json');c.claims(opening)
    c.exact(opening['selected'],selected,'SEEN_OPEN_SELECTION')
    c.exact(opening['calibration'],calibration['artifact'],'SEEN_OPEN_CALIBRATION')
    if timestamp(opening['opened_at'])<timestamp(load(e4.ROOT/calibration['artifact']['path'])['created_at']):raise ValueError('E4_SEEN_OPEN_BEFORE_CALIBRATION')
    result=load(report/'BASELINE_E3_E4_COMPARISON.json')['result'];c.claims(result)
    old=load(e4.e3.REPORT/'BASELINE_COMPARISON.json')['result']
    c.exact(result['exact_observation_ids'],old['exact_outer_observation_ids'],'FINAL_POPULATION_IDS')
    if result['date_weight_digest']!=old['same_date_balanced_weight_digest']:raise ValueError('E4_WEIGHTS_CHANGED')
    c.exact(result['E3_quantile_diagnostics'],load(e4.e3.REPORT/'OUTER_TEST_EVALUATION.json')['result']['quantile_diagnostics'],'E3_QUANTILE_DIAGNOSTICS')
    if result['E4_quantile_diagnostics']['coherent_crossing_rows']!=0 or calibration['diagnostics']['coherent_crossing_rows']!=0:raise ValueError('E4_COHERENCE_FAILED')
    # Exact inherited full-scoped exclusions and known debt identities, not just counts.
    regression=load(report/'SCOPED_REGRESSION_SUMMARY.json');prior=load(e4.e3.REPORT/'SCOPED_REGRESSION_SUMMARY.json')
    c.exact(sorted(regression['failed_nodes']),sorted(prior['failed_nodes']),'EXISTING_DEBT_IDENTITIES')
    c.exact([v for v in regression['command'] if v.startswith('--deselect=')],[v for v in prior['command'] if v.startswith('--deselect=')],'REGRESSION_EXCLUSIONS')
    if regression['introduced_active_failures']:raise ValueError('E4_INTRODUCED_ACTIVE_FAILURES')
    protected=load(report/'PROTECTED_STATE_READBACK.json')
    if protected['R25_selection']['status']!='WAIT_ACCEPTED_DAILY_INPUT':raise ValueError('E4_R25_WAIT_CHANGED')
    head=protected['R25_protected']
    if (head['Stage'],head['Data'],head['V4_16_ACCEPTED_HEAD'])!=('V4_00_TO_V4_15_ACCEPTED','2026-09-30','NOT_CREATED'):
        raise ValueError('E4_ACCEPTED_HEAD_STATE_CHANGED')
    import psycopg
    from psycopg import sql
    database_readbacks={}
    for port,name in [(55488,'fep_e1_fresh'),(55489,'fep_e1_upgrade')]:
        with psycopg.connect(f'host=127.0.0.1 port={port} user=fep_e1_admin dbname={name}') as db:
            tables=[r[0] for r in db.execute("select tablename from pg_tables where schemaname='fep' order by tablename")]
            counts={t:db.execute(sql.SQL('select count(*) from fep.{}').format(sql.Identifier(t))).fetchone()[0] for t in tables}
        if len(counts)!=33 or any(counts.values()):raise ValueError('E4_DATABASE_FINAL_READBACK')
        database_readbacks[name]=counts
    exit_state=dict(status='PASS_EVIDENCE_ONLY_READBACK',V4_15E4_LOCAL_IMPLEMENTATION=candidate['status'],FEP_CHALLENGER_ENGINEERING='PASS_LOCAL',
        CHALLENGER_EFFECTIVENESS=result['CHALLENGER_EFFECTIVENESS'],E3_MODEL_EFFECTIVENESS='NO_INCREMENT',
        V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_15_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',V4_16_ACCEPTED_HEAD='NOT_CREATED',
        R25='WAIT_ACCEPTED_DAILY_INPUT',PRIORITY_V1='UNCHANGED',FIRST_OBSERVED='NOT_GRANTED',
        NEW_INDEPENDENT_OOS_EVIDENCE=False,FEP_PRODUCTION='UNGRANTED',E5='NOT_BLOCKED_BY_E4',
        NEXT='STOP_WAIT_V4_15E4_INDEPENDENT_EXTERNAL_AUDIT',evidence_only=True,new_fits=0,new_scoring=0,
        exact_existing_debt=52,exact_exclusions=2,registry=registry,database_readbacks=database_readbacks,**c.FLAGS)
    e4.emit('FINAL_EXIT_READBACK',exit_state)
    # Candidate is final packaging. The experiment protocol, trial/model and diagnostic seals remain untouched.
    candidate['code_bindings'].append(e4.binding(e4.ROOT/'scripts/seal_fep_e4_r1_readback.py'))
    candidate['evidence_bindings']=[e4.binding(path) for path in sorted(report.iterdir()) if path.is_file() and path.name!='FEP_E4_R1_CANDIDATE_SEAL.json']
    candidate['final_readback']=e4.binding(report/'FINAL_EXIT_READBACK.json');candidate['FEP_PRODUCTION']='UNGRANTED'
    candidate['logical_digest']=digest({k:v for k,v in candidate.items() if k!='logical_digest'})
    e4.emit('FEP_E4_R1_CANDIDATE_SEAL',candidate)
    print('PASS final evidence readback; new fits=0; new scoring=0',flush=True)


if __name__=='__main__':main()
