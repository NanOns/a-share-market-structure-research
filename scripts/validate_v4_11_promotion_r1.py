"""Read-only independent R6 promotion validator with exact out-of-band pins."""
from scripts.v4_11_promotion_contract_r1 import *
import subprocess

def git_exact(path,commit):
    raw=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
    current=(ROOT/path).read_bytes()
    if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        return ('oid sha256:'+hashlib.sha256(current).hexdigest()).encode() in raw
    return raw==current

def protected_exact(ref):
    try:exact(ref);return True
    except ValueError:
        if ref['path'] not in ('data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json','data/v4/V4_03_ACCEPTED_HEAD.json'):return False
        from workbench_analysis.parallel_scoped_acceptance_r1 import validate_protected_binding
        validate_protected_binding(ROOT,ref);return True

def preexisting_source_unchanged(path):
    if git_exact(path,SEALED):return True
    if path!='src/workbench_online/collector.py':return False
    proof=read(P+'M14_COLLECTOR_BYTE_REPRESENTATION.json')
    original=exact(proof['original_archive']).read_bytes()
    gitraw=subprocess.check_output(['git','show',SEALED+':'+path],cwd=ROOT)
    current=(ROOT/path).read_bytes()
    return hashlib.sha256(original).hexdigest()=='dc935bbfc2405d281a2db8bd84532a01960f9a92c950a7d90ce14a56cfa4fd5d' and hashlib.sha256(gitraw).hexdigest()=='9bb7f4d0953a09585e39538e4292b91340404f4be98ea0d8ecdf2c8b1941b131' and current==original and original.replace(b'\r\n',b'\n')==gitraw

