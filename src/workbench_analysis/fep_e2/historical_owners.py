"""E2 isolated historical transport to byte-frozen business owners.

Admission is reconstructed engineering admission, never accepted/live admission.
No numerical, state transition or event predicate is reimplemented here.
"""
from copy import deepcopy
from dataclasses import asdict
from functools import lru_cache
import json
from pathlib import Path
import types
import ast
from workbench_analysis.fep_e1.contracts import digest
from .historical_dataset import LINEAGE,admissible,feature_cutoff,read_gzip,write_gzip,slots_for,owner_packages


class RecordStore:
    """Per-entity immutable record bundle with explicit payload references."""
    def __init__(self):self.records={};self.kinds={}
    def append(self,kind,key,value):
        value=deepcopy(value);sha=digest(value);identity=kind+':'+key
        if identity in self.records and self.records[identity]!=value:raise ValueError('E2_OWNER_RECORD_MUTATION')
        self.records[identity]=value
        ref=dict(record_id=identity,sha256=sha,reference_contract='E2_OWNER_BUNDLE_PAYLOAD_V1')
        self.kinds.setdefault(kind,{})[identity]=ref
        return ref
    def read(self,ref):
        value=self.records[ref['record_id']]
        if digest(value)!=ref['sha256']:raise ValueError('E2_OWNER_RECORD_DIGEST')
        return deepcopy(value)
    def refs(self,kind):return list(self.kinds.get(kind,{}).values())
    def rows(self):
        for key in sorted(self.records):yield dict(record_id=key,payload=self.records[key],sha256=digest(self.records[key]),
            source_kind='REAL_ACCEPTED_HISTORICAL_SOURCE',**LINEAGE)


def transport_validate(inputs, context):
    """Caller-owned sealed real-source context; serialized input cannot authorize itself."""
    from src.v4.confirmation_d2_candidate_r5 import candidate_policy
    from src.v4.state_identity import digest as owner_digest
    x=deepcopy(inputs);admissible(context)
    if x!=context['expected_input']:raise ValueError('E2_HISTORICAL_OWNER_INPUT_MUTATION')
    if x['trade_date']!=context['date'] or x['session_index']!=context['ordinal']:
        raise ValueError('E2_HISTORICAL_CALENDAR_IDENTITY')
    fields=x['input_provenance'];values={k:f['value'] for k,f in fields.items()}
    if set(fields)!=set(candidate_policy()['fields']):raise ValueError('E2_HISTORICAL_FIELD_COMPLETENESS')
    prior=x['prior_state']
    if prior and (prior['trade_date']>=x['trade_date'] or prior['session_index']!=x['session_index']-1):
        raise ValueError('E2_HISTORICAL_PRIOR_TIME')
    for field in fields.values():
        payload=field['source_field_payload']
        if payload and (payload['trade_date']>x['trade_date'] or field['source_output_digest']!=owner_digest(payload)):
            raise ValueError('E2_HISTORICAL_FACT_DIGEST_OR_FUTURE')
    x['detectors']={s:dict(value=values[s],status=fields[s]['status'],contract_id=fields[s]['producer_contract_id'],
        parameter_set_id=fields[s]['producer_parameter_set_id'],publication_id=fields[s]['publication_id'])
        for s in ('CONFIRMED','WARM','PREWATCH','SEED')}
    x.update(core_price_damage=values['core_price_damage'],
        frozen_invalidation=dict(value=values['frozen_invalidation'],episode_id=fields['frozen_invalidation']['source_field_payload'].get('episode_id'),
            contract_id=fields['frozen_invalidation']['source_field_payload'].get('invalidation_contract_id')),
        episode_invalidation_contract_id=None if values['episode_invalidation_contract_id']=='UNKNOWN' else values['episode_invalidation_contract_id'],
        risk=values['risk'],delta3=None if values['delta3']=='UNKNOWN' else values['delta3'],dq5=None,
        scenario=dict(value=values['scenario'],status='UNKNOWN' if values['scenario']=='UNKNOWN' else 'KNOWN'),
        suspended=values['suspended'],followup_complete=values['followup_complete'],model_boundary=False,
        provenance_unknown=[],authorized_boundary=None)
    return x


