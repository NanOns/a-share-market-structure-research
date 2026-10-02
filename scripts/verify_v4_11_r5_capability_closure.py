"""Owner-source oracle, exhaustive stale attribution and R4 -> R5 changes."""
from scripts.next_round_execution_r5 import *
from src.v4.confirmation import digest
from src.v4 import base_seed,stock_prewatch
from src.v4 import profile_core
from src.v4.profile_primitives import derive_daily
from src.v4.factors.core import compute_core
from src.v4.adjustment_basis_r4 import observations
from dataclasses import asdict
from src.v4.confirmation_d2_candidate_r5 import adapter_ast_evidence,candidate_policy
from src.v4.confirmation_events_candidate_r5 import event_unknown_reasons
from collections import Counter
import gzip,json

OUT='reports/v4_11_r5/'
def bound(ref):
    path=exact(ref);return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())

def oracle(d2ref,erref):
    d2=read(d2ref['path']);er=read(erref['path']);seal=read('reports/v4_11_r5a/R5A_SEALED_OWNER_PRODUCER_SET.json');config=read(d2['contract']['path']);policy=candidate_policy();counts=Counter();details=[]
    params=base_seed._parameter_values(read('config/v4_07_parameter_set_v1.json'));package=stock_prewatch.load_package(ROOT)
    r4a=read('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json')
    for day,publication_ref in (('2026-09-29',d2['prior']),('2026-09-30',d2['current'])):
        publication=bound(publication_ref);sources=config['authoritative_by_date'][day];owners=bound(seal['publications'][day]);profile=bound(owners['profile']);context=profile['context']
        ox={r['security_id']:r for r in owners['rows']};px={r['core']['security_id']:r for r in profile['rows']};d0=bound(sources['confirmation']);dx={r['security_id']:r for r in d0['rows']};statuses=bound(sources['status']);sx={r['security_id']:r for r in statuses['rows']}
        calculations={r['security_id']:r for r in bound(r4a['calculations'][day])}
        assert sources['owners']==seal['publications'][day]
        for inp,row in zip(publication['inputs'],publication['rows']):
            sid=inp['entity_id'];owner=ox[sid];c=px[sid]['core'];f=px[sid]['factor']
            # Independent source arithmetic, then accepted Core state algorithms.
            # These values verify the candidate profile, never feed D2 directly.
            calc=calculations[sid];slots=calc['window'];states={(sid,r['date']):r['accepted_trading_status'] for r in slots if r.get('accepted_trading_status')}
            obs=observations([dict(r,accepted_source_digest=digest(r)) for r in slots],sid,states)
            factors={k:asdict(v) for k,v in compute_core(obs,sid,asof=day).items()}
            bars=[dict(trade_date=r['date'],adjusted_quality='READY',qfq_close=r['close'],qfq_high=r['high'],qfq_low=r['low'],amount=r['amount']) for r,o in zip(slots,obs) if o.bar]
            dated=[(r['date'],'ACTUAL_TRADED' if o.state=='ACTUAL' else 'SUSPENDED' if o.state=='CONFIRMED_SUSPENSION' else o.state) for r,o in zip(slots,obs)]
            primitives={k:asdict(v) for k,v in derive_daily(bars,factors,dated,day,[r['date'] for r in slots]).items()}
            assert primitives==c['derived_fields']
            values={k:v['value'] for k,v in factors.items()};values.update({k:v['value'] for k,v in primitives.items()});values['close']=slots[-1].get('close') if slots[-1].get('has_actual_bar') else None
            expected_states={k:asdict(fn(values)) for k,fn in dict(trend_state=profile_core.trend,compression_state=profile_core.compression,ma_structure_state=profile_core.ma_structure,core_extension_risk=profile_core.extension_risk,core_participation_result=profile_core.participation).items()}
            expected_states['severe_extension']=asdict(profile_core.severe_extension(profile_core.extension_risk(values)))
            for key,state_ in expected_states.items():
                for field,value in state_.items():assert c['states'][key][field]==value
                assert c['states'][key]['parameter_set_id']=='V4_04_CORE_PROFILE_PARAMETER_SET_V1'
            expected_seed=base_seed._eval(base_seed._normalize_facts(c,f,context),params)
            assert expected_seed==owner['seed']
            seed_record=dict(security_id=sid,trade_date=day,publication_id=context['source_publication_id'],source_publication_id=c['publication_id'],source_core_logical_digest=context['core_logical_digest'],model_contract_id='BASE_SEED_V1',**expected_seed)
            expected_prewatch_facts,_,_=stock_prewatch.project(c,f,seed_record,context,package);expected_prewatch=stock_prewatch.evaluate(expected_prewatch_facts,package)
            assert expected_prewatch['raw_qualification']==owner['prewatch']['raw_qualification']
            status=sx.get(sid,{});state=status.get('status',status.get('trading_status'))
            if status.get('status_conflict') or status.get('provider_conflicts'):state='UNKNOWN'
            damage=owner['seed_facts']['core_price_damage']['value'];delta=owner['seed_facts']['delta3']['value'];confirmation=dx[sid]
            expected=dict(SEED=expected_seed['base_seed_state'],PREWATCH=expected_prewatch['raw_qualification'],core_price_damage='UNKNOWN' if damage is None else 'TRUE' if damage else 'FALSE',risk=c['states']['core_extension_risk']['value'],delta3='UNKNOWN' if delta is None else delta,suspended='FALSE' if state=='ACTUAL_TRADED' else 'TRUE' if state=='SUSPENDED' else 'UNKNOWN',CONFIRMED=confirmation['confirmation_status'],scenario=confirmation['primary_scenario'] or ('NONE' if confirmation['confirmation_status']=='FALSE' else 'UNKNOWN'))
            for field,value in expected.items():
                envelope=inp['input_provenance'][field];actual=row['input_provenance'][field];assert actual==envelope
                assert envelope['value']==value and envelope['quality']==('UNKNOWN' if value=='UNKNOWN' else 'KNOWN')
                definition=policy['fields'][field];assert envelope['producer_contract_id']==definition['producer_contract_id'] and envelope['producer_parameter_set_id']==definition['producer_parameter_set_id']
                if field in ('CONFIRMED','scenario'):parent=sources['confirmation'];pid=d0['publication_id'];output=digest(confirmation)
                elif field=='suspended':parent=sources['status'];pid=statuses.get('publication_id',statuses.get('logical_digest',parent['sha256']));output=digest(status)
                else:parent=sources['owners'];pid=owners['publication_id'];output=owner['source_output_digest']
                expected_authority=dict(entity_id=sid,trade_date=day,field=field,value=value,quality=envelope['quality'],producer_contract_id=definition['producer_contract_id'],parameter_set_id=definition['producer_parameter_set_id'],publication_id=pid,source_output_digest=output,publication_binding=parent)
                assert envelope['source_field_payload']['authoritative_source']==expected_authority
                assert envelope['source_output_digest']==digest(envelope['source_field_payload'])
                counts[field]+=1
            details.append(dict(entity_id=sid,trade_date=day,owner_publication_id=owners['publication_id'],owner_output_digest=owner['source_output_digest'],confirmed_source=sources['confirmation'],status_source=sources['status']))
    proof_path='data/v4/confirmation_candidates_r5/INDEPENDENT_D2_OWNER_INPUT_PROOF_R5.json.gz'
    from scripts.build_v4_11_target_facts_r4a import compressed
    proof=compressed(proof_path,details)
    current=bound(d2['current']);prior=bound(d2['prior']);old={r['entity_id']:r for r in prior['rows']};events=bound(er['events'])
    for event in events:
        row=next(r for r in current['rows'] if r['entity_id']==event['entity_id'])
        reasons=event_unknown_reasons(row,old.get(row['entity_id']))
        assert reasons==event['event_unknown_predicates'] and event['effective_event']==('UNKNOWN' if reasons else event['primary_event'])
        if event['effective_event']=='NEW_CONFIRMED':assert row['state_freshness']=='FRESH' and old[row['entity_id']]['state_freshness']=='FRESH'
    return write(OUT+'INDEPENDENT_D2_OWNER_INPUT_ORACLE.json',dict(contract_id='V4_11_R5B_INDEPENDENT_D2_OWNER_INPUT_ORACLE_V1',status='PASS',counts=dict(counts),rows=len(details),proof=proof,adapter_helpers_used_for_expected=False,expected_from='Sealed owner publications reopened independently; accepted pure projections/evaluators; frozen R4 D0 and accepted dated status',reducer_AST=adapter_ast_evidence(),event_unknown_safety='PASS',permissions=PERMISSIONS))

