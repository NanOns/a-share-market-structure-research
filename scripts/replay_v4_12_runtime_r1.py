"""R10B scoped runner. Runtime never imports this synthetic/real evidence driver."""
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import sys
import time
from scripts.v4_11_promotion_contract_r1 import ROOT,bind,PERMISSIONS
from scripts.record_r7_stage_contract import put
from scripts.prepare_v4_12_runtime_entry_r1 import OUT,ENTRY
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore,digest,exact_json
from workbench_analysis.v4_12_ast_runtime import ASTEngine
from workbench_analysis.v4_12_structure_engine import StructureEngine,SessionLedger
from workbench_analysis.v4_12_anchor_runtime import coordinate_view,create_anchor,create_event
from workbench_analysis.v4_12_input_binder import check_availability

def norm(value):
    if value is None:return 'UNKNOWN'
    if isinstance(value,Decimal):return str(value)
    return value
def equals(actual,expected):
    if isinstance(expected,bool):return actual is expected
    if isinstance(expected,(int,float)) or isinstance(expected,str) and expected[:1] in '-0123456789':
        try:return Decimal(str(actual))==Decimal(str(expected))
        except Exception:return False
    return actual==expected

def synthetic_anchor(c,values=None,revision='r1'):
    values=values or dict(price_basis='SYNTHETIC_QFQ',adjustment_source_revision=revision)
    return create_anchor(c,'BULLISH_IMPULSE_LOW','SYNTHETIC','2026-09-24','2026-09-24T16:00:00+00:00',values,'SYNTHETIC_EVENT','0'*64,
        (10,10),dict(scope='SYNTHETIC_ENGINEERING_ONLY'),dict(mul='1',add='0',scope='SYNTHETIC_ENGINEERING_ONLY'))

def business_vectors(c):
    pack=c.config['machine_vectors'];rows=[]
    for v in pack['vectors']:
        inputs={**pack['defaults'],**v['inputs']}
        if v['kind']=='AST':
            result=ASTEngine(c.config,inputs).target(v['target']);actual=norm(result.value);detail=result.record()
        else:
            target=v['target'];detail={}
            if target=='basis_identity':
                a=synthetic_anchor(c,dict(price_basis=inputs['left'][0],adjustment_source_revision=inputs['left'][1]));view=coordinate_view(a,*inputs['right'],'2026-09-30','r1');actual=view['quality']=='KNOWN'
            elif target=='coordinate_gate':
                a=synthetic_anchor(c);view=coordinate_view(a,'SYNTHETIC_QFQ','unavailable_cross_basis','2026-09-30','r1');actual='UNKNOWN:'+view['reason']
            elif target=='immutable_anchor':
                a=synthetic_anchor(c);a['anchor_raw_lower']=a['anchor_raw_upper']=str(inputs['original']['price']);a['frozen_transform_coefficients'].update(mul=str(inputs['alpha']),add=str(inputs['beta']))
                before=digest(a);view=coordinate_view(a,a['anchor_price_basis'],a['adjustment_source_revision'],'2026-09-30','r1');actual=before==digest(a) and Decimal(view['lower'])==5
            elif target=='future_source':
                try:check_availability(inputs['source_available'],inputs['cutoff']);actual='KNOWN'
                except ValueError as error:actual='REJECT:'+str(error)
            else:raise ValueError('UNKNOWN_FROZEN_GATE')
        rows.append(dict(vector_id=v['vector_id'],target=v['target'],expected=v['expected'],actual=actual,detail=detail,status='PASS' if equals(actual,v['expected']) else 'FAIL'))
    return dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',total=len(rows),rows=rows,
        runtime_evaluator='src/workbench_analysis/v4_12_ast_runtime.py',expected_source=c.refs['machine_vectors'],scope='SYNTHETIC_ENGINEERING_ONLY_NOT_SOURCE_CAPABILITY_UPGRADE')

def sequence_vectors(c):
    book=c.config['time_counter_vectors_r2_1'];out=[]
    for sequence in book['sequences']:
        ledger=SessionLedger(c,sequence['available_date'],sequence['calendar'],'SYNTHETIC_ANCHOR');rows=[]
        for step in sequence['steps']:
            defaults={**c.config['machine_vectors']['defaults'],'C':step['C'],'L':10 if step['C'] is None or step['C']>=10 else 8,'H':11,
                'CLV':step.get('CLV',.7 if step['date']==sequence['available_date'] else .4),'lo':10,'hi':10,'atr_prior_view':1}
            record=ledger.observe(step['date'],step['revision'],step['evaluable'],defaults)
            actual={k:norm(record[k]) for k in step['expected']}
            rows.append(dict(id=step['id'],date=step['date'],revision=step['revision'],expected=step['expected'],actual=actual,
                previous_session_state_ref=record['previous_session_state_ref'],preserved_support_state=record['preserved_support_state'],
                status='PASS' if all(equals(actual[k],v) for k,v in step['expected'].items()) else 'FAIL'))
        out.append(dict(id=sequence['id'],steps=rows))
    # Quality correction replaces date membership against t-1, not the last revision.
    q=SessionLedger(c,'2026-09-24',['2026-09-24','2026-09-25'],'SYNTHETIC_Q')
    values={**c.config['machine_vectors']['defaults'],'C':10,'H':11,'L':10,'lo':10,'hi':10,'atr_prior_view':1,'CLV':.7}
    correction=[]
    for revision,evaluable,expected in [('r1',True,1),('r2',False,0),('r3',True,1)]:
        actual=q.observe('2026-09-25',revision,evaluable,values)
        correction.append(dict(revision=revision,evaluable=evaluable,expected_count=expected,actual_count=actual['evaluable_count'],status='PASS' if actual['evaluable_count']==expected else 'FAIL'))
    return dict(status='PASS' if all(r['status']=='PASS' for s in out for r in s['steps']) and all(r['status']=='PASS' for r in correction) else 'FAIL',
        total=sum(len(s['steps']) for s in out),sequences=out,quality_correction=correction,expected_source=c.refs['time_counter_vectors_r2_1'])

