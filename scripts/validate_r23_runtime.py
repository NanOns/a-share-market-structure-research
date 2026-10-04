"""Independent SQLite oracle. Never imports runtime/driver/writer/predicates."""
import hashlib,json,sqlite3,subprocess,ast
from pathlib import Path
from scripts.r23_io import ROOT,BASE,AUDIT,ACCEPT,AUTH,DEPS,read,ref,atomic
def require(value,message):
    if not value:raise ValueError(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def sha(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def authority(root=ROOT):
    a=read(ACCEPT,root);d=read(DEPS,root);activation=read(AUTH,root)
    require(a['audited_remote_head']==BASE and a['tested_source']=='319d598ef372ac52829083567e41188a15c053a3','AUDIT_IDENTITY')
    require(a['external_decision']=='PASS_FINAL_CLOCK_AUTHORITY_AND_GOVERNANCE_NORMALIZATION' and a['runtime_engineering_entry'] is True,'ENGINEERING_EXTERNAL_ENTRY')
    require(a['external_authority']==ref(AUDIT,root) and a['external_authority']['sha256']=='92dc3b5a4b359df6fa42bbdf541fd284b4b53ab46afb1e850a99621e60c5ac83','EXTERNAL_AUDIT_EXACT')
    tag=subprocess.check_output(['git','rev-parse',a['immutable_tested_tag']+'^{commit}'],cwd=root,text=True).strip();require(tag==a['tested_source'],'R22R1_TAG')
    subprocess.run(['git','merge-base','--is-ancestor',tag,BASE],cwd=root,check=True)
    for b in a['bindings']+d['bindings']+[d['fixture_registry']]:require(ref(b['path'],root)==b,'EXACT_DEPENDENCY '+b['path'])
    require(d['current_audit_head']==ref('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json',root),'EXPLICIT_V3_REQUIRED')
    for obj in (a,activation):
        for k in ('runtime_authorized','real_shadow_authorized','production','shadow','focus','V4_16'):require(obj[k] is False,'PERMISSION_OVERCLAIM')
    require(d['blocked_capabilities']==['A04_H21_CONSUMER','A04_HISTORICAL_AMOUNT_A','A08_CURRENT_RUNTIME'],'CAPABILITY_ISOLATION')
    return d
def inspect_database(path,root=ROOT):
    deps=authority(root);db=sqlite3.connect('file:'+Path(path).as_posix()+'?mode=ro',uri=True)
    require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLITE_INTEGRITY')
    require(not db.execute('PRAGMA foreign_key_check').fetchall(),'FOREIGN_KEY_INTEGRITY')
    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    require(all(t.startswith('shadow_') for t in tables),'LEGACY_NAMESPACE_LEAK')
    bodies={}
    for table in tables:
        if table=='shadow_publication_heads':continue
        records=[]
        for identity,namespace,origin,payload,digest in db.execute('SELECT * FROM '+table+' ORDER BY rowid'):
            p=json.loads(payload);require(hashlib.sha256(payload.encode()).hexdigest()==digest,'DURABLE_ROW_DIGEST')
            require(namespace=='SHADOW_V4' and origin=='ENGINEERING_FIXTURE','REAL_SAMPLE_LEAK')
            require(p.get('evidence_origin','ENGINEERING_FIXTURE')!='PIT_OBSERVED','PIT_CLAIM')
            records.append(p)
        bodies[table]=records
    publications=bodies['shadow_publications'];enrollments=bodies['shadow_first_enrollments'];outcomes=bodies['shadow_outcome_revisions']
    require(len(publications)==2 and [p['revision'] for p in publications]==[1,2],'PUBLICATION_REVISIONS')
    require(len(enrollments)==1,'ONE_ORIGINAL_ENROLLMENT')
    e=enrollments[0];require(e['T0']=='2026-09-28' and e['entity_id']=='S','T0_IDENTITY')
    event=sha(['RESEARCH_STATE_V1','R23_ENGINEERING_LINEAGE','STOCK','S','R23_EP_S','FIRST_PREWATCH','2026-09-28'])
    require(e['logical_event_id']==event and e['enrollment_id']==sha([event,'ENGINEERING_SYNTHETIC']),'INDEPENDENT_COHORT_IDENTITY')
    require(e['FIRST_OBSERVED']==e['enrollment_id'] and e['evidence_origin']=='ENGINEERING_FIXTURE','FIRST_OBSERVED_IMMUTABLE')
    slots=bodies['shadow_observation_slots'];accepted=[p for p in slots if p['slot_status']=='ACCEPTED_ON_TIME']
    require(len(accepted)==2,'ON_TIME_ENGINEERING_SLOTS')
    slot_id=sha(['RESEARCH_STATE_V1','R23_ENGINEERING_LINEAGE','2026-09-28'])
    for p in accepted:
        require(p['slot_id']==slot_id and p['scheduled_cutoff_at']=='2026-09-28T13:00:00Z' and p['observation_deadline']=='2026-09-28T14:30:00Z','CLOCK_AND_SLOT_KEY')
        require(p['sample_class']=='ENGINEERING_ONLY' and p['accepted_at']<=p['observation_deadline'],'ENGINEERING_ON_TIME_ONLY')
    for p in publications:
        require(p['slot_id']==slot_id and p['prior_session_state_head']['trade_date']=='2026-09-24','PREVIOUS_ACCEPTED_SESSION')
        require(p['prior_session_state_head']['publication_id']=='R23_ISOLATED_SEED','EXACT_PRIOR_HEAD')
        require(any(f['source_manifest_digest']==p['source_manifest_digest'] for f in bodies['shadow_source_freeze_manifests']),'FROZEN_MANIFEST')
        require(any(t['publication_id']==p['publication_id'] and t['state']=='COMMIT_VISIBLE' for t in bodies['shadow_transaction_receipts']),'COMMITTED_TRANSACTION_RECEIPT')
    for f in bodies['shadow_source_freeze_manifests']:
        check=dict(f);check.pop('source_manifest_digest');require(sha(check)==f['source_manifest_digest'],'MANIFEST_DIGEST')
        by_id={r['receipt_id']:r for r in bodies['shadow_source_readiness_receipts']}
        receipts=[by_id[k] for k in f['mandatory_source_receipt_ids']]
        require(len(receipts)==2 and [r['source_digest'] for r in receipts]==f['mandatory_source_digests'],'MANIFEST_RECEIPT_BINDING')
        for r in receipts:
            require(r['first_observed_at']<=r['integrity_passed_at']<=r['system_available_at']<=f['scheduled_cutoff_at'],'VISIBILITY_ORDER')
            require(r['source_digest']==r['consumed_binding']['sha256'] and ref(r['consumed_binding']['path'],root)==r['consumed_binding'],'CONSUMED_EXACT_BYTES')
    require(len(bodies['shadow_observations'])==2 and len({o['logical_event_id'] for o in bodies['shadow_observations']})==1,'REVISION_NO_NEW_EVENT')
    due=bodies['shadow_due_outbox'];require(len(due)==5 and sorted(d['horizon'] for d in due)==[1,3,5,10,20],'FROZEN_DUE_HORIZONS')
    require(next(d for d in due if d['horizon']==1)['due_date']=='2026-09-29','DUE_T1')
    require(len(outcomes)==2 and [o['revision_sequence'] for o in outcomes]==[1,2],'APPEND_ONLY_SETTLEMENT_REVISIONS')
    require(outcomes[0]['first_observed_id']==outcomes[1]['first_observed_id']==outcomes[0]['outcome_revision_id'],'OUTCOME_FIRST_OBSERVED')
    for o,expected,mfe in zip(outcomes,(0.1,0.2),(0.2,0.3)):
        require(o['horizon']==1 and o['due_date']=='2026-09-29' and o['outcome_status']=='OBSERVED','ENGINEERING_SETTLEMENT')
        require(abs(o['R_N']-expected)<1e-12 and abs(o['MFE_N']-mfe)<1e-12 and abs(o['MAE_N']+0.1)<1e-12 and o['PATH_MDD_CLOSE_N']==0,'LITERAL_NUMERIC_EXPECTATIONS')
        require(o['price_path'][0]['trade_date']>e['T0'] and o['evaluation_basis_date']=='2026-09-29','FUTURE_PRICE_BASIS')
        require(o['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' and o['future_read_count']>0,'ENGINEERING_NOT_REAL_MATURITY')
        require(o['frozen_t0']==e['frozen_t0'],'T0_FREEZE_BINDING')
        source=o['evaluation_source'];require(ref(source['path'],root)==source,'FUTURE_SOURCE_EXACT')
        require(o['price_path']==[read(source['path'],root)['rows']['S']['2026-09-29']],'CONSUMED_FUTURE_ENDPOINT_BYTES')
    artifacts={row[0]:json.loads(row[1])['value'] for row in db.execute('SELECT id,payload FROM shadow_artifacts')}
    freeze=artifacts[e['frozen_t0']['path'][7:]]
    for o in outcomes:
        require(o['controls']['B']['assignment_digest']==freeze['controls']['assignment_digest'],'CONTROL_FROZEN')
        require(o['market_benchmark']['benchmark_id']==freeze['market']['benchmark_id'],'BENCHMARK_FROZEN')
    ops=bodies['shadow_runtime_operations'];require(ops[0]['operation']=='T0_BENCHMARK_CONTROL_FROZEN' and all(o['operation']=='ACCEPTED_ENGINEERING_FUTURE_READ' for o in ops[1:]),'T0_BEFORE_FUTURE_READ')
    for h in bodies['shadow_health_receipts']:
        require(h['REAL_SHADOW_OBSERVATIONS']==h['PIT_OBSERVED_REAL_SAMPLES']==0,'ZERO_REAL_COUNTERS')
        for k in ('SHADOW_STABLE','PROVISIONAL_FORWARD_EVIDENCE','FORWARD_SUPPORTED'):require(h[k]=='NOT_GRANTED','HEALTH_CANNOT_GRANT_CAPABILITY')
        require(h['capability_states']=={k:'BLOCKED_AFFECTED_SCOPE' for k in deps['blocked_capabilities']},'CAPABILITY_HEALTH')
    heads=db.execute('SELECT * FROM shadow_publication_heads').fetchall();require(heads==[(slot_id,publications[-1]['publication_id'],2)],'EXACT_HEAD_CAS')
    require(len(bodies['shadow_control_receipts'])==1 and bodies['shadow_control_receipts'][0]['preserve_pending_obligations'],'STOP_PRESERVES_OBLIGATIONS')
    db.close()
    return dict(status='PASS_LOCAL',database=ref(str(Path(path).resolve().relative_to(root)),root),publications=2,enrollments=1,observations=2,due_items=5,outcome_revisions=2,independent_expected='LITERAL_AUTHORED_NO_RUNTIME_HELPERS',REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0)
def protected(root=ROOT):
    existing=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=root,text=True,encoding='utf8').splitlines())
    changed=set(subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=root,text=True,encoding='utf8').splitlines())
    require((changed&existing)<={'.gitattributes'},'HISTORICAL_BASELINE_MUTATION')
    require(not (root/'data/v4/V4_16_ACCEPTED_HEAD.json').exists(),'NO_ACCEPTED_HEAD')
    stage=read('data/v4/V4_STAGE_ACCEPTED_HEAD.json',root);require(stage['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED','STAGE_UNCHANGED')
    require(read('data/v4/V4_DATA_ACCEPTED_HEAD.json',root)['accepted_trade_date']=='2026-09-30','DATA_UNCHANGED')
    bindings=[ref(p,root) for p in sorted(existing) if p.startswith(('data/v4/V4_','config/v4_16_','config/v4_cross_stage_','reports/r22/','reports/r22r1/'))]
    return dict(status='PASS_LOCAL',baseline=BASE,all_existing_baseline_files_immutable_except_additive_gitattributes=True,bindings=bindings)
def negative_matrix(root=ROOT):
    expected={1:'REAL_SHADOW_NOT_AUTHORIZED',2:'CLOCK_MISMATCH',3:'MISSED_OBSERVATION_SLOT',4:'MISSING_DURABLE_RECORD',5:'SOURCE_DIGEST_MISMATCH',6:'BACKDATED_OR_UNREGISTERED_READINESS',7:'LEGACY_PRIOR_FORBIDDEN',8:'GAP_FAIL_CLOSED',9:'CORRECTION_NEW_ORIGINAL_FORBIDDEN',10:'INJECTED_TRANSACTION_FAILURE',11:'UNIQUE constraint failed',12:'NO_RAW_PROVIDER_FALLBACK',13:'PRE_DUE_FUTURE_READ_FORBIDDEN',14:'UNACCEPTED_FUTURE_DATA_HEAD',15:'MEMBERSHIP_REPLAY_CANNOT_CLAIM_PIT',16:'BLOCKED_A04_A08_CAPABILITY',17:'BLOCKED_A04_A08_CAPABILITY',19:'PARAMETER_CHANGE_WITHOUT_NEW_IDENTITY',20:'CLOCK_POLICY_CHANGE_WITHOUT_NEW_VERSION',21:'FORBIDDEN_FEEDBACK_OR_REAL_COUNTER',22:'CONTROL_BENCHMARK_REDRAW_FORBIDDEN',23:'FORBIDDEN_FEEDBACK_OR_REAL_COUNTER',24:'ROLLBACK_DELETE_FORBIDDEN'}
    result=[]
    for n in range(1,25):
        record=read('reports/r23/negative_evidence/N%02d.json'%n,root)
        require(record['database_binding']==ref(record['database_binding']['path'],root),'NEGATIVE_DB_BYTES')
        db=sqlite3.connect('file:'+(root/record['database_binding']['path']).as_posix()+'?mode=ro',uri=True)
        count=lambda t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]
        original=1 if n in (9,11,13,14,18,22,24) else 0
        require(count('shadow_publications')==count('shadow_publication_heads')==count('shadow_first_enrollments')==original,'NEGATIVE_VISIBLE_PUBLICATION_LEAK')
        require(count('shadow_due_outbox')==5*original and count('shadow_outcome_revisions')==0,'NEGATIVE_DUE_OR_OUTCOME_LEAK')
        for namespace,origin in db.execute('SELECT namespace,evidence_origin FROM shadow_observations'):require((namespace,origin)==('SHADOW_V4','ENGINEERING_FIXTURE'),'NEGATIVE_REAL_SAMPLE_LEAK')
        if n==18:require(not record['rejections'],'PURE_CORE_OPTIONAL_SOURCE_CONTINUES')
        else:require(any(expected[n] in error for error in record['rejections']),'NEGATIVE_REQUIRED_REJECTION')
        if n==10:require(record['before']==record['after'],'TRANSACTION_ROLLBACK_ALL_TABLES')
        db.close();result.append(dict(case='N%02d'%n,status='PASS_LOCAL',actual_rejections=record['rejections'],visible_originals=original,evidence_origin='ENGINEERING_FIXTURE'))
    return dict(status='PASS_LOCAL',cases=result,count=24,expected_authored_independently=True)
if __name__=='__main__':
    import sys
    result=inspect_database(Path(sys.argv[1]));atomic('reports/r23/INDEPENDENT_RUNTIME_ORACLE.json',result);atomic('reports/r23/PROTECTED_BYTES.json',protected());print(json.dumps(result))
