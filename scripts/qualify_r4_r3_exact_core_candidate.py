"""Separate new exact engineering algorithms from inherited accepted references."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
workspace=Path('G:/codex_tmp/r4_r3_pg_publication_v2').resolve()
run_id=sys.argv[1]
if not run_id.startswith('SOURCE_DERIVATION_R') or not run_id.replace('_','').isalnum():raise ValueError('VERSIONED_CANDIDATE_RUN_REQUIRED')
audit=ROOT/'docs/audits/r4_r3_consumers_20261011'/run_id
def digest(blob):return hashlib.sha256(blob).hexdigest()
def bound(binding):
    path=(workspace/binding['path']).resolve()
    if not path.is_relative_to(workspace) or digest(path.read_bytes())!=binding['sha256']:raise ValueError('EXACT_ENGINEERING_CANDIDATE_BINDING_REQUIRED')
    return path
result=json.loads((audit/'RESULT.json').read_bytes())
if result['production_changed'] or result['protected_before']!=result['protected_after']:raise ValueError('PROTECTED_AUTHORITY_MOVED')
original_binding=result['result']['candidate']
original=bound(original_binding)
candidate=json.loads(original.read_bytes())
receipt=json.loads(bound(candidate['day_receipt']).read_bytes())
freeze_binding=receipt['source_freeze'];freeze=json.loads(bound(freeze_binding).read_bytes())
specification=freeze['engineering_exact_adjustment_candidate']
if specification['contract']!='V4_OPERATIONAL_CORE_EXACT_AFFINE_CANDIDATE_R3' or specification['production_permission'] or specification['PIT_ELIGIBLE']:
    raise ValueError('EXACT_CANDIDATE_SCOPE_REQUIRED')
folder=workspace/'data/v4/exact_engineering_qualifications'/run_id
folder.mkdir(parents=True,exist_ok=False)
actual=[]
for relative,expected in specification['executed_sources'].items():
    source=(ROOT/relative).resolve()
    if not source.is_relative_to(ROOT/'src') or source.suffix!='.py':raise ValueError('CANDIDATE_SOURCE_SCOPE_INVALID')
    blob=source.read_bytes()
    if digest(blob)!=expected:raise ValueError('ACTUAL_CANDIDATE_SOURCE_MOVED')
    target=folder/'sources'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
    actual.append(dict(path=target.relative_to(workspace).as_posix(),sha256=expected,bytes=len(blob)))
contract=ROOT/'config/v4_operational_core_exact_candidate_r3.json'
contract_path=folder/'CONTRACT.json';contract_path.write_bytes(contract.read_bytes())
qualified=dict(candidate)
qualified['contract_id']='R4_R3_EXACT_CORE_ENGINEERING_CANDIDATE_QUALIFICATION_V1'
qualified['authority_mode']='ISOLATED_ENGINEERING_CANDIDATE_NO_EXTERNAL_ACCEPTANCE'
qualified['inherited_accepted_algorithm_bindings']=qualified.pop('accepted_algorithm_bindings',[])
qualified['inherited_builder_registry']=qualified.pop('registry')
qualified['candidate_algorithm_bindings']=actual
qualified['candidate_contract']=dict(path=contract_path.relative_to(workspace).as_posix(),sha256=digest(contract_path.read_bytes()),bytes=contract_path.stat().st_size)
qualified['original_derivation_candidate']=original_binding
qualified['acceptance']='ENGINEERING_CANDIDATE_ONLY'
qualified['permissions']=dict(production=False,shadow=False,focus_cutover=False)
qualified['PIT_ELIGIBLE']=False
qualified['external_acceptance']='NOT_GRANTED'
qualified['qualification_limitations']=['Inherited accepted references remain historical evidence and do not accept the new kernel.',
    'The original candidate replaces only its target-date owners; inherited dates do not acquire exact-candidate numerical acceptance.',
    'Every actual candidate history window and all real consumers require separate independent numerical evidence.']
target=folder/'QUALIFIED_CANDIDATE.json'
target.write_text(json.dumps(qualified,indent=2)+'\n',encoding='utf8')
record=dict(contract='R4_R3_EXACT_CORE_ENGINEERING_CANDIDATE_QUALIFICATION_V1',original_candidate=original_binding,
    qualified_candidate=dict(path=target.relative_to(workspace).as_posix(),sha256=digest(target.read_bytes()),bytes=target.stat().st_size),
    candidate_algorithm_bindings=actual,original_candidate_unchanged=digest(original.read_bytes())==original_binding['sha256'],
    all_numerical_and_consumer_acceptance='OPEN',production_changed=False)
output=audit/'EXACT_CANDIDATE_AUTHORITY_QUALIFICATION_R1.json'
if output.exists():raise ValueError('RETAIN_EXISTING_QUALIFICATION_EVIDENCE')
output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps(record))