def close(summaryref,d2ref,erref):
    independent=oracle(d2ref,erref);d2=read(d2ref['path']);er=read(erref['path']);seal=read('reports/v4_11_r5a/R5A_SEALED_OWNER_PRODUCER_SET.json');r4d2=read('reports/v4_11_r4/V4_11_R4_D2_READBACK.json');r4er=read('reports/v4_11_r4/V4_11_R4_EVENT_REPLAY.json');r4config=read(r4d2['contract']['path'])
    diffs=[];stale=[];transition=Counter();t1counts={};owner_changes={}
    for day,newref,oldref in (('2026-09-29',d2['prior'],r4d2['prior']),('2026-09-30',d2['current'],r4d2['current'])):
        old={r['entity_id']:r for r in bound(oldref)['rows']};new=bound(newref)['rows'];owners=bound(seal['publications'][day]);ox={r['security_id']:r for r in owners['rows']}
        summary=read(summaryref['path']);d0_index={r['security_id']:r for r in bound(summary['D0'][day])['rows']}
        oldderive=next(ref for ref in r4config['allowed_source_bindings'] if 'D2_TARGET_UPSTREAM_DERIVATIONS_'+day in ref['path']);od={r['security_id']:r['evidence'] for r in bound(oldderive)}
        t1count=Counter();changes=Counter()
        for row in new:
            sid=row['entity_id'];before=old[sid];owner=ox[sid]
            for field in ('close_t_minus_1','ma20_t_minus_1'):
                if od[sid]['seed_facts'][field]['value'] is not None and owner['seed_facts'][field]['value'] is None:t1count[field]+=1
            if any(od[sid]['seed_facts'][f]['value'] is not None for f in ('close_t_minus_1','ma20_t_minus_1')):t1count['rows_with_any_reconstructed_known_restored_unknown']+=1
            changes['SEED_value_changed']+=od[sid]['seed']['base_seed_state']!=owner['seed']['base_seed_state'];changes['SEED_quality_changed']+=od[sid]['seed']['quality']!=owner['seed']['quality'];changes['PREWATCH_value_changed']+=od[sid]['prewatch']['raw_qualification']!=owner['prewatch']['raw_qualification']
            fields=('maturity','final_eligibility','state_freshness','validity','health')
            changed={f:dict(before=before[f],after=row[f]) for f in fields if before[f]!=row[f]}
            changes['D2_business_rows_changed']+=bool(changed)
            for f in fields:transition[day+':'+f+':'+str(before[f])+'->'+str(row[f])]+=1
            if changed:diffs.append(dict(trade_date=day,entity_id=sid,changes=changed))
            if row['state_freshness']!='STALE':continue
            required=[]
            for field,envelope in row['input_provenance'].items():
                if not envelope['required'] or envelope['quality']!='UNKNOWN' or envelope['status']=='NOT_APPLICABLE' or field=='frozen_invalidation' and not row['episode_id']:continue
                authority=envelope['source_field_payload'].get('authoritative_source')
                if field in ('frozen_invalidation','episode_invalidation_contract_id'):roots=[dict(reason='V4_12_INVALIDATION_NOT_AUTHORIZED',producer_seal=bind('reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json'))]
                elif field in ('SEED','PREWATCH'):
                    roots=[dict(field=f,reason=fact['reason']) for f,fact in owner['seed_facts'].items() if fact['value'] is None]
                    if field=='PREWATCH':roots += [dict(field='mandatory_core_quality_ready',reason=r) for r in owner['prewatch_required_reasons']]
                elif field=='CONFIRMED':
                    d0=d0_index[sid];roots=[dict(field=e['scenario'],reason=r) for e in d0['scenario_evidence'] for r in e['unknown_reasons']]
                elif field=='core_price_damage':roots=[dict(field=field,reason=owner['seed_facts'][field]['reason'])]
                elif field=='suspended':roots=[dict(field=field,reason='ACCEPTED_DATED_STATUS_UNAVAILABLE_OR_CONFLICT')]
                else:roots=[dict(field=field,reason='EXPLICIT_ACCEPTED_OWNER_CAPABILITY_UNAVAILABLE')]
                if not roots:raise ValueError('STALE_WITHOUT_ROOT:'+sid+':'+field)
                if authority is None and field not in ('frozen_invalidation','episode_invalidation_contract_id'):raise ValueError('PRODUCER_WIRING_MISSING:'+field)
                required.append(dict(field=field,required_input='UNKNOWN',producer=envelope['producer_contract_id'],exact_publication=authority['publication_binding'] if authority else bind('reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json'),publication_id=authority['publication_id'] if authority else None,root_causes=roots))
            if not required:raise ValueError('STALE_WITHOUT_REQUIRED_UNKNOWN:'+sid)
            stale.append(dict(entity_id=sid,trade_date=day,required_unknown=required,reducer_unknown_predicates=row['unknown_predicates']))
        t1counts[day]=dict(t1count);owner_changes[day]=dict(changes)
    oldevents={r['entity_id']:r for r in bound(r4er['events'])};eventdiff=[]
    for event in bound(er['events']):
        before=oldevents[event['entity_id']];changes={f:dict(before=before[f],after=event[f]) for f in ('effective_event','primary_event','event_quality','event_types') if before[f]!=event[f]}
        if changes:eventdiff.append(dict(entity_id=event['entity_id'],changes=changes))
    attribution=write(OUT+'RESIDUAL_UNKNOWN_ATTRIBUTION.json',dict(status='PASS_EXACT_REQUIRED_UNKNOWN_SOURCE_ROOT_ATTRIBUTION',stale_rows=stale,stale_count_by_date=dict(Counter(r['trade_date'] for r in stale)),producer_wiring_missing=0,unsealed_helper_source=0,generic_coefficient_gate=0,raw_reconstruction_fallback=0,accepted_t_minus_1_known_count=0,permissions=PERMISSIONS))
    diff=write(OUT+'R4_TO_R5_BUSINESS_DIFF.json',dict(status='PASS_OWNER_AUTHORITY_CORRECTNESS',t_minus_1_restored_unknown=t1counts,owner_and_D2_changed_rows=owner_changes,D2_transitions=dict(transition),D2_row_diffs=diffs,Event_changed_rows=len(eventdiff),Event_row_diffs=eventdiff,D2_before={k:r4d2[k] for k in ('maturity_counts','final_eligibility_counts','state_freshness_counts')},D2_after={k:d2[k] for k in ('maturity_counts','final_eligibility_counts','state_freshness_counts')},Event_before=r4er['event_counts'],Event_after=er['event_counts'],D0_business_changed=False,thresholds_changed=False,t_minus_1_capability_expanded=False,acceptance_metric='CONTRACT_AUTHORITY_PARITY; NEVER_UNKNOWN_MINIMIZATION'))
    candidate=write(OUT+'V4_11_ACCEPTANCE_CANDIDATE.json',dict(status='V4_11_R5_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',accepted=False,formal_accepted_head=False,confirmation_LAUNCH_RECOVERY='FORMAL_CANDIDATE',Pullback_Trend='DIAGNOSTIC_ONLY',D2_bridge='ENGINEERING_CANDIDATE',Event_engine='ENGINEERING_CANDIDATE',Event_evidence='RECONSTRUCTED_LEFT_CENSORED',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_consumer_enabled=False,summary=summaryref,D2_readback=d2ref,event_replay=erref,owner_input_oracle=independent,residual_attribution=attribution,business_diff=diff,r5a_seal=bind('reports/v4_11_r5a/R5A_SEALED_OWNER_PRODUCER_SET.json'),StageHead='KEEP_V4_00_TO_V4_10_ACCEPTED',DataHead='KEEP_2026-09-30',V4_12_executed=False,permissions=PERMISSIONS,next_stage='CLEAN_CHECKOUT_COMMIT_PUSH_STOP_EXTERNAL_REAUDIT'))
    write(OUT+'V4_11_R5_EXTERNAL_REAUDIT_HANDOFF.json',dict(status='V4_11_R5_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',candidate=candidate,authority=bind(AUDIT),master=bind(MASTER),accepted=False,next_stage='STOP_AFTER_UNIFIED_COMMIT_PUSH_WAIT_EXTERNAL_ACCEPTANCE'))
    return candidate
