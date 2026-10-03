"""Persist production-shaped engineering evidence, without current maturity grants."""
import json,subprocess
from scripts.r20r1r2_io import ROOT,BASE,ref,exact,atomic
from scripts.r20r1r2_fixture import build,put
from scripts.r20r1r2_maturity_debt import refresh
from scripts.r20r1r2_dm01_resolver import resolve_accepted_adjusted_daily_path
from scripts.r20r1r2_forward_projection import native_row
from scripts.validate_r20r1r2_oracle import validate

def run():
    current=refresh();directory=ROOT/'reports/r20r1r2/engineering_fixtures/sequence_r2';report=ROOT/'reports/r20r1r2/PRODUCTION_SHAPED_REACHABILITY.json'
    if not report.exists() or json.loads(report.read_bytes()).get('source_binding_revision')!='R2':
        packets=build(directory);steps=[]
        for label,batch,coverage in [('open',[],[]),('t1',packets[:1],[1]),('t3',packets[1:2],[1,3]),('full',packets[2:],[1,3,5,10,20])]:
            refresh(batch,directory);binding=atomic('reports/r20r1r2/engineering_fixtures/snapshots_r2/'+label+'.json',(directory/'reports/r20r1r2/MATURITY_DEBT_READBACK.json').read_bytes(),raw=True,immutable=True)
            steps.append(dict(fixture_directory=directory.relative_to(ROOT).as_posix(),readback=binding,proved_horizons=coverage))
        atomic('reports/r20r1r2/PRODUCTION_SHAPED_REACHABILITY.json',dict(source_binding_revision='R2',evidence_class='ISOLATED_ENGINEERING_REACHABILITY_ONLY',current_real_capability_upgrade=False,transitions=steps,no_invented_endpoint_list=True,production_batch_chain=True,all_five_horizons=True))
    correction=ROOT/'reports/r20r1r2/engineering_fixtures/correction_r2';correction_report=ROOT/'reports/r20r1r2/PRODUCTION_CORRECTION_REACHABILITY.json'
    if not correction_report.exists() or json.loads(correction_report.read_bytes()).get('source_binding_revision')!='R2':
        old=build(correction,(1,))[0];refresh([old],correction);initial=json.loads((correction/'reports/r20r1r2/MATURITY_DEBT_READBACK.json').read_bytes());new=build(correction,(1,),revision=2,prior_accepted_revision=old['data_head'])[0]
        out=exact(new['outcome'],correction);out.update(revision_sequence=2,supersedes=old['outcome']);new['outcome']=put(correction,'fixtures/r2/corrected_outcome.json',out);put(correction,'fixtures/correction_packets.json',[old,new]);refresh([new],correction)
        final=atomic('reports/r20r1r2/engineering_fixtures/snapshots_r2/correction.json',(correction/'reports/r20r1r2/MATURITY_DEBT_READBACK.json').read_bytes(),raw=True,immutable=True)
        atomic('reports/r20r1r2/PRODUCTION_CORRECTION_REACHABILITY.json',dict(source_binding_revision='R2',fixture_directory=correction.relative_to(ROOT).as_posix(),readback=final,original_first_observed=initial['FIRST_OBSERVED'],prior_accepted_snapshot=old['data_head'],evidence_class='ISOLATED_ENGINEERING_REACHABILITY_ONLY',current_real_capability_upgrade=False))
    atomic('reports/r20r1r2/SUPERSEDED_ATTEMPT_REGISTRY.json',dict(status='SUPERSEDED_ENGINEERING_ATTEMPT_NOT_ACCEPTANCE_EVIDENCE',superseded_directories=['reports/r20r1r2/engineering_fixtures/sequence','reports/r20r1r2/engineering_fixtures/correction','reports/r20r1r2/engineering_fixtures/snapshots'],reason='SOURCE_FREEZE_AND_INPUT_PUBLICATION_IDS_RECEIPT_BINDING_TIGHTENED',active_revision='R2',active_directories=['reports/r20r1r2/engineering_fixtures/sequence_r2','reports/r20r1r2/engineering_fixtures/correction_r2','reports/r20r1r2/engineering_fixtures/snapshots_r2'],current_real_upgrade=False))
    for isolated in [directory,correction]:
        put(isolated,'config/v4_data_accepted_head_v2.json',raw=(ROOT/'config/v4_data_accepted_head_v2.json').read_bytes())
    reg=json.loads((ROOT/'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json').read_bytes());freeze=exact(reg['freeze']);resolved=resolve_accepted_adjusted_daily_path(freeze['T0'],freeze['T0']);row=native_row(resolved['T0_adjusted_daily'],freeze['signal_id'],freeze['T0'],ROOT)
    atomic('reports/r20r1r2/CURRENT_REAL_DM01_ADMISSION.json',dict(status='PASS_LOCAL',actual_native_row_admitted=True,actual_production_head=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json'),native_artifact=resolved['T0_adjusted_daily'],native_receipt=resolved['T0_component_receipt'],native_price_basis=row['price_basis'],adjustment_readiness=row['adjustment_readiness'],native_T0_close=row['close'],frozen_T0_reference=freeze['comparison_reference'],future_accepted_endpoint_count=0,proved_horizons=[],CURRENT_REAL_MATURITY_EVIDENCE='NONE',REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME='NOT_GRANTED_PENDING_MATURITY_EVIDENCE',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED'))
    bindings=[]
    for prefix in ['reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/v4_15_runtime_r20','reports/r20r1','reports/r20r1r1','data/v4/V4_14_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_15_maturity_t0_lineage_r20r1r1_v2.json','config/v4_15_maturity_debt_contract_r20r1r1_v2.json']:
        bindings.extend(ref(p) for p in subprocess.check_output(['git','ls-files',prefix],cwd=ROOT,text=True,encoding='utf8').splitlines())
    bindings.extend(json.loads((ROOT/'reports/r20r1r2/ACTUAL_DM01_CONTRACT_FREEZE.json').read_bytes())['bindings'].values())
    atomic('reports/r20r1r2/FROZEN_BASELINE_BINDINGS.json',dict(execution_baseline=BASE,bindings=bindings))
    result=validate();atomic('reports/r20r1r2/R20R1R2_INDEPENDENT_ORACLE.json',result)
    atomic('reports/r20r1r2/REAL_DM01_INTEGRATION_SCOPE_GATE.json',dict(result,execution_baseline=BASE,current_debt_revision=current,V4_15_ACCEPTED_HEAD='NOT_CREATED',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_14_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',Production=False,Shadow=False,Focus=False,V4_16=False,bindings={k:ref(p) for k,p in {'projection_contract':'config/v4_15_forward_projection_r20r1r2_v1.json','actual_contract_freeze':'reports/r20r1r2/ACTUAL_DM01_CONTRACT_FREEZE.json','native_admission':'reports/r20r1r2/CURRENT_REAL_DM01_ADMISSION.json','production_shape_reachability':'reports/r20r1r2/PRODUCTION_SHAPED_REACHABILITY.json','independent_oracle':'reports/r20r1r2/R20R1R2_INDEPENDENT_ORACLE.json','master':'docs/evidence/r20r1r2/V4_NEXT_ROUND_EXECUTION_MASTER_R20R1R2_20261003.md','external_audit':'docs/evidence/r20r1r2/V4_R20R1R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md'}.items()}))
    print(json.dumps(result))
if __name__=='__main__':run()
