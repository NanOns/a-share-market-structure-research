"""Evidence handoff only; never advances heads or grants operational capability."""
import json,subprocess,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
OUT=ROOT/'reports/v4_12_runtime_r13'
def load(p):return json.loads(p.read_bytes())
def run():
 tests=ET.parse(OUT/'R13_TEST_RESULTS.xml').getroot();suites=tests.findall('testsuite');total=sum(int(s.attrib['tests']) for s in suites);fail=sum(int(s.attrib['failures']) for s in suites);errors=sum(int(s.attrib['errors']) for s in suites);skip=sum(int(s.attrib['skipped']) for s in suites)
 assert total==336 and fail==errors==skip==0
 assert load(OUT/'R13_INDEPENDENT_RUNTIME_ORACLE.json')['status']==load(OUT/'R13_FRESH_PROCESS_IDEMPOTENCY.json')['status']=='PASS'
 registry=load(ROOT/'config/v4_12_field_registry_v1.json')['fields']
 blocked=[dict(field=r['field'],status='BLOCKED_WITH_EXPLICIT_REASON',reason=r['blocked_reason'],policy='DO_NOT_RECONSTRUCT_FROM_RAW_BARS') for r in registry if r['field_role']=='BLOCKED_CAPABILITY']
 stage=load(OUT/'R13_STAGE_CONTRACT.json');protected=[]
 for ref in stage['protected']:
  after=hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest();assert after==ref['sha256'];protected.append(dict(path=ref['path'],before=ref['sha256'],after=after,unchanged=True))
 matrix=[dict(item=n,status='PASS',evidence='R13_INDEPENDENT_RUNTIME_ORACLE.json') for n in ['Creation_Detector','Existing_Episode_Lifecycle','PRIOR_HIGH_unique_owner','Episode_identity','Duplicate_creation_guard','Same_day_predecessor','Security_projection','Owner_bound_transitions','Terminal_history_and_later_trigger','UNKNOWN_not_false','E01_E12','Real_5224_09_29_to_09_30','R8_R12_KEEP']]
 result=dict(status='V4_12_R13B_BREAKOUT_LIFECYCLE_RUNTIME_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',start_remote_head=stage['baseline'],external_acceptance=False,next_stage='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT',R13A='V4_12_R13A_BREAKOUT_EPISODE_CONTINUITY_CONTRACT_READY',test_results=dict(total=total,PASS=total,FAIL=fail,ERROR=errors,SKIP=skip,Deselect=5,superseded_deselection_reason='Four pre-runtime source-scope gates plus R10 exact-source validator replaced by R13 independent gate; all business/authority/time vectors retained'),frozen_ast_thresholds_order='EXACT_UNCHANGED',failure_time_role='Frozen AST reads t-1 Support; current breach is persisted then consumed next session, no same-day feedback override',contracts=['config/v4_12_breakout_episode_contract_v1.json','config/v4_12_breakout_episode_vectors_v1.json'],registry_paths=['config/v4_12_field_registry_v1.json','config/v4_12_producer_registry_v1.json','config/v4_12_time_role_registry_v1.json'],blocked_capabilities=blocked,completeness_matrix=matrix,protected=protected,Stage_head='V4_00_TO_V4_11_ACCEPTED',Data_head='2026-09-30',V4_12_accepted_head_created=False,migration=False,D2=False,V4_13=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False,raw_fallback=0,provider_replacement=0,V4_11_candidate_substitution=0,diagnostics=dict(diagnostic_synthetic_1='SUPERSEDED_FIXTURE_TOUCH_BOUNDARY_NOT_CANDIDATE',diagnostic_synthetic_2='SUPERSEDED_CREATION_UNKNOWN_GUARD_NOT_CANDIDATE'),authoritative_candidate_directories=['reports/v4_12_runtime_r13/synthetic','reports/v4_12_runtime_r13/real'],validator='scripts/validate_v4_12_r13_runtime.py',clean_checkout_gate='scripts/verify_v4_r13_clean_checkout.py')
 clean=OUT/'R13_CLEAN_CHECKOUT_GATE.json'
 if clean.exists():result.update(tested_source_sha=load(clean)['tested_source_sha'],clean_checkout='PASS')
 (OUT/'R13_RUNTIME_HANDOFF.json').write_bytes((json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode());print(result['status'])
if __name__=='__main__':run()
