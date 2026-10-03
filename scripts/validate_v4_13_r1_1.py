"""Independent semantic/authority gate. No runtime implementation imports."""
import json,hashlib,subprocess
from copy import deepcopy
from scripts.repair_v4_13_r1_1 import ROOT,P,OUT,BASE,read,ref,exact,write
from src.workbench_analysis.historical_stage_governance_r17 import resolve as historical_resolve,current_state,registry,STAGE
QUALITIES=['KNOWN','UNKNOWN','NOT_IMPLEMENTED','NOT_APPLICABLE','DEGRADED']
# Independent literal oracle for metadata quality, not business state logic.
PAIR_ROWS=[['KNOWN','DEGRADED','DEGRADED','DEGRADED','DEGRADED'],['DEGRADED','UNKNOWN','UNKNOWN','UNKNOWN','DEGRADED'],['DEGRADED','UNKNOWN','NOT_IMPLEMENTED','NOT_IMPLEMENTED','DEGRADED'],['DEGRADED','UNKNOWN','NOT_IMPLEMENTED','NOT_APPLICABLE','DEGRADED'],['DEGRADED','DEGRADED','DEGRADED','DEGRADED','DEGRADED']]
EXPECTED_PAIRS={a+'|'+b:PAIR_ROWS[i][j] for i,a in enumerate(QUALITIES) for j,b in enumerate(QUALITIES)}
FIRST_INTRODUCED={'SECTOR_CONTEXT_STATE_V1','ROTATION_STRUCTURE_ENRICHMENT_V1'}
def validate_lineage(obj):
 if obj['contract_id'] in FIRST_INTRODUCED:
  assert 'supersedes' not in obj, 'FALSE_SUPERSEDES_FIRST_INTRODUCTION'
  assert obj.get('introduced_in')=='V4_13_R1_1_CONTRACT_REPAIR' and obj.get('derived_from'), 'INTRODUCED_DERIVED_LINEAGE_REQUIRED'
  for source in obj['derived_from']:exact(source)
 elif 'supersedes' in obj:
  predecessor=json.loads(exact(obj['supersedes']))
  assert predecessor['contract_id']==obj['contract_id'], 'SUPERSEDES_CONTRACT_ID_MISMATCH'
  def semver(value):
   parts=value.split('.');assert len(parts)==3 and all(p.isdigit() for p in parts), 'SEMVER_REQUIRED'
   return tuple(map(int,parts))
  assert semver(obj['version'])>semver(predecessor['version']), 'VERSION_MUST_INCREASE'
 return True

def get(n):return read(P+n+'_v1_1.json')
def prove_membership_scope(route):
 try:
  stage=json.loads(exact(route['stage_binding']));sector=json.loads(exact(route['sector_owner']));member=json.loads(exact(route['membership_owner']))
  assert stage['v4_08_binding']['path']==route['sector_owner']['path'] and stage['v4_08_binding']['sha256']==route['sector_owner']['sha256']
  assert sector['membership_binding']['path']==route['membership_owner']['path'] and sector['membership_binding']['sha256']==route['membership_owner']['sha256'];exact(sector['membership_binding'])
  assert sector['capabilities']['ACCEPTED_CONTEXT_ROUTING']=='ENGINEERING_ACCEPTED'
  assert member['head_id']=='V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1' and member['status']=='ACCEPTED' and member['external_acceptance']=='EXTERNALLY_ACCEPTED'
  assert member['membership_acceptance_scope']=='FORWARD_PIT_MEMBERSHIP_ONLY'
  assert sector['production_permission'] is False and route['production_permission'] is False
  assert route['consumer']=='V4_13_SCOPED_ENGINEERING_ONLY' and route['formal_consumers_flag_override'] is False
  assert route['current_membership_replay_claimed_pit'] is False
  assert not route['provider_direct_read'] and not route['raw_fallback'] and not route['current_membership_silent_fallback']
  for n in ['snapshot','facts','source_revision']:exact(member[n])
  snapshot=json.loads(exact(member['snapshot']));assert snapshot['membership_basis']=='PIT_OBSERVED' and snapshot['target_trade_date']=='2026-09-30' and snapshot['snapshot_id']==member['membership_snapshot_id']
  return dict(snapshot_metadata={k:snapshot[k] for k in ['snapshot_id','target_trade_date','cutoff','membership_basis','membership_quality','source_revision_id']},status='ENGINEERING_CONSUMER_SCOPE_PROVEN',path=[route['consumer'],route['sector_owner'],sector['membership_binding'],route['membership_owner']],membership_scope=member['membership_acceptance_scope'],formal_consumers_enabled=member['formal_consumers_enabled'],production=False)
 except (AssertionError,KeyError,FileNotFoundError):return dict(status='BLOCKED_MEMBERSHIP_CONSUMER_SCOPE',production=False,provider_fallback=False)
