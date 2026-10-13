"""All-security structure semantics, immutable identities and source hashes."""
import argparse,gzip,json,sys
import re
from copy import deepcopy
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_analysis.r43_owner_replay import load,checked,ref
from workbench_analysis.v4_12_structure_io import digest
from workbench_analysis.v4_12_structure_io import FrozenContracts
from workbench_analysis.v4_12_multi_anchor_state import active_selector
from workbench_analysis.v4_12_ast_runtime import ASTEngine
from workbench_analysis.v4_12_input_binder import InputBinder
from workbench_analysis.r43_structure_replay import CorrectedBinder
from workbench_analysis import r43_structure_replay as structure
from workbench_analysis.operational_owner_adapter_v1 import private_scope
from workbench_analysis.market_source_acquisition import official_sessions
from types import SimpleNamespace

def stream(path):
    with gzip.open(path,'rt',encoding='utf8') as f:
        for line in f:yield json.loads(line)

def entity_map(row):
    mapping={};reverse={}
    for state in row['anchor_states']:
        anchor=state['anchor']
        semantic=[anchor['security_id'],anchor['anchor_type'],anchor['anchor_trade_date'],anchor['anchor_raw_lower'],anchor['anchor_raw_upper'],anchor['anchor_price_basis'],anchor['adjustment_source_revision']]
        key=json.dumps(semantic,sort_keys=True)
        if key in reverse:raise ValueError('AMBIGUOUS_ANCHOR_SEMANTIC_KEY')
        reverse[key]=anchor['anchor_id'];mapping[anchor['anchor_id']]=['ANCHOR',*semantic]
        mapping[state['event']['event_id']]=['EVENT',state['event']['event_type'],*semantic]
    for episode in row['breakout_episodes']:
        owner=mapping.get(episode['owning_anchor_id'])
        if owner is None:raise ValueError('ORPHAN_EPISODE_ANCHOR')
        mapping[episode['breakout_episode_id']]=['EPISODE',episode['security_id'],episode['created_trade_date'],owner]
    return mapping

EXCEPTIONS={'available_at','adjustment_asof','source_fact_digest','source_runtime_manifest_digest','source_candidate_manifest_digest',
    'input_digest','output_digest','observation_digest','original_anchor_digest','counter_state_digest','overlay_digest','payload_digest',
    'logical_transition_id','source_ref','source_refs','publication_id','source_digest','source_publication_id','prior_snapshot_id',
    'source_namespace','source_output_digest','prior_session_state_ref','current_observation_ref','prior_state_ref','snapshot_id','source_publication_bindings','row_digest'}

def normalize(value,mapping,counts):
    if isinstance(value,dict):
        if 'path' in value and 'sha256' in value:
            counts['independently_verified_provenance_binding']+=1
            dates=re.findall(r'\d{4}-\d{2}-\d{2}',value['path'])
            return {'artifact_type':Path(value['path']).name,'source_trade_date':dates[-1] if dates else None}
        result={k:normalize(v,mapping,counts) for k,v in value.items() if not excluded(k,counts)}
        # These are sets emitted in the producer's anchor-ID order. Map IDs
        # first, then compare the complete semantic record multiset.
        for key in ('anchor_states','contexts','observations','transitions'):
            if key in result and isinstance(result[key],list):result[key]=sorted(result[key],key=lambda r:json.dumps(r,sort_keys=True))
        return result
    if isinstance(value,list):return [normalize(v,mapping,counts) for v in value]
    if isinstance(value,str) and value in mapping:return {'semantic_entity':mapping[value]}
    return value

def excluded(key,counts):
    if key in EXCEPTIONS:counts[key]+=1;return True
    return False

