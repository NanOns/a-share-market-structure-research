"""Join conserved independent receipts to the final current executable bindings.

Admission is current dated operational research only. It grants no historical
PIT, model permission, future settlement or Windows production acceptance.
"""
import hashlib,json,os
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_daily_exact_policy_v2 import verify as verify_policy,verify_loaded_versions
from workbench_analysis.operational_sealed_preparation_v1 import KEY,verify as verify_sealed
from workbench_analysis.operational_successor_v1 import validate

ROOT=Path('G:/codex work/v4-production-20261012')
REPO=Path(__file__).resolve().parents[1]
AUDIT=REPO/'docs/audits/v4_full_closeout_20261012/continuation_20261013'
SOURCE=AUDIT/'CURRENT_PUBLICATION_JOINT_AUDIT_R1'
OUT=ROOT/'data/v4/current_four_gate_admission_r1'

def load(path):return json.loads(Path(path).read_bytes())
def frozen(path):
    raw=Path(path).read_bytes();target=OUT/'receipts'/hashlib.sha256(raw).hexdigest()/Path(path).name
    if target.exists() and target.read_bytes()!=raw:raise ValueError('RECEIPT_ARCHIVE_CONFLICT')
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_suffix('.tmp');tmp.write_bytes(raw);os.replace(tmp,target)
    return ref(ROOT,target)
def passed(path,expected):
    doc=load(path)
    if doc.get('acceptance')!=expected:raise ValueError('RECEIPT_SCOPE_NOT_ACCEPTED:'+str(path))
    for key in ('error_count','type_error_count'):
        if doc.get(key,0)!=0:raise ValueError('UNRESOLVED_ERRORS:'+str(path))
    return frozen(path)