def audit_bundle(bundle):
 fields=bundle['field_registry']['fields'];by={r['field']:r for r in fields};times={r['field']:r for r in bundle['time_role_registry']['fields']};route=bundle['membership_consumer_route']
 assert prove_membership_scope(route)['status']=='ENGINEERING_CONSUMER_SCOPE_PROVEN'
 for f in ['primary_industry','supporting_concepts']:
  r=by[f];assert r['time_role']==times[f]['role']=='T_EXACT_MEMBERSHIP_AT_CUTOFF'
  assert r['dependencies']['history']==times[f]['history_dependencies']==[] and r['loo_history_required'] is False
  assert times[f]['prior']=='NOT_REQUIRED_FOR_THIS_FIELD' and r['missing']=='UNKNOWN_VALUE_NULL_NOT_EMPTY_ARRAY'
  assert r['source_binding']==route['membership_owner'] and r['consumer_route']==ref(P+'membership_consumer_route_v1_1.json')
 assert 'loo_history' not in bundle['input_schema']['required']
 schema=bundle['sector_context_state_schema'];required={'selected_sector_id','sector_type','loo_b0_raw','loo_confirmed_raw','loo_warm_raw','emergence','adjusted_seed_width','rotation_core_state','relative_sector_state','membership_basis','context_quality','reasons','source_refs'}
 assert set(schema['required'])==required and schema['semantic']=='LOSSLESS_SELECTED_LOO_CONTEXT_SNAPSHOT_NO_NEW_SCORE_OR_STATE_MACHINE'
 assert by['sector_context_state']['data_type']=='object_or_null' and by['sector_context_state']['object_schema']==ref(P+'sector_context_state_schema_v1_1.json')
 assert set(schema['properties'])==required and schema['additionalProperties'] is False
 assert set(schema['components'])==required-{'selected_sector_id','sector_type','membership_basis','context_quality','reasons','source_refs'}
 assert bundle['quality_map']['component_pair_table']==EXPECTED_PAIRS
 edges=bundle['dag_edge_registry']['edges'];context_edges={e['field']:e for e in edges if e['consumer']=='CONTEXT'}
 assert 'accepted_membership_and_non_target_primitives' not in context_edges
 owners={'date_valid_membership':route['membership_owner']['path'],'non_target_core_facts':'data/v4/V4_04_ACCEPTED_HEAD.json','non_target_native_facts':'data/v4/V4_05_ACCEPTED_HEAD.json','non_target_base_seed_raw':'data/v4/V4_07_ACCEPTED_HEAD.json'}
 for f,path in owners.items():assert context_edges[f]['source_owner_binding']['path']==path;exact(context_edges[f]['source_owner_binding'])
 assert context_edges['date_valid_membership']['consumer_route']==ref(P+'membership_consumer_route_v1_1.json')
 for e in edges:
  if e['field'] in ['base_seed_raw','base_seed_aggregates','non_target_base_seed_raw']:assert e['source_owner_binding']['path']=='data/v4/V4_07_ACCEPTED_HEAD.json'
 for r in bundle['field_registry']['input_fields']:
  if r['field']=='member_base_seed_raw':assert r['owner_binding']['path']=='data/v4/V4_07_ACCEPTED_HEAD.json'
 rotation=by['rotation_structure_enrichment'];dual=bundle['rotation_structure_enrichment_schema']['source_bindings']
 assert 'source_binding' not in rotation and rotation['source_bindings']==dual and len(dual)==2
 assert {r['role']:r['binding']['path'] for r in dual}=={'rotation_source':'data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json','structure_source':'data/v4/V4_12_ACCEPTED_HEAD.json'}
 for r in dual:exact(r['binding'])
 assert bundle['rotation_structure_enrichment_schema']['writeback_to_B1'] is False
 assert bundle['output_schema']['raw_qualification_mutable'] is False
 forbidden=bundle['dag_edge_registry']['forbidden_edges'];graph={}
 for e in edges:
  assert [e['producer'],e['consumer'],e['time_role']] not in forbidden
  if e['time_role']=='T':graph.setdefault(e['producer'],set()).add(e['consumer'])
 def reach(start):
  seen=set();todo=list(graph.get(start,[]))
  while todo:
   n=todo.pop()
   if n not in seen:seen.add(n);todo.extend(graph.get(n,[]))
  return seen
 assert not {'A','C'}&reach('CONTEXT') and not {'B0','B1','B2','D1'}&reach('D1') and 'D1' not in reach('D2')
 return True
