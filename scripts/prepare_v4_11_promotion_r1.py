"""Read audit and prepare exact capability-scoped head; mutate no head."""
from scripts.v4_11_promotion_contract_r1 import *
import subprocess
from datetime import datetime,timezone

EXPECTED_BUNDLE = {
    AUDIT: ('0ae15dfddd4673e05eeb9a33a8b1679a0ba0680a18e3640a520ac9aaa5bfd590', 10061),
    MASTER: ('1585f9d0e69df5f2bb55ce2f0961830593a8c90391aa7fd89e4a380eafc39cc0', 2512),
    TASK: ('e291b27e86383c374bfcfed6da8fc3d185d8d615e03b8aa8c657cc8f6582aa26', 10383),
}

def ensure_bundle(root=ROOT, bundle_dir=None):
    """Validate repo bytes first. Bootstrap only missing, explicitly supplied files."""
    root = Path(root).resolve()
    missing = [p for p in EXPECTED_BUNDLE if not (root / p).is_file()]
    if missing and bundle_dir is None:
        raise ValueError('R6_EXTERNAL_BUNDLE_SOURCE_REQUIRED')
    plans = []
    for path, expected in EXPECTED_BUNDLE.items():
        source = root / path if path not in missing else Path(bundle_dir).resolve() / Path(path).name
        raw = source.read_bytes()
        if (hashlib.sha256(raw).hexdigest(), len(raw)) != expected:
            raise ValueError('R6_EXTERNAL_BUNDLE_EXACT_MISMATCH:' + path)
        if path in missing:
            plans.append((path, raw, dict(source_path=str(source), source_sha256=expected[0],
                                        source_bytes=expected[1], destination=path)))
    # Persist the complete validated source plan before any destination write.
    def put(path, raw):
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix=destination.name + '.')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
    if plans:
        receipt = dict(contract_id='R6_EXPLICIT_BUNDLE_BOOTSTRAP_V1', sources=[p[2] for p in plans])
        put('reports/next_round_r6r1/R6_EXPLICIT_BUNDLE_SOURCE_PLAN.json',
            (json.dumps(receipt, ensure_ascii=False, indent=2)+'\n').encode('utf8'))
        for path, raw, _ in plans:
            if (root / path).exists():
                raise ValueError('R6_BUNDLE_DESTINATION_APPEARED:' + path)
            put(path, raw)
    return dict(status='PASS', mode='REPO_FIRST_EXACT_VALIDATION' if not plans else 'EXPLICIT_BOOTSTRAP',
                copied_files=[p[0] for p in plans])

def prepare(bundle_dir=None):
    result = ensure_bundle(ROOT, bundle_dir)
    if (ROOT / HEAD).is_file():
        print(json.dumps(result, sort_keys=True))
        return result
    return _prepare_initial_promotion()

