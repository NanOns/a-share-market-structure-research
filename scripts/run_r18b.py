"""Cross-process full owner-DAG replay and immutable execution attestations."""
import sys,json,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_authority import ReplayAuthority
from workbench_analysis.v4_14_replay_io import publish,exact,ref,digest

def invoke(a,artifact_root,namespace,date,choice,prior,index,revision='r1'):
    envelope=dict(target_trade_date=date,target_revision=revision,previous_market_session=a.previous(date),cutoff=date+'T16:00:00+00:00',authority_bindings=a.bindings(),contract_package_digest=a.package_digest,previous_state_publication=prior,source_refs=[*a.refs,*a.owners.values(),ref(ROOT,'config/v4_07_machine_vectors_v1.json'),ref(ROOT,'config/v4_10_machine_vectors_r1_2.json'),ref(ROOT,'config/v4_12_machine_vectors_v1.json')],source_availability=[dict(max_source_trade_date=date,system_available_at=date+'T01:00:00+00:00',basis='EXPLICIT_SYNTHETIC_FACTS')],evidence_class='ENGINEERING_SYNTHETIC',owner_inputs=choice)
    input_ref=publish(artifact_root,namespace+'/execution/'+str(index)+'/input.json',envelope)
    rp=namespace+'/execution/'+str(index)+'/child_receipt.json'
    process=subprocess.Popen([sys.executable,'-m','scripts.r18_replay_worker',str(Path(artifact_root)/input_ref['path']),str(artifact_root),namespace,rp],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf8',errors='replace')
    out,err=process.communicate(timeout=120);exited=datetime.now(timezone.utc).isoformat()
    if process.returncode:raise RuntimeError(err)
    receipt=json.loads(exact(artifact_root,ref(artifact_root,rp)))
    if receipt['pid']!=process.pid:raise ValueError('CHILD_PID_ATTESTATION_MISMATCH')
    receipt.update(exit_code=process.returncode,exited_at=exited,producer_exited=process.poll() is not None,os_wait_completed=True)
    rr=publish(artifact_root,namespace+'/execution/'+str(index)+'/parent_wait_receipt.json',receipt)
    return receipt['publication'],rr,receipt

def run(artifact_root=ROOT,namespace='reports/v4_14_replay_r18/full_dag_r3'):
    a=ReplayAuthority(ROOT);dates=[d for d in a.calendar['session_dates'] if '2026-08-31'<=d<='2026-09-30'];records=[];prior=None;previous_receipt=None;rows=[]
    choices={
        '2026-09-01':dict(structure_vector='S01'),
        '2026-09-02':dict(structure_vector='S05_hold'),
        '2026-09-03':dict(structure_vector='S05_retest'),
        '2026-09-04':dict(structure_vector='S05_confirm'),
        '2026-09-16':dict(severe_extension=True), '2026-09-17':dict(severe_extension=True),
        '2026-09-21':dict(confirmation=True,structure_vector='S05_hold'),
        '2026-09-22':dict(confirmation=True,structure_vector='S05_retest'),
        '2026-09-23':dict(confirmation=True,structure_vector='S05_confirm'),
        '2026-09-24':dict(confirmation=True,damage=True,structure_vector='S03'),
        '2026-09-28':dict(confirmation=True,unknown=True),
        '2026-09-29':dict(confirmation=True,structure_vector='S03'), '2026-09-30':dict(confirmation=True,structure_vector='S03')}
    for i,date in enumerate(dates):
        choice=choices.get(date,dict(structure_vector='S05_no_separation' if i==0 else 'S01'))
        publication,receipt_ref,receipt=invoke(a,artifact_root,namespace,date,choice,prior,i)
        manifest=json.loads(exact(artifact_root,publication));row=manifest['output']['d2']['rows'][0];rows.append(dict(date=date,state=row,events=manifest['output']['events'],structure=manifest['output']['structure_observation']))
        if previous_receipt:
            assert receipt['pid']!=previous_receipt['pid'] and receipt['started_at']>previous_receipt['exited_at'] and receipt['previous_readback']==prior
        records.append(dict(publication=publication,execution=receipt_ref,producer_execution=records[-1]['execution'] if records else None))
        prior=publication;previous_receipt=receipt
    # T r2 and a second fresh-process identical T r1 both use the exact T-1.
    predecessor=records[-2]['publication'];choice=choices[dates[-1]]
    r2,r2ref,r2receipt=invoke(a,artifact_root,namespace,dates[-1],choice,predecessor,len(dates),'r2')
    identical,identref,identreceipt=invoke(a,artifact_root,namespace,dates[-1],choice,predecessor,len(dates)+1,'r1')
    r1=records[-1]['publication'];assert identical==r1
    r1m=json.loads(exact(artifact_root,r1));r2m=json.loads(exact(artifact_root,r2))
    assert r1m['previous_state_publication']==r2m['previous_state_publication']==predecessor
    assert r1m['output']['d2']['rows']==r2m['output']['d2']['rows'] and r1m['output']['logical_events']==r2m['output']['logical_events']
    gate=dict(R18B_CROSS_PROCESS_FULL_DAG_REPLAY='PASS_LOCAL',CROSS_PROCESS_PREVIOUS_SESSION='PASS',SAME_DAY_REVISION_ISOLATION='PASS',FULL_DAG_PERSISTED_REPLAY='PASS_LOCAL',records=records,trajectory=rows,same_day=dict(r1=r1,r2=r2,previous=predecessor,r2_execution=r2ref),determinism=dict(first=r1,second=identical,first_execution=records[-1]['execution'],second_execution=identref),calendar_binding=a.calendar_ref,authority_bindings=a.bindings(),contract_package_digest=a.package_digest,bootstrap='EXPLICIT_SYNTHETIC_NO_PRIOR_STATE',NEXT='R18C',ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT')
    return publish(artifact_root,namespace+'/completion_gate.json',gate)
if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