def load_bundle():return {n:get(n) for n in ['field_registry','time_role_registry','producer_registry','input_schema','output_schema','quality_map','loo_context','dag_edge_registry','projection','parameter_set','machine_vectors','membership_consumer_route','sector_context_state_schema','rotation_structure_enrichment_schema']}
def combine(qualities,table):
 assert qualities;result=qualities[0]
 for quality in qualities[1:]:result=table[result+'|'+quality]
 return result
def vector_actual(v,bundle):
 i=deepcopy(v['input']);kind=v['kind'];rows={r['field']:r for r in bundle['field_registry']['fields']};table=bundle['quality_map']['component_pair_table']
 if kind=='relationships':
  assert not rows['primary_industry']['dependencies']['history'] and not rows['supporting_concepts']['dependencies']['history']
  known=i['membership_quality']=='KNOWN';return dict(primary_industry=dict(value=i['industry'] if known else None,quality='KNOWN' if known else 'UNKNOWN'),supporting_concepts=dict(value=i['concepts'] if known else None,quality='KNOWN' if known else 'UNKNOWN'))
 if kind=='dependencies':return {f:'UNKNOWN' if r['dependencies']['history'] and i['loo_history'] is None else 'KNOWN' for f,r in rows.items() if f in ['primary_industry','supporting_concepts','algorithmic_support_sector','relative_sector_state']}
 if kind=='sector_snapshot':
  schema=bundle['sector_context_state_schema'];assert set(i)==set(schema['required'])
  for name,c in schema['components'].items():
   item=i[name];assert set(item)==set(c['required']) and item['quality'] in c['quality_values']
   for r in item['source_refs']:assert all(k in r for k in c['source_refs_required']) and r['sector_id']==i['selected_sector_id']
   if item['quality'] in ['UNKNOWN','NOT_IMPLEMENTED']:assert item['value'] is None
  i['context_quality']=combine([i[n]['quality'] for n in schema['components']],table);return i
 if kind=='membership_authority':return dict(membership_owner=bundle['membership_consumer_route']['membership_owner']['path'],scope=prove_membership_scope(bundle['membership_consumer_route'])['status'],production=False)
 if kind in ['core_authority','seed_authority']:
  wanted=['non_target_core_facts','non_target_native_facts'] if kind=='core_authority' else ['non_target_base_seed_raw'];return {e['field']:e['source_owner_binding']['path'] for e in bundle['dag_edge_registry']['edges'] if e['field'] in wanted}
 if kind=='dual_binding':return {r['role']:r['binding']['path'] for r in rows['rotation_structure_enrichment']['source_bindings']}
 if kind=='enrichment':i['combined_quality']=table[i['rotation_quality']+'|'+i['structure_quality']];return i
 if kind=='D1_perturbation':assert bundle['rotation_structure_enrichment_schema']['writeback_to_B1'] is False;return dict(B1_before=i['B1'],B1_after=i['B1'])
 if kind=='context_perturbation':assert bundle['output_schema']['raw_qualification_mutable'] is False;return dict(A=i['A'],C=i['C'])
 if kind=='predecessor':return dict(predecessors=[max(d for d in i['calendar'] if d<i['target']) for _ in i['revisions']])
 raise AssertionError(kind)
