"""Independent persisted-state oracle. Does not import runtime or writer."""
import hashlib, json, sqlite3, re
from datetime import datetime
from pathlib import Path
from scripts.r24_io import ROOT, read, ref

def canonical(p):return json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(p):return hashlib.sha256(canonical(p).encode()).hexdigest()
def check(ok,reason):
    if not ok:raise ValueError(reason)
def exact(root,b):
    check(ref(b['path'],root)==b,'EXACT_BINDING_MISMATCH')
    return read(b['path'],root)
def protected(root=ROOT):
    paths=['data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json',
      'data/v4/V4_15_ACCEPTED_HEAD.json','config/v4_16_runtime_activation_authority_v1.json',
      'migrations/v4_16_r23_shadow_v1.sql']
    check(not (Path(root)/'data/v4/V4_16_ACCEPTED_HEAD.json').exists(),'V4_16_ACCEPTED_HEAD_FORBIDDEN')
    authority=read('config/v4_16_runtime_activation_authority_v2.json',root)
    check(not authority['runtime_authorized'] and not authority['real_shadow_authorized'],'COMMITTED_AUTHORITY_ENABLED')
    check(authority['REAL_SHADOW_OBSERVATIONS']==authority['PIT_OBSERVED_REAL_SAMPLES']==0,'REAL_COUNTERS_CHANGED')
    check(not (Path(root)/'data/v4/shadow_real_v1').exists(),'REAL_STORAGE_CREATED_IN_R24')
    return dict(bindings=[ref(p,root) for p in paths],committed_authority=ref('config/v4_16_runtime_activation_authority_v2.json',root),
        REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,V4_16_ACCEPTED_HEAD='NOT_CREATED')

