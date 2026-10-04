"""Independent persisted slot/revision oracle. Never imports runtime writers."""
import hashlib,json,sqlite3,subprocess
from datetime import datetime
from pathlib import Path
from scripts.r23r1_io import ROOT,BASE,read,ref
from scripts.validate_r23_runtime import inspect_database as prior_oracle
def require(ok,reason):
    if not ok:raise ValueError(reason)
def hash_value(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def timestamp(value):
    require(isinstance(value,str) and value.endswith('Z'),'UTC_REQUIRED')
    return datetime.fromisoformat(value.replace('Z','+00:00'))
def load(path):
    db=sqlite3.connect('file:'+Path(path).resolve().as_posix()+'?mode=ro',uri=True)
    try:
        require(db.execute('PRAGMA integrity_check').fetchone()==('ok',),'SQLITE_INTEGRITY')
        result={}
        for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            if table=='shadow_publication_heads':continue
            values=[]
            for namespace,origin,payload,digest in db.execute('SELECT namespace,evidence_origin,payload,digest FROM '+table+' ORDER BY rowid'):
                require(namespace=='SHADOW_V4' and origin=='ENGINEERING_FIXTURE','ENGINEERING_ONLY')
                require(hashlib.sha256(payload.encode()).hexdigest()==digest,'ROW_DIGEST')
                values.append(json.loads(payload))
            result[table]=values
        return result
    finally:db.close()
def inspect_records(records,root=ROOT):
    root=Path(root);deps=read('config/v4_16_runtime_dependencies_v1.json',root)
    require(ref(deps['slot']['path'],root)==deps['slot'],'EXACT_SLOT_V2')
    fields=read(deps['slot']['path'],root)['fields'];require(len(fields)==18,'REQUIRED_FIELD_COUNT')
    policy=ref('config/v4_16_r23r1_slot_runtime_policy_v1.json',root)
    require(policy['sha256']=='427798478357a7411b8f969d3acc7f9220145900e16ade8f0f041dfffa83b4c4','EXACT_REPAIR_POLICY')
    receipts={r['receipt_id']:r for r in records['shadow_source_readiness_receipts']}
    manifests={r['source_manifest_digest']:r for r in records['shadow_source_freeze_manifests']}
    pubs={r['publication_id']:r for r in records['shadow_publications']}
    for r in receipts.values():
        require(timestamp(r['first_observed_at'])<=timestamp(r['integrity_passed_at'])<=timestamp(r['system_available_at'])<=timestamp(r['created_at']),'RECEIPT_CHRONOLOGY')
    slots=records['shadow_observation_slots'];accepted=[]
    for s in slots:
        require(set(fields)<=s.keys(),'MISSING_SLOT_FIELD')
        require(s['slot_id']==hash_value([s[k] for k in ('model_contract_id','state_lineage_id','trade_date')]),'SLOT_ID')
        require(s['namespace']=='SHADOW_V4' and s['execution_mode']=='SHADOW' and s['evidence_origin']=='ENGINEERING_FIXTURE','SLOT_NAMESPACE_OR_ORIGIN')
        require(s['sample_class']=='ENGINEERING_ONLY' and s.get('REAL_SHADOW_OBSERVATIONS',0)==s.get('PIT_OBSERVED_REAL_SAMPLES',0)==0,'SLOT_CANNOT_GRANT_REAL_SAMPLE')
        require(s['quality_contract']=='V4_16_R23R1_SLOT_RUNTIME_POLICY_V1','QUALITY_CONTRACT')
        require(s['field_quality']=={k:('NOT_YET_AVAILABLE' if s[k] is None else 'KNOWN') for k in fields},'FIELD_QUALITY')
        require(isinstance(s['capability_scope'],list) and bool(s['capability_scope']) and s['capability_scope']==sorted(set(s['capability_scope'])),'CANONICAL_SCOPE')
        ids=s['visibility_receipt_ids']
        for field,source in [('source_provider_available_at','first_observed_at'),('system_available_at','system_available_at')]:
            expected=max((receipts[i][source] for i in ids),key=timestamp,default=None)
            require(s[field]==expected,'VISIBILITY_AGGREGATE_'+field)
        if s['slot_status']!='ACCEPTED_ON_TIME':
            require(s['slot_status'] in ('PLANNED','BLOCKED_SOURCE_NOT_READY','MISSED_OBSERVATION_SLOT'),'SLOT_STATUS')
            require(all(s[k] is None for k in ('publication_id','core_revision','source_manifest_digest','computation_started_at','computation_finished_at','accepted_at')),'UNACCEPTED_SLOT_CANNOT_CLAIM_COMPLETION')
            continue
        require(all(s[k] is not None for k in fields),'NULL_ACCEPTED_FIELD')
        require(s['source_manifest_digest'] in manifests,'MANIFEST_BINDING')
        m=manifests[s['source_manifest_digest']];body={k:v for k,v in m.items() if k!='source_manifest_digest'}
        require(hash_value(body)==s['source_manifest_digest'],'MANIFEST_DIGEST')
        require(ids==m['mandatory_source_receipt_ids'] and s['visibility_complete'],'EXACT_CONSUMED_RECEIPTS')
        request=s['evaluated_request'];p=pubs.get(s['publication_id'])
        require(p is not None and hash_value(request)==p['request_digest'],'REQUEST_BINDING')
        for k in ('model_contract_id','state_lineage_id','trade_date'):require(s[k]==request[k]==m[k],'REQUEST_SLOT_IDENTITY')
        require(s['capability_scope']==sorted(set(request['capabilities'])) and not set(s['capability_scope'])&set(deps['blocked_capabilities']),'CAPABILITY_SCOPE')
        require(s['parameter_set_id']==request['parameter_set_id']==m['parameter_set_id']==read(deps['fixture_registry']['path'],root)['parameter_set_id'],'PARAMETER_IDENTITY')
        for k in ('computation_started_at','computation_finished_at','accepted_at'):require(s[k]==request[k],'REQUEST_TIMESTAMP')
        require(s['publication_id']==s['core_revision']==hash_value([s['model_contract_id'],s['state_lineage_id'],s['trade_date'],s['revision']]),'CORE_REVISION')
        require(p['source_manifest_digest']==s['source_manifest_digest'],'PUBLICATION_MANIFEST')
        provider,system,cutoff,start,finish,accept,deadline=(timestamp(s[k]) for k in ('source_provider_available_at','system_available_at','scheduled_cutoff_at','computation_started_at','computation_finished_at','accepted_at','observation_deadline'))
        require(provider<=system<=cutoff and system<=start<=finish<=accept<=deadline,'SLOT_TIME_ORDER')
        accepted.append(s)
    observations={r['observation_id']:r for r in records['shadow_observations']}
    for o in observations.values():
        previous=[r for r in observations.values() if r['logical_event_id']==o['logical_event_id'] and r['slot_id']==o['slot_id'] and r['revision']<o['revision']]
        expected=max(previous,key=lambda r:r['revision'])['observation_id'] if previous and o['source_correction'] else None
        require(o['supersedes_observation']==expected,'OBSERVATION_PREDECESSOR')
        seen={o['observation_id']};cursor=o
        while cursor['supersedes_observation'] is not None:
            key=cursor['supersedes_observation'];require(key in observations and key not in seen,'OBSERVATION_CYCLE_OR_MISSING');seen.add(key)
            prior=observations[key]
            require(prior['logical_event_id']==cursor['logical_event_id'] and prior['slot_id']==cursor['slot_id'] and prior['revision']<cursor['revision'],'OBSERVATION_LINEAGE')
            cursor=prior
        require(o['shadow_publication_id'] in pubs and pubs[o['shadow_publication_id']]['revision']==o['revision'],'OBSERVATION_PUBLICATION')
        require(pubs[o['shadow_publication_id']]['slot_id']==o['slot_id'],'OBSERVATION_PUBLICATION_SLOT')
    require(len(accepted)==2 and accepted[0]['slot_id']==accepted[1]['slot_id'] and [s['revision'] for s in accepted]==[1,2],'SLOT_REVISIONS')
    for k in ('scheduled_cutoff_at','observation_deadline','namespace','execution_mode'):require(accepted[0][k]==accepted[1][k],'SLOT_REVISION_IDENTITY')
    require(len(records['shadow_first_enrollments'])==1,'ONE_ORIGINAL_ENROLLMENT')
    return dict(status='PASS_LOCAL',required_slot_field_count=len(fields),missing_slot_fields=[],accepted_revisions=2,same_slot=True,supersedes_validated=True,no_second_original=True,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0)
def inspect_database(path,root=ROOT):
    result=inspect_records(load(path),root);result['prior_scope']=prior_oracle(path,root);return result
def protected(root=ROOT):
    allowed={'.gitattributes','scripts/v4_16_shadow_runtime.py','tests/test_r23_runtime.py'}
    changed=set(subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=root,text=True,encoding='utf8').splitlines())
    existing=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=root,text=True,encoding='utf8').splitlines())
    require((changed&existing)<=allowed,'PROTECTED_BASELINE_MUTATION')
    require(not (Path(root)/'data/v4/V4_16_ACCEPTED_HEAD.json').exists(),'NO_ACCEPTED_HEAD')
    require(read('data/v4/V4_STAGE_ACCEPTED_HEAD.json',root)['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED','STAGE_HEAD')
    require(read('data/v4/V4_DATA_ACCEPTED_HEAD.json',root)['accepted_trade_date']=='2026-09-30','DATA_HEAD')
    return dict(status='PASS_LOCAL',baseline=BASE,allowed_repairs=sorted(allowed),changed_existing=sorted(changed&existing),all_other_existing_files_unchanged=True)