def main():
    result_path=SOURCE/'FOUR_GATE_ADMISSION_R1.json'
    if result_path.exists():raise ValueError('PRESERVE_PRIOR_ADMISSION')
    preparation=load(SOURCE/'UPDATED_CANDIDATE_SOURCE_PREPARATION_R2.json')
    candidate=load(checked(ROOT,preparation['candidate']))
    policy,binding=verify_policy(ROOT,preparation['policy'],candidate_only=True)
    verify_loaded_versions(policy['accepted_algorithm_bindings']+policy['component_source_bindings'])
    verify_sealed(ROOT,candidate,policy);validate(ROOT,candidate)
    pg=load(AUDIT/'PG_CURRENT_CANDIDATE_CONSUMER_R1/RESULT.json')
    old=load(checked(ROOT,pg['candidate']))
    for key in ('owners','source_registry','membership_snapshot','day_receipt','exact_daily_generation_scope','accepted_trade_date','published_sessions','native_pg_owner_authority','native_product_read_authority','native_membership_reference','native_profile_semantic_corrections','native_profile_dependent_corrections'):
        if candidate.get(key)!=old.get(key):raise ValueError('CURRENT_RECEIPT_INPUT_DRIFT:'+key)
    # Every original checked receipt must still have exactly the recorded bytes.
    receipt_index=[]
    for index in pg['receipt_index']:
        path=Path(index['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=index['sha256']:raise ValueError('PG_RECEIPT_DRIFT:'+index['name'])
        receipt_index.append(dict(name=index['name'],binding=frozen(path)))
    stage=load(AUDIT/'STAGE1_NUMERIC_CLOSEOUT_R1/RESULT.json')
    for evidence in stage['evidence']:
        if hashlib.sha256(Path(evidence['path']).read_bytes()).hexdigest()!=evidence['sha256']:raise ValueError('NUMERIC_RECEIPT_DRIFT')
    exact=load(AUDIT/'ORIGINAL56_DISPOSITION_R2/RESULT.json')
    rows=load(AUDIT/'ORIGINAL56_DISPOSITION_R2/MATRIX.json')
    if exact['denominator']!=56 or exact['unknown']!=0 or len(rows)!=56:raise ValueError('EXACT56_COMPLETE_SCOPE_REQUIRED')
    for row in rows:
        if hashlib.sha256((REPO/row['path']).read_bytes()).hexdigest()!=row['source_sha256']:raise ValueError('EXACT56_SOURCE_DRIFT')
    original_graph=load(Path('G:/codex_tmp/v4_full_closeout_20261012/ORIGINAL56_REACHABILITY_R4.json'))
    graph_path=Path('G:/codex_tmp/v4_full_closeout_20261012/CURRENT_JOINT_EXACT56_SOURCE_R1/ORIGINAL56_REACHABILITY_R4.json')
    graph=load(graph_path)
    if [(x['path'],x['static_reachable'],x['current_source']['sha256']) for x in graph['rows']]!=[(x['path'],x['static_reachable'],x['current_source']['sha256']) for x in original_graph['rows']] or graph['dynamic_sites']!=original_graph['dynamic_sites']:raise ValueError('EXACT56_CHANGED_CLOSURE_REQUIRES_REVIEW')
    projection=pg['field_projection']
    if (projection['original_checks'],projection['original_failures'],projection['reused_pass'],projection['rechecked'])!=(4526104,10448,4515656,15672):raise ValueError('FIELD_DENOMINATOR_NOT_RECONCILED')
    if projection['failure_buckets']['hidden_other_error_count']!=0:raise ValueError('FIELD_UNCLASSIFIED_FAILURES')
    common=dict(acceptance='PASS',accepted_algorithm_bindings=policy['accepted_algorithm_bindings'],component_source_bindings=policy['component_source_bindings'],T0=candidate['accepted_trade_date'],input_candidate=preparation['candidate'],conserved_from_candidate=pg['candidate'],numeric_producers_reexecuted=False,scope='CURRENT_DATED_OPERATIONAL_RESEARCH_ONLY',historical_PIT_permission=False,automated_trading_permission=False,probability_claims=False,production_cutover=False)
    numeric=[passed(AUDIT/'STAGE1_NUMERIC_CLOSEOUT_R1/RESULT.json','PASS_CURRENT_STAGE1_SCOPE'),passed(AUDIT/'D1_PROFILE_FINAL_SCOPE_R1/RESULT.json','PASS_D1_PROFILE_REMAINING_SCOPE')]
    for name,acceptance in [('RESULT.json','PASS_CORE_AVAILABILITY_SCOPE'),('WINDOW_METADATA.json','PASS_CORE_WINDOW_METADATA_SCOPE'),('RPS_METADATA.json','PASS_RPS_METADATA_SCOPE'),('CORE47_COVERAGE.json','PASS_CURRENT_CORE47_SCOPE')]:numeric.append(passed(AUDIT/'CORE_AVAILABILITY_ORACLE_R1'/name,acceptance))
    for name,acceptance in [('RESULT.json','PASS_CURRENT_MARKET_ARITHMETIC_SCOPE'),('METADATA_AND_REGIME_R2.json','PASS_MARKET_METADATA_AND_REGIME_SCOPE')]:numeric.append(passed(AUDIT/'CURRENT_MARKET_ORACLE_R1'/name,acceptance))
    numeric.append(passed(AUDIT/'FORMAL_EXACT_FOCUS_ORACLE_R6/RESULT.json','PASS'))
    supplemental=passed(AUDIT/'SUPPLEMENTAL_PG_HTTP_R1/RESULT.json','PASS_SUPPLEMENTAL_CURRENT_PG_HTTP_SCOPE')
    snapshot=passed(SOURCE/'ACTUAL_CURRENT_NATIVE_SNAPSHOT_PG_R2.json','PASS_CURRENT_NATIVE_SNAPSHOT_PG_PREPARATION_SCOPE')
    pg_binding=passed(AUDIT/'PG_CURRENT_CANDIDATE_CONSUMER_R1/RESULT.json','PASS_CURRENT_CANDIDATE_PG_CONSUMER_SCOPE')
    gate_documents={
      'full_numeric_oracle':dict(contract_id='V4_CURRENT_COMPLETE_NUMERIC_GATE_R1',evidence=numeric,receipt_index=receipt_index,failure_resolution=stage['failure_resolution'],comparison_boundary=load(AUDIT/'CORE_AVAILABILITY_ORACLE_R1/CORE47_COVERAGE.json')['reused_numeric_comparison_boundary']),
      'exact_56_dispositions':dict(contract_id='V4_CURRENT_EXACT56_GATE_R1',evidence=[frozen(AUDIT/'ORIGINAL56_DISPOSITION_R2/RESULT.json'),frozen(AUDIT/'ORIGINAL56_DISPOSITION_R2/MATRIX.json'),frozen(graph_path),pg_binding],counts=exact['counts'],unknown=0,denominator=56),
      'native_pg_consumers':dict(contract_id='V4_CURRENT_NATIVE_PG_CONSUMER_GATE_R1',evidence=[pg_binding,supplemental,snapshot,frozen(SOURCE/'TRANSACTION_CONTROLS_R1.xml')],receipt_index=receipt_index,pg_system_identifier=pg['pg_system_identifier'],pg_database=pg['pg_database'],limitations=pg['limitations'][1:]),
      'field_semantics':dict(contract_id='V4_CURRENT_COMPLETE_FIELD_SEMANTICS_GATE_R1',evidence=[pg_binding,supplemental]+numeric[2:6],field_projection=projection,original_failures_preserved=True,all_original_failure_buckets_closed=True)
    }
    gates={}
    for name,document in gate_documents.items():
        document.update(common);gates[name]=frozen_document(name,document)
    admission=dict(contract_id='V4_AUTO_EXACT_RUNTIME_ACCEPTANCE_R1',**common,**gates,receipt_reuse='Identical base owners/native authorities and explicit source conservation; added publication IO separately verified. Original failed reports retained with bounded resolutions.',future_watch=['First genuine capture/PIT','Authorized validation cohort, FEP and settlement','Future H21/OOS'],windows_acceptance='NOT_YET_EXECUTED')
    admission_binding=frozen_document('ADMISSION',admission)
    admitted=dict(policy,publication_ready=True,status='PASS_CURRENT_FOUR_REQUIRED_GATES',admission_evidence=admission_binding)
    raw=(json.dumps(admitted,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode('utf8')
    path=ROOT/'data/v4/exact_daily_policies_v2'/hashlib.sha256(raw).hexdigest()/'POLICY.json'
    if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    admitted_binding=ref(ROOT,path);verify_policy(ROOT,admitted_binding)
    receipt=load(checked(ROOT,candidate[KEY]));folder=ROOT/'data/v4/sealed_numeric_preparations_v1'/hashlib.sha256(json.dumps(receipt,sort_keys=True).encode()+admitted_binding['sha256'].encode()).hexdigest()
    atomic_json(ROOT,folder/'CONSERVATION.json',receipt);candidate[KEY]=ref(ROOT,folder/'CONSERVATION.json');candidate['release_policy']=admitted_binding
    verify_sealed(ROOT,candidate,admitted);validate(ROOT,candidate);atomic_json(ROOT,folder/'CANDIDATE.json',candidate)
    result=dict(acceptance='PASS_CURRENT_FOUR_REQUIRED_GATES',candidate=ref(ROOT,folder/'CANDIDATE.json'),policy=admitted_binding,admission=admission_binding,gates=gates,publication=False,production_cutover=False)
    atomic_json(SOURCE,result_path,result);print(json.dumps(result))

def frozen_document(name,document):
    raw=(json.dumps(document,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode('utf8')
    path=OUT/hashlib.sha256(raw).hexdigest()/(name+'.json')
    if path.exists() and path.read_bytes()!=raw:raise ValueError('IMMUTABLE_GATE_CONFLICT')
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.tmp');temporary.write_bytes(raw);os.replace(temporary,path)
    return ref(ROOT,path)

if __name__=='__main__':main()
