"""Independent contract witnesses and graph audit; not a context/runtime producer."""
from copy import deepcopy
from statistics import median
import json,hashlib
from scripts.v4_12_promotion_r14 import ROOT,read,ref,exact,write
from scripts.validate_v4_12_promotion_r14 import validate as promotion
P='config/v4_13_';OUT='reports/v4_13_r1/'
def get(n):return read(P+n+'_v1.json')
def policy(v):
 forbidden=get('dag_edge_registry')['forbidden_edges']
 assert not v.get('self_including',False)
 assert not v.get('ui_first',False)
 assert not (v.get('membership_basis')=='CURRENT_MEMBERSHIP_REPLAY' and v.get('pit',False))
 assert not v.get('context_writes_raw',False)
 assert v.get('edge') not in forbidden
 assert not v.get('missing_as_false',False) and not v.get('unknown_as_weak',False)
 assert not v.get('display_cap_changes_set',False) and not v.get('recompute_structure',False)
def witnesses():
 vectors=get('machine_vectors')['vectors'];assert [v['id'] for v in vectors]==['L%02d'%i for i in range(1,13)]
 proofs=[]
 for vector in vectors:
  n=vector['id'];i=deepcopy(vector['input']);expected=vector['expected']
  if n=='L01':
   members=sorted(k for k in i['returns'] if k!=i['target']);actual=dict(loo_median=median(i['returns'][m] for m in members),seed_k=sum(i['seeds'][m] for m in members),member_n=len(members),excluded=i['target']);assert i['target'] not in members
  elif n=='L02':
   count=len(set(i['members'])-{i['target']});params=read('config/v4_08_algorithm_parameter_set_r5.json')['parameters'];minimum=next(p['value'] for p in params if p['parameter_id']=='V4_08_SECTOR_MIN_MEMBERS');assert count<minimum;actual=dict(remaining=count,quality='UNKNOWN_INSUFFICIENT_LOO_MEMBERS')
  elif n=='L03':
   industry=min(i['industries'],key=lambda x:(x['priority'],-x['depth'],x['id']));concepts=sorted(i['concepts']);cap=get('parameter_set')['parameters'][0]['value'];actual=dict(primary=industry['id'],concepts=concepts,display=concepts[:cap]);assert len(concepts)==10
  elif n=='L04':assert i['membership'] is None;actual=dict(value='UNKNOWN',missing_is_false=False)
  elif n=='L05':assert i['complete'] and not i['candidates'];actual=dict(value=None,quality='NOT_APPLICABLE')
  elif n=='L06':actual={k:get('quality_map')['map'][i['basis']][k] for k in ['value','pit','formal_context_eligible']}
  elif n=='L07':
   from scripts.v4_04_machine_executor_r4 import execute_rule
   contracts=read('config/v4_04_algorithm_contracts_v3.json');params=read('config/v4_04_parameter_set_v1.json');parameters={p['parameter_id']:p['value'] for p in params['parameters']}
   for old,new in get('loo_context')['relative_state']['field_substitution'].items():i[old]=i[new]
   actual=dict(relative_sector_state=execute_rule(contracts['rules'],'RELATIVE_STATE_V1',i,parameters),owner_contract='RELATIVE_STATE_V1')
  elif n=='L08':
   assert not get('output_schema')['raw_qualification_mutable'];actual={k:i[k] for k in ['raw_A','raw_C']}
  elif n=='L09':
   assert ['D1','B0','T'] in get('dag_edge_registry')['forbidden_edges'];actual={k:i[k] for k in ['B0','B1','B2']}
  elif n=='L10':
   assert get('projection')['mode']=='COPY_VALUE_QUALITY_REASON_PRODUCER_IDENTITY_SOURCE_REF_NO_RECOMPUTATION';actual=dict(projected_before=deepcopy(i['source_before']),projected_after=deepcopy(i['source_after']),recompute=False)
  elif n=='L11':actual=dict(predecessors=[max(d for d in i['calendar'] if d<i['date']) for _ in i['revisions']])
  else:
   old=deepcopy(i['old']);before=hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest();history=[old,deepcopy(i['correction'])];assert before==hashlib.sha256(json.dumps(history[0],sort_keys=True).encode()).hexdigest();actual=dict(old=history[0],new=history[1],append_only=True)
  assert actual==expected,(n,actual,expected);proofs.append(dict(id=n,status='PASS',actual=actual))
 return proofs