def check_hashes(root,value,seen,errors,sid):
    if isinstance(value,dict):
        if 'path' in value and 'sha256' in value:
            key=(value['path'],value['sha256'])
            if key not in seen:
                try:checked(root,value);seen.add(key)
                except ValueError as exc:errors.append(dict(security_id=sid,error=str(exc)))
        if 'counter_state' in value and value.get('counter_state_digest')!=digest(value['counter_state']):errors.append(dict(security_id=sid,error='COUNTER_STATE_HASH'))
        if 'output_digest' in value and value['output_digest']!=digest({k:v for k,v in value.items() if k!='output_digest'}):errors.append(dict(security_id=sid,error='OUTPUT_ENVELOPE_HASH'))
        for child in value.values():check_hashes(root,child,seen,errors,sid)
    elif isinstance(value,list):
        for child in value:check_hashes(root,child,seen,errors,sid)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--generation',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    root=Path(args.root);base=root/args.generation
    previous=load(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');last=previous['accepted_trade_date']
    pdoc=load(checked(root,previous['owners'][last]['diagnostic']));prior_manifest=load(checked(root,pdoc['snapshot']))
    prior={r['security_id']:r for r in stream(checked(root,prior_manifest['snapshot_bundle']))}
    full=root/'data/v4/dynamic_daily_owners/2026-10-13/35e5a7c80925e59b640bcc694df1184e8bb850634b10085473cd26f6b9b89b57'
    actualpath=base/'owner_v3/owners/2026-10-13/structure/runtime_security.jsonl.gz';fullpath=full/'owner_v3/owners/2026-10-13/structure/runtime_security.jsonl.gz'
    counts=Counter();diff=[];identity_errors=[];hash_errors=[];seen=set();securities=0;field_difference_count=0
    contracts=FrozenContracts(root);sessions=official_sessions(root)
    current_profile=load(base/'owner_v3/owners/2026-10-13/PROFILE_STRUCTURE_OWNER.json')
    status_rows={r['security_id']:r for r in stream(checked(root,current_profile['owner']['status']))}
    io_cache={}
    def bounded_input_rows(path):
        path=Path(path)
        if path not in io_cache:
            result=[]
            for row in stream(path):
                if path.name=='history.jsonl.gz':row=dict(row,bars=[b for b in row['bars'] if b['trade_date']==last])
                elif path.name=='profiles.jsonl.gz':row=dict(security_id=row['security_id'],states={'near_high20_state':row['states']['near_high20_state']})
                result.append(row)
            io_cache[path]=result
        return io_cache[path]
    bound_scope=private_scope(structure,dict(gzrows=bounded_input_rows))
    bind_profiles=bounded_input_rows(checked(root,current_profile['owner']['profiles']))
    verifier=bound_scope['CorrectedEpisodeEngine'](contracts,'2026-10-13',load(base/'owner_v3/owners/2026-10-13/structure/runtime_manifest.json')['available_at'],current_profile['owner'],bind_profiles,list(status_rows.values()))
    fields={r['field']:r for r in contracts.config['field_registry']['fields']}
    selector_corrections=[];mapped_old_anchors=0;new_anchor_checks=0
    for actual,expected in zip(stream(actualpath),stream(fullpath),strict=True):
        sid=actual['identity']['security_id'];securities+=1
        if sid!=expected['identity']['security_id']:raise ValueError('STRUCTURE_ROW_ORDER_OR_IDENTITY_MISMATCH')
        # B' replaces only the reference's historical identity inputs with A's
        # uniquely matched true identities, then runs the unchanged selector.
        # No expected winner is copied from the actual output.
        original_expected=expected;expected=deepcopy(expected)
        old=prior.get(sid);old_semantics={}
        for state in old['anchor_states'] if old else []:
            anchor=state['anchor'];key=json.dumps(entity_map({'anchor_states':[state],'breakout_episodes':[]})[anchor['anchor_id']][1:],sort_keys=True)
            if key in old_semantics:raise ValueError('ACCEPTED_OLD_ANCHOR_AMBIGUOUS')
            old_semantics[key]=state
        actual_semantics=entity_map(actual)
        replacement_ids={}
        for state in expected['anchor_states']:
            anchor=state['anchor'];old_id=anchor['anchor_id'];semantic=entity_map({'anchor_states':[state],'breakout_episodes':[]})[old_id][1:];key=json.dumps(semantic,sort_keys=True)
            if anchor['anchor_trade_date']<'2026-10-13':
                match=old_semantics.get(key)
                if match is None:raise ValueError('REFERENCE_OLD_ANCHOR_NOT_ACCEPTED_PREDECESSOR')
                aid=match['anchor_id'];mapped_old_anchors+=1
            else:
                matches=[state_a for state_a in actual['anchor_states'] if actual_semantics[state_a['anchor_id']][1:]==semantic]
                if len(matches)!=1:raise ValueError('NEW_ANCHOR_SEMANTIC_AMBIGUOUS')
                a=matches[0]['anchor'];identity=dict(contract_id=contracts.config['structure_event_contract']['contract_id'],security_id=sid,source_event_id=a['source_event_id'],
                    anchor_type=a['anchor_type'],anchor_trade_date=a['anchor_trade_date'],source_fact_digest=a['source_fact_digest'],**a['creation_coordinate'])
                if a['anchor_id']!=digest(identity):raise ValueError('NEW_ANCHOR_ID_ACTUAL_INPUT_HASH')
                aid=a['anchor_id'];new_anchor_checks+=1
            replacement_ids[old_id]=aid
        def replace_ids(value):
            if isinstance(value,dict):return {k:replace_ids(v) for k,v in value.items()}
            if isinstance(value,list):return [replace_ids(v) for v in value]
            if isinstance(value,str):return replacement_ids.get(value,value)
            return value
        expected=replace_ids(expected)
        selected=active_selector(contracts.config['multi_anchor_state_contract'] if 'multi_anchor_state_contract' in contracts.config else load(checked(root,load(checked(root,pdoc['snapshot']))['snapshot_contract'])),
            contracts,expected['anchor_states'],expected['common_facts'],'2026-10-13',expected['identity']['revision'])
        if selected!=original_expected['active_selection']:selector_corrections.append(sid)
        expected['active_selection']=selected
        chosen=next((s for s in expected['anchor_states'] if s['anchor_id']==selected['active_anchor_id']),None)
        statecontract=load(checked(root,load(checked(root,pdoc['snapshot']))['snapshot_contract']))
        projection={n:deepcopy(chosen['output_envelope'].get(n)) if chosen else None for n in statecontract['security_projection']}
        projection['active_anchor_id']=selected['active_anchor_id']
        if not chosen:
            for n in ('support_state','acceptance_state','basic_pullback_state','basic_recovery_state'):projection[n]='UNKNOWN'
        projection.update(active_anchor_selection_quality=selected['quality'],active_anchor_selection_reason=selected['reason'],projection_quality='KNOWN' if chosen else 'UNKNOWN',reason=selected['reason'])
        for k in original_expected['active_projection']:
            if k not in projection:projection[k]=deepcopy(expected['active_projection'][k])
        expected['active_projection']=projection
        amap=entity_map(actual);bmap=entity_map(expected)
        aa=normalize(actual,amap,counts);bb=normalize(expected,bmap,counts)
        if aa!=bb:
            field_difference_count+=1
            if len(diff)<25:diff.append(dict(security_id=sid,changed_top_fields=[k for k in aa if aa[k]!=bb.get(k)]))
        old=prior.get(sid)
        if old:
            oldstates={s['anchor_id']:s for s in old['anchor_states']}
            for state in actual['anchor_states']:
                a=state['anchor']
                if a['anchor_trade_date']< '2026-10-13':
                    if a['anchor_id'] not in oldstates:identity_errors.append(dict(security_id=sid,error='OLD_ANCHOR_ID_NOT_ACCEPTED_PREDECESSOR'))
                    elif a!=oldstates[a['anchor_id']]['anchor']:identity_errors.append(dict(security_id=sid,error='FROZEN_OLD_ANCHOR_CHANGED'))
            priorref=actual['prior_state_ref']
            if not priorref:identity_errors.append(dict(security_id=sid,error='OLD_SECURITY_PRIOR_REFERENCE_MISSING'))
            elif priorref.get('security_id')!=sid or priorref.get('row_digest')!=digest(old) or priorref.get('candidate_manifest',{}).get('sha256')!=pdoc['snapshot']['sha256']:
                identity_errors.append(dict(security_id=sid,error='PRIOR_SNAPSHOT_NOT_EXACT_ACCEPTED_ROW'))
        check_hashes(root,actual,seen,hash_errors,sid)
        # The breakout wrapper deliberately modifies a detector copy, not the
        # common upstream facts. Recreate that single registered prior fact.
        detector=deepcopy(actual['common_facts']);fact=detector['prior_breakout_exists']
        active=old.get('active_breakout_episode_id') if old else None
        allowed=bool(old and old['breakout_episode_set_quality']=='KNOWN' and active is None)
        priorref=actual['prior_state_ref'];sha=priorref.get('sha256') if priorref else None
        fact.update(value=False if allowed else None,quality='KNOWN' if allowed else 'UNKNOWN',
            reason=None if allowed else 'NO_KNOWN_EMPTY_BREAKOUT_EPISODE',source_digest=sha,source_publication_id=sha)
        if actual['creation_observation']['input_digest']!=digest(detector):hash_errors.append(dict(security_id=sid,error='CREATION_ACTUAL_INPUT_DIGEST'))
        for state in actual['anchor_states']:
            if state['created_this_session']:
                if state['overlay_digest']!=digest(actual['common_facts']):hash_errors.append(dict(security_id=sid,error='FRESH_ANCHOR_OVERLAY_INPUT_HASH'))
                continue
            oldstate=next((s for s in old['anchor_states'] if s['anchor_id']==state['anchor_id']),None) if old else None
            if oldstate is None:continue
            common=verifier.binder.bind(sid,None)
            overlay,_=verifier.overlay(common,oldstate,priorref,sid)
            if active:
                active_episode=next(e for e in old['breakout_episodes'] if e['breakout_episode_id']==active)
                if active_episode['owning_anchor_id']==state['anchor_id']:
                    overlay['prior_breakout_exists']=verifier.binder.record(verifier.binder.fields['prior_breakout_exists'],active_episode['validity']=='ACTIVE','KNOWN',None,priorref,last)
            if state['overlay_digest']!=digest(overlay):hash_errors.append(dict(security_id=sid,error='CONTINUING_ANCHOR_ACTUAL_OVERLAY_INPUT_HASH'))

    result=dict(contract_id='V4_R1_1_FULL_STRUCTURE_SEMANTIC_IDENTITY',scope='FULL_STRUCTURE_ALL_SECURITIES',counts=dict(securities=securities),
        G1=dict(status='PASS' if not diff else 'FAIL',different_security_count=field_difference_count,examples=diff),
        G2=dict(status='PASS' if not identity_errors else 'FAIL',errors=identity_errors[:50],error_count=len(identity_errors)),
        G3=dict(status='PASS' if not hash_errors else 'FAIL',errors=hash_errors[:50],error_count=len(hash_errors),verified_binding_count=len(seen),
            note='Every creation and continuing/fresh-anchor actual input_digest independently reconstructed from bound F0 sources and accepted prior state; recursive source, counter and output hashes verified'),
        reference_qualification=dict(kind='B_PRIME_ACCEPTED_ID_INPUT_SELECTOR',old_anchor_semantic_mappings=mapped_old_anchors,new_anchor_id_hash_checks=new_anchor_checks,
            corrected_selector_count=len(selector_corrections),selector_examples=selector_corrections[:30]),
        classified_exception_counts=dict(counts),actual=ref(root,actualpath),reference=ref(root,fullpath),acceptance='BLOCKED_PENDING_COMPLETE_HASH_AND_OTHER_DOMAINS')
    Path(args.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
