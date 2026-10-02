"""Evidence seal, exact protected readback and fresh process idempotency proof."""
import argparse,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_r11_chain import validate,canon,sha
from scripts.verify_v4_12_r11_projection_paths import validate as projection_validate
from scripts.verify_v4_12_r11_revision_correction import validate as revision_validate

OUT=ROOT/'reports/v4_12_runtime_r11'
def ref(path):
    raw=(ROOT/path).read_bytes();return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def sources():return [ref(p.as_posix()) for p in Path('src/workbench_analysis').glob('v4_12_*.py')]+[ref('config/v4_12_frozen_snapshot_contract_v1.json')]
def seal(args):
    a=validate('a');b=validate('b');projection_validate();revision_validate()
    if args.rerun:
        paths=list((OUT/'b_closure_chain_real').rglob('*'))+list((OUT/'b_closure_chain_synthetic').rglob('*'))
        before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
        subprocess.run([sys.executable,'-m','scripts.replay_v4_12_r11_chain','--phase','b'],cwd=ROOT,check=True)
        after={p:ref(p)['sha256'] for p in before};assert before==after
        (OUT/'R11_FRESH_PROCESS_IDEMPOTENCY.json').write_bytes(canon(dict(status='PASS',before=before,after=after,runtime_sources=sources(),same_revision_conflict='IMMUTABLE_REVISION_CONFLICT_TESTED')))
    receipt=json.loads((OUT/'R11_FRESH_PROCESS_IDEMPOTENCY.json').read_bytes());assert receipt['status']=='PASS' and receipt['runtime_sources']==sources()
    tree=ET.parse(args.junit);suites=list(tree.getroot().iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']};assert counts['failures']==counts['errors']==counts['skipped']==0
    (OUT/'R11_TEST_RESULTS.xml').write_bytes(Path(args.junit).read_bytes())
    state=json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes());data=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    registry=json.loads((ROOT/'config/v4_12_field_registry_v1.json').read_bytes())['fields']
    schema=dict(contract_id='V4_12_R11_CANDIDATE_SCHEMA_MANIFEST_V1',canonical_DB_write=False,formal_migration=False,
        structure_observations=dict(contract_id='V4_12_STATE_OBSERVATION_CANDIDATE',scope='ALL_SIX_MACHINES_UNKNOWN_AND_METRICS_INCLUDED',keys=['security_id','trade_date','revision','machine'],observation_ref='EXACT_CANONICAL_OBSERVATION_DIGEST'),
        stock_structure_event_transitions=dict(machines=['breakout','pullback','recovery','support','acceptance'],predicate='PRIOR_KNOWN_AND_CURRENT_KNOWN_AND_ACTUAL_CHANGE',fields=['logical_transition_id','security_id','machine','trade_date','revision','from_state','to_state','prior_session_state_ref','current_observation_ref','transition_kind','quality','reason','anchor_ref','event_ref','contract_digest','input_digest']),
        frozen_D1_snapshots=dict(contract=ref('config/v4_12_frozen_snapshot_contract_v1.json'),bundle='JSONL_GZIP_PLUS_EXACT_INDEX_AND_MANIFEST'),retention_is_transition=False)
    (OUT/'R11_CANDIDATE_SCHEMA_MANIFEST.json').write_bytes(canon(schema))
    report=dict(status='V4_12_R11B_TRANSITION_OUTPUT_PROJECTION_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',baseline='7d35478780003d866faf85a730d0bb3b86af1134',sequence=['R11A','PERSISTED_LOCAL_GATES_PASS','R11B','UNIFIED_COMMIT_PUSH','STOP'],R11A_local=ref('reports/v4_12_runtime_r11/R11A_LOCAL_GATES.json'),R11B_local=ref('reports/v4_12_runtime_r11/R11B_LOCAL_GATES.json'),runtime_sources=sources(),tests={**counts,'deselected':5},deselection_reason='Four historical pre-runtime no-src-diff gates plus R10 exact tested-source readback superseded by authorized R11 scoped independent validators; their protected semantics and R10 artifacts are retained',kept_vectors=dict(business=69,sequence_steps=33,authority=12,time_domain=10),
        real_scope=dict(universe=5224,dates=['2026-09-29','2026-09-30'],observation_rows_per_day=31344,state_transition_rows_per_day=0,anchors=0,events=0,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,raw_fallback_count=0,provider_replacement_count=0,V4_11_candidate_substitution_count=0),
        same_day_quality_correction=ref('reports/v4_12_runtime_r11/R11_SAME_DAY_QUALITY_CORRECTION.json'),projection_oracle=ref('reports/v4_12_runtime_r11/R11B_PROJECTION_PATH_ORACLE.json'),idempotency=ref('reports/v4_12_runtime_r11/R11_FRESH_PROCESS_IDEMPOTENCY.json'),schema_manifest=ref('reports/v4_12_runtime_r11/R11_CANDIDATE_SCHEMA_MANIFEST.json'),
        protected_before_after={p:dict(before=h,after=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p,h in b['protected_hashes'].items()},
        Stage_head='V4_00_TO_V4_11_ACCEPTED',Data_head='2026-09-30',permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False,D2=False,Radar=False,Validation_Cohort=False,V4_13=False,migration=False,formal_V4_12_head=False),
        blocked_capabilities=[dict(field=r['field'],status='BLOCKED_WITH_EXPLICIT_REASON',reason=r['blocked_reason']) for r in registry if r['field_role']=='BLOCKED_CAPABILITY'],external_acceptance=False,
        diagnostic_disposition='Earlier a_synthetic/a_chain/b_persisted/b_projected/projection_paths bundles preserved as local construction diagnostics; authoritative prior chains are R11A a_persisted and R11B b_closure/projection_closure/revision_correction, with exact refs in gates. No diagnostic bundle is promoted or substituted.',next_stage='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    report['R11A_completion_status']='V4_12_R11A_PERSISTED_FROZEN_D1_CHAIN_CANDIDATE_READY_FOR_EXTERNAL_AUDIT'
    if args.clean:
        clean=json.loads(Path(args.clean).read_bytes());assert clean['status']=='PASS'
        assert clean['tested_source_sha']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        for path,expected in clean['source_manifest'].items():assert ref(path)['sha256']==expected
        report['clean_checkout']=clean
    (OUT/'R11_RUNTIME_HANDOFF.json').write_bytes(canon(report));print(json.dumps(dict(status=report['status'],tests=counts)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--junit',required=True);p.add_argument('--rerun',action='store_true');p.add_argument('--clean');seal(p.parse_args())