def validate():
 assert promotion(post=True)['status']=='PASS'
 entry=read(OUT+'V4_13_STAGE_ENTRY.json');assert entry['status']=='AUTHORIZED_CONTRACT_DESIGN_ONLY' and entry['runtime_implemented'] is False
 for r in entry['contracts']:exact(r)
 fields=get('field_registry')['fields'];required=set(get('output_schema')['fields']);assert {r['field'] for r in fields}==required
 producer=get('producer_registry')['producers'];assert {r['producer_contract_id'] for r in fields}=={r['producer_contract_id'] for r in producer}
 assert {r['field'] for r in get('time_role_registry')['fields']}==required
 assert all(r['required'] and not r['raw_reconstruction'] and r['source_field'] and r['time_role'] and r['publication_namespace'] for r in fields)
 for r in fields:exact(r['source_binding'])
 loo=get('loo_context');assert len(loo['recipe'])==7 and 'REMOVE_TARGET_FROM_EVERY_SECTOR_BEFORE_ALL_CALCULATIONS' in loo['recipe']
 exact(loo['relative_state']['owner']);assert loo['relative_state']['rule_pointer']=='/rules/RELATIVE_STATE_V1'
 dag=get('dag_edge_registry');edges=dag['edges'];graph={}
 for edge in edges:
  assert all(k in edge for k in ['producer','consumer','field','time_role','contract_id','version','required','namespace','quality_propagation'])
  if edge['time_role']=='T':graph.setdefault(edge['producer'],set()).add(edge['consumer'])
 def reachable(start):
  found=set();todo=list(graph.get(start,[]))
  while todo:
   node=todo.pop()
   if node not in found:found.add(node);todo+=list(graph.get(node,[]))
  return found
 assert not ({'A','C'}&reachable('CONTEXT')) and not ({'B0','B1','B2','D1'}&reachable('D1')) and 'D1' not in reachable('D2')
 assert {'A','B0','B1','B2','C','D0','D1','D2','CONTEXT'}<=set(e['producer'] for e in edges)|set(e['consumer'] for e in edges)
 negatives=[dict(self_including=True),dict(ui_first=True),dict(membership_basis='CURRENT_MEMBERSHIP_REPLAY',pit=True),dict(context_writes_raw=True),dict(edge=['D1','B0','T']),dict(edge=['D2','D1','T']),dict(missing_as_false=True),dict(unknown_as_weak=True),dict(display_cap_changes_set=True),dict(recompute_structure=True)]
 for negative in negatives:
  try:policy(negative)
  except AssertionError:continue
  raise AssertionError(negative)
 proofs=witnesses()
 return dict(status='PASS',V4_13_R1_PROFILE_ADVANCED_PROJECTION_CONTRACT_FREEZE='PASS',V4_13_RUNTIME='NOT_IMPLEMENTED',NEXT='V4_13_RUNTIME_IMPLEMENTATION_TASKS_AFTER_EXTERNAL_AUDIT',contracts=entry['contracts'],independent_vectors=proofs,negative_gate_rejections=len(negatives),dag_edges=len(edges),dag_isolation='PASS',required_fields=sorted(required),completeness_matrix=[dict(component=n,status='PASS',binding=ref(P+n+'_v1.json')) for n in ['field_registry','producer_registry','time_role_registry','input_schema','output_schema','loo_context','projection','dag_edge_registry','quality_map','machine_vectors','parameter_set']],blocked_capabilities=[dict(capability='V4_13_LOO_CONTEXT_PRODUCER',status='BLOCKED_WITH_EXPLICIT_REASON',reason='V4_13_RUNTIME_NOT_AUTHORIZED'),dict(capability='HISTORICAL_PIT_LOO_CONTEXT',status='BLOCKED_WITH_EXPLICIT_REASON',reason='NO_DATE_VALID_ACCEPTED_MEMBERSHIP_OR_COMPLETE_LOO_HISTORY_WHEN_UNAVAILABLE'),dict(capability='structure_health_projection_when_not_published',status='BLOCKED_WITH_EXPLICIT_REASON',reason='NO_ACCEPTED_OWNER_FIELD_PUBLICATION_DO_NOT_DERIVE_FROM_SUPPORT')],production=False,shadow=False,focus=False,global_mandatory_adoption=False)
if __name__=='__main__':
 result=validate();write(OUT+'V4_13_CONTRACT_COMPLETENESS_GATE.json',result);print('V4_13_R1_PROFILE_ADVANCED_PROJECTION_CONTRACT_FREEZE=PASS')
