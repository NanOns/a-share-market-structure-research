"""R5B consumes only sealed owner outputs and frozen R4 D0."""
from scripts.next_round_execution_r5 import *
from scripts.build_v4_11_target_facts_r4a import compressed
from src.v4.confirmation import digest
from src.v4.confirmation_d2_candidate_r5 import candidate_policy,candidate_envelope,input_skeleton,seal_fact_manifest,candidate_d2_publication,verify_candidate_d2_publication,adapter_ast_evidence,MODE,CONTRACT
from src.v4.confirmation_events_candidate_r5 import freeze,events
from src.v4.sealed_owner_authority_r5 import resolve_sources
from collections import Counter
from copy import deepcopy
import gzip,json

OUT='reports/v4_11_r5/'
D='data/v4/confirmation_candidates_r5/'
def bound(ref):
    p=exact(ref);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())

def main():
    entry=verify_protected();a=read('reports/v4_11_r5a/R5A_SEALED_OWNER_PRODUCER_SET.json')
    if a['status']!='V4_11_R5A_OWNER_INPUT_AUTHORITY_PARITY_CANDIDATE_READY' or not a['sealed']:raise ValueError('R5A_PASS_SEAL_REQUIRED_BEFORE_R5B')
    r4=read('reports/v4_11_r4/V4_11_R4_FULL_MARKET_SUMMARY.json');aseal=bind('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json');bseal=bind('reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json');r5seal=bind('reports/v4_11_r5a/R5A_SEALED_OWNER_PRODUCER_SET.json')
    head=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');calendar=bound(head['calendar']);dates=calendar['session_dates'];chain=bound(head['accepted_chain']);cutoff=entry['observed_at_utc']
    cal=dict(contract_id='V4_11_R5B_CALENDAR_CANDIDATE',producer_contract_id='MARKET_CALENDAR_V1',lineage_id=head['calendar']['sha256'],mode=MODE,source_bindings=[head['calendar']],sessions=[dict(trade_date=d,session_index=i) for i,d in enumerate(dates)],accepted=False,AS_RECORDED=False)
    cal['publication_id']='V4_11_R5B_CALENDAR:'+digest(cal);calref=write(D+'D2_ACCEPTED_SOURCE_CALENDAR_R5.json',cal)
    stage=write(OUT+'R5B_STAGE_CONTRACT.json',dict(contract_id='V4_11_R5B_STAGE_CONTRACT',authority=bind(AUDIT),task=bind(DOCROOT+TASKS[1]),r5a_seal=r5seal,r4a_seal=aseal,r3b_seal=bseal,sealed_dependency_gate='PASS',upgrade=bind(UPGRADE),upgrade_sections=['13A','14','22.1','31','34A.2A','78'],permissions=PERMISSIONS,accepted=False,AS_RECORDED=False,next_stage='REBUILD_OWNER_D2_EVENT_CANDIDATE_THEN_EXTERNAL_REAUDIT'))
    astref=write(OUT+'V4_11_R5_D2_ADAPTER_AST_EVIDENCE.json',adapter_ast_evidence())
    authority_refs={}
    for day in a['publications']:
        node=next(n for n in chain['nodes'] if n['trade_date']==day);sr=node['components']['TRADING_STATUS']
        authority_refs[day]=dict(owners=a['publications'][day],confirmation=r4['D0'][day],status=dict(path=sr['artifact_path'],sha256=sr['artifact_sha256'],bytes=sr['artifact_bytes']))
    config_material=dict(contract_id=CONTRACT,permissions=PERMISSIONS,r4a_seal=aseal,r3b_seal=bseal,r5a_seal=r5seal,stage=stage,accepted_calendar_source=head['calendar'],authoritative_by_date=authority_refs,frozen_R4_D0_publications=r4['D0'],accepted_reducer_source=bind('src/v4/research_state.py'),accepted_provenance_source=bind('src/v4/state_provenance.py'),exact_owner_runtime=[bind(p) for p in ('src/v4/base_seed.py','src/v4/stock_prewatch.py','src/v4/factors/core.py','src/v4/profile_primitives.py','src/v4/profile_core.py','src/v4/sealed_owner_authority_r5.py')],exact_owner_parameters=[bind(p) for p in ('config/v4_07_parameter_set_v1.json','config/v4_09_parameter_set_v1.json','config/v4_04_parameter_set_v1.json')],accepted=False,formal_consumer_enabled=False,AS_RECORDED=False,scope='SEALED_OWNER_CANDIDATE_INTERFACE_ONLY',business_rules='EXACT_ACCEPTED_V4_10_AST; PARAMETERS_THRESHOLDS_RULE_ORDER_UNCHANGED',admission_changes_only=['CANDIDATE_NAMESPACE','SEALED_OWNER_PUBLICATION_WIRING','ACTUAL_RECONSTRUCTED_KNOWLEDGE_TIME','FROZEN_R4_D0_CANDIDATE_CAPABILITY'],V4_12_RUNTIME=False)
    authoritative=resolve_sources(config_material,bound,candidate_policy());manifests={};pubrefs={};allowed=[]
    for day,rows in authoritative.items():
        session=dates.index(day);fields_by_row=[]
        for sid,sources in rows.items():
            fields={}
            for field,definition in candidate_policy()['fields'].items():
                status='IMPLEMENTED' if definition['implemented'] else 'NOT_IMPLEMENTED';value=sources[field]['value'] if field in sources else 'UNKNOWN'
                if field in ('WARM','dq5'):status='NOT_APPLICABLE'
                extra=dict(knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
                if field in sources:extra['authoritative_source']=sources[field]
                envelope=candidate_envelope(field,value,status,session_index=session if definition['time_role']=='T' else session-1,trade_date=day if definition['time_role']=='T' else dates[session-1],system_available_at=cutoff,payload_extra=extra)
                envelope.pop('publication_id');fields[field]=envelope
            fields_by_row.append(dict(entity_id=sid,entity_type='STOCK',fields=fields))
        refs=[*authority_refs[day].values(),r5seal,aseal,bseal,bind('data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json')];allowed+=refs
        material=dict(contract_id='V4_11_R5B_STATE_INPUT_FACT_PUBLICATION_V1',producer_contract_id='V4_11_R5B_SEALED_OWNER_WIRING_V1',mode=MODE,trade_date=day,calendar_publication_id=cal['publication_id'],rows=fields_by_row,source_bindings=refs,accepted=False,AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',permissions=PERMISSIONS)
        manifests[day]=seal_fact_manifest(material);pubrefs[day]=compressed(D+'D2_SOURCE_FACTS_'+day+'_R5.json.gz',manifests[day])
    source_set=write(D+'D2_SEALED_SOURCE_SET_R5.json',dict(contract_id='V4_11_R5B_D2_SOURCE_SET_V1',mode=MODE,accepted=False,calendar=calref,publications=list(pubrefs.values()),r4a_seal=aseal,r3b_seal=bseal,r5a_seal=r5seal,permissions=PERMISSIONS))
    config_material.update(allowed_source_bindings=list({r['path']:r for r in allowed}.values()),authorized_source_sets=[source_set]);config=write('config/v4_11_r5b_candidate_d2_contract_v1.json',config_material)
    def inputs(day,prior=None):
        old={} if prior is None else {r['entity_id']:r for r in prior['rows']};manifest=manifests[day];result=[]
        for row in manifest['rows']:
            fields={f:dict(v,publication_id=manifest['publication_id'] if v['status']=='IMPLEMENTED' else None) for f,v in row['fields'].items()}
            result.append(input_skeleton(entity_id=row['entity_id'],trade_date=day,session_index=dates.index(day),cutoff=cutoff,calendar_manifest=cal,fields=fields,prior_state=old.get(row['entity_id']),prior_publication_id=prior['publication_id'] if prior else None))
        return result
    prior=candidate_d2_publication(inputs('2026-09-29'),producer_set=source_set);priorref=compressed(D+'D2_2026-09-29_CANDIDATE_R5.json.gz',prior)
    current=candidate_d2_publication(inputs('2026-09-30',prior),producer_set=source_set,prior_binding=priorref,prior_publication=prior);curref=compressed(D+'D2_2026-09-30_CANDIDATE_R5.json.gz',current)
    readback=verify_candidate_d2_publication(bound(curref),producer_set=source_set)
    frozen=freeze(target_date='2026-09-30',prior_date='2026-09-29',calendar_publication_id=cal['publication_id'],rows=prior['rows'],source_binding=prior,scope='REAL_SEALED_CANDIDATE_REPLAY_ONLY',calendar_manifest=cal)
    frozenref=compressed(D+'FROZEN_PRIOR_SESSION_STATE_CANDIDATE_R5.json.gz',frozen);eventrows=events(current,frozen);eventref=compressed(D+'STATE_EVENT_2026-09-30_CANDIDATE_R5.json.gz',eventrows)
    revised=events(current,frozen,revision_of=current['publication_id'])
    invariant=('event_types','primary_event','prior_session_state_head_digest')
    if any(any(x[k]!=y[k] for k in invariant) for x,y in zip(eventrows,revised)):raise ValueError('SAME_DAY_REVISION_INVARIANCE')
    # Freeze business outputs; correct lineage in a new metadata matrix only.
    oldmatrix=read('reports/v4_11_r4/V4_11_R4_SCENARIO_CAPABILITY_MATRIX.json');matrix=deepcopy(oldmatrix);r4aseal=bound(aseal)
    for scenario,entry_ in matrix['scenarios'].items():
        if entry_['capability']!='DIAGNOSTIC_ONLY':entry_.update(reason='R4A_SEALED_TARGET_FACT_SET',parent_producer_set=dict(**aseal,contract_id=r4aseal['contract']['path'],status=r4aseal['status']))
        entry_['diagnostic_capability_seal']=bseal
    # Contract identity is sourced from the contract contents, not its path.
    for x in matrix['scenarios'].values():
        if 'parent_producer_set' in x:x['parent_producer_set']['contract_id']=bound(r4aseal['contract'])['contract_id']
    matrixref=write(OUT+'V4_11_R5_SCENARIO_CAPABILITY_MATRIX.json',matrix)
    d2ref=write(OUT+'V4_11_R5_D2_READBACK.json',dict(status='PASS_EXACT_REDUCER_SEALED_OWNER_REEXECUTION',row_count=len(readback),source_set=source_set,contract=config,adapter_AST=astref,current=curref,prior=priorref,maturity_counts=dict(Counter(r['maturity'] for r in readback)),final_eligibility_counts=dict(Counter(r['final_eligibility'] for r in readback)),state_freshness_counts=dict(Counter(r['state_freshness'] for r in readback)),accepted=False,AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',prior_evidence='RECONSTRUCTED_LEFT_CENSORED',permissions=PERMISSIONS))
    er=write(OUT+'V4_11_R5_EVENT_REPLAY.json',dict(status='PASS_EXACT_EVENT_MECHANICS_SEALED_PRIOR',current_d2=curref,prior_d2=priorref,frozen_prior=frozenref,events=eventref,event_counts=dict(Counter(r['effective_event'] for r in eventrows)),raw_exact_predicate_counts=dict(Counter(r['primary_event'] for r in eventrows)),event_quality_counts=dict(Counter(r['event_quality'] for r in eventrows)),same_day_revision_predecessor_invariant=True,accepted=False,AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',event_evidence='RECONSTRUCTED_LEFT_CENSORED',permissions=PERMISSIONS))
    summary=write(OUT+'V4_11_R5_FULL_MARKET_SUMMARY.json',dict(status='V4_11_R5_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',eligible_universe=5224,trade_date='2026-09-30',D0=r4['D0'],D0_business_frozen=True,confirmation_counts=r4['confirmation_counts'],scenario_counts=r4['scenario_counts'],multi_scenario_count=r4['multi_scenario_count'],D2=d2ref,Event=er,scenario_matrix=matrixref,accepted=False,permissions=PERMISSIONS))
    from scripts.verify_v4_11_r5_capability_closure import close
    close(summary,d2ref,er);verify_protected();print(json.dumps(dict(status='R5B_REBUILD_COMPLETE',D2=read(d2ref['path'])['state_freshness_counts'],Event=read(er['path'])['event_counts'])))

if __name__=='__main__':main()