def negative_vectors(c,engine):
    rows=[]
    for namespace in c.entry['forbidden_namespaces']+['D2[t]','same-day Event','future dates']:
        try:engine.evaluate('SYNTHETIC',extra_namespaces={namespace:{}});actual='WRONGLY_ACCEPTED'
        except ValueError as error:actual=str(error).split(':')[0]
        rows.append(dict(id='DAG_'+namespace,expected='FORBIDDEN_RUNTIME_INPUT_NAMESPACE',actual=actual,status='PASS' if actual=='FORBIDDEN_RUNTIME_INPUT_NAMESPACE' else 'FAIL'))
    anchor=synthetic_anchor(c);before=digest(anchor)
    for label,revision in [('cash_dividend','cash'),('bonus_split','bonus'),('rights_issue','rights'),('same_day_revision','r2'),('cross_company_action_support','cross')]:
        view=coordinate_view(anchor,anchor['anchor_price_basis'],revision,'2026-09-30','r1')
        actual=dict(quality=view['quality'],reason=view['reason'],original_immutable=digest(anchor)==before)
        expected=dict(quality='UNKNOWN',reason='PRICE_BASIS_MISMATCH',original_immutable=True)
        rows.append(dict(id='COORD_'+label,expected=expected,actual=actual,status='PASS' if actual==expected else 'FAIL'))
    return dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',rows=rows)

def real_replay(c,engine):
    head=engine.binder.data;universe_ref=head['component_artifacts']['IDENTITY_UNIVERSE'];universe=exact_json(c.root,universe_ref)['rows']
    ids=sorted(r['security_id'] for r in universe)
    if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_ACCEPTED_SECURITY_ID')
    observations=[];bindings=[];anchors=[];events=[];transitions=[];fields=defaultdict(Counter);reasons=defaultdict(Counter);outputs=defaultdict(Counter);out_reasons=defaultdict(Counter)
    for security_id in ids:
        result=engine.evaluate(security_id);observations.append(result['observation']);bindings.append(result['bindings'])
        anchors.extend(result['anchors']);events.extend(result['events']);transitions.extend(result['transitions'])
        for name,fact in result['bindings']['fields'].items():
            fields[name][fact['quality']]+=1
            if engine.binder.fields[name]['field_role']=='BLOCKED_CAPABILITY':fields[name]['BLOCKED_CAPABILITY']+=1
            if fact['reason']:reasons[name][str(fact['reason'])]+=1
        for name,record in result['observation']['outputs'].items():
            outputs[name][record['state']]+=1
            for reason in record['reason']:out_reasons[name][reason]+=1
    summary=dict(trade_date=engine.trade_date,universe_count=len(ids),universe_binding=universe_ref,security_ids_digest=digest(ids),
        per_field={n:dict(KNOWN=fields[n]['KNOWN'],UNKNOWN=fields[n]['UNKNOWN'],BLOCKED_CAPABILITY=fields[n]['BLOCKED_CAPABILITY'],reason_counts=dict(reasons[n])) for n in sorted(fields)},
        per_output={n:dict(states=dict(outputs[n]),UNKNOWN_reason_distribution=dict(out_reasons[n])) for n in sorted(outputs)},
        anchors_created=len(anchors),events_created=len(events),support_observations=len(observations),acceptance_states=dict(outputs['acceptance']),
        prior_D1_history_status='NO_ACCEPTED_PRIOR_D1_PUBLICATION',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
        first_available_at_target_proven=False,raw_fallback_count=0,provider_replacement_count=0,V4_11_candidate_substitution_count=0,
        source_bindings=sorted(engine.binder.source_refs.values(),key=lambda r:r['path']))
    return summary,observations,bindings,anchors,events,transitions

