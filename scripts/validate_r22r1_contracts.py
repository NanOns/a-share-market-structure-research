"""Independent contract audit and engineering-only temporal predicates.

Does not import the writer, create slots, enroll cohorts or grant PIT evidence.
"""
from copy import deepcopy
from datetime import datetime,date,time,timezone,timedelta
import hashlib,json,subprocess
from scripts.r22r1_io import ROOT,BASE,AUDIT,ACCEPT,CLOCK,SLOT,HEAD,CONFIG,VECTORS,read,ref,atomic
def require(condition,message):
    if not condition:raise ValueError(message)
def stamp(value):
    require(isinstance(value,str) and value.endswith('Z'),'UTC_RFC3339_REQUIRED')
    return datetime.fromisoformat(value.replace('Z','+00:00'))
def boundaries(day):
    d=date.fromisoformat(day);tz=timezone(timedelta(hours=8),'Asia/Shanghai')
    return tuple(datetime.combine(d,time(h,m),tz).astimezone(timezone.utc) for h,m in ((21,0),(22,30)))
def engineering_clock_case(v):
    """Predicate on authored fixtures only; result never constitutes observed PIT."""
    if not v['market_session']:return 'NO_SLOT'
    cutoff,deadline=boundaries(v['trade_date'])
    try:
        sources=v['mandatory_sources'];require(bool(sources),'EMPTY_MANDATORY_SOURCE_SET')
        latest=[]
        for s in sources:
            require(s.get('receipt') and s.get('accepted') and s.get('integrity_pass'),'MISSING_PROOF')
            require(s.get('consumed_digest')==s.get('receipt_digest') and len(s['consumed_digest'])==64,'SOURCE_IDENTITY')
            require(s['receipt_kind'] in ('FIRST_ACCEPTED_PROVIDER_READINESS_OBSERVATION','ACCEPTED_LOCAL_OBSERVATION_ACQUISITION'),'RECEIPT_KIND')
            p=stamp(s['provider_at']);observed=stamp(s['first_observed_at']);system=stamp(s['system_at']);checked=stamp(s['integrity_passed_at'])
            require(p==observed,'BACKDATED_PROVIDER')
            require(p<=system and checked<=system,'VISIBILITY_ORDER')
            if system>cutoff:return 'MISSED_RECONSTRUCTED_ONLY'
            latest.append(system)
        start,finish,accepted=(stamp(v[k]) for k in ('started_at','finished_at','accepted_at'))
        require(max(latest)<=start<=finish<=accepted,'COMPUTATION_ORDER')
        return 'ELIGIBLE_ENGINEERING_ONLY' if accepted<=deadline else 'MISSED_RECONSTRUCTED_ONLY'
    except (ValueError,KeyError,TypeError):return 'REJECT_NO_PIT'
def revision_decision(old,new):
    changed=any(old[k]!=new[k] for k in ('scheduled_source_cutoff_local','observation_publication_deadline_local','source_provider_available_at','system_available_at'))
    if not changed:return dict(new_policy_identity_required=False,reset_affected_window=False,rewrite_old_slots=False)
    require(old['contract_id']!=new['contract_id'] and old['version']!=new['version'],'NEW_CLOCK_VERSION_REQUIRED')
    return dict(new_policy_identity_required=True,reset_affected_window=True,rewrite_old_slots=False)
def same_binding(binding,root):require(ref(binding['path'],root)==binding,'EXACT_BINDING '+binding['path'])
def normalize_compare(root):
    h=read(HEAD,root);old=read('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V2.json',root)
    c=read(CONFIG,root);oc=read('config/v4_cross_stage_current_audit_authority_v2.json',root)
    for n,o,head in ((h,old,True),(c,oc,False)):
        actual=deepcopy(n)
        for key in ('descriptive_normalization_predecessor','normalization_status'):actual.pop(key)
        for key in ('contract_id','version'):actual[key]=o[key]
        actual['blocking_schema']['runtime_activation_dependency']=o['blocking_schema']['runtime_activation_dependency']
        if head:
            actual['NEXT']=o['NEXT']
            for key in ('scope','limitations'):actual['entries']['GOV_PRE16_01'][key]=o['entries']['GOV_PRE16_01'][key]
        else:
            actual['current_head']=o['current_head'];actual['historical_predecessor_semantics']=o['historical_predecessor_semantics']
        require(actual==o,'V3_MACHINE_OR_EVIDENCE_CHANGE')
        require('externally closed' in n['blocking_schema']['runtime_activation_dependency'],'STALE_GLOBAL_HOLD')
        require(n['normalization_status']=='V3_NORMALIZED_CANDIDATE','V3_CANDIDATE_ONLY')
    same_binding(c['current_head'],root)
    for p in (h,c):same_binding(p['descriptive_normalization_predecessor'],root)
    require(h['entries']['GOV_PRE16_01']['current_state']=='EXTERNALLY_ACCEPTED_CLOSED','GOV01_CLOSED')
    require(h['GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS']==[],'GLOBAL_BLOCKERS')
    return dict(status='PASS_LOCAL',machine_states_blockers_evidence_permissions_identical=True,descriptive_only=True)
