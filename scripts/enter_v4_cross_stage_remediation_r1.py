"""Master-card first execution: governance and entries, no capability promotion."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.promote_v4_09_accepted_head import bind
MASTER='V4_CROSS_STAGE_INDEPENDENT_AUDIT_REMEDIATION_MASTER_TASK_R1_20261001.md'
ITEMS=[
 ('A01','DM01_REAL_INCREMENTAL_BUILDERS','P0','DM01','src/workbench_analysis/dm01_accepted_builder_registry.py',[],False),
 ('A02','V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01','P0','PRIOR-RPS','V4_RPS_PIT_HISTORY_V1',['A01'],True),
 ('A03','FORWARD_PIT_HISTORY_ACCUMULATION','P1','FORWARD-PIT','forward_pit_daily_builder',[],True),
 ('A04','AUD-AMOUNT-A-06','P1','AMOUNT-A','independent_amount_a_contract',[],False),
 ('A05','LEGACY_VALID_MEMBER_EXACT_PRODUCER','P1','LEGACY-VALID-MEMBER','legacy_missing_state_source_archaeology',[],False),
 ('A06','V4-06-BAOSTOCK-BINDING-TOLERANCE-01','P2','BAOSTOCK','baostock_strict_binding_matrix',[],False),
 ('A07','HISTORICAL_AS_RECORDED_ADJUSTED_PRICE','P2','HIST-AS-RECORDED','first_availability_lineage',[],True),
 ('A08','AUD-V4-09-REPAIR-FREEZE-SELF-VALIDATION-N01','P2','V4-09-N01','src/v4/stock_prewatch.py',[],False),
 ('A09','AUD-V4-09-DB-CONSUMER-IDENTITY-N02','P2','V4-09-N02','src/v4/stock_prewatch_persistence.py',[],False)]
PLANS={
 'A01':'Export nine target-date adapters around pinned accepted domain runtimes; target-only staging, parent/source/calendar binding, independent postcheck and atomic rollback. Real next completed-session candidate must pass independent external acceptance before Data Head promotion.',
 'A02':'Immutable accepted RPS history T/T-1/T-3 chain, declared revision/universe/calendar/cutoff; independently recompute deltas and warm-up; then rerun unchanged V4-07.',
 'A03':'Daily builder, gap/revision/late-source detectors and immutable append from the first accepted PIT date. Implement automation in this WP; future observations accumulate naturally, never retrospectively invent availability.',
 'A04':'Freeze source/unit/20-session denominator/coverage/concentration with independent arithmetic and repo-wide consumer inventory; dependent formal paths stay disabled.',
 'A05':'Archaeology first. Recover exact missing_state/validity and golden examples or publish an explicitly non-equivalent replacement with B2 retirement/migration.',
 'A06':'Representative board/date matrix and official unit/denominator evidence; derive tolerance from generation/rounding mechanism, never fit arbitrary percentages.',
 'A07':'Capture first_available_at/source_revision/knowledge_time for GBBQ/provider/manual records; unverifiable pre-capture history remains permanently capability-blocked.',
 'A08':'Independent wrong-status/authority/binding-set/file/consumer/parent negative vectors; accepted replay bytes/logical digest unchanged; hardening only.',
 'A09':'New unused migration (024 reserved for V4-10 R1.2); old rows/readback, immutable consumer identity, collision/revision rejection and exact rollback. Preserve historical 021.'}
def main():
    for name in [MASTER,'V4_10_R1_2_EXTERNAL_REAUDIT_REPAIR_TASK_20261001.md']:
        atomic_bytes(ROOT/'docs/evidence'/name,(Path(r'D:\Users\lps\Desktop')/name).read_bytes())
    head=bind('data/v4/V4_DATA_ACCEPTED_HEAD.json');stage=bind('data/v4/V4_STAGE_ACCEPTED_HEAD.json')
    entries=[]
    for number,audit,priority,label,owner,deps,time in ITEMS:
        wp='WP-'+number+'-'+label;task=f'docs/evidence/cross_stage/{wp}/TASK_R1.md';status=f'reports/audits/work_packages/{wp}/STATUS_R1.json'
        text=f'# {wp} formal work package\n\nAuthority: {MASTER}; scope and requirements remain the corresponding A-item, not a replacement formula.\n\nAudit: {audit}. Priority: {priority}. Owner: {owner}.\n\nImplementation plan: {PLANS[number]}\n\nDependencies: {", ".join(deps) or "accepted baseline only"}. Does not block unrelated engineering stages.\n\nEngineering contract/schema/synthetic replay can proceed immediately. Real observation accumulation required: {time}; no estimate of days and no wait before unrelated development.\n\nAcceptance: independent scope evidence, clean regression, candidate closure, then STOP for independent external audit. OPEN capabilities remain unavailable to production; no production/shadow/Focus permission. Preserve accepted heads, source roots, old artifacts and migrations.\n'
        atomic_bytes(ROOT/task,text.encode('utf8'))
        value=dict(work_package=wp,audit_id=audit,priority=priority,status='OPEN',implementation_status='IMPLEMENTATION_ENTRY_AUTHORIZED' if number in ('A01','A08','A09') else 'QUEUED_FORMAL_WORK_PACKAGE',
            owner_module=owner,depends_on=deps,does_not_block_engineering_stage=True,production_gate=True,formal_consumer_authorization=False,
            task=bind(task),evidence=[],external_acceptance=None,next_step=PLANS[number],requires_real_observation_accumulation=time,
            engineering_can_proceed_immediately=True,history_reconstruction_prohibited=True)
        atomic_json(ROOT/status,value);entries.append(dict(**value,status_path=status))
    registry=dict(contract_id='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1',status='PASS_MASTER_GOVERNANCE_ENTRY',
        authority=bind('docs/evidence/'+MASTER),baseline_commit='db6319856468c6788c9dd656da3992e569a64572',audit_count=9,entries=entries,
        data_head=head,stage_head=stage,main_engineering_lane='V4-10 R1.2 independent; V4-11 blocked until its external acceptance/promotion entry',
        dependency_graph={e['work_package']:e['depends_on'] for e in entries},first_work_package='WP-A01-DM01',
        permissions=dict(production=False,shadow=False,focus_cutover=False),governance_only=True,all_capabilities_remain_unaccepted=True,
        next_stage='WP-A01 implementation; A08/A09 entries ready; each WP commits/pushes and stops independently for external acceptance')
    atomic_json(ROOT/'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json',registry)
    for number,path in [('A01','reports/dm01/DM01_INCREMENTAL_BUILDERS_REPAIR_ENTRY_R1.json'),('A08','reports/v4_09/V4_09_N01_HARDENING_ENTRY_R1.json'),('A09','reports/v4_09/V4_09_N02_CONSUMER_IDENTITY_ENTRY_R1.json')]:
        value=next(e for e in entries if e['work_package'].startswith('WP-'+number+'-'))
        atomic_json(ROOT/path,dict(status='PASS_IMPLEMENTATION_ENTRY_ONLY',work_package=value,authority=registry['authority'],data_head=head,stage_head=stage,
            accepted_runtime_registry=bind('config/v4_dm01_accepted_builder_registry_v1.json') if number=='A01' else bind('reports/v4_09/V4_09_R1_1_STAGE_CANDIDATE_MANIFEST.json'),
            next_stage=value['next_step'],external_acceptance=None,capability_implemented=False))
    atomic_bytes(ROOT/'docs/evidence/V4_CROSS_STAGE_REMEDIATION_MASTER_ENTRY_20261001.md',
        ('# Cross-stage remediation master first entry\n\nAll nine audits now have explicit owners, formal task/status paths, dependencies and independent external acceptance gates. First-execution scope is Master §40; this entry implements governance only and does not claim nine capability repairs.\n\nA01/A08/A09 implementation entries are ready. A01 is first. A02/A03 and first-availability history need authentic observations; their code/contracts can be built immediately without waiting for history. A04/A05/A06 are independent evidence/algorithm work. All OPEN production-dependent paths remain unauthorized.\n\nThe master registry is independent of V4-10 R1.2. No accepted head or historical migration changed. Commit/push this first-entry package; continue V4-10 repair separately.\n').encode('utf8'))
    assert len(entries)==9 and len({e['audit_id'] for e in entries})==9
    assert bind(head['path'])==head and bind(stage['path'])==stage
    assert all((ROOT/e['task']['path']).exists() and (ROOT/e['status_path']).exists() and e['external_acceptance'] is None for e in entries)
    print('PASS: 9 formal WP entries; A01/A08/A09 entry only; no capability or accepted head promotion')
if __name__=='__main__':main()