@lru_cache(maxsize=1)
def reducer():
    from src.v4.confirmation_d2_candidate_r5 import extracted_runtime,adapter_ast_evidence
    adapter_ast_evidence()
    accepted,_=extracted_runtime()
    return types.FunctionType(accepted.__code__,dict(accepted.__globals__,validate_inputs=transport_validate))


@lru_cache(maxsize=16)
def cached_source(ref_json):
    from workbench_analysis.fep_e1.feature_owner import verify_file
    root=Path(__file__).resolve().parents[3]
    return verify_file(root,json.loads(ref_json))


@lru_cache(maxsize=1)
def confirmation_runtime():
    from src.v4.confirmation_candidate_r4 import detect
    from src.v4.target_fact_producers_r4 import validate
    import inspect
    node=ast.parse(inspect.getsource(validate)).body[0]
    removed=[n for n in node.body if isinstance(n,ast.ImportFrom) and n.module=='scripts.next_round_bundle_r1']
    if len(removed)!=1:raise ValueError('E2_VALIDATOR_CACHE_IMPORT_WHITELIST_CHANGED')
    node.body=[n for n in node.body if n not in removed]
    globals_=dict(validate.__globals__,exact=lambda ref:cached_source(json.dumps(ref,sort_keys=True)))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<E2_exact_validator_cached_source_read>','exec'),globals_)
    validated=globals_['validate']
    runtime=types.FunctionType(detect.__code__,dict(detect.__globals__,
        validate=lambda p,r:validated(p,r,expected_sources=p['source_bindings'])))
    return runtime


def confirmation(publication,root):return confirmation_runtime()(publication,root)


@lru_cache(maxsize=1)
def frozen_authority(root):
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    return CurrentStageAuthority(root)


def events(current,prior,inputs,calendar,history):
    from src.v4.confirmation_events_candidate_r5 import runtime,event_unknown_reasons
    from src.v4.state_identity import digest as owner_digest
    original=runtime();states=[current];previous=[] if prior is None else [prior]
    publication=dict(publication_id=current['publication_id'],rows=states,inputs=[inputs])
    source=dict(publication_id=prior['publication_id'] if prior else 'NO_PRIOR',rows=previous)
    allowed=[publication,source,*history]
    def verify(p):
        if p not in allowed:raise ValueError('E2_HISTORICAL_EVENT_SOURCE_NOT_BOUND')
        from src.v4.confirmation_d2_candidate_r5 import validate_candidate_output
        for state in p['rows']:validate_candidate_output(state)
        return p['rows']
    def freeze(**kwargs):
        target=kwargs.pop('target_date');previous=kwargs.pop('prior_date')
        value=dict(kwargs,contract_id='FEP_E2_HISTORICAL_PRIOR_STATE_BUNDLE_V1',target_trade_date=target,prior_trade_date=previous)
        return dict(value,head_digest=owner_digest(value))
    frozen=freeze(target_date=current['trade_date'],prior_date=calendar['sessions'][current['session_index']-1]['trade_date'],
        calendar_publication_id=current['calendar_publication_id'],rows=previous,source_binding=source,
        scope='REAL_SEALED_CANDIDATE_REPLAY_ONLY',calendar_manifest=calendar,episode_history=history)
    fn=types.FunctionType(original.__code__,dict(original.__globals__,verify_d2_publication=verify,freeze_prior_session=freeze))
    result=fn(publication,frozen,revision_of=None)
    for row in result:
        unknown=event_unknown_reasons(current,prior)
        if unknown:row['event_types']=[]
        row.update(event_quality='UNKNOWN' if unknown else 'KNOWN',event_unknown_predicates=unknown,**LINEAGE)
    return result


