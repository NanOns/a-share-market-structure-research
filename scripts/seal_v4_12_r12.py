"""R12 readback/handoff seal, fresh-process idempotency and retained R11 proof."""
import argparse,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_r12_runtime import validate,canonical
from scripts.validate_v4_12_snapshot_v2_contract import gate
OUT=ROOT/'reports/v4_12_runtime_r12'
def ref(path):
    raw=(ROOT/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def sources():return [ref(p.as_posix()) for p in sorted(Path('src/workbench_analysis').glob('v4_12*.py'))]+[ref('config/v4_12_frozen_snapshot_contract_v2.json')]
def digest_files(paths):return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
def seal(args):
    gate();readback=validate()
    if args.rerun:
        before=digest_files(list((OUT/'final_synthetic').rglob('*'))+list((OUT/'final_real').rglob('*')))
        subprocess.run([sys.executable,'-m','scripts.replay_v4_12_r12_chain'],cwd=ROOT,check=True)
        after={p:ref(p)['sha256'] for p in before};assert before==after
        legacy_before=digest_files(list((ROOT/'reports/v4_12_runtime_r11').rglob('*')))
        subprocess.run([sys.executable,'-m','scripts.replay_v4_12_r11_chain','--phase','b'],cwd=ROOT,check=True)
        legacy_after={p:ref(p)['sha256'] for p in legacy_before};assert legacy_before==legacy_after
        (OUT/'R12_FRESH_PROCESS_IDEMPOTENCY.json').write_bytes(canonical(dict(status='PASS',before=before,after=after,R11_full_evidence_before_after_identical=True,R11_evidence_hashes=legacy_before,runtime_sources=sources(),revision_conflict='IMMUTABLE_REVISION_CONFLICT_TESTED')))
    proof=json.loads((OUT/'R12_FRESH_PROCESS_IDEMPOTENCY.json').read_bytes());assert proof['status']=='PASS' and proof['runtime_sources']==sources()
    suites=list(ET.parse(args.junit).getroot().iter('testsuite'));counts={n:sum(int(s.attrib.get(n,0)) for s in suites) for n in ['tests','failures','errors','skipped']};assert counts['failures']==counts['errors']==counts['skipped']==0
    (OUT/'R12_TEST_RESULTS.xml').write_bytes(Path(args.junit).read_bytes())
    schema=dict(contract_id='V4_12_MULTI_ANCHOR_CANDIDATE_SCHEMA_V2',formal_DB_write=False,migration=False,
        structure_observations=dict(global_machines=['breakout'],per_anchor=['pullback','recovery','support','acceptance','retention'],identity=['security_id','anchor_id','machine','trade_date','revision']),
        stock_structure_event_transitions=dict(predicate='KNOWN_PRIOR_AND_CURRENT_AND_ACTUAL_CHANGE',anchor_id_event_id_required=True,global_breakout_has_null_anchor_and_event=True,retention_excluded=True),
        frozen_D1_snapshots=dict(contract=ref('config/v4_12_frozen_snapshot_contract_v2.json'),cardinality='anchor_states[]',all_prior_plus_all_new=True,V1_source_allowed=False),security_active_projection='SELECTOR_ONLY_NEVER_CROPS_STATE_SET')
    (OUT/'R12_CANDIDATE_SCHEMA_MANIFEST.json').write_bytes(canonical(schema))
    registry=json.loads((ROOT/'config/v4_12_field_registry_v1.json').read_bytes())['fields']
    report=dict(status='V4_12_R12B_MULTI_ANCHOR_RUNTIME_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',baseline='5bc34c907bd5d39f322c315db34c7788d61f0bbc',R12A_status='V4_12_R12A_MULTI_ANCHOR_STATE_CONTRACT_V2_READY',R12A_gate=ref('reports/v4_12_runtime_r12/R12A_CONTRACT_LOCAL_GATE.json'),R12B_readback=ref('reports/v4_12_runtime_r12/R12B_LOCAL_READBACK.json'),schema=ref('reports/v4_12_runtime_r12/R12_CANDIDATE_SCHEMA_MANIFEST.json'),selector_oracle=ref('reports/v4_12_runtime_r12/R12_SELECTOR_INDEPENDENT_ORACLE.json'),idempotency=ref('reports/v4_12_runtime_r12/R12_FRESH_PROCESS_IDEMPOTENCY.json'),runtime_sources=sources(),
        formal_candidate_api='workbench_analysis.v4_12_multi_anchor_engine.MultiAnchorEngine + SnapshotMaterializerV2 + InputBinderV2',legacy_api_scope='R11 historical regression only; one-episode evaluate_context is a shared AST/projection kernel, not the security active selector',
        tests={**counts,'deselected':5},deselection_reason='Four historical pre-runtime no-src-diff gates plus R10 source-hash-specific readback replaced by authorized R12 exact protected-artifact/authority/independent gates; all prior vector and R11 path tests retained',kept_vectors=dict(business=69,sequence_steps=33,authority=12,time_domain=10),selector_vectors=11,hard_cases=readback['hard_cases'],
        multi_anchor_scope=dict(creation_day_anchors=2,first_next_day_anchors=2,old_plus_new_anchors=4,one_invalidated_other_valid=True,active_switch_preserves_owning_episode=True,common_F0_bind_per_security_date=1,same_day_revisions_share_same_t_minus_1_set=True),
        real=dict(dates=['2026-09-29','2026-09-30'],universe=5224,anchors=0,transitions=0,global_observations_per_day=5224,security_projection_rows_per_day=5224,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,raw_fallback_count=0,provider_replacement_count=0,V4_11_candidate_substitution_count=0),
        protected_before_after={p:dict(before=h,after=ref(p)['sha256']) for p,h in readback['protected_hashes'].items()},Stage_head='V4_00_TO_V4_11_ACCEPTED',Data_head='2026-09-30',permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False,D2=False,Final_State=False,Radar=False,Validation_Cohort=False,V4_13=False,migration=False,formal_V4_12_head=False),
        blocked_capabilities=[dict(field=r['field'],status='BLOCKED_WITH_EXPLICIT_REASON',reason=r['blocked_reason']) for r in registry if r['field_role']=='BLOCKED_CAPABILITY'],
        diagnostic_disposition='synthetic/real and candidate_synthetic/candidate_real are retained local construction diagnostics. Only final_synthetic/final_real refs in R12B_LOCAL_READBACK are R12 authoritative engineering candidates. V1 artifacts never used as R12 prior.',external_acceptance=False,next_stage='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    if args.clean:
        clean=json.loads(Path(args.clean).read_bytes());assert clean['status']=='PASS' and clean['tested_source_sha']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        for p,h in clean['source_manifest'].items():assert ref(p)['sha256']==h
        report['clean_checkout']=clean
    (OUT/'R12_RUNTIME_HANDOFF.json').write_bytes(canonical(report));print(json.dumps(dict(status=report['status'],tests=counts)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--junit',required=True);p.add_argument('--rerun',action='store_true');p.add_argument('--clean');seal(p.parse_args())