def negatives(bundle):
 cases=[]
 for f in ['primary_industry','supporting_concepts']:
  b=deepcopy(bundle);next(r for r in b['field_registry']['fields'] if r['field']==f)['dependencies']['history']=['t-1'];cases.append((f+'_history',b))
 b=deepcopy(bundle);b['membership_consumer_route']['membership_owner']=ref('data/v4/V4_04_ACCEPTED_HEAD.json');cases.append(('wrong_membership_owner',b))
 b=deepcopy(bundle);b['membership_consumer_route']['provider_direct_read']=True;cases.append(('provider_bypass',b))
 b=deepcopy(bundle);next(e for e in b['dag_edge_registry']['edges'] if e['field']=='non_target_base_seed_raw')['source_owner_binding']=ref('data/v4/V4_04_ACCEPTED_HEAD.json');cases.append(('seed_owned_by_core',b))
 b=deepcopy(bundle);next(r for r in b['field_registry']['fields'] if r['field']=='rotation_structure_enrichment')['source_bindings'].pop();cases.append(('single_source_enrichment',b))
 b=deepcopy(bundle);b['sector_context_state_schema']['required']=[];cases.append(('undefined_context_object',b))
 b=deepcopy(bundle);b['output_schema']['raw_qualification_mutable']=True;cases.append(('context_changes_qualification',b))
 for a,c in [('D1','B0'),('D1','B1'),('D1','B2'),('D2','D1')]:
  b=deepcopy(bundle);b['dag_edge_registry']['edges'].append(dict(producer=a,consumer=c,field='forbidden',time_role='T'));cases.append((a+'_to_'+c,b))
 b=deepcopy(bundle);next(r for r in b['field_registry']['fields'] if r['field']=='supporting_concepts')['missing']='EMPTY_ARRAY';cases.append(('unknown_to_empty',b))
 b=deepcopy(bundle);b['membership_consumer_route']['formal_consumers_flag_override']=True;cases.append(('current_membership_claimed_pit_or_formal_override',b))
 b=deepcopy(bundle);b['membership_consumer_route']['current_membership_replay_claimed_pit']=True;cases.append(('current_replay_claimed_pit',b))
 proofs=[]
 for name,b in cases:
  try:audit_bundle(b)
  except (AssertionError,KeyError):proofs.append(dict(id=name,result='REJECTED'));continue
  raise AssertionError('NEGATIVE_ACCEPTED:'+name)
 return proofs
