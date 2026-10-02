"""Versioned R15 contract repair only. Never calls promotion or runtime."""
import argparse,json,hashlib,subprocess,os,tempfile
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1]
BASE='226270c3178736e9b52e0e3574339039ed191350'
OUT='reports/v4_13_r1_1/'
ARCH='docs/evidence/next_round_r15/'
P='config/v4_13_'
Q=['KNOWN','UNKNOWN','NOT_IMPLEMENTED','NOT_APPLICABLE','DEGRADED']
def read(p):return json.loads((ROOT/p).read_bytes())
def ref(p):
 b=(ROOT/p).read_bytes();return dict(path=p,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def exact(r):
 p=(ROOT/r['path']).resolve();assert p.is_relative_to(ROOT.resolve());b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r.get('bytes',r.get('byte_count')),r['path'];return b
def write(p,v,raw=False):
 b=v if raw else (json.dumps(v,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode();target=ROOT/p;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and target.read_bytes()==b:return
 fd,tmp=tempfile.mkstemp(dir=target.parent,prefix='.r15-',suffix='.tmp')
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(tmp,target)
def new(name,obj):
 old=P+name+'_v1.json';obj=deepcopy(obj);obj.update(version='1.1.0',supersedes=ref(old),reason='R14_EXTERNAL_AUDIT_C01_C04_REPAIR',runtime_implemented=False)
 write(P+name+'_v1_1.json',obj)
def introduced_lineage(obj, sources):
 obj=deepcopy(obj);obj.pop('supersedes',None)
 obj['introduced_in']='V4_13_R1_1_CONTRACT_REPAIR'
 obj['derived_from']=[ref(p) for p in sources]
 return obj

def run(bundle):
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
 for n in ['V4_R14_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md','V4_NEXT_ROUND_EXECUTION_MASTER_R15_20261002.md','V4_13_R1_1_CONTRACT_SEMANTIC_AUTHORITY_REPAIR_TASK_20261002.md']:write(ARCH+n,(Path(bundle)/n).read_bytes(),True)
 write(ARCH+'.gitattributes',b'* -text\n',True);write(OUT+'.gitattributes',b'* -text\n',True)
 tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()
 protected=[p for p in tracked if p.startswith(('config/v4_13_','config/v4_12_','src/','reports/v4_12','reports/v4_13_r1/'))]+['AGENTS.md','data/v4/V4_12_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']
 write(OUT+'R15_STAGE_CONTRACT.json',dict(baseline=BASE,phase0=read('data/v4/V4_STAGE_ACCEPTED_HEAD.json')['phase0_status'],scope=['C01','C02','C03','C04'],upgrade=ref('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),sections=['20.1','20.2','20.3','20.4','41A.3','81.4','87A'],protected=[ref(p) for p in sorted(set(protected))],next='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT'))
 stage=read('data/v4/V4_STAGE_ACCEPTED_HEAD.json');sector_path=stage['v4_08_binding']['path'];sector=read(sector_path);membership_path=sector['membership_binding']['path']
 owners={n:ref(stage['v4_'+n+'_binding']['path']) for n in ['04','05','07','08','12']};owners['MEMBERSHIP']=ref(membership_path)
 old={p.stem[len('v4_13_'):-len('_v1')]:read(p.relative_to(ROOT).as_posix()) for p in (ROOT/'config').glob('v4_13_*_v1.json')}
 route=dict(contract_id='V4_13_ENGINEERING_MEMBERSHIP_CONSUMER_ROUTE_V1',version='1.0.0',runtime_implemented=False,consumer='V4_13_SCOPED_ENGINEERING_ONLY',stage_binding=ref('data/v4/V4_STAGE_ACCEPTED_HEAD.json'),sector_owner=owners['08'],membership_binding_pointer='/membership_binding',membership_owner=owners['MEMBERSHIP'],required_sector_capability={'ACCEPTED_CONTEXT_ROUTING':'ENGINEERING_ACCEPTED'},membership_scope='FORWARD_PIT_MEMBERSHIP_ONLY',formal_consumers_flag_override=False,production_permission=False,provider_direct_read=False,raw_fallback=False,current_membership_silent_fallback=False,failure='BLOCKED_MEMBERSHIP_CONSUMER_SCOPE',current_membership_replay_claimed_pit=False,snapshot_fields=['membership_snapshot_id','source_revision','trade_date','available_at','cutoff','membership_basis','membership_quality'])
 write(P+'membership_consumer_route_v1_1.json',route)
 table={}
 for a in Q:
  for b in Q:
   v=a if a==b else 'DEGRADED' if 'DEGRADED' in [a,b] or 'KNOWN' in [a,b] else 'UNKNOWN' if 'UNKNOWN' in [a,b] else 'NOT_IMPLEMENTED'
   table[a+'|'+b]=v
 quality=old['quality_map'];quality.update(component_quality_values=Q,component_pair_table=table,combine='COMMUTATIVE_TABLE_FOLD_OVER_DECLARED_COMPONENTS_METADATA_ONLY',component_values='COPY_UNCHANGED_NEVER_COERCE_UNKNOWN_OR_NOT_IMPLEMENTED_TO_FALSE',all_not_applicable='NOT_APPLICABLE',no_selected_sector='KNOWN_COMPLETE_NONE => value=null quality=NOT_APPLICABLE; uncertain selection never NOT_APPLICABLE',degradation_scope='ONLY_FIELD_OR_COMPONENT_WITH_ACTUAL_MISSING_DEPENDENCY')
 new('quality_map',quality)
 component=dict(type='object',required=['value','quality','reasons','source_refs'],quality_values=Q,source_refs_required=['path','sha256','bytes','producer_contract_id','trade_date','available_at','source_revision'],value='EXACT_SOURCE_VALUE_OR_NULL_FOR_UNAVAILABLE',quality='EXACT_SOURCE_QUALITY',reasons='LOSSLESS_SOURCE_REASONS',false_allowed='ONLY_KNOWN_BOOLEAN_FALSE')
 schema=dict(contract_id='SECTOR_CONTEXT_STATE_V1',version='1.0.0',supersedes=ref(P+'output_schema_v1.json'),reason='R14_EXTERNAL_AUDIT_C02_REPAIR',runtime_implemented=False,type='object_or_null',semantic='LOSSLESS_SELECTED_LOO_CONTEXT_SNAPSHOT_NO_NEW_SCORE_OR_STATE_MACHINE',required=['selected_sector_id','sector_type','loo_b0_raw','loo_confirmed_raw','loo_warm_raw','emergence','adjusted_seed_width','rotation_core_state','relative_sector_state','membership_basis','context_quality','reasons','source_refs'],components={n:deepcopy(component) for n in ['loo_b0_raw','loo_confirmed_raw','loo_warm_raw','emergence','adjusted_seed_width','rotation_core_state','relative_sector_state']},source_mapping={'selected_sector_id':'selected_context.sector_id','sector_type':'selected_context.sector_type','loo_b0_raw':'selected_context.b0_raw','loo_confirmed_raw':'selected_context.confirmed_raw','loo_warm_raw':'selected_context.warm_raw','emergence':'selected_context.emergence','adjusted_seed_width':'selected_context.adjusted_seed_width','rotation_core_state':'selected_context.rotation_core_state','relative_sector_state':'selected_context.relative_sector_state','membership_basis':'selected_context.membership_basis','reasons':'selected_context.reasons','source_refs':'selected_context.source_refs'},identity_rule='ALL_COMPONENT_SOURCE_REFS_BELONG_TO_SAME_SELECTED_SECTOR_TARGET_DATE_AND_LOO_LINEAGE',selection='COPY_SELECTION_IDENTITY_NEVER_CHOOSE_OR_UPGRADE_ELIGIBILITY',selection_unknown='NULL_ID_AND_UNKNOWN_UNBOUND_COMPONENTS; retain valid selected diagnostic snapshot when already published, never fabricate selection',no_eligible='KNOWN_COMPLETE_NO_ELIGIBLE => null/NOT_APPLICABLE',component_missing='OBJECT_REMAINS_AND_ONLY_COMPONENT_IS_UNKNOWN_OR_NOT_IMPLEMENTED',context_quality_rule=ref(P+'quality_map_v1_1.json'))
 schema['properties']={n:dict(type='object',required=c['required'],additionalProperties=False,properties={'value':{'type':['boolean','number','string','object','null'],'semantics':'EXACT_SOURCE_TYPE_NO_COERCION'},'quality':{'enum':Q},'reasons':{'type':'array','items':{'type':'string'}},'source_refs':{'type':'array','items':{'type':'object','required':c['source_refs_required']}}}) for n,c in schema['components'].items()}
 schema['properties'].update(selected_sector_id={'type':['string','null']},sector_type={'type':['string','null']},membership_basis={'enum':['PIT_OBSERVED','HISTORICAL_REPLAY_CURRENT_MEMBERSHIP','UNKNOWN']},context_quality={'enum':Q},reasons={'type':'array','items':{'type':'string'}},source_refs={'type':'array','items':{'type':'object','required':component['source_refs_required']}})
 schema['additionalProperties']=False
 schema=introduced_lineage(schema,[P+'output_schema_v1.json',P+'field_registry_v1.json'])
 write(P+'sector_context_state_schema_v1_1.json',schema)
 enrichment=dict(contract_id='ROTATION_STRUCTURE_ENRICHMENT_V1',version='1.0.0',supersedes=ref(P+'field_registry_v1.json'),reason='R14_EXTERNAL_AUDIT_C04_REPAIR',runtime_implemented=False,type='object',required=['rotation_core_state','rotation_quality','rotation_source_ref','structure_component','structure_quality','structure_source_ref','combined_quality','reasons'],source_bindings=[dict(role='rotation_source',binding=owners['08'],source_field='rotation_core_state',contract_binding=ref(sector['rotation_contract']['path'])),dict(role='structure_source',binding=owners['12'],source_field='READ_ONLY_AUTHORIZED_V4_12_STRUCTURE_PUBLICATION',publication_authority_pointer='/publication_authority/authorized_manifests')],quality_rule=ref(P+'quality_map_v1_1.json'),rotation='COPY_VALUE_AND_QUALITY_AND_SOURCE_REF_UNCHANGED',structure='COPY_EXISTING_V4_12_PROJECTION_COMPONENT_NO_RECOMPUTATION',structure_schema=ref(P+'projection_v1.json'),missing_structure='STRUCTURE_ONLY_UNKNOWN_OR_NOT_IMPLEMENTED; ROTATION_UNCHANGED',missing_rotation='ROTATION_ONLY_UNKNOWN_OR_NOT_IMPLEMENTED; STRUCTURE_UNCHANGED',combined='METADATA_ONLY_COMPONENT_PAIR_TABLE',writeback_to_B1=False)
 enrichment=introduced_lineage(enrichment,[P+'field_registry_v1.json',P+'dag_edge_registry_v1.json'])
 write(P+'rotation_structure_enrichment_schema_v1_1.json',enrichment)
 deps={
 'primary_industry':dict(time_role='T_EXACT_MEMBERSHIP_AT_CUTOFF',current=['trade_date_valid_membership','source_revision','available_at_le_cutoff','membership_quality'],history=[]),
 'supporting_concepts':dict(time_role='T_EXACT_MEMBERSHIP_AT_CUTOFF',current=['trade_date_valid_membership','source_revision','available_at_le_cutoff','membership_quality'],history=[]),
 'algorithmic_support_sector':dict(time_role='T_LOO_SELECTION_WITH_REGISTERED_HISTORY',current=['membership','loo_b0_raw','loo_confirmed_raw','loo_warm_raw','emergence','adjusted_seed_width'],history=['ACCEPTED_OWNER_REGISTERED_B0_B2_COMPARE_ENDPOINTS_AND_LOO_LINEAGE']),
 'relative_sector_state':dict(time_role='T_CURRENT_LOO_RETURNS_AND_ACCEPTED_CORE',current=['membership','non_target_ret1_ret5','accepted_stock_relative_required_fields'],history=[]),
 'sector_context_state':dict(time_role='T_READ_ONLY_SELECTED_LOO_SNAPSHOT',current=['selected_context_publication'],history=[],component_dependencies='ONLY_EACH_SOURCE_COMPONENT_REGISTERED_DEPENDENCIES'),
 'sector_context_quality':dict(time_role='T_COMPONENT_QUALITY_METADATA',current=['component_qualities','membership_basis'],history=[]),
 'rotation_structure_enrichment':dict(time_role='T_ROTATION_AND_READ_ONLY_D1',current=['rotation_publication','structure_publication'],history=[],component_dependencies='ROTATION_OWNER_HISTORY_AND_D1_OWNER_PREDECESSOR_STAY_IN_THEIR_OWN_LINEAGE')}
 field=old['field_registry']
 for row in field['fields']:
  f=row['field'];row.update(semantic_status='FROZEN',consumer_scope='CONTRACT_ONLY_SCOPED_ENGINEERING_NOT_PRODUCTION',quality_propagation='LOSSLESS_COMPONENT_QUALITY; missing affects actual dependency only')
  if f in deps:row.update(time_role=deps[f]['time_role'],dependencies=deps[f])
  if f in ['primary_industry','supporting_concepts']:
   row.update(producer_contract_id='MEMBERSHIP_RELATION_PROJECTION_V1',source_owner='V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1',source_binding=owners['MEMBERSHIP'],consumer_route=ref(P+'membership_consumer_route_v1_1.json'),data_type='nullable_sector_id' if f=='primary_industry' else 'nullable_array_sector_id',semantic='EXACT_CURRENT_DATE_DETERMINISTIC_RELATION_ONLY',missing='UNKNOWN_VALUE_NULL_NOT_EMPTY_ARRAY',not_applicable='ONLY_KNOWN_COMPLETE_NO_RELATION',loo_history_required=False)
  elif f=='sector_context_state':row.update(producer_contract_id='SECTOR_CONTEXT_STATE_V1',data_type='object_or_null',source_field='SELECTED_LOO_CONTEXT_LOSSLESS_SNAPSHOT',object_schema=ref(P+'sector_context_state_schema_v1_1.json'))
  elif f=='sector_context_quality':row.update(source_field='SECTOR_CONTEXT_STATE_V1.context_quality',producer_contract_id='SECTOR_CONTEXT_STATE_V1')
  elif f=='rotation_structure_enrichment':
   row.pop('source_binding',None);row.update(producer_contract_id='ROTATION_STRUCTURE_ENRICHMENT_V1',source_owner='DUAL_V4_08_ROTATION_AND_V4_12_STRUCTURE',source_field='DUAL_READ_ONLY_COMPONENTS',source_bindings=deepcopy(enrichment['source_bindings']),data_type='object',object_schema=ref(P+'rotation_structure_enrichment_schema_v1_1.json'))
  row['semantic_definition']=row.get('semantic',row.get('source_field'))
 for row in field['input_fields']:
  f=row['field']
  owner='07' if f=='member_base_seed_raw' else 'MEMBERSHIP' if f=='membership_snapshot' else '05' if f in ['member_ret1','member_ret5','member_ret20','member_amount','member_close'] else '04' if row['accepted_owner']=='V4_04' else '08'
  row.update(accepted_owner='V4_'+owner if owner!='MEMBERSHIP' else 'V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1',owner_binding=owners[owner],source_field='base_seed_raw' if owner=='07' else f.removeprefix('member_'),consumer_scope='SCOPED_ENGINEERING_ONLY',missing='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE')
  if owner=='MEMBERSHIP':row['consumer_route']=ref(P+'membership_consumer_route_v1_1.json')
 new('field_registry',field)
 times=old['time_role_registry']
 for row in times['fields']:
  if row['field'] in deps:
   d=deps[row['field']];row.update(role=d['time_role'],current_dependencies=d['current'],history_dependencies=d['history'],prior='NOT_REQUIRED_FOR_THIS_FIELD' if not d['history'] else 'EXACT_REGISTERED_PREVIOUS_SESSION_OR_K_LAG_ENDPOINT_NOT_SAME_DAY_REVISION',missing='DEGRADE_ONLY_DEPENDENT_FIELD_OR_COMPONENT')
 for row in times['input_fields']:
  if row['field']=='membership_snapshot':row['role']='T_EXACT_MEMBERSHIP_AT_CUTOFF'
 new('time_role_registry',times)
 loo=old['loo_context'];loo.update(membership_authority=owners['MEMBERSHIP'],membership_consumer_route=ref(P+'membership_consumer_route_v1_1.json'),accepted_owner_bindings={**loo['accepted_owner_bindings'],'V4_05':owners['05'],'V4_07':owners['07'],'V4_08_PIT_MEMBERSHIP':owners['MEMBERSHIP']},field_dependencies=deps,relationship_projection='CURRENT_MEMBERSHIP_ONLY_NOT_GATED_BY_LOO_HISTORY',base_seed_authority=owners['07'],sector_context_schema=ref(P+'sector_context_state_schema_v1_1.json'))
 new('loo_context',loo)
 inputs=old['input_schema'];inputs['required']=['security_id','trade_date','revision','cutoff','accepted_source_refs'];inputs.update(field_dependencies=deps,field_level_missing='UNKNOWN_ONLY_WHERE_ACTUAL_REQUIRED_DEPENDENCY_MISSING',membership_consumer_route=ref(P+'membership_consumer_route_v1_1.json'),core_owner_bindings=[owners['04'],owners['05']],seed_owner_binding=owners['07']);new('input_schema',inputs)
 output=old['output_schema'];output.update(object_schemas={'sector_context_state':ref(P+'sector_context_state_schema_v1_1.json'),'rotation_structure_enrichment':ref(P+'rotation_structure_enrichment_schema_v1_1.json')},field_dependencies=deps,current_membership_unknown='primary_industry=null/UNKNOWN; supporting_concepts=null/UNKNOWN, not []');new('output_schema',output)
 producers=old['producer_registry'];producers['producers']=[dict(producer_contract_id=id,outputs=outputs,runtime='NOT_IMPLEMENTED',source_authorities=bindings,operation=op) for id,outputs,bindings,op in [('MEMBERSHIP_RELATION_PROJECTION_V1',['primary_industry','supporting_concepts'],[owners['08'],owners['MEMBERSHIP']],'CURRENT_DATE_RELATION_ONLY'),('LOO_CONTEXT_V1',['algorithmic_support_sector','relative_sector_state'],[owners[n] for n in ['MEMBERSHIP','04','05','07','08']],'EXACT_OWNER_AST_TARGET_EXCLUDED'),('SECTOR_CONTEXT_STATE_V1',['sector_context_state','sector_context_quality'],[owners['08']],'LOSSLESS_CONTEXT_SNAPSHOT'),('ROTATION_STRUCTURE_ENRICHMENT_V1',['rotation_structure_enrichment'],[owners['08'],owners['12']],'LOSSLESS_DUAL_SOURCE_COMPONENTS'),('PROFILE_ADVANCED_PROJECTION_V1',old['projection']['fields'],[owners['12']],'LOSSLESS_READ_ONLY_STRUCTURE')]];new('producer_registry',producers)
 dag=old['dag_edge_registry'];edges=[]
 for edge in dag['edges']:
  if edge['field']=='accepted_membership_and_non_target_primitives':continue
  if edge['field'] in ['base_seed_raw','base_seed_aggregates']:edge.update(source_owner_binding=owners['07'],contract_binding=owners['07'],contract_id='BASE_SEED_V1',version='EXACT_V4_07_ACCEPTED_HEAD')
  if edge['consumer']=='CONTEXT' or edge['producer']=='CONTEXT':edge['contract_binding']=ref(P+'loo_context_v1_1.json')
  if edge['field']=='rotation_structure_enrichment':edge.update(source_bindings=deepcopy(enrichment['source_bindings']),contract_binding=ref(P+'rotation_structure_enrichment_schema_v1_1.json'),contract_id='ROTATION_STRUCTURE_ENRICHMENT_V1')
  edges.append(edge)
 template=dict(consumer='CONTEXT',time_role='T',version='EXACT_ACCEPTED_OWNER_SHA',required=True,namespace='LOO_TARGET_EXCLUDED_READ_ONLY',quality_propagation='UNKNOWN_NEVER_FALSE_COMPONENT_SCOPED',runtime_implemented=False,contract_binding=ref(P+'loo_context_v1_1.json'),contract_id='LOO_CONTEXT_V1')
 for producer,f,owner in [('MEMBERSHIP','date_valid_membership','MEMBERSHIP'),('CORE_V4_04','non_target_core_facts','04'),('NATIVE_V4_05','non_target_native_facts','05'),('BASE_SEED_V4_07','non_target_base_seed_raw','07')]:
  edge=dict(**template,producer=producer,field=f,source_owner_binding=owners[owner]);
  if owner=='MEMBERSHIP':edge['consumer_route']=ref(P+'membership_consumer_route_v1_1.json');edge['required_identity_metadata']=route['snapshot_fields']
  edges.append(edge)
 edges.append(dict(**template,producer='B1',field='rotation_core_state_read_only_for_enrichment',source_owner_binding=owners['08']))
 dag['edges']=edges;new('dag_edge_registry',dag)
 new('projection',old['projection']);new('parameter_set',old['parameter_set'])
 from scripts.v4_13_r15_vectors import VECTORS
 vector=old['machine_vectors'];vector.update(oracle='HAND_WRITTEN_R15_INDEPENDENT_CONTRACT_VECTORS',retained_R1_vectors=ref(P+'machine_vectors_v1.json'),vectors=VECTORS);new('machine_vectors',vector)
 files=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'config').glob('v4_13_*_v1_1.json'))
 write(OUT+'V4_13_CONTRACT_AMENDMENT_R1_1.json',dict(contract_id='V4_13_CONTRACT_AMENDMENT_R1_1',status='CONTRACT_REPAIR_CANDIDATE',version='1.1.0',stage_entry_parent=ref('reports/v4_13_r1/V4_13_STAGE_ENTRY.json'),accepted_parent=owners['12'],supersedes_contract_manifest=ref('reports/v4_13_r1/V4_13_STAGE_ENTRY.json'),contracts=[ref(p) for p in files],runtime_implemented=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False,next='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT'))
 print('R15_C01_C04_VERSIONED_CONTRACTS_PREPARED')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle-dir',required=True);run(p.parse_args().bundle_dir)