def replay():
    readback=json.loads((ROOT/(OUT+'R10A_LOCAL_READBACK.json')).read_bytes());assert readback['status']=='PASS' and readback['entry']==bind(ENTRY)
    c=FrozenContracts(ROOT);engine=StructureEngine(c,'2026-09-30','2026-10-02T06:00:00+00:00')
    business=business_vectors(c);sequence=sequence_vectors(c);negative=negative_vectors(c,engine)
    assert all(r['status']=='PASS' for r in [business,sequence,negative]),json.dumps([business,sequence,negative],default=str)
    started=time.perf_counter();summary,observations,bindings,anchors,events,transitions=real_replay(c,engine);elapsed=time.perf_counter()-started
    store=CandidateStore(ROOT)
    refs=[]
    for name,rows,compressed in [('V4_12_D1_RUNTIME_CANDIDATE.jsonl',observations,False),('V4_12_INPUT_BINDING_CANDIDATE.jsonl.gz',bindings,True),
        ('V4_12_ANCHOR_CANDIDATE.jsonl',anchors,False),('V4_12_EVENT_CANDIDATE.jsonl',events,False),('V4_12_TRANSITION_CANDIDATE.jsonl',transitions,False)]:
        refs.append(store.jsonl(name,rows,compressed))
    for name,value in [('V4_12_SYNTHETIC_BUSINESS_PARITY',business),('V4_12_SYNTHETIC_SEQUENCE_PARITY',sequence),('V4_12_DAG_COORDINATE_NEGATIVE_PARITY',negative),
        ('V4_12_REAL_SCOPED_REPLAY',summary)]:refs.append(store.json(name+'.json',value))
    capability=dict(entry_binding=c.entry_ref,fields=[dict(field=r['field'],role=r['field_role'],capability=r['capability'],blocked_reason=r['blocked_reason'],target_publication_available=r['target_publication_available']) for r in c.config['field_registry']['fields']],
        blocked_anchor_types=[dict(anchor_type=r['anchor_type'],reason=r['blocked_reason']) for r in c.config['anchor_schema']['types'] if r.get('blocked_reason')],raw_fallback=False,prior_D1_history_status=summary['prior_D1_history_status'])
    refs.append(store.json('V4_12_RUNTIME_CAPABILITY_MATRIX.json',capability))
    refs.append(store.json('V4_12_CANDIDATE_SCHEMA_MANIFEST.json',dict(canonical_DB_write=False,migration=False,
        tables=dict(stock_structure_events=c.config['structure_event_contract']['event_required_fields'],stock_structure_anchors=c.config['anchor_schema']['required_fields'],
            stock_structure_event_transitions=['identity','state','quality','reason','prior_state_ref','anchor_ref','contract_digest'],structure_observations=list(observations[0])),frozen_schema_refs=[c.refs[n] for n in ['anchor_schema','output_schema']])))
    manifest=dict(contract_id='V4_12_D1_RUNTIME_CANDIDATE_MANIFEST_R1',status='ENGINEERING_CANDIDATE_NOT_ACCEPTED',entry=c.entry_ref,frozen_contract_digest=c.digest,
        trade_date='2026-09-30',cutoff=engine.cutoff,revision='r1',artifacts=refs,universe_count=len(observations),source_bindings=summary['source_bindings'],
        prior_D1_history_status=summary['prior_D1_history_status'],permissions=PERMISSIONS,Stage_head_advanced=False,Data_head_advanced=False)
    store.json('V4_12_RUNTIME_MANIFEST.json',manifest)
    # Persisted source readback and content-address equality are independently validated next.
    idempotency=dict(status='PASS',artifact_digests_before=[r['sha256'] for r in refs],artifact_digests_after=[store.jsonl(name,rows,compressed)['sha256'] for name,rows,compressed in [
        ('V4_12_D1_RUNTIME_CANDIDATE.jsonl',observations,False),('V4_12_INPUT_BINDING_CANDIDATE.jsonl.gz',bindings,True),('V4_12_ANCHOR_CANDIDATE.jsonl',anchors,False),('V4_12_EVENT_CANDIDATE.jsonl',events,False),('V4_12_TRANSITION_CANDIDATE.jsonl',transitions,False)]],
        immutable_conflict_policy='Existing different bytes rejected; prior revisions never overwritten')
    assert idempotency['artifact_digests_before'][:5]==idempotency['artifact_digests_after']
    store.json('V4_12_RUNTIME_IDEMPOTENCY.json',idempotency)
    peak=None
    try:
        import psutil
        info=psutil.Process().memory_info();peak=getattr(info,'peak_wset',info.rss)
    except ImportError:pass
    put(OUT+'V4_12_RUNTIME_PERFORMANCE.json',dict(full_universe_rows=len(observations),wall_clock_seconds=elapsed,peak_memory_bytes=peak,
        artifact_bytes=sum(r['bytes'] for r in refs),complexity='Indexed accepted-source lookup O(universe * registered fields), no universe cross-product'))
    print(json.dumps(dict(universe_count=len(observations),anchors_created=len(anchors),events_created=len(events),business_vectors=business['total'],sequence_steps=sequence['total'],wall_clock_seconds=elapsed)))

if __name__=='__main__':replay()