def validate(checkout=False):
 amendment=read(OUT+'V4_13_CONTRACT_AMENDMENT_R1_1.json')
 for r in amendment['contracts']:exact(r)
 bundle=load_bundle();audit_bundle(bundle)
 for n,obj in bundle.items():
  validate_lineage(obj)
  assert obj['runtime_implemented'] is False
 proofs=[]
 for v in bundle['machine_vectors']['vectors']:
  actual=vector_actual(v,bundle);assert actual==v['expected'],(v['id'],actual,v['expected']);proofs.append(dict(id=v['id'],alias=v.get('alias'),status='PASS'))
 rejection=negatives(bundle);matrix=[];producers={p['producer_contract_id'] for p in bundle['producer_registry']['producers']};roles={r['field']:r for r in bundle['time_role_registry']['fields']}
 for row in bundle['field_registry']['fields']:
  assert all(row.get(k) for k in ['semantic_definition','data_type','producer_contract_id','time_role','quality_propagation','missing','runtime_capability','consumer_scope'])
  assert row['producer_contract_id'] in producers and row['time_role']==roles[row['field']]['role']
  sources=[r['binding'] for r in row['source_bindings']] if 'source_bindings' in row else [row['source_binding']]
  for r in sources:exact(r)
  if row['data_type'] in ['object','object_or_null']:
   assert 'object_schema' in row or row['field']=='anchor_view_asof_t'
   if 'object_schema' in row:exact(row['object_schema'])
  matrix.append(dict(field=row['field'],semantic_definition='FROZEN',data_type_and_schema='FROZEN',producer='FROZEN',source_bindings='FROZEN',time_role='FROZEN',quality_propagation='FROZEN',unknown_not_applicable='FROZEN',consumer_scope='FROZEN',runtime_capability='BLOCKED_WITH_EXPLICIT_REASON',reason='V4_13_RUNTIME_NOT_AUTHORIZED'))
 protected=[]
 for r in read(OUT+'R15_STAGE_CONTRACT.json')['protected']:
  actual=ref(r['path'])
  archived=next((row for row in registry(ROOT)['source_archives'] if row['original_namespace']==r),None)
  if r['path']==STAGE or archived:
   historical=historical_resolve(ROOT,r,source=bool(archived)).read_bytes()
   assert hashlib.sha256(historical).hexdigest()==r['sha256']
   protected.append(dict(path=r['path'],before=r['sha256'],after=r['sha256'],unchanged=True,comparison='EXPLICIT_IMMUTABLE_HISTORICAL_ARCHIVE',current_sha256=actual['sha256']))
  elif checkout and r['path'].startswith('src/') and actual['sha256']!=r['sha256']:
   baseline=subprocess.check_output(['git','show',BASE+':'+r['path']],cwd=ROOT)
   assert (ROOT/r['path']).read_bytes()==baseline
   protected.append(dict(path=r['path'],before=r['sha256'],after=actual['sha256'],unchanged=True,comparison='EXACT_GIT_BASELINE_BLOB',main_checkout_line_endings='RECORDED_SEPARATELY_NO_SOURCE_EDIT'))
  else:
   exact(r);protected.append(dict(path=r['path'],before=r['sha256'],after=actual['sha256'],unchanged=True,comparison='EXACT_BYTES'))
 assert json.loads(historical_resolve(ROOT,dict(path=STAGE,sha256='b0e1c2402efdd71d706a87f45280206a87fbe9e637a4168255b7ff4c036520f7')).read_bytes())['accepted_stage_range']=='V4_00_TO_V4_12_ACCEPTED'
 assert subprocess.run(['git','cat-file','-e',registry(ROOT)['baseline']+':data/v4/V4_13_ACCEPTED_HEAD.json'],cwd=ROOT,capture_output=True).returncode!=0
 current_state(ROOT)
 changed=subprocess.check_output(['git','diff',BASE,registry(ROOT)['baseline'],'--name-only'],cwd=ROOT,text=True).splitlines()
 # R16 external acceptance authorizes only new scoped runtime files; frozen contracts stay design-authoritative.
 authorized=[]
 entry=ROOT/'reports/v4_13_runtime_r16/STAGE_CONTRACT.json'
 if entry.exists():
  stage=read('reports/v4_13_runtime_r16/STAGE_CONTRACT.json');authority=exact(stage['authority'])
  assert b'PASS_FULL_CONTRACT_FREEZE' in authority and b'AUTHORIZED_NEXT_SCOPED_ENGINEERING' in authority
  authorized=stage['runtime_files']
  assert all(p.startswith('src/workbench_analysis/v4_13_') for p in authorized)
  for p in authorized:
   assert subprocess.run(['git','cat-file','-e',stage['baseline']+':'+p],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
 assert not any(p.startswith(('src/','migrations/','data/')) and p not in authorized for p in changed)
 return dict(V4_13_R1_1_CONTRACT_SEMANTIC_AUTHORITY_REPAIR='PASS',V4_13_CONTRACT_COMPLETENESS='PASS_READY_FOR_EXTERNAL_AUDIT',V4_13_RUNTIME='NOT_IMPLEMENTED',membership_consumer_scope=prove_membership_scope(bundle['membership_consumer_route']),vectors=proofs,negative_gates=rejection,component_quality_matrix_cases=25,completeness_matrix=matrix,protected=protected,production=False,shadow=False,focus=False,global_mandatory_adoption=False,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
if __name__=='__main__':
 result=validate();write(OUT+'R15_LOCAL_INDEPENDENT_CONTRACT_GATE.json',result);print('V4_13_CONTRACT_COMPLETENESS=PASS_READY_FOR_EXTERNAL_AUDIT')
