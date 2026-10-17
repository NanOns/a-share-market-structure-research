"""Independent readback: standard-library source/identity checks, no runtime imports."""
import argparse
import ast
from collections import Counter,defaultdict
from decimal import Decimal
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
from scripts.v4_11_promotion_contract_r1 import ROOT,PERMISSIONS
from scripts.prepare_v4_12_runtime_entry_r1 import OUT,BASELINE,ENTRY
from scripts.validate_v4_12_runtime_entry_r1 import validate as entry_validate
from scripts.record_r7_stage_contract import put
from scripts.validate_v4_12_contract_freeze_r1 import FixtureExpressionVerifier,UNKNOWN,load_configs

def canonical(value):return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8')
def sha(value):return hashlib.sha256(canonical(value)).hexdigest()
def exact(ref):
    path=(ROOT/ref['path']).resolve();assert path.is_relative_to(ROOT)
    raw=path.read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],ref['path']
    return raw
def read(path):return json.loads((ROOT/path).read_bytes())
def lines(path):
    p=ROOT/path;stream=gzip.open(p,'rt',encoding='utf-8') if p.suffix=='.gz' else p.open(encoding='utf-8')
    with stream:
        for line in stream:
            if line.strip():yield json.loads(line)

def validate(emit=False):
    entry_result=entry_validate();entry=read(ENTRY);contract_digest=sha(entry['frozen_contracts'])
    manifest=read(OUT+'V4_12_RUNTIME_MANIFEST.json');assert manifest['frozen_contract_digest']==contract_digest
    assert manifest['entry']==entry_result['entry'] and manifest['trade_date']=='2026-09-30'
    assert manifest['prior_D1_history_status']=='NO_ACCEPTED_PRIOR_D1_PUBLICATION'
    assert manifest['permissions']==PERMISSIONS and not manifest['Stage_head_advanced'] and not manifest['Data_head_advanced']
    artifacts={Path(r['path']).name:r for r in manifest['artifacts']}
    for ref in manifest['artifacts']:exact(ref)
    registry={r['field']:r for r in read('config/v4_12_field_registry_v1.json')['fields']};parameters=read('config/v4_12_parameter_set_v1.json')
    data=read('data/v4/V4_DATA_ACCEPTED_HEAD.json')
    universe= json.loads(exact(data['component_artifacts']['IDENTITY_UNIVERSE']))['rows'];ids=sorted(r['security_id'] for r in universe)
    assert len(ids)==len(set(ids))==manifest['universe_count']
    sources={};allowed={}
    for row in registry.values():
        if row['field_role']=='UPSTREAM_ACCEPTED':
            head_raw=(ROOT/row['accepted_head_path']).read_bytes();assert hashlib.sha256(head_raw).hexdigest()==row['accepted_head_sha256']
            for pub in row['target_publications'].values():allowed[pub['artifact']['path']]=pub['artifact']
    calendar=read('config/v4_12_time_counter_contract_v2.json')['definitions']['calendar_authority'];allowed[calendar['path']]=calendar
    trading=read('config/v4_12_source_derivations_r2.json')['dependency_ledger']['evaluable']['publications']['2026-09-30'];allowed[trading['path']]=trading
    for ref in manifest['source_bindings']:
        assert ref==allowed[ref['path']],'UNAUTHORIZED_SOURCE_PUBLICATION'
        payload=json.loads(exact(ref));sources[ref['sha256']]={r['security_id']:r for r in payload.get('rows',[])}
    summary=read(OUT+'V4_12_REAL_SCOPED_REPLAY.json');assert summary['source_bindings']==manifest['source_bindings'] and summary['universe_count']==len(ids)
    fields=defaultdict(Counter);reason_counts=defaultdict(Counter);input_digests={};binding_ids=[];independent_states={};configs=load_configs()
    previous=max(day for day in json.loads(exact(calendar))['session_dates'] if day<'2026-09-30')
    for pack in lines(artifacts['V4_12_INPUT_BINDING_CANDIDATE.jsonl.gz']['path']):
        identity=pack['identity'];security=identity['security_id'];binding_ids.append(security)
        assert identity['trade_date']=='2026-09-30' and identity['revision']=='r1'
        facts=pack['fields'];assert set(facts)=={n for n,r in registry.items() if r['field_role']!='D1_OUTPUT'}
        input_digests[security]=sha(facts)
        # Independent historical verifier is separate from runtime; no shared evaluator implementation.
        verifier=FixtureExpressionVerifier(configs,{name:f['value'] if f['quality']=='KNOWN' else None for name,f in facts.items()})
        expected_states={}
        for name in [*configs['machine_ast']['machines'],'retention']:
            actual=verifier.target('retention_value' if name=='retention' else name)
            expected_states[name]='UNKNOWN' if actual is UNKNOWN else str(actual)
        independent_states[security]=expected_states
        for name,fact in facts.items():
            row=registry[name];assert fact['logical_field']==name and fact['producer_contract_id']==row['producer_contract_id']
            assert fact['source_namespace']==row['source_namespace'] and fact['time_role']==row['time_role']
            assert fact['trade_date']==(previous if row['time_role']=='T_MINUS_1' else '2026-09-30')
            fields[name][fact['quality']]+=1
            if fact['reason']:reason_counts[name][str(fact['reason'])]+=1
            if row['field_role']=='BLOCKED_CAPABILITY':
                assert fact['value'] is None and fact['quality']=='UNKNOWN' and fact['reason']==row['blocked_reason']
                assert fact['source_digest'] is None;fields[name]['BLOCKED_CAPABILITY']+=1
            if row['field_role']=='FROZEN_PRIOR_D1':assert fact['value'] is None and fact['quality']=='UNKNOWN' and fact['reason']=='NO_ACCEPTED_PRIOR_D1_PUBLICATION'
            if row['field_role']=='UPSTREAM_ACCEPTED':
                pub=row['target_publications']['2026-09-30']
                assert datetime.fromisoformat(pub['available_at'])<=datetime.fromisoformat(manifest['cutoff'])
                assert pub['trade_date']==fact['trade_date'] and fact['source_digest']==pub['artifact']['sha256']
                source=sources[fact['source_digest']].get(security)
                if source is None:expected_quality='UNKNOWN'
                elif 'fields' in source:
                    item=source['fields'].get(row['accepted_source_field'],{})
                    expected_quality='KNOWN' if item.get('quality_state')=='OBSERVED' and item.get('value') is not None else 'UNKNOWN'
                else:expected_quality='KNOWN' if source[pub['quality_field']]=='READY' and source.get(row['accepted_source_field']) is not None else 'UNKNOWN'
                assert fact['quality']==expected_quality,'ACCEPTED_SOURCE_QUALITY_PARITY'
            if fact['quality']=='KNOWN' and row['field_role']=='UPSTREAM_ACCEPTED':
                pub=row['target_publications']['2026-09-30'];assert fact['source_digest']==fact['source_publication_id']==pub['artifact']['sha256']
                source=sources[fact['source_digest']][security]
                if 'fields' in source:
                    accepted=source['fields'][row['accepted_source_field']];assert accepted['quality_state']=='OBSERVED';value=accepted['value']
                else:assert source[pub['quality_field']]=='READY';value=source[row['accepted_source_field']]
                if row['data_type'] in ['number','integer']:assert Decimal(str(fact['value']))==Decimal(str(value))
                else:assert fact['value']==value
            if fact['quality']=='UNKNOWN':assert fact['value'] is None and fact['reason']
    assert sorted(binding_ids)==ids
    for name,counts in summary['per_field'].items():
        assert counts==dict(KNOWN=fields[name]['KNOWN'],UNKNOWN=fields[name]['UNKNOWN'],BLOCKED_CAPABILITY=fields[name]['BLOCKED_CAPABILITY'],reason_counts=dict(reason_counts[name]))
    outputs=defaultdict(Counter);output_reasons=defaultdict(Counter);observation_ids=[];identity_set=set()
    for row in lines(artifacts['V4_12_D1_RUNTIME_CANDIDATE.jsonl']['path']):
        security=row['security_id'];observation_ids.append(security);identity=sha(row['identity']);assert identity not in identity_set;identity_set.add(identity)
        assert row['input_digest']==input_digests[security] and row['contract_digest']==contract_digest
        assert row['prior_state_ref'] is None and row['prior_D1_history_status']=='NO_ACCEPTED_PRIOR_D1_PUBLICATION' and row['AS_RECORDED'] is False
        envelope=row['frozen_output_envelope'];assert envelope['output_digest']==sha({k:v for k,v in envelope.items() if k!='output_digest'})
        assert set(envelope)==set(read('config/v4_12_output_schema_v1.json')['schema']['properties'])
        for name,record in row['outputs'].items():
            assert record['state']==independent_states[security][name],'INDEPENDENT_REAL_AST_PARITY'
            assert record['input_digest']==row['input_digest'] and record['contract_digest']==contract_digest
            assert record['parameter_set_id']==parameters['parameter_set_id']
            assert record['prior_state_ref'] is None and record['source_event_ref'] is None and record['anchor_ref'] is None
            outputs[name][record['state']]+=1
            if record['quality']=='UNKNOWN':assert record['state']=='UNKNOWN' and record['reason'] and record['value'] in [None,'UNKNOWN']
            for reason in record['reason']:output_reasons[name][reason]+=1
    assert sorted(observation_ids)==ids
    for name,counts in summary['per_output'].items():assert counts==dict(states=dict(outputs[name]),UNKNOWN_reason_distribution=dict(output_reasons[name]))
    assert summary['acceptance_states']==dict(outputs['acceptance']) and summary['support_observations']==len(ids)
    anchors=list(lines(artifacts['V4_12_ANCHOR_CANDIDATE.jsonl']['path']));events=list(lines(artifacts['V4_12_EVENT_CANDIDATE.jsonl']['path']))
    assert len(anchors)==summary['anchors_created']==0 and len(events)==summary['events_created']==0
    transitions=list(lines(artifacts['V4_12_TRANSITION_CANDIDATE.jsonl']['path']));assert len(transitions)==len(ids)*len(outputs)
    assert len({sha(r['identity']) for r in transitions})==len(transitions)
    assert all(r['prior_state_ref'] is None and r['same_day_revision_is_prior'] is False for r in transitions)
    business=read(OUT+'V4_12_SYNTHETIC_BUSINESS_PARITY.json');expected={r['vector_id']:r for r in read('config/v4_12_machine_vectors_v1.json')['vectors']}
    assert business['status']=='PASS' and business['total']==len(expected)==69
    for r in business['rows']:
        assert r['expected']==expected[r['vector_id']]['expected'] and r['status']=='PASS'
        if isinstance(r['expected'],bool):assert r['actual'] is r['expected']
        elif isinstance(r['expected'],(int,float)) or isinstance(r['expected'],str) and r['expected'][:1] in '-0123456789':assert Decimal(str(r['actual']))==Decimal(str(r['expected']))
        else:assert r['actual']==r['expected']
    sequence=read(OUT+'V4_12_SYNTHETIC_SEQUENCE_PARITY.json');book=read('config/v4_12_time_counter_vectors_r2_1.json')
    assert sequence['status']=='PASS' and sequence['total']==33
    for actual_sequence,expected_sequence in zip(sequence['sequences'],book['sequences']):
        assert actual_sequence['id']==expected_sequence['id']
        for a,e in zip(actual_sequence['steps'],expected_sequence['steps']):
            assert a['expected']==e['expected'] and a['status']=='PASS'
            for key,val in e['expected'].items():
                observed=a['actual'][key]
                if isinstance(val,bool):assert observed is val
                elif isinstance(val,int):assert Decimal(str(observed))==val
                else:assert observed==val
            if a['previous_session_state_ref']:assert a['previous_session_state_ref']<a['date']
    assert [r['actual_count'] for r in sequence['quality_correction']]==[1,0,1]
    negative=read(OUT+'V4_12_DAG_COORDINATE_NEGATIVE_PARITY.json');assert negative['status']=='PASS' and all(r['actual']==r['expected'] for r in negative['rows'])
    authority=read(OUT+'V4_12_RUNTIME_R2_AUTHORITY_PARITY.json');assert authority['total']==12 and all(r['actual']==r['expected'] for r in authority['rows'])
    time=read(OUT+'V4_12_RUNTIME_TIME_DOMAIN_NEGATIVE_PARITY.json');assert time['total']==10 and all(r['actual']==r['expected'] for r in time['rows'])
    idempotency=read(OUT+'V4_12_RUNTIME_IDEMPOTENCY.json');assert idempotency['artifact_digests_before'][:5]==idempotency['artifact_digests_after']==[manifest['artifacts'][i]['sha256'] for i in range(5)]
    fresh=read(OUT+'V4_12_FRESH_RUNTIME_RERUN_DIGEST_EQUALITY.json');assert fresh['status']=='PASS' and fresh['before']==fresh['after']==manifest['artifacts']
    for ref in fresh['runtime_sources']:exact(ref)
    lifecycle=read(OUT+'V4_12_SYNTHETIC_CANDIDATE_LIFECYCLE_R1_SCHEMA_VALID.json');assert lifecycle['status']=='PASS' and lifecycle['conflict_rejected'] and lifecycle['original_fact_unchanged']
    from jsonschema import Draft202012Validator
    schema=read('config/v4_12_anchor_schema_v1.json')['schema']
    Draft202012Validator(schema).validate({k:lifecycle['original_anchor'][k] for k in schema['required']})
    assert sha(lifecycle['original_anchor'])==lifecycle['immutable_anchor_digest'] and lifecycle['event']['anchor_id']==lifecycle['episode_bound_anchor_id']!=lifecycle['active_display_anchor_id']
    assert lifecycle['event']['frozen_invalidation_ast']==read('config/v4_12_machine_ast_v1.json')['definitions']['episode_invalidated']
    assert [r['observation_revision'] for r in lifecycle['observation_views']]==['r1','r2','r3']
    for path in sorted((ROOT/'src/workbench_analysis').glob('v4_12_*.py')):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):assert not (node.module or '').startswith(('scripts','tests'))
            if isinstance(node,ast.Name):assert node.id!='FixtureExpressionVerifier'
        assert 'v4_11' not in path.read_text(encoding='utf-8').lower()
    changed=subprocess.check_output(['git','diff','--name-only',BASELINE],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('data/','migrations/','alembic/','config/')) or '/migrations/' in p for p in changed)
    result=dict(status='PASS',candidate_status='V4_12_D1_RUNTIME_ENGINE_R1_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',entry_readback=entry_result,
        universe_count=len(ids),binding_fields=len(summary['per_field']),business_vectors=69,authority_vectors=12,sequence_steps=33,time_domain_vectors=10,
        input_authority='PASS_EXACT_SOURCE_VALUE_AND_PUBLICATION',UNKNOWN_attribution='PASS_ALL_FIELDS_AND_OUTPUTS',same_day_prior_isolation='PASS',
        counter_readback='PASS',append_only_identity='PASS',idempotency='PASS',DAG_negative='PASS',runtime_validator_independent=True,
        raw_fallback_count=0,V4_11_candidate_substitution_count=0,provider_replacement_count=0,stage_accepted=False,schema_migration=False,permissions=PERMISSIONS,
        external_acceptance=False,next_stage='UNIFIED_COMMIT_PUSH_STOP_WAIT_EXTERNAL_AUDIT')
    if emit:put(OUT+'V4_12_RUNTIME_READBACK.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--emit',action='store_true');r=validate(p.parse_args().emit)
    print(json.dumps({k:r[k] for k in ['status','candidate_status','universe_count','binding_fields','business_vectors','sequence_steps','raw_fallback_count']}))