def validate(root=ROOT,protected=True):
    a=read(ACCEPT,root);clock=read(CLOCK,root);slot=read(SLOT,root)
    require(a['acceptance_scope']=='CONTRACT_FREEZE_ONLY' and a['audited_remote_head']==BASE,'ACCEPTANCE_SCOPE')
    require(a['tested_source']=='2456f6cdae99431bb475f077d4eaccd5f24c3b75' and a['tested_tag']=='refs/tags/codex/r22-contract-tested-source-20261004-r1','AUDITED_SOURCE')
    require(a['external_decision']=='PASS_FINAL_V4_16_CONTRACT_FREEZE_CAPABILITY_SCOPED','EXTERNAL_DECISION')
    for key in ('external_authority','package','candidate_seal'):same_binding(a[key],root)
    require(a['external_authority']['path']==AUDIT,'EXTERNAL_AUDIT_PATH')
    require(a['external_authority']['sha256']=='f75d8a6c3d75e312c67a32afb783400717afb27f5815cc01d50e4f5ea231ce71','EXTERNAL_AUDIT_BYTES')
    audit=(root/AUDIT).read_text(encoding='utf8');require(BASE in audit and a['tested_source'] in audit and a['external_decision'] in audit,'AUDIT_CONTENT')
    tag=subprocess.check_output(['git','rev-parse',a['tested_tag']+'^{commit}'],cwd=root,text=True).strip();require(tag==a['tested_source'],'IMMUTABLE_R22_TAG')
    subprocess.run(['git','merge-base','--is-ancestor',tag,BASE],cwd=root,check=True)
    for k,v in dict(contract_id='V4_16_CLOCK_CONTRACT_V1',version='1.0.0',policy_origin='POST_REV4_V4_16_EXTERNAL_GOVERNANCE_POLICY',historical_v4_00c_claim=False,timezone='Asia/Shanghai',timestamp_storage='UTC_RFC3339',scheduled_source_cutoff_local='21:00:00',observation_publication_deadline_local='22:30:00',scheduled_source_cutoff_utc='13:00:00Z',observation_publication_deadline_utc='14:30:00Z',market_session_only=True,publication_before_cutoff_allowed=True,backdating_allowed=False).items():require(clock.get(k)==v,'CLOCK_POLICY '+k)
    require(clock['source_provider_available_at']=='EARLIEST_PROJECT_OBSERVED_AUTHORITATIVE_READINESS_FOR_EXACT_CONSUMED_MANDATORY_SOURCE','PROVIDER_SEMANTICS')
    require(clock['system_available_at']=='EXACT_BYTES_LOCALLY_AVAILABLE_AND_REQUIRED_ACCEPTANCE_INTEGRITY_PASSED','SYSTEM_SEMANTICS')
    require(clock['visibility_order']==['source_provider_available_at <= system_available_at <= scheduled_cutoff_at < observation_deadline','system_available_at <= computation_started_at <= computation_finished_at <= accepted_at <= observation_deadline'],'VISIBILITY_INVARIANTS')
    require(clock['optional_baostock']=='SUPPLEMENTAL_ONLY; CANNOT_MOVE_CORE_CLOCK_OR_INVALIDATE_PURE_CORE','OPTIONAL_BAOSTOCK')
    require(clock['missing_late_mandatory']=='MISSED_OBSERVATION_SLOT; PIT_OBSERVED=false; RECONSTRUCTED_ASOF_OR_CORRECTED_ONLY','MISSING_LATE_RULE')
    require(clock['remote_receipt']=='FIRST_ACCEPTED_PROVIDER_READINESS_OBSERVATION_RECEIPT' and clock['local_receipt']=='ACCEPTED_LOCAL_OBSERVATION_ACQUISITION_RECEIPT','READINESS_SEMANTICS')
    require(clock['revision_rule']==dict(new_version_required=True,new_policy_identity_required=True,reset_affected_shadow_stability_window=True,rewrite_old_slots=False),'CLOCK_REVISION_RULE')
    for k in ('external_policy','task','calendar_authority'):same_binding(clock[k],root)
    require(clock['calendar_authority']==read('data/v4/V4_15_ACCEPTED_HEAD.json',root)['bindings']['calendar'],'ACCEPTED_CALENDAR')
    cutoff,deadline=boundaries('2026-09-30');require(cutoff.isoformat()=='2026-09-30T13:00:00+00:00' and deadline.isoformat()=='2026-09-30T14:30:00+00:00','UTC_CONVERSION')
    oldslot=read('config/v4_16_observation_slot_contract_v1.json',root)
    permitted={'contract_id','version','execution_baseline','status','predecessor','clock_authority','activation_gate','slot_states','no_clock_rule'}
    require({k:v for k,v in slot.items() if k not in permitted}=={k:v for k,v in oldslot.items() if k not in permitted},'SLOT_IDENTITY_RULES_CHANGED')
    same_binding(slot['predecessor'],root);same_binding(slot['clock_authority']['contract'],root)
    require(slot['status']=='CLOCK_BOUND_CANDIDATE' and slot['clock_authority']['contract']==ref(CLOCK,root),'SLOT_CLOCK_BINDING')
    for artifact in (a,clock,slot,read(CONFIG,root)):
        for flag in ('production','shadow','focus','V4_16'):require(artifact[flag] is False,'PERMISSION '+flag)
    require(not a['runtime_authorized'] and not clock['runtime_authorized'] and not slot['runtime_authorized'] and not slot['runtime_implemented'],'NO_RUNTIME')
    require(not (root/'data/v4/V4_16_ACCEPTED_HEAD.json').exists(),'NO_RUNTIME_ACCEPTED_HEAD')
    normalization=normalize_compare(root)
    vectors=read(VECTORS,root);require(vectors['evidence_origin']=='ENGINEERING_VECTORS_ONLY' and vectors['actual_runtime_executed'] is False,'NO_REAL_OBSERVATIONS')
    results=[]
    sessions=set(read(clock['calendar_authority']['path'],root)['session_dates'])
    required={'CLOCK-01':'ELIGIBLE_ENGINEERING_ONLY','CLOCK-02':'ELIGIBLE_ENGINEERING_ONLY','CLOCK-03':'MISSED_RECONSTRUCTED_ONLY','CLOCK-04':'ELIGIBLE_ENGINEERING_ONLY','CLOCK-05':'MISSED_RECONSTRUCTED_ONLY','CLOCK-06':'REJECT_NO_PIT','CLOCK-07':'REJECT_NO_PIT','CLOCK-08':'ELIGIBLE_ENGINEERING_ONLY','CLOCK-09':'NO_SLOT'}
    require(len({v['id'] for v in vectors['cases']})==len(vectors['cases']),'DUPLICATE_VECTOR')
    require({v['id']:v['expected'] for v in vectors['cases'] if v['id'] in required}==required,'INDEPENDENT_EXPECTED_COVERAGE')
    for v in vectors['cases']:
        require(v['market_session']==(v['trade_date'] in sessions),'ACCEPTED_SESSION_ONLY')
        actual=engineering_clock_case(v);require(actual==v['expected'],v['id']);results.append(dict(id=v['id'],expected=v['expected'],actual=actual,PIT_OBSERVED=False))
    require(len(results)>=10,'VECTOR_COVERAGE')
    new=dict(clock,contract_id='V4_16_CLOCK_CONTRACT_V2',version='2.0.0',scheduled_source_cutoff_local='21:01:00')
    require(revision_decision(clock,new)==vectors['revision_expected'],'REVISION_VECTOR')
    require(vectors['revision_id']=='CLOCK-10','CLOCK10_ID')
    results.append(dict(id='CLOCK-10',expected=vectors['revision_expected'],actual=revision_decision(clock,new),PIT_OBSERVED=False))
    bindings=[]
    if protected:
        changed=subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=root,text=True,encoding='utf8').splitlines()
        existing=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=root,text=True,encoding='utf8').splitlines())
        require(set(changed)&existing<={'.gitattributes'},'HISTORICAL_BASELINE_MODIFIED')
        prior=read('reports/pre16_governance_r1_1/PROTECTED_BYTES.json',root)
        # Independent historical literal-byte validator remains unchanged.
        from scripts.validate_pre16_finalization import validate as previous
        previous(root)
        for path in sorted(existing):
            if path.startswith(('config/v4_16_','data/v4/V4_','config/v4_cross_stage_','config/v4_current_stage_','reports/r22/','docs/evidence/r22/')):bindings.append(ref(path,root))
    return dict(status='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',normalization=normalization,vectors=results,protected_bindings=bindings,runtime_authorized=False,REAL_SHADOW_OBSERVATIONS=0,NEXT='STOP_WAIT_R22R1_INDEPENDENT_EXTERNAL_AUDIT')
def report(root=ROOT):
    result=validate(root)
    for name,value in [('R22_EXTERNAL_ACCEPTANCE_BINDING',dict(status='FORMALIZED_CONTRACT_ONLY',accepted_head=ref(ACCEPT,root))),('CLOCK_POLICY_GATE',dict(status=result['status'],contract=ref(CLOCK,root),runtime_authorized=False)),('SOURCE_VISIBILITY_TIME_GATE',dict(status='PASS_LOCAL',engineering_only=True,results=result['vectors'])),('CLOCK_MACHINE_VECTORS',dict(status='PASS_LOCAL',vectors=result['vectors'],actual_runtime_executed=False)),('PRE16_V3_NORMALIZATION_GATE',result['normalization']),('PROTECTED_BYTES',dict(status='PASS_LOCAL',baseline=BASE,bindings=result['protected_bindings'],all_existing_baseline_files_unchanged_except_gitattributes=True))]:atomic('reports/r22r1/'+name+'.json',value,root)
    return result
if __name__=='__main__':print(json.dumps(report(),ensure_ascii=False))