def validate(candidate=None,detached_probe=False,post=False):
    h=read(CANDIDATE) if candidate is None else candidate;checks={};hard={}
    def check(name,condition):checks[name]='PASS' if condition else 'FAIL'
    def gate(name,condition):hard[name]='PASS' if condition else 'FAIL'
    evidence=h.get('evidence_bindings',{})
    check('P01_schema_stage_external_decision',h.get('contract_id')=='V4_11_ACCEPTED_HEAD_V1' and h.get('stage')=='V4-11' and h.get('status')=='ENGINEERING_PASS_CAPABILITY_SCOPED' and h.get('external_acceptance')=='EXTERNALLY_ACCEPTED' and h.get('external_acceptance_decision')==DECISION)
    check('P02_parent_V4_10_exact',h.get('parent_binding')==bind(PARENT) and git_exact(PARENT,SEALED))
    manifest=read('reports/next_round_r5/BATCH_SOURCE_MANIFEST.json')
    check('P03_implementation_commit_exact',h.get('implementation_commit')==IMPLEMENTATION and all(exact(r) and git_exact(r['path'],IMPLEMENTATION) for r in manifest['artifacts']))
    check('P04_audited_seal_descendant',h.get('audited_sealed_head')==SEALED and subprocess.run(['git','merge-base','--is-ancestor',IMPLEMENTATION,SEALED],cwd=ROOT).returncode==0 and subprocess.run(['git','merge-base','--is-ancestor',SEALED,'HEAD'],cwd=ROOT).returncode==0)
    audit=(ROOT/AUDIT).read_text(encoding='utf8')
    stage=bound(h['promotion_stage_contract'])
    check('P05_external_acceptance_document_exact',evidence.get(AUDIT)==stage['authority']==bind(AUDIT) and bind(AUDIT)['sha256']=='0ae15dfddd4673e05eeb9a33a8b1679a0ba0680a18e3640a520ac9aaa5bfd590' and all(x in audit for x in (IMPLEMENTATION,SEALED,'PASS_CAPABILITY_SCOPED_ENGINEERING','AUTHORIZED_WITH_EXACT_SCOPE')) and DECISION in (ROOT/MASTER).read_text(encoding='utf8'))
    check('P06_R4A_seal_exact',evidence.get(EVIDENCE[0])==bind(EVIDENCE[0]) and git_exact(EVIDENCE[0],SEALED))
    check('P07_R5A_parity_exact',all(evidence.get(p)==bind(p) and git_exact(p,SEALED) for p in EVIDENCE[1:4]))
    check('P08_owner_oracle_exact',read(EVIDENCE[2])['status']=='PASS' and read(EVIDENCE[2])['formal_t_minus_1_known_count']==0)
    seal=read('reports/v4_11_r5a/R5A_SEALED_OWNER_PRODUCER_SET.json')
    check('P09_R5A_seal_exact',seal['sealed'] and seal['status']=='V4_11_R5A_OWNER_INPUT_AUTHORITY_PARITY_CANDIDATE_READY' and all(exact(r) for r in seal['publications'].values()))
    astreport=read('reports/v4_11_r5/V4_11_R5_D2_ADAPTER_AST_EVIDENCE.json');oracle=read('reports/v4_11_r5/INDEPENDENT_D2_OWNER_INPUT_ORACLE.json')
    from src.v4.confirmation_d2_candidate_r5 import adapter_ast_evidence,candidate_policy,bound as bridge_bound
    check('P10_D2_AST_exact',adapter_ast_evidence()==astreport)
    check('P11_D2_owner_oracle_exact',oracle['status']=='PASS' and oracle['rows']==10447 and all(n==10447 for n in oracle['counts'].values()) and not oracle['adapter_helpers_used_for_expected'] and bool(bound(oracle['proof'])))
    residual=read('reports/v4_11_r5/RESIDUAL_UNKNOWN_ATTRIBUTION.json')
    check('P12_residual_attribution_exact',all(residual[k]==0 for k in ('producer_wiring_missing','unsealed_helper_source','generic_coefficient_gate','raw_reconstruction_fallback','accepted_t_minus_1_known_count')) and all(r['required_unknown'] and all(x['exact_publication'] and x['root_causes'] for x in r['required_unknown']) for r in residual['stale_rows']))
    diff=read('reports/v4_11_r5/R4_TO_R5_BUSINESS_DIFF.json')
    check('P13_business_diff_exact',diff['D0_business_changed'] is False and diff['thresholds_changed'] is False and diff['t_minus_1_capability_expanded'] is False)
    d2=read('reports/v4_11_r5/V4_11_R5_D2_READBACK.json');config=bound(d2['contract']);source_set=bound(d2['source_set'])
    from src.v4.sealed_owner_authority_r5 import resolve_sources,verify_manifest_sources
    authority=resolve_sources(config,bridge_bound,candidate_policy())
    for ref in source_set['publications']:verify_manifest_sources(bound(ref),authority)
    prior=bound(d2['prior']);current=bound(d2['current'])
    check('P14_D2_readback_exact',len(prior['rows'])==5223 and len(current['rows'])==5224 and all(x['input_provenance']==r['input_provenance'] for pub in (prior,current) for x,r in zip(pub['inputs'],pub['rows'])))
    er=read('reports/v4_11_r5/V4_11_R5_EVENT_REPLAY.json');frozen=bound(er['frozen_prior']);events=bound(er['events'])
    from src.v4.confirmation_events_candidate_r5 import event_unknown_reasons
    from src.v4.confirmation import digest
    old={r['entity_id']:r for r in prior['rows']};now={r['entity_id']:r for r in current['rows']}
    safety=all(e['event_unknown_predicates']==event_unknown_reasons(now[e['entity_id']],old.get(e['entity_id'])) and e['effective_event']==('UNKNOWN' if e['event_unknown_predicates'] else e['primary_event']) for e in events)
    frozen_material=dict(frozen);frozen_id=frozen_material.pop('head_digest')
    check('P15_Event_replay_exact',len(events)==5224 and safety and er['same_day_revision_predecessor_invariant'] is True and frozen['source_binding']==prior and frozen['rows']==prior['rows'] and frozen_id==digest(frozen_material))
    matrix=read('reports/v4_11_r5/V4_11_R5_SCENARIO_CAPABILITY_MATRIX.json');a=read(EVIDENCE[0])
    formal=('LAUNCH_CONFIRM','RECOVERY_TURN');diagnostic=('STRONG_PULLBACK','TREND_CONTINUE')
    check('P16_capability_matrix_exact',all(matrix['scenarios'][s]['capability']=='FORMAL_CANDIDATE' and matrix['scenarios'][s]['parent_producer_set']['sha256']==bind(EVIDENCE[0])['sha256'] for s in formal) and all(matrix['scenarios'][s]['capability']=='DIAGNOSTIC_ONLY' for s in diagnostic))
    clean=read('reports/v4_11_r5/V4_11_R5_CLEAN_CHECKOUT.json')
    check('P17_clean_checkout_exact',clean['tested_commit']==IMPLEMENTATION and clean['summary']==dict(tests=2069,passed=2067,skipped=2,failures=0,errors=0) and clean['new_deselects']==[] and clean['git_status_before']==clean['git_status_after']=='' and clean['R5_real_DAG_readback']==dict(status='PASS_R5_EXACT_SEALED_OWNER_D2_REEXECUTION_EVENT_SAFETY',parity_rows=5222,owner_input_rows=10447,current_rows=5224,prior_rows=5223,event_rows=5224,permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False)))
    protected=h.get('protected_head_bindings',[])
    def pinned(path):return any(r['path']==path and protected_exact(r) and r in stage['protected_head_bindings'] for r in protected)
    check('P18_Data_Head_unchanged',pinned('data/v4/V4_DATA_ACCEPTED_HEAD.json') and read('data/v4/V4_DATA_ACCEPTED_HEAD.json')['accepted_trade_date']=='2026-09-30')
    check('P19_Dev_Baseline_unchanged',pinned('data/v4/V4_DEV_BASELINE_HEAD.json'))
    check('P20_PIT_membership_unchanged',pinned('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json'))
    check('P21_all_scoped_heads_unchanged',protected==stage['protected_head_bindings'] and all(protected_exact(r) for r in protected))
    global_=read(GLOBAL);parent=read(ARCHIVE)
    check('P22_permissions_false',all(h.get(k) is False and global_.get(k,False) is False for k in PERMISSIONS))
    check('P23_capability_map_exact',h.get('capabilities')==CAPABILITIES)
    check('P24_historical_AS_RECORDED_not_overclaimed',h.get('AS_RECORDED') is False and h.get('event_evidence')=='RECONSTRUCTED_LEFT_CENSORED' and h.get('historical_as_recorded_event_proven') is False and er['event_evidence']=='RECONSTRUCTED_LEFT_CENSORED')
    check('P25_diagnostic_not_promoted',h.get('capabilities')==CAPABILITIES and all(matrix['scenarios'][s]['capability']=='DIAGNOSTIC_ONLY' for s in diagnostic))
    collection=read('reports/v4_11_r5/FULL_REPOSITORY_COLLECTION.json')
    check('P26_M14_M2_separate_unresolved',collection['status']=='PREEXISTING_NON_MAINLINE_M14_M2_COLLECTION' and collection['full_repository_runtime_pass_claim'] is False and h.get('full_repository_runtime_pass_claim') is False and len(h.get('non_mainline_audits',[]))==2 and all(x.get('classification')=='PREEXISTING_NON_MAINLINE' and x.get('resolution_claim') is False for x in h['non_mainline_audits']) and all(preexisting_source_unchanged(p) for p in ('tests/upgrade_m14/test_online_batches.py','tests/upgrade_m2/test_api.py','src/workbench_online/collector.py','src/workbench_service/app.py')))
    additions={'v4_11_binding':dict(bind(CANDIDATE),path=HEAD),'v4_11_status':h['status'],'v4_11_external_acceptance':DECISION,'v4_11_capabilities':CAPABILITIES,'v4_12_entry':dict(status='AUTHORIZED_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_ONLY',binding=bind(ENTRY)) if (ROOT/ENTRY).exists() else None}
    unchanged=all(global_.get(k)==v for k,v in parent.items() if k not in ('accepted_stage_range','version'))
    is_post=(ROOT/HEAD).exists()
    if is_post:
        allowed=set(parent)|set(additions)|set(PERMISSIONS)
        idempotent=read(HEAD)==h and global_['accepted_stage_range']=='V4_00_TO_V4_11_ACCEPTED' and unchanged and set(global_)<=allowed and all(global_.get(k)==v for k,v in additions.items()) and global_['version']=='2.5.0'
    else:idempotent=global_==parent and parent['accepted_stage_range']=='V4_00_TO_V4_10_ACCEPTED'
    check('P27_idempotent_promotion_parent_preserved',idempotent and exact(h['global_head_parent']) and h['global_head_parent']==bind(ARCHIVE))
    if detached_probe:
        check('P28_clean_detached_validation',subprocess.run(['git','symbolic-ref','-q','HEAD'],cwd=ROOT,capture_output=True).returncode!=0 and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip() and not (ROOT/'config/.env').exists())
    else:
        c=read(CLEAN) if (ROOT/CLEAN).exists() else {}
        check('P28_clean_detached_validation',c.get('status')=='PASS' and c.get('checks',{}).get('P28_clean_detached_validation')=='PASS' and c.get('candidate_sha256')==bind(CANDIDATE)['sha256'] and c.get('validator_bindings')==[bind(p) for p in VALIDATORS])
    parity=read('reports/v4_11_r5a/V4_07_V4_09_EXACT_OWNER_PARITY.json')
    for name,ok in [('P01_parity_scope',parity['row_scope']==5222),('P02_business_mismatch',parity['business_mismatches']==0),('P03_quality_mismatch',parity['quality_mismatches']==0),('P04_UNKNOWN_reason_mismatch',parity['unknown_reason_mismatches']==0),('P05_t_minus_1_known',parity['formal_t_minus_1_known_count']==0),('P06_owner_oracle',checks['P08_owner_oracle_exact']=='PASS'),('P07_owner_publications',checks['P09_R5A_seal_exact']=='PASS'),('P08_D2_oracle',oracle['status']=='PASS'),('P09_owner_field_counts',all(n==10447 for n in oracle['counts'].values())),('P10_raw_fallback',residual['raw_reconstruction_fallback']==0),('P11_unsealed_helper',residual['unsealed_helper_source']==0),('P12_wiring_missing',residual['producer_wiring_missing']==0),('P13_coefficient_gate',residual['generic_coefficient_gate']==0),('P14_frozen_D0',all(exact(r) and git_exact(r['path'],SEALED) for r in config['frozen_R4_D0_publications'].values())),('P15_formal_scope',checks['P16_capability_matrix_exact']=='PASS'),('P16_diagnostic_scope',checks['P25_diagnostic_not_promoted']=='PASS'),('P17_normalized_AST',all(x['normalized_business_AST_exact'] for x in astreport['business_AST_comparisons'].values())),('P18_threshold_order',astreport['exact_rule_order'] and astreport['exact_business_thresholds']),('P19_event_UNKNOWN',safety),('P20_reconstructed_scope',checks['P24_historical_AS_RECORDED_not_overclaimed']=='PASS')]:gate(name,ok)
    check('P29_exact_evidence_set',set(evidence)==set(EVIDENCE) and all(evidence[p]==bind(p) and (p==AUDIT or git_exact(p,SEALED)) for p in EVIDENCE))
    check('P30_expected_V4_10_fail_closed_boundary',clean['current_v4_10_protected_gate']=='FAIL' and 'current_v10["checks"]["P19_protected"] != "FAIL"' in (ROOT/'scripts/verify_v4_r5_clean_checkout.py').read_text(encoding='utf8') and git_exact('scripts/verify_v4_r5_clean_checkout.py',IMPLEMENTATION))
    check('P31_validator_hash_bound',h.get('validator_bindings')==[bind(p) for p in VALIDATORS])
    surface=bound(h['entry_contract_surface'])
    check('P32_entry_surface_no_runtime',surface['runtime_implemented'] is False and surface['runtime_implementation_authorized'] is False and surface['dag']['allowed_inputs']==['F0[t]','t-1 frozen Anchor/event'] and surface['dag']['earliest_support_path_test']=='t+1' and surface['dag']['new_anchor_self_confirmation_allowed'] is False and surface['coordinate']['basis_identity']=='price_basis + adjustment_source_revision' and surface['upgrade']==bind(UPGRADE))
    if post:
        entry_=read(ENTRY)
        check('P33_post_entry_exact',is_post and entry_==dict(contract_id='V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_V1',stage='V4-12',stage_name='Structure / Anchor / Support',status='AUTHORIZED',scope='STAGE_ENTRY_ONLY_RUNTIME_NOT_IMPLEMENTED',accepted_parent=bind(HEAD),surface=h['entry_contract_surface'],upgrade=bind(UPGRADE),sections=surface['sections'],runtime_implemented=False,runtime_implementation_authorized=False,contract_completeness=surface['contract_completeness'],**PERMISSIONS))
    return dict(contract_id='V4_11_PROMOTION_READ_ONLY_VALIDATOR_R1',status='PASS' if all(v=='PASS' for v in [*checks.values(),*hard.values()]) else 'FAIL',checks=checks,R5_hard_gates=hard,candidate_sha256=bind(CANDIDATE)['sha256'],validator_bindings=[bind(p) for p in VALIDATORS],post_promotion=post,external_stage_acceptance=DECISION,V4_12_runtime_executed=False)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--detached-probe',action='store_true');p.add_argument('--post',action='store_true');args=p.parse_args()
    result=validate(detached_probe=args.detached_probe,post=args.post);print(json.dumps(result));raise SystemExit(result['status']!='PASS')