def entry_worker(job):
    import math
    import numpy as np
    import pandas as pd
    from market_calendar.trading_calendar import StockTimeline
    from normalize.universe_recent import qualifies_normal_universe
    from workbench_analysis.research_features import build_stock_research_features,ResearchFeatureContext
    from src.v4.base_seed import _eval
    from src.v4.stock_prewatch import evaluate
    from src.v4.target_fact_producers_r4 import produce,seal,CONTRACT,PARAMETERS
    from src.v4.adjustment_basis_r4 import basis_id
    from src.v4.adjustment_basis_r4 import observations
    from src.v4.factors.core import Observation,compute_core
    from src.v4.profile_primitives import derive_daily
    from src.v4.confirmation_d2_candidate_r5 import candidate_envelope,candidate_policy,input_skeleton
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    from workbench_analysis.v4_15_radar_cohort import RadarCohortRuntime
    sid,raw,sessions,members,statuses,start,temp,output,source_bindings,cutoff=job
    root,seed_parameters,prewatch_package,_=owner_packages()
    slots=slots_for(sid,raw,sessions,set(members),statuses)
    history_observations=observations(slots,sid,{(sid,r['date']):r['accepted_trading_status'] for r in slots})
    history_observations=[Observation(r['date'],'IDENTITY_UNKNOWN') if o.bar and not r['identity_verified'] else o
        for r,o in zip(slots,history_observations)]
    cached={r['ordinal']:r for r in read_gzip(Path(temp)/'features'/(sid+'.jsonl.gz'))}
    index=json.loads((Path(temp)/'rank_index.json').read_bytes())['entities'].index(sid)
    ranks=np.load(Path(temp)/'ranks.npy',mmap_mode='r')
    params=json.loads((root/'config/research_attention_v3.yaml').read_bytes())
    manifest=json.loads((root/'config/v4_11_legacy_extraction_manifest_r2.json').read_bytes())
    source_sha=digest(source_bindings)
    calendar=dict(sessions=[dict(trade_date=d,session_index=i) for i,d in enumerate(sessions)],lineage_id='E2_RECONSTRUCTED_HISTORICAL_CALENDAR')
    calendar['publication_id']='V4_11_R5B_CALENDAR:'+digest(calendar)
    raw_features=[];observed=set();prior=None;history=[];population=[];counts={};store=RecordStore();state_scan=[]
    radar=RadarCohortRuntime(frozen_authority(root),store)
    for i,slot in enumerate(slots):
        if slot['raw_actual_bar']:observed.add(int(slot['date'].replace('-','')))
        raw_features.append(dict(security_id=sid,trade_date=slot['date'],adj_close=slot.get('close') if slot['has_actual_bar'] else None,
            raw_amount=slot.get('amount'),has_actual_bar=slot['raw_actual_bar'],price_basis='TDX_NATIVE_QFQ',
            adjustment_status='VERIFIED_REPRODUCIBLE_TDX_NATIVE' if slot['has_actual_bar'] else 'UNKNOWN',
            project_price_basis='FORWARD_ADJUSTED',adjustment_version=basis_id(slot),is_synthetic_fill=False))
        if i<start:continue
        feature=cached[i];feature_cutoff(slots[:i+1],slot['date'])
        blocked=bool(prior and prior['episode_id'] and not candidate_policy()['fields']['frozen_invalidation']['implemented'])
        if not blocked:
            rs=[]
            for j in (i-3,i):
                rs.append(dict(security_id=sid,trade_date=sessions[j],rps5=float(ranks[0,index,j])/100,rps20=float(ranks[1,index,j])/100))
            legacy=build_stock_research_features(pd.DataFrame(raw_features[max(0,i-129):i+1]),pd.DataFrame(rs),sessions[max(0,i-129):i+1],
                ResearchFeatureContext(CONTRACT,CONTRACT+':'+slot['date'],source_sha,'NO_SECTOR_INPUT',calendar['publication_id'],slot['date']),
                liquidity20_amount_gte=params['thresholds']['stock_signals']['risk']['liquidity20_amount_gte']).to_dict('records')[0]
            legacy={k:(None if isinstance(v,float) and not math.isfinite(v) else v) for k,v in legacy.items()}
            feature=dict(feature,relative=dict(rps5=legacy['rps5'],rps20=legacy['rps20'],rps5_delta3=legacy['rps5_delta3'],
                owner_contracts=['RPS_MIDRANK_V1','RESEARCH_FEATURES_PREVIEW_1'],unit='fraction',
                prior_trade_date=sessions[i-3],asof_trade_date=slot['date']))
            timeline=StockTimeline(sid,min(observed) if observed else None,max(observed) if observed else None,len(observed),frozenset(observed),
                file_exists=bool(observed),structurally_valid=bool(observed),current_member=i in members)
            normal,_=qualifies_normal_universe(timeline,[int(d.replace('-','')) for d in sessions[max(0,i-119):i+1]])
            calculation_window=[dict(r,session_index=j,anchor_cutoff=slot['date'],is_synthetic_fill=False)
                for j,r in enumerate(slots[max(0,i-26):i+1],start=max(0,i-26))]
            values,_=produce(calculation_window,legacy,normal_universe=normal,identity_compatible=slot['identity_verified'],parameters=params)
            facts={f:dict(value=values.get(f),quality='UNKNOWN' if values.get(f) is None else 'KNOWN',reason='HISTORICAL_OWNER_INPUT_UNAVAILABLE' if values.get(f) is None else None,
                time_role='TARGET_SESSION_D0',source_digest=source_sha,system_available_at=cutoff) for f in manifest['input_fields']}
            pub=seal(dict(producer_contract_id=CONTRACT,parameter_set_id=PARAMETERS,scope='REAL_ACCEPTED_SOURCE_CANDIDATE',accepted=False,
                AS_RECORDED=False,knowledge_cutoff=cutoff,trade_date=slot['date'],source_bindings=source_bindings,source_digest=source_sha,
                rows=[dict(security_id=sid,trade_date=slot['date'],facts=facts)],permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False)))
            d0=confirmation(pub,root)['rows'][0]
            v=feature['values'];p=feature['profiles'];delta=legacy['rps5_delta3'];delta=delta*100 if delta is not None else None
            def fact(value):return dict(value=value,reason='HISTORICAL_OWNER_INPUT_UNAVAILABLE' if value is None else None)
            def enum(name):return fact(None if p[name]['value']=='UNKNOWN' else p[name]['value'])
            seedfacts=dict(research_universe=fact(i in members),actual_bar=fact(slot['raw_actual_bar']),price_identity_READY=fact(True if feature['actual'] else None),
                minimum_liquidity=fact(v['minimum_liquidity']),core_price_damage=fact(v['core_price_damage']),severe_extension=fact(p['severe']['value']),
                bias20_atr=fact(v['bias20_atr']),compression_state=enum('compression'),delta3=fact(delta),ma_structure_state=enum('trend'),
                close_t=fact(v['close']),ma20_t=fact(v['ma20']),close_t_minus_1=fact(v['previous_close']),ma20_t_minus_1=fact(v['previous_ma20']),core_participation_result=enum('participation'))
            seed=_eval(seedfacts,seed_parameters)
            quality='TRUE' if v['core_price_damage'] is not None and seed['base_seed_state']!='UNKNOWN' and seed['quality']=='COMPLETE' else 'UNKNOWN'
            pw=evaluate(dict(base_seed_state=seed['base_seed_state'],mandatory_core_quality_ready=quality,delta3=delta,
                compression_state=p['compression']['value'],ma_structure_state=p['trend']['value'],core_extension_risk=p['risk']['value']),prewatch_package)
            pid='E2_HISTORICAL_FACT:'+digest([feature,seed,pw,d0])
            vals=dict(SEED=seed['base_seed_state'],PREWATCH=pw['raw_qualification'],CONFIRMED=d0['confirmation_status'],
                core_price_damage='UNKNOWN' if v['core_price_damage'] is None else 'TRUE' if v['core_price_damage'] else 'FALSE',
                risk=p['risk']['value'],delta3='UNKNOWN' if delta is None else delta,scenario=d0['primary_scenario'] or 'UNKNOWN',
                suspended='FALSE' if feature['actual'] else 'TRUE' if slot['accepted_trading_status']=='CONFIRMED_SUSPENSION' else 'UNKNOWN')
        else:
            v=feature['values'];p=feature['profiles']
            vals=dict(SEED='UNKNOWN',PREWATCH='UNKNOWN',CONFIRMED='UNKNOWN',
                core_price_damage='UNKNOWN' if v['core_price_damage'] is None else 'TRUE' if v['core_price_damage'] else 'FALSE',
                risk=p['risk']['value'],delta3='UNKNOWN',scenario='UNKNOWN',
                suspended='FALSE' if feature['actual'] else 'TRUE' if slot['accepted_trading_status']=='CONFIRMED_SUSPENSION' else 'UNKNOWN')
            pid='E2_REQUIRED_INPUT_BLOCKED:'+digest([feature,prior['publication_id'],vals])
        fields={}
        for field in candidate_policy()['fields']:
            definition=candidate_policy()['fields'][field]
            status='NOT_APPLICABLE' if field=='WARM' or (field in ('frozen_invalidation','episode_invalidation_contract_id') and not prior) else 'IMPLEMENTED' if field in vals or definition['implemented'] else 'NOT_IMPLEMENTED'
            fields[field]=candidate_envelope(field,vals.get(field,'UNKNOWN'),status,session_index=i,trade_date=slot['date'],
                system_available_at=cutoff,publication_id=pid,payload_extra={'evaluation_status':'NOT_EVALUATED_REQUIRED_UPSTREAM_INCOMPLETE'} if blocked and field in ('SEED','PREWATCH','CONFIRMED','delta3','scenario') else None)
        inputs=input_skeleton(entity_id=sid,trade_date=slot['date'],session_index=i,cutoff=cutoff,calendar_manifest=calendar,
            fields=fields,prior_state=prior,prior_publication_id=prior['publication_id'] if prior else None)
        context=dict(LINEAGE,source_kind='REAL_ACCEPTED_HISTORICAL_SOURCE',expected_input=inputs,date=slot['date'],ordinal=i)
        state=reducer()(inputs,ledger=context)
        if blocked and state['final_eligibility']=='TRUE':raise ValueError('E2_REQUIRED_INPUT_GATE_OWNER_PARITY_FAIL')
        counts[state['final_eligibility']]=counts.get(state['final_eligibility'],0)+1
        state_scan.append(dict(entity_id=sid,trade_date=slot['date'],date_ordinal=i,publication_id=state['publication_id'],
            eligibility=state['final_eligibility'],maturity=state['maturity'],episode_id=state['episode_id'],
            validity=state['validity'],tracking=state['tracking'],transition_reasons=state['transition_reasons'],
            upstream_derivation='NOT_EVALUATED_REQUIRED_UPSTREAM_INCOMPLETE' if blocked else 'FULL_OWNER_EVALUATION',
            unknown_predicates=state['unknown_predicates'],state_digest=digest(state),source_kind='REAL_ACCEPTED_HISTORICAL_SOURCE',**LINEAGE))
        ev=events(state,prior,inputs,calendar,history) if state['final_eligibility']=='TRUE' else []
        exact_state=deepcopy(state)
        state=dict(state,comparison_reference=slot.get('close'),signal_reference=slot.get('close'),
            adjustment_identity=slot.get('adjustment_source_revision'),comparison_reference_source=source_bindings[0],
            t0_transform=dict(qfq_mul=slot.get('mul'),qfq_add=slot.get('add')))
        projected={'enrollments':[]}
        if state['final_eligibility']=='TRUE':
            store.append('historical_facts',pid,dict(feature_snapshot=feature,seed_facts=seedfacts,seed_output=seed,
                prewatch_output=pw,d0_publication=pub,d0_output=d0,legacy_features=legacy,calculation_window=calculation_window,
                source_bindings=source_bindings,**LINEAGE))
            state_ref=store.append('historical_state',state['publication_id'],dict(owner_output=exact_state,
                transport_metadata={k:state[k] for k in ('comparison_reference','signal_reference','adjustment_identity','comparison_reference_source','t0_transform')},
                **LINEAGE))
            projected=store.read(radar._project([state],ev,{},slot['date'],state['publication_id'],state_ref,
                'ENGINEERING_HISTORICAL_REPLAY',{},source_bindings))
        for ref in projected['enrollments']:
            enrollment=store.read(ref)
            core=compute_core(history_observations[:i+1],sid,asof=slot['date'])
            if digest({k:v.output_digest for k,v in core.items()})!=feature['core_output_digest']:
                raise ValueError('E2_CORE_REEXECUTION_DIGEST_MISMATCH')
            bars=[dict(trade_date=r['date'],adjusted_quality='READY',qfq_close=r['close'],qfq_high=r['high'],qfq_low=r['low'],amount=r['amount'])
                for r,o in zip(slots[:i+1],history_observations[:i+1]) if o.bar]
            dated=[(r['date'],'ACTUAL_TRADED' if o.state=='ACTUAL' else 'SUSPENDED' if o.state=='CONFIRMED_SUSPENSION' else o.state)
                for r,o in zip(slots[:i+1],history_observations[:i+1])]
            primitives=derive_daily(bars,{k:dict(value=v.value,quality_state=v.quality_state) for k,v in core.items()},dated,slot['date'],sessions[:i+1])
            if digest({k:asdict(v) for k,v in primitives.items()})!=feature['primitive_output_digest']:
                raise ValueError('E2_PRIMITIVE_REEXECUTION_DIGEST_MISMATCH')
            snapshot=dict(feature,core_envelopes={k:asdict(v) for k,v in core.items()},primitive_envelopes={k:asdict(v) for k,v in primitives.items()})
            row=dict(observation_id=enrollment['enrollment_id'],entity_id=sid,trade_date=slot['date'],date_ordinal=i,
                entry_event_type=enrollment['signal_type'],
                label_end_ordinal=i+1,episode_start=i,episode_end=i+1,episode_key=enrollment['episode_id'],
                enrollment_ref=ref,source_state_ref=state_ref,feature_snapshot=snapshot,regime='UNAVAILABLE',sector='UNAVAILABLE',
                trend=p['trend']['value'],position=p['position']['value'],risk=p['risk']['value'],
                feature_support='COMPLETE_OWNER_VECTOR' if all(value is not None for value in feature['values'].values()) else 'PARTIAL_EXPLICIT_UNKNOWN',
                source_kind='REAL_ACCEPTED_HISTORICAL_SOURCE',**LINEAGE)
            admissible(row);population.append(row)
        prior={k:v for k,v in state.items() if k not in ('comparison_reference','signal_reference','adjustment_identity','comparison_reference_source','t0_transform')}
        if prior['maturity']=='CONFIRMED' and prior['final_eligibility']=='TRUE':history.append(dict(publication_id=prior['publication_id'],rows=[prior]))
    spans={}
    for state in state_scan:
        if state['episode_id']:
            spans.setdefault(state['episode_id'],[state['date_ordinal'],state['date_ordinal']])[1]=state['date_ordinal']
    for row in population:
        row['episode_start'],row['episode_end']=spans[row['episode_key']]
        row['episode_interval_policy']='FULL_OBSERVED_OWNER_EPISODE_SPAN_INCLUDING_UNKNOWN_FOLLOWUP'
    out=Path(output);bundle_sha=write_gzip(out/'owner_records'/(sid+'.jsonl.gz'),store.rows())
    population_sha=write_gzip(out/'population'/(sid+'.jsonl.gz'),population)
    scan_sha=write_gzip(out/'state_scan'/(sid+'.jsonl.gz'),state_scan)
    return dict(entity_id=sid,rows=len(population),state_counts=counts,bundle_sha256=bundle_sha,population_sha256=population_sha,
        state_scan_sha256=scan_sha,state_rows=len(state_scan))