def inspect(path,manifest,root=ROOT, test_only_storage_copy=False):
    root=Path(root)
    deps=read(manifest,root)
    authority=exact(root,deps['activation'])
    check(authority['environment_class']=='ACTIVATION_SIMULATION','SIMULATION_AUTHORITY_REQUIRED')
    check(authority['runtime_authorized'] is True and authority['real_shadow_authorized'] is True,'SIMULATION_AUTHORITY_DISABLED')
    acceptance=exact(root,authority['external_acceptance'])
    check(acceptance['authority_digest']==digest({k:v for k,v in authority.items() if k!='external_acceptance'}),'ACCEPTANCE_DIGEST')
    check(acceptance['decision']=='SIMULATION_ONLY_NOT_REAL_ACCEPTANCE','SIMULATION_ACCEPTANCE')
    grant=authority['grant']
    check(set(authority['required_grant_fields'])<=grant.keys(),'GRANT_COMPLETENESS')
    check(acceptance['authority_id']==authority['authority_id']==grant['authority_id'],'GRANT_AUTHORITY_IDENTITY')
    for key in ('clock','slot','storage','source_adapters','initialization_boundary'):
        check(grant[key]==deps[key],'GRANT_DEPENDENCY_BINDING')
    dependency_set={k:v for k,v in deps.items() if k not in ('activation','bindings')}
    dependency_set['bindings']=[b for b in deps['bindings'] if b!=deps['activation']]
    check(grant['runtime_dependency_contract_id']==deps['contract_id'] and grant['dependency_set_digest']==digest(dependency_set),'GRANT_DEPENDENCY_SET')
    for binding in deps['bindings']:check(ref(binding['path'],root)==binding,'EXACT_BINDING_MISMATCH')
    sources=exact(root,authority['grant']['source_authority'])
    check(test_only_storage_copy or Path(path).resolve()==(root/authority['grant']['storage_identity']['database_path']).resolve(),'ORACLE_STORAGE_IDENTITY')
    conn=sqlite3.connect('file:'+Path(path).resolve().as_posix()+'?mode=ro',uri=True)
    try:
        check(conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLITE_INTEGRITY')
        check(conn.execute('SELECT * FROM storage_identity').fetchall()==[(1,'ACTIVATION_SIMULATION','ACTIVATION_SIMULATION')],'STORAGE_IDENTITY')
        schema=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('index','trigger')")]
        check(set(['no_fact_update','no_fact_delete','origin_guard','unique_original_event','unique_slot_revision','unique_publication_revision','unique_due'])<=set(schema),'STORAGE_CONSTRAINTS_MISSING')
        expected=sqlite3.connect(':memory:')
        try:
            expected.executescript((root/deps['migration']['path']).read_text(encoding='utf-8'))
            def schema_signature(database):
                return sorted((typ,name,table,re.sub(r'\s+','',sql or '').replace('IFNOTEXISTS',''))
                    for typ,name,table,sql in database.execute('SELECT type,name,tbl_name,sql FROM sqlite_master'))
            check(schema_signature(conn)==schema_signature(expected),'STORAGE_SCHEMA_SEMANTICS')
        finally:expected.close()
        rows={}
        for kind,key,namespace,mode,origin,raw,sha in conn.execute('SELECT * FROM facts ORDER BY rowid'):
            p=json.loads(raw)
            check(hashlib.sha256(raw.encode()).hexdigest()==sha,'ROW_DIGEST')
            check((namespace,mode,origin)==('SHADOW_V4','SHADOW','ACTIVATION_SIMULATION'),'ROW_ORIGIN')
            check(p['evidence_class']=='NOT_REAL_EVIDENCE','SIMULATION_MISCLASSIFIED')
            identity_field={'receipt':'receipt_id','publication':'publication_id','enrollment':'enrollment_id','observation':'observation_id'}.get(kind)
            if identity_field:check(key==p[identity_field],'FACT_IDENTITY')
            if kind=='manifest':
                value={k:v for k,v in p.items() if k not in ('namespace','execution_mode','evidence_origin','evidence_class')}
                check(key==digest(value),'MANIFEST_FACT_IDENTITY')
            rows.setdefault(kind,[]).append(p)
        receipt_map={r['receipt_id']:r for r in rows.get('receipt',[])}
        for receipt in receipt_map.values():
            check(receipt['source_digest']==receipt['consumed_binding']['sha256'],'CONSUMED_DIGEST')
            exact(root,receipt['consumed_binding'])
            expected=sources['sources'][receipt['source_family']]
            check(receipt['consumed_binding']==expected['binding'] and receipt['target_trade_date']==expected['target_trade_date'],'SOURCE_AUTHORITY_BINDING')
            check(receipt['accepted_source_authority']==authority['grant']['source_authority'],'SOURCE_ACCEPTANCE')
            times=[datetime.fromisoformat(receipt[k].replace('Z','+00:00')) for k in ('first_observed_at','integrity_passed_at','system_available_at','created_at')]
            check(times==sorted(times),'RECEIPT_CHRONOLOGY')
        fields=exact(root,deps['slot'])['fields']
        manifests={digest({k:v for k,v in m.items() if k not in ('namespace','execution_mode','evidence_origin','evidence_class')}):m for m in rows.get('manifest',[])}
        pubs={p['publication_id']:p for p in rows.get('publication',[])}
        for slot in rows.get('slot',[]):
            check(all(k in slot and slot[k] is not None for k in fields),'SLOT_COMPLETENESS')
            check(slot['field_quality']=={k:'KNOWN' for k in fields},'SLOT_FIELD_QUALITY')
            check(slot['quality_contract']==exact(root,deps['slot_runtime_policy'])['contract_id'],'SLOT_QUALITY_CONTRACT')
            check(slot['slot_status']=='ACCEPTED_ON_TIME','SLOT_STATUS')
            receipts=[receipt_map[i] for i in slot['visibility_receipt_ids']]
            check({r['source_family'] for r in receipts}==set(exact(root,deps['source_adapters'])['mandatory_families']) and len(receipts)==2,'MANDATORY_SOURCE_SET')
            check(slot['source_provider_available_at']==max(r['first_observed_at'] for r in receipts),'PROVIDER_AGGREGATE')
            check(slot['system_available_at']==max(r['system_available_at'] for r in receipts),'SYSTEM_AGGREGATE')
            check(slot['source_provider_available_at']<=slot['system_available_at']<=slot['scheduled_cutoff_at'] and
                  slot['system_available_at']<=slot['computation_started_at']<=slot['computation_finished_at']<=slot['accepted_at']<=slot['observation_deadline'],'SLOT_CHRONOLOGY')
            check(slot['core_revision']==slot['publication_id'] and slot['source_manifest_digest'] in manifests,'SLOT_MANIFEST')
            manifest_payload=manifests[slot['source_manifest_digest']]
            check(manifest_payload['receipt_ids']==slot['visibility_receipt_ids'],'MANIFEST_VISIBILITY')
            for k in ('trade_date','model_contract_id','parameter_set_id','state_lineage_id','capability_scope'):
                check(slot[k]==manifest_payload[k],'MANIFEST_IDENTITY')
            for k in ('model_contract_id','parameter_set_id','state_lineage_id'):
                check(slot[k]==grant[k],'SLOT_ACTIVATION_IDENTITY')
            check(slot['slot_id']==digest([slot[k] for k in ('model_contract_id','state_lineage_id','trade_date')]),'SLOT_IDENTITY')
            check(slot['publication_id']==digest([slot['slot_id'],slot['revision']]),'PUBLICATION_REVISION_IDENTITY')
            check(slot['capability_scope']==sorted(set(slot['capability_scope'])) and set(slot['capability_scope'])<=set(authority['grant']['capability_scope']),'CAPABILITY_SCOPE')
            check(pubs[slot['publication_id']]['source_manifest_digest']==slot['source_manifest_digest'],'PUBLICATION_MANIFEST')
        obs={p['observation_id']:p for p in rows.get('observation',[])}
        for observation in obs.values():
            predecessor=observation['supersedes_observation']
            if predecessor:
                check(predecessor in obs,'MISSING_SUPERSEDES')
                prior=obs[predecessor]
                check(prior['logical_event_id']==observation['logical_event_id'] and prior['slot_id']==observation['slot_id'] and prior['revision']+1==observation['revision'],'SUPERSEDES_LINEAGE')
            else:check(observation['revision']==1,'CORRECTION_MISSING_PREDECESSOR')
        enrollments=rows.get('enrollment',[])
        artifacts={r[0]:json.loads(r[1])['value'] for r in conn.execute("SELECT id,payload FROM facts WHERE kind='artifact'")}
        def artifact(binding):
            check(binding['path'].startswith('sqlite:') and binding['path'][7:] in artifacts,'ARTIFACT_MISSING')
            value=artifacts[binding['path'][7:]]
            raw=canonical(value).encode()
            check(hashlib.sha256(raw).hexdigest()==binding['sha256'] and len(raw)==binding['bytes'],'ARTIFACT_BINDING')
            return value
        check(len({p['logical_event_id'] for p in enrollments})==len(enrollments),'SECOND_ORIGINAL')
        for e in enrollments:
            check(e['FIRST_OBSERVED']==e['enrollment_id'] and e['cohort_namespace']=='FIRST_OBSERVED','FIRST_OBSERVED_IDENTITY')
            check(e['enrollment_id']==digest([e['logical_event_id'],'SHADOW_V4_FIRST_OBSERVED']),'ENROLLMENT_IDENTITY')
            check(e['slot_status']=='ACCEPTED_ON_TIME' and any(s['slot_id']==e['slot_id'] and s['revision']==1 and s['trade_date']==e['T0'] for s in rows.get('slot',[])),'ENROLLMENT_SLOT')
            check(len([d for d in rows.get('due',[]) if d['enrollment_id']==e['enrollment_id']])==5,'DUE_OBLIGATIONS')
            frozen=artifact(e['frozen_t0'])
            check(frozen['T0']==e['T0'] and frozen['enrollment_id']==e['enrollment_id'],'FROZEN_T0_IDENTITY')
            check(frozen['snapshot']==sources['sources']['T0_SNAPSHOT']['binding'],'FROZEN_SNAPSHOT')
            check(all(frozen[k]['benchmark_id']==e['benchmark_ids'][k] for k in ('market','sector')),'BENCHMARK_IDENTITY')
            check(all(frozen['controls'][k]['control_assignment_id']==e['control_assignment_ids'][k] for k in ('A','B','C')),'CONTROL_IDENTITY')
            for due in rows.get('due',[]):
                if due['enrollment_id']==e['enrollment_id']:check(due['frozen_t0']==e['frozen_t0'],'DUE_FROZEN_T0')
        for publication in pubs.values():artifact(publication['radar_publication'])
        for outcome in rows.get('outcome',[]):
            check(outcome['enrollment_id'] in {e['enrollment_id'] for e in enrollments},'OUTCOME_ENROLLMENT')
            check(outcome['revision_sequence']>=1 and outcome['first_observed_id'],'OUTCOME_REVISION')
        for slot_id,pid,revision in conn.execute('SELECT * FROM publication_heads'):
            check(pid in pubs and pubs[pid]['slot_id']==slot_id and pubs[pid]['revision']==revision,'HEAD_READBACK')
            check(revision==max(p['revision'] for p in pubs.values() if p['slot_id']==slot_id),'HEAD_NOT_LATEST_ACCEPTED_REVISION')
        check(all(p['REAL_SHADOW_OBSERVATIONS']==p['PIT_OBSERVED_REAL_SAMPLES']==0 for p in rows.get('health',[])),'REAL_COUNTERS')
        check(conn.execute('SELECT authority_id FROM activation_head WHERE singleton=1').fetchone()==(authority['authority_id'],),'ACTIVATION_HEAD')
        check(all(p['preserve_accepted_observations'] and p['preserve_pending_obligations'] and not p['legacy_mutated'] for p in rows.get('control',[])),'ROLLBACK_POLICY')
        return dict(status='PASS_LOCAL',required_slot_field_count=len(fields),publications=len(pubs),
           observations=len(obs),enrollments=len(enrollments),due_items=len(rows.get('due',[])),
           outcomes=len(rows.get('outcome',[])),rollback=bool(rows.get('control')),
           evidence_origin='ACTIVATION_SIMULATION',evidence_class='NOT_REAL_EVIDENCE',protected=protected(root))
    finally:conn.close()
