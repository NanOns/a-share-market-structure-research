"""R4B executes only sealed R3A/R3B -> real D0 -> candidate D2 -> events."""
from scripts.next_round_execution_r4 import *
from scripts.build_v4_11_target_facts_r4a import compressed
from src.v4.confirmation import digest
from src.v4.confirmation_candidate_r4 import detect
from src.v4.confirmation_d2_upstream_r4 import derive
from src.v4.confirmation_d2_candidate_r4 import (candidate_policy,candidate_envelope,input_skeleton,seal_fact_manifest,candidate_d2_publication,verify_candidate_d2_publication,MODE,CONTRACT)
from src.v4.confirmation_d2_candidate_r4 import adapter_ast_evidence
from src.v4.confirmation_events_candidate_r4 import freeze,events
from collections import Counter
from copy import deepcopy
import gzip,json

P0='reports/v4_11_r4/'
D='data/v4/confirmation_candidates_r4/'
def bound_gz(ref):return json.loads(gzip.decompress(exact(ref).read_bytes()))
def main():
    from src.v4.confirmation_d2_upstream_r4 import owner_packages
    owner_packages.cache_clear()
    entry=verify_protected();prepare_target_facts();a=read('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json');b=read('reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json')
    if not a['sealed'] or a['status']!='V4_11_R4A_ADJUSTMENT_BASIS_REPAIR_CANDIDATE_READY' or b['status']!='V4_11_R3B_EPISODE_SAFETY_LOO_CANDIDATE_READY':raise ValueError('R3A_R3B_MUST_BE_SEALED_BEFORE_R4B')
    aref=bind('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json');bref=bind('reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json')
    for ref in a['publications'].values():exact(ref)
    cutoff=entry['observed_at_utc'];head=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');cal_source=read(head['calendar']['path']);dates=cal_source['session_dates']
    cal=dict(contract_id='V4_11_R4B_CALENDAR_CANDIDATE',producer_contract_id='MARKET_CALENDAR_V1',lineage_id=head['calendar']['sha256'],mode=MODE,source_bindings=[head['calendar']],
        sessions=[dict(trade_date=d,session_index=i) for i,d in enumerate(dates)],accepted=False,AS_RECORDED=False)
    cal['publication_id']='V4_11_R4B_CALENDAR:'+digest(cal);calref=write(D+'D2_ACCEPTED_SOURCE_CALENDAR_R4.json',cal)
    entryref=write(P0+'R4B_STAGE_CONTRACT.json',dict(contract_id='V4_11_R4B_STAGE_CONTRACT',authority=bind(AUDIT),stage_task=bind(DOCROOT+TASKS[1]),
        r4a_seal=aref,r3b_seal=bref,sealed_dependency_gate='PASS',accepted_stage_head_action='KEEP',accepted_data_head_action='KEEP',permissions=PERMISSIONS,
        knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,acceptance='REAL_SOURCE_DAG_CANDIDATE_ONLY',next_stage='EXTERNAL_REAUDIT_AFTER_COMMIT_PUSH_STOP'))
    astref=write(P0+'V4_11_R4_D2_ADAPTER_AST_EVIDENCE.json',adapter_ast_evidence())
    d0={};d0refs={};source_manifests={};source_refs={};derivations={};allowed=[]
    chain=read(head['accepted_chain']['path']);dated_status={};accepted_states={};status_refs=[]
    for node in chain['nodes']:
        receipt=node['components']['TRADING_STATUS'];ref=dict(path=receipt['artifact_path'],sha256=receipt['artifact_sha256'],bytes=receipt['artifact_bytes']);exact(ref)
        dated_status[node['trade_date']]={r['security_id']:r for r in read(ref['path'])['rows']}
        status_refs.append(ref)
        accepted_states.update({(sid,node['trade_date']):r.get('status',r.get('trading_status')) for sid,r in dated_status[node['trade_date']].items()})
    for day in ('2026-09-29','2026-09-30'):
        inp=bound_gz(a['publications'][day]);d0[day]=detect(inp,ROOT);d0refs[day]=compressed(D+'D0_'+day+'_R4.json.gz',d0[day]);allowed+=inp['source_bindings']+[a['publications'][day],a['calculations'][day],d0refs[day],aref,bref]
        calculations=bound_gz(a['calculations'][day]);index={r['security_id']:r for r in d0[day]['rows']};fields_by_row=[];calculation_outputs=[]
        defs=candidate_policy()['fields'];session=dates.index(day)
        for calc in calculations:
            sid=calc['security_id'];confirmation=index[sid];values,evidence=derive(calc,ROOT,accepted_states);status_row=dated_status[day].get(sid,{});state=status_row.get('status',status_row.get('trading_status'))
            values.update(CONFIRMED=confirmation['confirmation_status'],
                scenario=confirmation['primary_scenario'] or ('NONE' if confirmation['confirmation_status']=='FALSE' else 'UNKNOWN'),
                suspended='FALSE' if state=='ACTUAL_TRADED' else 'TRUE' if state=='SUSPENDED' else 'UNKNOWN')
            fields={}
            for field,definition in defs.items():
                status='IMPLEMENTED' if definition['implemented'] else 'NOT_IMPLEMENTED';value=values.get(field,'UNKNOWN')
                if field in ('WARM','dq5'):status='NOT_APPLICABLE';value='UNKNOWN'
                envelope=candidate_envelope(field,value,status,session_index=session if definition['time_role']=='T' else session-1,
                    trade_date=day if definition['time_role']=='T' else dates[session-1],system_available_at=cutoff,
                    payload_extra=dict(source_calculation_digest=digest(calc),source_D0_publication_id=d0[day]['publication_id'],
                        source_knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
                envelope.pop('publication_id');fields[field]=envelope
            fields_by_row.append(dict(entity_id=sid,entity_type='STOCK',fields=fields));calculation_outputs.append(dict(security_id=sid,trade_date=day,evidence=evidence))
        derivations[day]=compressed(D+'D2_TARGET_UPSTREAM_DERIVATIONS_'+day+'_R4_R1.json.gz',calculation_outputs)
        refs=[a['publications'][day],a['calculations'][day],d0refs[day],derivations[day],aref,bref]+[r for r in status_refs if read(r['path'])['trade_date']<=day];allowed+=refs
        material=dict(contract_id='V4_11_R4B_STATE_INPUT_FACT_PUBLICATION_V1',producer_contract_id='V4_11_R4B_TARGET_UPSTREAM_ADAPTER_V1',
            parameter_set_id='UNCHANGED_ACCEPTED_OWNER_PARAMETERS',mode=MODE,accepted=False,AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',
            trade_date=day,calendar_publication_id=cal['publication_id'],rows=fields_by_row,source_bindings=refs,permissions=PERMISSIONS)
        source_manifests[day]=seal_fact_manifest(material);source_refs[day]=compressed(D+'D2_SOURCE_FACTS_'+day+'_R4_R1.json.gz',source_manifests[day])
    allowed=list({r['path']:r for r in allowed}.values())
    config_material=dict(contract_id=CONTRACT,permissions=PERMISSIONS,r4a_seal=aref,r3b_seal=bref,
        stage=entryref,accepted_calendar_source=head['calendar'],allowed_source_bindings=allowed,
        accepted_reducer_source=bind('src/v4/research_state.py'),accepted_provenance_source=bind('src/v4/state_provenance.py'),
        exact_owner_runtime=[bind(p) for p in ('src/v4/factors/core.py','src/v4/profile_primitives.py','src/v4/profile_core.py','src/v4/base_seed.py','src/v4/stock_prewatch.py')],
        exact_owner_parameters=[bind(p) for p in ('config/v4_03_parameter_registry_v1.json','config/v4_04_parameter_set_v1.json','config/v4_07_parameter_set_v1.json','config/v4_09_parameter_set_v1.json')],
        accepted=False,AS_RECORDED=False,scope='REAL_CANDIDATE_INTERFACE_ONLY_NOT_ACCEPTED_FACT_INTERFACE',
        admission_changes_only=['VERSIONED_REAL_CANDIDATE_MODE','SEALED_SOURCE_FILE_LEDGER','CONFIRMED_CANDIDATE_CAPABILITY','ACTUAL_RECONSTRUCTED_KNOWLEDGE_TIMESTAMP','CANDIDATE_IDENTITIES'],
        business_rules='EXACT_ACCEPTED_V4_10_AST_EXTRACT; THRESHOLDS_UNCHANGED',prior_bootstrap='LEFT_CENSORED_NO_PRIOR_PUBLICATION; no historical NONE claim',
        V4_12_RUNTIME=False,formal_consumer_enabled=False)
    source_set=write(D+'D2_SEALED_SOURCE_SET_R4_R1.json',dict(contract_id='V4_11_R4B_D2_SOURCE_SET_V1',mode=MODE,accepted=False,calendar=calref,
        publications=list(source_refs.values()),r4a_seal=aref,r3b_seal=bref,permissions=PERMISSIONS))
    config_material['authorized_source_sets']=[source_set]
    config_material.update(revision='R2',upstream_adapter=bind('src/v4/confirmation_d2_upstream_r4.py'),accepted_status_admission='Exact dated SUSPENDED -> CONFIRMED_SUSPENSION; absent status remains UNKNOWN',price_identity='Accepted price_basis + adjustment_source_revision; coefficients are evidence only')
    config=write('config/v4_11_r4b_candidate_d2_contract_v1.json',config_material)
    def inputs(day,prior=None):
        old={} if prior is None else {r['entity_id']:r for r in prior['rows']};manifest=source_manifests[day];result=[]
        for row in manifest['rows']:
            fields={f:dict(v,publication_id=manifest['publication_id'] if v['status']=='IMPLEMENTED' else None) for f,v in row['fields'].items()}
            result.append(input_skeleton(entity_id=row['entity_id'],trade_date=day,session_index=dates.index(day),cutoff=cutoff,calendar_manifest=cal,
                fields=fields,prior_state=old.get(row['entity_id']),prior_publication_id=prior['publication_id'] if prior else None))
        return result
    prior=candidate_d2_publication(inputs('2026-09-29'),producer_set=source_set);priorref=compressed(D+'D2_2026-09-29_CANDIDATE_R4_R1.json.gz',prior)
    current_inputs=inputs('2026-09-30',prior);current=candidate_d2_publication(current_inputs,producer_set=source_set,prior_binding=priorref,prior_publication=prior)
    curref=compressed(D+'D2_2026-09-30_CANDIDATE_R4_R1.json.gz',current)
    readback=verify_candidate_d2_publication(bound_gz(curref),producer_set=source_set)
    frozen=freeze(target_date='2026-09-30',prior_date='2026-09-29',calendar_publication_id=cal['publication_id'],rows=prior['rows'],
        source_binding=prior,scope='REAL_SEALED_CANDIDATE_REPLAY_ONLY',calendar_manifest=cal)
    frozenref=compressed(D+'FROZEN_PRIOR_SESSION_STATE_CANDIDATE_R4_R1.json.gz',frozen)
    eventrows=events(current,frozen);eventref=compressed(D+'STATE_EVENT_2026-09-30_CANDIDATE_R4_R1.json.gz',eventrows)
    repeated=events(current,frozen,revision_of=current['publication_id'])
    predicates=[dict(entity_id=r['entity_id'],event_types=r['event_types'],primary_event=r['primary_event'],prior_session_state_head_digest=r['prior_session_state_head_digest']) for r in eventrows]
    revised=[dict(entity_id=r['entity_id'],event_types=r['event_types'],primary_event=r['primary_event'],prior_session_state_head_digest=r['prior_session_state_head_digest']) for r in repeated]
    if predicates!=revised:raise ValueError('SAME_DAY_EVENT_PREDECESSOR_INVARIANT_FAILED')
    target=d0['2026-09-30'];counts=Counter(r['confirmation_status'] for r in target['rows']);scenarios={s:Counter() for s in target['scenario_capability_matrix']};unknown=Counter()
    for row in target['rows']:
        for e in row['scenario_evidence']:
            scenarios[e['scenario']][e['status']]+=1;unknown.update(e['unknown_reasons'])
    if len(target['rows'])!=5224:raise ValueError('REAL_FULL_MARKET_SCOPE_REQUIRED')
    summary=write(P0+'V4_11_R4_FULL_MARKET_SUMMARY.json',dict(status='V4_11_R4_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
        eligible_universe=5224,trade_date='2026-09-30',confirmation_counts=dict(counts),scenario_counts={s:dict(v) for s,v in scenarios.items()},
        unknown_reasons=dict(unknown),field_coverage=a['coverage'],multi_scenario_count=sum(len(r['matched_scenarios'])>1 for r in target['rows']),
        diagnostic_only_reasons={s:v['reason'] for s,v in target['scenario_capability_matrix'].items() if v['capability']=='DIAGNOSTIC_ONLY'},
        D0= d0refs,D2_current=curref,D2_prior=priorref,events=eventref,accepted=False,AS_RECORDED=False,permissions=PERMISSIONS))
    matrix=write(P0+'V4_11_R4_SCENARIO_CAPABILITY_MATRIX.json',dict(scenarios=target['scenario_capability_matrix'],counts={s:dict(v) for s,v in scenarios.items()},formal_consumer_enabled=False))
    d2rb=write(P0+'V4_11_R4_D2_READBACK.json',dict(status='PASS_REAL_CANDIDATE_RULE_REEXECUTION',row_count=len(readback),
        source_set=source_set,contract=config,adapter_AST=astref,current=curref,prior=priorref,maturity_counts=dict(Counter(r['maturity'] for r in readback)),
        final_eligibility_counts=dict(Counter(r['final_eligibility'] for r in readback)),state_freshness_counts=dict(Counter(r['state_freshness'] for r in readback)),
        unknown_reasons=dict(Counter(x for r in readback for x in r['unknown_predicates'])),
        source_date_limit='Old accepted V4_05/V4_07/V4_09 are 2026-09-28; new target candidate publications rerun pure owner rules, no date relabelling.',
        prior_state_authenticity='Re-executed immutable real 9/29 candidate, left-censored bootstrap; no AS_RECORDED historical state claim.',
        accepted_ledger_written=False,main_heads_changed=False,production_enabled=False))
    er=write(P0+'V4_11_R4_EVENT_REPLAY.json',dict(status='PASS_REAL_CANDIDATE_FROZEN_PRIOR_SESSION',current_d2=curref,prior_d2=priorref,frozen_prior=frozenref,
        events=eventref,event_counts=dict(Counter(r['effective_event'] for r in eventrows)),raw_exact_predicate_counts=dict(Counter(r['primary_event'] for r in eventrows)),
        event_quality_counts=dict(Counter(r['event_quality'] for r in eventrows)),same_day_revision_predecessor_invariant=True,NEW_CONFIRMED_semantics_invariant=True,
        same_day_revision_trace=dict(revision_of=current['publication_id'],prior_state_publication_id=prior['publication_id'],event_predicate_digest=digest(predicates)),
        accepted=False,AS_RECORDED=False,permissions=PERMISSIONS))
    handoff=write(P0+'V4_11_R4_EXTERNAL_REAUDIT_HANDOFF.json',dict(status='V4_11_R4_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',summary=summary,matrix=matrix,
        D2_readback=d2rb,event_replay=er,producer_seals=dict(R4A=aref,R3B=bref),stage_contract=entryref,
        independent_oracle_path=P0+'V4_11_R4_INDEPENDENT_ORACLE.json',clean_checkout_path=P0+'V4_11_R4_CLEAN_CHECKOUT.json',
        StageHead='KEEP_V4_00_TO_V4_10_ACCEPTED',DataHead='KEEP_2026-09-30',accepted=False,permissions=PERMISSIONS,
        V4_12_runtime=False,next_stage='STOP_COMMIT_PUSH_WAIT_INDEPENDENT_EXTERNAL_ACCEPTANCE'))
    capability_closure(summary,d2rb,er);verify_protected();print(json.dumps(dict(status='V4_11_R4_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',counts=dict(counts),scenarios={s:dict(v) for s,v in scenarios.items()},handoff=handoff)))


def prepare_target_facts():
    from scripts.build_v4_11_target_facts_r4a import build
    gate=read('reports/v4_11_r4a/R4A_SEALED_REPAIR_R4.json')
    if gate['gate']!='PASS' or not gate['sealed']:raise ValueError('R4A_PASS_SEALED_PREREQUISITE')
    exact(gate['contract']);exact(gate['parity']);publications={};calculations={};coverage={}
    if (ROOT/'reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json').exists():
        current=read('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json')
        if current['contract']==gate['contract']:return
    for day in ('2026-09-29','2026-09-30'):
        pub,calc=build(day)
        publications[day]=compressed(D+'TARGET_FACTS_'+day+'_R4A.json.gz',pub)
        calculations[day]=compressed(D+'CALCULATIONS_'+day+'_R4A.json.gz',calc)
        coverage[day]={f:dict(known=sum(r['facts'][f]['value'] is not None for r in pub['rows']),unknown=sum(r['facts'][f]['value'] is None for r in pub['rows']),unknown_reasons=dict(Counter(r['facts'][f]['reason'] for r in pub['rows'] if r['facts'][f]['value'] is None))) for f in pub['rows'][0]['facts']}
    cover=write('reports/v4_11_r4a/TARGET_FIELD_COVERAGE.json',dict(by_date=coverage,publications=publications))
    write('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json',dict(status=gate['status'],sealed=True,accepted=False,contract=gate['contract'],parity=gate['parity'],repair_gate=bind('reports/v4_11_r4a/R4A_SEALED_REPAIR_R4.json'),publications=publications,calculations=calculations,coverage=cover,permissions=PERMISSIONS))

def capability_closure(summary,d2rb,er):
    from scripts.verify_v4_11_r4_capability_closure import close
    close(summary,d2rb,er)

if __name__=='__main__':main()
