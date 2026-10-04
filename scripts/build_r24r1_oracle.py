"""Generate independent successor oracle retaining R24 checks without writer imports."""
from pathlib import Path

def build():
    p=Path('scripts/validate_r24_activation.py').read_text()
    p=p.replace('from scripts.r24_io import ROOT, read, ref','from scripts.r24r1_io import ROOT, read, ref')
    p=p.replace('config/v4_16_runtime_activation_authority_v2.json','config/v4_16_runtime_activation_authority_v3.json')
    p=p.replace("digest([e['logical_event_id'],'SHADOW_V4_FIRST_OBSERVED'])","digest([e[k] for k in cohort['enrollment_key']])")
    p=p.replace("sources=exact(root,authority['grant']['source_authority'])","sources=exact(root,authority['grant']['source_authority'])\n    daily=inspect_daily(root,deps,grant,sources)\n    cohort=exact(root,exact(root,deps['realtime_admission'])['cohort_contract'])")
    p=p.replace("for e in enrollments:","for e in enrollments:\n            admissions=[a for a in rows.get('realtime_admission',[]) if a['enrollment_id']==e['enrollment_id']]\n            check(len(admissions)==1,'EXACT_REALTIME_ADMISSION_REQUIRED')\n            a=admissions[0]\n            check(a['logical_event_id']==e['logical_event_id']==a['owner_event']['logical_event_id'] and a['cohort_namespace']==e['cohort_namespace'],'EXACT_OWNER_EVENT_REQUIRED')\n            check(a['owner_event']['event_trade_date']==e['T0'] and a['owner_event']['entity_id']==e['entity_id'],'OWNER_EVENT_DATE_IDENTITY')\n            slot=[s for s in rows.get('slot',[]) if s['slot_id']==a['observation_slot']['slot_id'] and s['revision']==a['observation_slot']['revision']]\n            check(len(slot)==1 and slot[0]['accepted_at']==a['accepted_at']==e['accepted_at'],'ADMISSION_ACCEPTED_SLOT')\n            check(a['source_manifest_digest']==slot[0]['source_manifest_digest']==e['source_manifest_digest'] and a['visibility_receipt_ids']==slot[0]['visibility_receipt_ids'],'ADMISSION_READINESS_MANIFEST')\n            check(e['admission_role']==a['admission_role']=='REALTIME_COHORT_ACCEPTANCE','ADMISSION_ROLE')")
    p=p.replace("for publication in pubs.values():artifact(publication['radar_publication'])","for publication in pubs.values():\n            projected=artifact(publication['radar_publication'])\n            events={artifact(b)['logical_event_id'] for b in projected['logical_events']}\n            for b in projected['enrollments']:\n                candidate=artifact(b)\n                check(candidate['admission_role']=='CANDIDATE_ENROLLMENT_TEMPLATE' and candidate['cohort_acceptance']=='NOT_COHORT_ACCEPTANCE','OWNER_TEMPLATE_IS_NOT_ACCEPTANCE')\n                check(candidate['logical_event_id'] in events,'CANDIDATE_OWNER_EVENT')\n            manifest=manifests[publication['source_manifest_digest']]\n            check(manifest['daily_input_authority']==grant['daily_input_authority'] and manifest['daily_input_digest']==daily['daily_input_digest'],'MANIFEST_DAILY_INPUT_AUTHORITY')\n            check(manifest['trade_date']==daily['target_trade_date'] and manifest['prior']['trade_date']==daily['previous_trade_date'],'MANIFEST_DAILY_SESSION')\n        check(len(rows.get('daily_input',[]))==1 and rows['daily_input'][0]['daily_input_digest']==daily['daily_input_digest'],'PERSISTED_DAILY_INPUT')")
    p+='''

def inspect_daily(root,deps,grant,runtime_sources):
    contract=exact(root,deps['go_forward_input'])
    d=exact(root,grant['daily_input_authority'])
    check(set(contract['required_fields'])<=d.keys(),'DAILY_FIELDS')
    check(d['contract_id']==contract['contract_id'] and d['environment_class']=='ACTIVATION_SIMULATION','DAILY_CONTRACT_ENVIRONMENT')
    check(d['daily_input_digest']==grant['daily_input_digest']==digest({k:v for k,v in d.items() if k!='daily_input_digest'}),'DAILY_DIGEST')
    target=d['target_trade_date']; boundary=grant['daily_input_boundary']
    check(target==grant['target_trade_date'] and d['target_session_confirmed'] and d['revision']>=grant['minimum_daily_input_revision'],'DAILY_TARGET_REVISION')
    check(d['accepted_at']<=boundary,'DAILY_BOUNDARY')
    sessions=exact(root,d['calendar'])['session_dates']
    check(target in sessions and sessions.index(target)>0 and sessions[sessions.index(target)-1]==d['previous_trade_date'],'DAILY_CALENDAR_PRIOR')
    identity=exact(root,d['identity'])
    check(identity['accepted'] and identity['target_trade_date']==target,'DAILY_UNIVERSE')
    required=set(grant['capability_scope'])&set(contract['membership_required_capabilities'])
    if isinstance(d['membership'],dict):
        m=exact(root,d['membership']); check(m['accepted'] and m['target_trade_date']==target,'DAILY_MEMBERSHIP')
    else:check(d['membership']=='NOT_REQUIRED_FOR_SCOPE' and not required,'DAILY_MEMBERSHIP_REQUIRED')
    check(d['immutable_algorithm_bindings']==contract['immutable_algorithm_bindings'],'DAILY_ALGORITHM_AUTHORITY')
    for b in d['immutable_algorithm_bindings'].values():exact(root,b)
    for k,v in contract['model_identity'].items():check(d[k]==grant[k]==v,'DAILY_MODEL_PARAMETER')
    sources=d['sources']; check(set(contract['mandatory_pure_core_sources'])<=sources.keys(),'DAILY_MANDATORY_SOURCES')
    for family,s in sources.items():
        payload=exact(root,s['binding'])
        check(payload['trade_date']==s['target_trade_date']==target and s['max_source_trade_date']<=target and payload.get('max_source_trade_date',target)<=target,'DAILY_SOURCE_DATE')
        check(s['provider_observed_at']<=s['system_available_at']<=s['accepted_at']<=boundary,'DAILY_SOURCE_BOUNDARY')
        check(s['quality']=='ACCEPTED' and s['capability']=='PURE_CORE_STOCK','DAILY_QUALITY')
    for family,s in runtime_sources['sources'].items():check(s['binding']==sources[family]['binding'],'DAILY_RUNTIME_SOURCE')
    check(d['max_source_trade_date']==max(s['max_source_trade_date'] for s in sources.values())<=target,'DAILY_MAX_SOURCE_DATE')
    check(d['source_manifest_digest']==digest(sources),'DAILY_SOURCE_MANIFEST')
    check(d['quality_capability_matrix']=={k:dict(quality=v['quality'],capability=v['capability']) for k,v in sources.items()},'DAILY_QUALITY_MATRIX')
    package=exact(root,d['day_package'])
    check(package['trade_date']==target and package['snapshot_identity']==d['snapshot_identity'] and package['sources']==sources,'DAILY_PACKAGE')
    return d
'''
    p=p.replace("sources=d['sources'];", "sources=d['sources'];")
    p=p.replace("check(payload['trade_date']==s['target_trade_date']==target", "check(max(payload_dates(payload),default=target)==s['max_source_trade_date'],'DAILY_PAYLOAD_MAX_DATE')\n        check(payload['trade_date']==s['target_trade_date']==target")
    p=p.replace("a=admissions[0]", "a=admissions[0]\n            owner=exact(root,sources['sources']['OWNER_OUTPUT']['binding'])\n            event=a['owner_event']\n            event_key=['model_contract_id','state_lineage_id','entity_type','entity_id','episode_id','event_type','event_trade_date']\n            check(event['logical_event_id']==digest([event[k] for k in event_key]),'OWNER_EVENT_KEY')\n            check(any(all(row.get(k)==event[k] for k in ['model_contract_id','state_lineage_id','entity_type','entity_id','episode_id']) for row in owner['rows']),'OWNER_EVENT_ROW')\n            check(any(ev.get('entity_id')==event['entity_id'] and ev.get('entity_type')==event['entity_type'] and ev.get('event_trade_date')==event['event_trade_date'] and event['event_type'] in ev.get('event_types',[]) for ev in owner.get('events',[])),'OWNER_EXPLICIT_EVENT')")
    p+='''

def payload_dates(value):
    result=[]
    if isinstance(value,dict):
        for k,v in value.items():
            if k in {'trade_date','event_trade_date','source_trade_date','source_asof','evaluation_basis_date','max_source_trade_date'} and isinstance(v,str):result.append(v[:10])
            elif isinstance(v,(dict,list)):result.extend(payload_dates(v))
    elif isinstance(value,list):
        for v in value:result.extend(payload_dates(v))
    return result
'''
    Path('scripts/validate_r24r1_activation.py').write_text(p,encoding='utf8',newline='\n')

if __name__=='__main__':build()