def _prepare_initial_promotion():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==SEALED
    from scripts.next_round_execution_r5 import verify_protected
    verify_protected()
    for folder in (P,DOC,'reports/v4_12/') :atomic(folder+'.gitattributes',b'* -text\n')
    atomic(ARCHIVE,(ROOT/GLOBAL).read_bytes());parent=read(ARCHIVE)
    assert parent['accepted_stage_range']=='V4_00_TO_V4_10_ACCEPTED'
    paths=subprocess.check_output(['git','ls-files','data/v4/*HEAD*.json'],cwd=ROOT,text=True).splitlines()
    protected=[bind(p) for p in paths if p!=GLOBAL]
    # Explicit prior pinned byte representation proof remains preservation only.
    source_manifest=read('reports/next_round_r5/BATCH_SOURCE_MANIFEST.json')
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    gate=validate_head_v2(ROOT,read('data/v4/V4_DATA_ACCEPTED_HEAD.json'))
    entry=write(P+'R6_STAGE_CONTRACT.json',dict(contract_id='V4_R6_PROMOTION_STAGE_CONTRACT_V1',authority=bind(AUDIT),master=bind(MASTER),task=bind(TASK),upgrade=bind(UPGRADE),baseline=SEALED,implementation=IMPLEMENTATION,phase0=dict(status='DEGRADED_PASS',scope='ACCEPTED_INPUT_PREFLIGHT',data_gate=gate),protected_head_bindings=protected,parent_stage=bind(ARCHIVE),source_manifests=[bind('reports/next_round_r4/BATCH_SOURCE_MANIFEST.json'),bind('reports/next_round_r5/BATCH_SOURCE_MANIFEST.json')],observed_at_utc=datetime.now(timezone.utc).isoformat(),permissions=PERMISSIONS,next_stage='CANDIDATE_DETACHED_VALIDATOR_PASS_THEN_PROMOTION_AND_STAGE_ENTRY_STOP',V4_12_runtime_authorized=False))
    surface=write('reports/v4_12/V4_12_ENTRY_CONTRACT_SURFACE_R1.json',dict(contract_id='V4_12_STRUCTURE_ANCHOR_SUPPORT_ENTRY_SURFACE_V1',status='ENTRY_SURFACE_REGISTERED_CONTRACT_COMPLETENESS_PENDING',upgrade=bind(UPGRADE),sections=['10J','10K','10L','13A','31','34A','41A0','41A','49A','72','78','81.4'],runtime_implemented=False,runtime_implementation_authorized=False,contract_completeness='CONTRACT_INCOMPLETE_UNTIL_VERSIONED_REGISTRIES_AST_PARAMETERS_CAPABILITY_AND_INDEPENDENT_VECTORS_ARE_FROZEN',contract_registry=[dict(name=n,status='REQUIRED_BEFORE_IMPLEMENTATION',authority_section=s) for n,s in [('STRUCTURE_EVENT_V1','10J/10K/10L'),('Anchor schema/identity','41A'),('Anchor coordinate identity','41A0'),('Anchor rebasing rules','41A0'),('Anchor lifecycle','41A'),('invalidation AST','31/41A'),('breakout AST','10J'),('pullback AST','10K'),('recovery AST','10L'),('producer registry','13A/81.4'),('field registry','81.4'),('parameter registry','72'),('machine AST','81.4'),('UNKNOWN semantics','10J/10K/10L'),('time roles','13A'),('input schema','81.4'),('output schema','81.4'),('machine vectors','81.4')]],dag=dict(allowed_inputs=['F0[t]','t-1 frozen Anchor/event'],forbidden_inputs=['D2[t]','same-day Final State','same-day Event diff','Focus','UI','future outcome','same-day newly-created Anchor as confirmation evidence'],new_anchor_can_emit_D1_event=True,new_anchor_self_confirmation_allowed=False,earliest_support_path_test='t+1'),source_capability=dict(F0='VERSIONED_ACCEPTED_PUBLICATION_BINDING_REQUIRED',prior_anchor_event='FROZEN_PREVIOUS_SESSION_PUBLICATION_REQUIRED',t_minus_1_core_close_ma20='ACCEPTED_UNAVAILABLE; DO_NOT_RECONSTRUCT',missing_required_fact='UNKNOWN_NEVER_FALSE',current_local_absence_is_provider_evidence=False),anchor_required_fields=['anchor_id','security_id','anchor_trade_date','anchor_raw_lower','anchor_raw_upper','anchor_price_basis','adjustment_contract_id','adjustment_source_identity','adjustment_source_revision','adjustment_asof','anchor_basis_trade_date','creation_coordinate','current_comparison_coordinate','frozen_transform_coefficients','source_event_id','source_fact_digest','rebase_lineage','corporate_action_transition'],coordinate=dict(basis_identity='price_basis + adjustment_source_revision',qfq_coefficient_equality_is_identity=False,anchor_original_immutable=True,observation_view='alpha * original_anchor + beta',price_levels_add_beta=True,ATR_differences_positive_scale_only=True,returns='RECOMPUTE_IN_COMMON_COORDINATE',unsupported_conversion=dict(state='UNKNOWN',reason='PRICE_BASIS_MISMATCH'),reference_only_legacy_focus_path=True),breakout=dict(no_active_event=[dict(when='C > prior_high20 + 0.1 * ATR20 AND CLV >= 0.7',state='BREAKOUT_TENTATIVE',emit_anchor='PRIOR_HIGH'),dict(when='near_high20 == NEAR',state='APPROACHING'),dict(when='otherwise evaluable',state='NO_BREAKOUT')],active_event_order=[['BROKEN/INVALIDATED','FAILED_BREAKOUT'],['HELD_CONFIRMED OR at least 2 consecutive evaluable post-creation sessions C >= anchor_upper','BREAKOUT_ACCEPTED'],['today touches anchor','TESTING'],['otherwise evaluable','BREAKOUT_TENTATIVE']],creation_day_accepted=False,unknown='UNKNOWN'),pullback=dict(prior_source='t-1 frozen valid rise/breakout/impulse event and Anchor',ordered_rules=[['no prior valid event','NOT_PULLBACK'],['BROKEN/INVALIDATED','PULLBACK_FAILED'],['HELD_CONFIRMED','PULLBACK_HELD'],['RECLAIMED/HELD_TENTATIVE','PULLBACK_RECLAIMED'],['touch by anchor type','PULLBACK_TO_MA/BREAKOUT/IMPULSE'],['post-event peak drawdown without touch','PULLBACK_IN_PROGRESS'],['otherwise evaluable','NOT_PULLBACK']],unknown='UNKNOWN_NEVER_FALSE'),recovery=dict(rule_order=['RECOVERY_FAILED','RECOVERY_CONFIRMED','ANCHOR_RECLAIM','MA20_RECLAIM','RELATIVE_RECOVERY','BOUNCE_ONLY','NONE'],confirmed_rule='At least 2 consecutive evaluable sessions after frozen recovery line creation held',ma20_reclaim='C[t-1] <= MA20[t-1] AND C[t] > MA20[t]',relative_recovery='delta3 changes from <=0 to >3 AND rel_market_1 >0',bounce='ret1 >0',creation_day_confirmed=False,missing_prior_core_fields='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'),parameter_seeds=[dict(name='breakout_ATR_buffer',value=0.1,source='10J',status='ENTRY_REFERENCE_REQUIRES_VERSIONED_PARAMETER_INSTANCE'),dict(name='breakout_CLV_min',value=0.7,source='10J',status='ENTRY_REFERENCE_REQUIRES_VERSIONED_PARAMETER_INSTANCE'),dict(name='consecutive_evaluable_sessions',value=2,source='10J/10L',status='ENTRY_REFERENCE_REQUIRES_VERSIONED_PARAMETER_INSTANCE')],required_independent_vectors=['same-day new Anchor cannot self-confirm','earliest support t+1','unknown/stale prior is not false','cash dividend','bonus shares','rights issue','same-day revision','cross-corporate-action support test','missing source capability','D2/Focus/UI/future perturbations cannot affect D1'],independent_vectors_status='REQUIRED_NOT_EXECUTED',permissions=PERMISSIONS))
    candidate=dict(contract_id='V4_11_ACCEPTED_HEAD_V1',stage='V4-11',status='ENGINEERING_PASS_CAPABILITY_SCOPED',external_acceptance='EXTERNALLY_ACCEPTED',external_acceptance_decision=DECISION,implementation_commit=IMPLEMENTATION,audited_sealed_head=SEALED,parent_binding=bind(PARENT),global_head_parent=bind(ARCHIVE),evidence_bindings={p:bind(p) for p in EVIDENCE},capabilities=CAPABILITIES,protected_head_bindings=protected,promotion_stage_contract=entry,entry_contract_surface=surface,validator_bindings=[bind(p) for p in VALIDATORS],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,historical_as_recorded_event_proven=False,event_evidence='RECONSTRUCTED_LEFT_CENSORED',full_repository_runtime_pass_claim=False,non_mainline_audits=[dict(id=n,classification='PREEXISTING_NON_MAINLINE',resolution_claim=False) for n in ('R5_FULL_REPOSITORY_PREEXISTING_M14_COLLECTION','R5_FULL_REPOSITORY_PREEXISTING_M2_UNTRACKED_PUBLICATION_DEPENDENCY')],**PERMISSIONS)
    write(CANDIDATE,candidate);print('R6_CANDIDATE_READY_NO_HEAD_MUTATION')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-dir', type=Path)
    prepare(parser.parse_args().bundle_dir)
