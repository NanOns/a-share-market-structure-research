"""R27 static contract authoring only; never connects to a database."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'c1787b77e08a26e344d3cbb88148a60f93c3df3e'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    target = ROOT / path
    assert path.startswith(('config/v4_18_', 'reports/r27/', 'docs/evidence/r27/'))
    target.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n'
    stage = target.with_name(target.name+'.r27-staging')
    with stage.open('wb') as stream:
        stream.write(data.replace('\r\n', '\n').encode('utf8'))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stage, target)


def build():
    documents = []
    for name in ('V4_NEXT_ROUND_EXECUTION_MASTER_R27_20261004.md', 'V4_18_R27_MIGRATION_REPLAY_CONTRACT_DESIGN_TASK_20261004.md', 'V4_R26_V4_17_SHADOW_UI_ENGINEERING_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'):
        source = Path('D:/Users/lps/Desktop/阶段任务') / name
        documents.append(dict(path=str(source), sha256=sha(source), repository_copy='docs/evidence/r27/'+name))
        write(documents[-1]['repository_copy'], source.read_text(encoding='utf8'))
    upgrade = 'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
    write('reports/r27/STAGE_CONTRACT.json', dict(stage='V4-18', mode='CONTRACT_DESIGN_ONLY', baseline=BASE, documents=documents, upgrade=dict(path=upgrade, sha256=sha(ROOT/upgrade), sections=['52A', '77', '78', '81.4', '83']), allowed=['config/v4_18_*', 'tests/test_v4_18_migration_contract.py', 'reports/r27/*', 'docs/evidence/r27/*'], forbidden=['production writer', 'database migration', 'TDX writes', 'accepted heads', 'source cutover'], acceptance='PENDING_LOCAL_DESIGN_VALIDATION', next_stage='STOP_WAIT_R27_INDEPENDENT_EXTERNAL_AUDIT'))
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True, encoding='utf8').splitlines()
    protected = {name: sha(ROOT/name) for name in names if (ROOT/name).is_file()}
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode('utf8').split('\0')
    unrelated = {name: sha(ROOT/name) for name in untracked if name and not name.startswith(('reports/r27/', 'docs/evidence/r27/', 'config/v4_18_', 'tests/test_v4_18_'))}
    write('reports/r27/PROTECTED_BASELINE.json', dict(baseline=BASE, tracked=protected, unrelated=unrelated))
    matrix = []
    # Inventory every repository-declared table: no assumption that these schemas are deployed.
    sources = list((ROOT/'src/workbench_db').rglob('*.sql'))+[ROOT/'migrations/v4_16_r24_real_shadow_v1.sql']
    for source in sorted(sources):
        for table in re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)', source.read_text(encoding='utf8'), re.I):
            relative = source.relative_to(ROOT).as_posix()
            shadow = relative.startswith('migrations/v4_16_r24')
            focus = 'focus_' in table
            ns = 'SHADOW_V4' if shadow or table.startswith('v4.') else 'V3_FOCUS' if focus else 'LEGACY_PRODUCTION'
            matrix.append(dict(state_or_table=table, declaration=relative, declaration_sha256=sha(source), read_source=ns, source_binding='ACCEPTED_SNAPSHOT_EXACT_TABLE_PK_AND_ROW_DIGEST; DECLARATION_IS_NOT_DEPLOYMENT_PROOF', write_target=None, disposition='REFERENCE', immutable_source_identity=['namespace', 'accepted_snapshot_digest', 'table', 'native_primary_key', 'row_digest'], target_identity_rule='PRESERVE_NATIVE_ID_IN_NAMESPACE_QUALIFIED_REFERENCE; NEVER_RELABEL_HISTORY', rollback='KEEP_SOURCE_AND_REFERENCE; RESTORE_ACCEPTED_LEGACY_ROUTING_ONLY'))
    semantic = {
        'prestate': ('SHADOW_V4', 'CARRY', ['model_contract_id', 'parameter_set_id', 'state_lineage_id', 'publication_id', 'publication_revision', 'state_digest']),
        'open_episode': ('SHADOW_V4', 'CARRY', ['logical_event_id', 'episode_id', 'T0', 'current_state', 'enrollment_id', 'control_assignment_ids', 'benchmark_ids', 'source_lineage']),
        'pending_settlement': ('SHADOW_V4', 'CARRY', ['enrollment_id', 'horizon', 'due_date', 'frozen_T0', 'control_assignment_ids', 'benchmark_ids', 'outcome_status', 'evaluation_revision', 'future_source_policy']),
        'algorithm_eligibility': ('SHADOW_V4', 'REFERENCE', ['publication_id', 'logical_event_id', 'eligibility_contract_id']),
        'system_selected_focus': ('V3_FOCUS', 'NOT_MIGRATED', ['focus_run_id', 'source_item_key', 'source_item_digest']),
        'user_pin': ('V3_FOCUS', 'CARRY', ['user_pin_id', 'user_identity', 'entity_id', 'created_at', 'revision', 'source_namespace']),
        'manual_notes_followup': ('V3_FOCUS', 'CARRY', ['user_work_id', 'user_identity', 'entity_id', 'revision', 'content_digest']),
        'historical_shadow_context': ('SHADOW_V4', 'REFERENCE', ['context_token', 'publication_id', 'publication_revision', 'readback_manifest_digest']),
        'legacy_gap_activity': ('LEGACY_PRODUCTION', 'CARRY', ['source_sequence', 'native_id', 'revision', 'payload_digest']),
        'shadow_gap_activity': ('SHADOW_V4', 'REFERENCE', ['source_sequence', 'native_id', 'revision', 'payload_digest']),
    }
    for name, (ns, disposition, fields) in semantic.items():
        matrix.append(dict(state_or_table='SEMANTIC:'+name, declaration='DESIGN_ONLY_NOT_CREATED', read_source=ns, write_target='V4_PRODUCTION_FUTURE' if disposition=='CARRY' else None, disposition=disposition, immutable_source_identity=fields, target_identity_rule='NAMESPACE_QUALIFIED_MAPPING_WITH_NATIVE_ID_UNCHANGED; PHYSICAL_TARGET_SCHEMA_REQUIRES_EXTERNAL_ACCEPTANCE', rollback='PRESERVE_FACTS_OBLIGATIONS_AND_USER_WORK; RECONCILE_GAP', adapter_status='UNBOUND_BLOCKS_AFFECTED_SCOPE; USER_WORK_NATIVE_EXPORT_MUST_BE_INDEPENDENTLY_ACCEPTED' if name in ('user_pin','manual_notes_followup') else 'FUTURE_EXACT_SNAPSHOT_BINDING_REQUIRED'))
    identities = dict(migration_run_id='SHA256_CANONICAL_JSON(contract_digest,source_snapshot_digest,source_head_digest,expected_target_head,cutover_authority_id)', source_head_digest='EXACT_ACCEPTED_HEAD_AND_REVISION_SET_AT_SNAPSHOT', expected_target_head='EXPLICIT_NULL_FOR_INITIAL_OR_EXACT_ACCEPTED_HEAD_VERSION', event_id='KEEP_LOGICAL_EVENT_ID', enrollment_id='KEEP_ORIGINAL_COHORT_V1_ID; NO_SECOND_ORIGINAL', due_id='KEEP_NATIVE_ID_AND_UNIQUE(enrollment_id,horizon)', user_pin_id='KEEP_NATIVE_USER_PIN_ID_AND_REVISION; NO_HEURISTIC_MATCH')
    contract = dict(contract_id='V4_18_MIGRATION_REPLAY_CONTRACT_V1', version='1.0.0', stage='V4-18', mode='CONTRACT_DESIGN_ONLY', baseline=BASE, status='LOCAL_DESIGN_PENDING_EXTERNAL_AUDIT', namespaces=['LEGACY_PRODUCTION','V3_FOCUS','SHADOW_V4','V4_PRODUCTION_FUTURE'], namespace_matrix=matrix, identities=identities,
        canonical_identity_encoding='UTF8_JSON_SORTED_KEYS_COMPACT_SEPARATORS_NO_NAN; TYPED_VALUES_AND_EXPLICIT_NULL; SHA256',
        prestate=dict(first_production='EXACT_LAST_ACCEPTED_SHADOW_PRESTATE_WITH_EXPLICIT_MIGRATION_MANIFEST_AND_EPISODE_MAPPING; SAME_MODEL_LINEAGE_ONLY', subsequent='EXACT_PRIOR_ACCEPTED_V4_PRODUCTION_HEAD', model_change='MODEL_BOUNDARY_NEW_COHORT; OLD_EPISODES_AND_PENDING_OUTCOMES_PRESERVED', initialization='RECONSTRUCTED_ASOF_MAY_INITIALIZE_STATE; NEVER_PIT_OBSERVED_ENROLLMENT_OR_REAL_SAMPLE', missing_predecessor='BLOCKED_AFFECTED_SCOPE'),
        open_episode=dict(preserve=semantic['open_episode'][2], original='ONE_ORIGINAL_PER_LOGICAL_EVENT; REPLAY_MUST_REFERENCE_EXISTING_ENROLLMENT', missing_original='BLOCKED_AFFECTED_SCOPE', exit='FOLLOWUP_AND_SETTLEMENT_CONTINUE_AFTER_EXIT_OR_INVALIDATION'),
        pending_settlement=dict(preserve=semantic['pending_settlement'][2], source_policy='ONLY_ACCEPTED_AS_OF_EVALUATION_AVAILABLE_AT; NEVER_USE_FUTURE_SOURCE_FOR_T0', revisions='APPEND; KEEP_FIRST_OBSERVED_AND_LATEST_CORRECTED_SEPARATE; NEVER_OVERWRITE_FROZEN_T0', unavailable='KEEP_DUE_BACKLOG_WITH_REASON; NEVER_REDRAW_CONTROLS_OR_BENCHMARKS', identity_contracts=['COHORT_V1','OUTCOME_REVISION_V1']),
        focus_user_state=dict(lanes=['algorithm_eligibility','system_selected_focus','user_pin','manual_notes_followup'], algorithm_evidence_excludes=['user_pin','manual_notes_followup','UI_TOP_K','display_cap'], preserve_user_work=True, unbound_native_user_export='BLOCKED_AFFECTED_SCOPE; NO_INVENTED_EXISTING_USER_PIN_TABLE', permissions='USER_OWNERSHIP_AND_ACCESS_SCOPE_UNCHANGED; AMBIGUOUS_OWNER_BLOCKED'),
        historical_context=dict(policy='IMMUTABLE_QUERYABLE_IN_SHADOW_V4; NEVER_RELABEL_TO_PRODUCTION', identity_fields=json.loads((ROOT/'config/v4_17_shadow_ui_contract_v1.json').read_text(encoding='utf8')).get('context_identity_fields', []), exact_binding='ORIGINAL_CONTEXT_TOKEN_AND_MANIFEST_DIGEST; NO_LATEST_OR_MTIME_DISCOVERY'),
        idempotency=dict(key=list(identities), identical='RETURN_SAME_ACCEPTED_RECEIPT_NO_DUPLICATE_EVENT_ENROLLMENT_DUE_PIN', changed_payload_same_id='IDEMPOTENCY_CONFLICT_BLOCKED_AFFECTED_SCOPE', transaction='FUTURE_ATOMIC_APPEND_FACTS_RECEIPT_AND_EXPECTED_TARGET_HEAD_CAS; CAS_FAILURE_NO_PARTIAL_ACCEPTANCE', source_changed='REJECT_STALE_PLAN; NEW_ACCEPTED_SNAPSHOT_OR_EXPLICIT_ACCEPTED_GAP_MANIFEST_REQUIRED'),
        gap_policy=dict(interval='(ACCEPTED_SNAPSHOT_WATERMARK, FINAL_CUTOVER_WATERMARK] PER_SOURCE_NAMESPACE', activity=['Legacy writes','Shadow publications','outcomes and corrections','user pins','manual notes','followup observations'], manifest_fields=['source_namespace','snapshot_digest','start_watermark','end_watermark','ordered_native_ids_and_revisions','payload_digests','counts_by_kind','missing_ranges','mapping_dispositions','reconciliation_digest','authority_receipt'], acceptance='ALL_SOURCE_ACTIVITY_ACCOUNTED_EXACTLY_ONCE_OR_EXPLICIT_REFERENCE; COUNT_AND_DIGEST_EQUALITY; GAPS_CONFLICTS_BLOCK_AFFECTED_SCOPE', concurrent='FENCE_NEW_WRITES_WITH_ACCEPTED_AUTHORITY; RESCAN_FINAL_WATERMARK_BEFORE_CAS', forbidden='RESTORE_ONE_BACKUP_AND_IGNORE_GAP'),
        rollback=dict(owner='EXPLICIT_EXTERNALLY_ACCEPTED_CUTOVER_ROLLBACK_AUTHORITY_ID; UNBOUND_BLOCKS_IMPLEMENTATION', order=['stop new V4 production writes under authority fence','capture final watermarks and preserve accepted V4/Shadow facts','reconcile all cutover-gap activity including user work and due obligations','restore accepted Legacy read/write source using CAS','append rollback receipt with final gap manifest and pending ownership mapping'], retain=['accepted V4 history','Shadow history and context tokens','pending settlements and revisions','user pins notes followup','outbox and accepted receipts'], forbidden=['delete accepted facts','redraw controls','drop due obligations','backup-only restore'], settlement_owner='EXACTLY_ONE_AUTHORIZED_WORKER_PER_EXISTING_DUE_ID; TRANSFER_OWNERSHIP_RECEIPT_NO_NEW_ENROLLMENT'),
        unknown_conflicts={k:'BLOCKED_AFFECTED_SCOPE' for k in ['identity_collision','missing_original','control_benchmark_mismatch','due_date_mismatch','user_pin_ambiguity','namespace_collision','missing_source_binding','target_CAS_conflict','source_head_changed','missing_gap_range']},
        implementation_entry=dict(status='BLOCKED_WAIT_REAL_SHADOW_GATE', required_all=['externally accepted real V4-16 Shadow publication','accepted V4-17 real readback binding','accepted migration source snapshot','accepted target storage contract','accepted cutover/rollback authority'], receipts=[None]*5, real_observations=0),
        permissions=dict(runtime_implemented=False, production_writer=False, migration_execution=False, production_focus_cutover=False, migration_replay_pass='NOT_GRANTED', v4_18_accepted_head=None),
        carry=dict(R25_REAL_ACTIVATION_PACKET='WAIT_ACCEPTED_DAILY_INPUT', V4_17_ENGINEERING='EXTERNALLY_ACCEPTED', V4_17_FINAL_ACCEPTANCE='NOT_GRANTED', R26_A01='OPEN_NONBLOCKING_HISTORICAL_DEBT'), next_stage='STOP_WAIT_R27_INDEPENDENT_EXTERNAL_AUDIT')
    contract['historical_context']['identity_fields'] = ['namespace','trade_date','publication_id','publication_revision','model_contract_id','parameter_set_id','state_lineage_id','daily_input_digest','source_manifest_digest','evidence_origin','readback_manifest_digest']
    contract['namespace_binding_policy'] = 'TABLE INVENTORY IS DECLARATION COVERAGE ONLY; read_source IS PROPOSED DESIGN ROLE, NOT CURRENT DEPLOYMENT AUTHORITY. Exact accepted snapshot must bind each physical database/table and row namespace; contrary binding blocks affected scope until independently accepted mapping. No source database is opened in R27.'
    interface_specs = [
        ('MigrationSnapshotReader',['accepted_source_snapshot_receipt','exact_heads','table_inventory','watermarks'],['immutable_snapshot_digest','native_identity_rows','coverage_manifest'],'READ_ONLY_EXACT_ACCEPTED_SOURCE; NO_DISCOVERY'),
        ('MigrationPlanBuilder',['snapshot_digest','contract_digest','expected_target_head','accepted_authorities'],['immutable_plan_digest','identity_mapping','obligation_mapping','conflicts'],'PURE_PLAN; NO_DATABASE_WRITE'),
        ('MigrationReplayWriter',['accepted_plan_digest','migration_run_id','expected_target_head','accepted_entry_receipts'],['append_receipt','target_head_version','idempotency_receipt'],'FUTURE_ONLY_ATOMIC_APPEND_AND_CAS; NO_R27_IMPLEMENTATION'),
        ('MigrationGapReconciler',['snapshot_watermarks','final_watermarks','exact_activity_rows'],['gap_manifest_digest','coverage_by_namespace','unresolved_ranges'],'NO_SILENT_GAP; FAIL_CLOSED'),
        ('MigrationRollbackController',['accepted_rollback_authority','current_head','gap_manifest','pending_owner_mapping'],['routing_CAS_receipt','preservation_manifest','rollback_receipt'],'FENCE_AND_RESTORE_ROUTING; NEVER_DELETE_FACTS'),
        ('MigrationIndependentOracle',['source_snapshot','target_receipts','gap_manifest','rollback_receipts','contract_digest'],['identity_set_comparison','obligation_comparison','user_work_comparison','acceptance_scope'],'INDEPENDENT_SOURCE_TARGET_RECONCILIATION; NOT_WRITER_SELF_REPORT'),
    ]
    contract['future_interfaces'] = [dict(name=n, version='1.0.0', inputs=i, outputs=o, policy=p, implemented=False, failure='BLOCKED_AFFECTED_SCOPE_WITH_REASON_AND_NO_PARTIAL_ACCEPTANCE', producer_time='EXACT_ACCEPTED_INPUT_REVISION; OUTPUT_RECEIPT_AVAILABLE_AT_AND_AUTHORITY_REQUIRED') for n,i,o,p in interface_specs]
    vector_rows = [
        ('clean pre-state inheritance','same model exact accepted Shadow head','prestate','PASS_DESIGN_EXPECTATION','target predecessor digest equals source state digest'),
        ('first production predecessor','empty production head and accepted Shadow predecessor','prestate','PASS_DESIGN_EXPECTATION','explicit null expected target; exact Shadow predecessor mapping'),
        ('open episode preserved','open episode with original enrollment and frozen T0','open_episode','PASS_DESIGN_EXPECTATION','event episode T0 enrollment controls benchmarks source lineage equal'),
        ('duplicate original rejected','same logical event with second original enrollment','open_episode','BLOCKED_AFFECTED_SCOPE','no accepted second original'),
        ('pending due preserved','unsettled accepted due obligation','pending_settlement','PASS_DESIGN_EXPECTATION','same enrollment horizon due date frozen references and status'),
        ('settlement revision preserved','first observed plus corrected outcome revision','pending_settlement','PASS_DESIGN_EXPECTATION','all revisions retained; first observed unchanged'),
        ('user pin preserved','native user pin with unambiguous owner and revision','focus_user_state','PASS_DESIGN_EXPECTATION','pin id owner entity revision preserved'),
        ('algorithm Focus vs user pin separated','pinned entity without algorithm eligibility','focus_user_state','PASS_DESIGN_EXPECTATION','no enrollment or algorithm evidence created from pin'),
        ('namespace mismatch blocked','Shadow fact submitted as production fact','unknown_conflicts','BLOCKED_AFFECTED_SCOPE','no history relabel or target acceptance'),
        ('rerun idempotent','identical migration run plan and source digests','idempotency','PASS_DESIGN_EXPECTATION','same receipt; no extra event enrollment due or user pin'),
        ('source head changed after snapshot','source digest changed without accepted gap receipt','idempotency','BLOCKED_AFFECTED_SCOPE','stale plan rejected before target acceptance'),
        ('target-head CAS conflict','actual target head differs from expected head','idempotency','BLOCKED_AFFECTED_SCOPE','no partial append or head acceptance'),
        ('Legacy cutover-gap activity','Legacy outcome pin and note writes after snapshot','gap_policy','PASS_DESIGN_EXPECTATION','ordered ids revisions counts digests reconciled through final watermark'),
        ('Shadow cutover-gap activity','Shadow publication and outcome revisions after snapshot','gap_policy','PASS_DESIGN_EXPECTATION','exact reference coverage; no production history relabel'),
        ('rollback preserves V4 history','accepted V4 history before rollback','rollback','PASS_DESIGN_EXPECTATION','accepted fact digests retained after routing restore'),
        ('rollback preserves pending settlement','accepted uncompleted due when rollback begins','rollback','PASS_DESIGN_EXPECTATION','same due id frozen references retained; exactly one authorized owner'),
        ('rollback preserves user pins','pins notes followup created during cutover gap','rollback','PASS_DESIGN_EXPECTATION','user work union retained with owner and revision'),
        ('reconstructed initialization not promoted to PIT','RECONSTRUCTED_ASOF initialization','prestate','PASS_DESIGN_EXPECTATION','origin unchanged; real observed sample count unchanged'),
        ('historical context token remains queryable','old exact Shadow context token after cutover or rollback','historical_context','PASS_DESIGN_EXPECTATION','same 11-field identity and readback manifest digest'),
        ('implicit latest/mtime migration source forbidden','snapshot inferred using newest path or mtime','historical_context','BLOCKED_AFFECTED_SCOPE','no source accepted without explicit pinned authority'),
    ]
    contract['vectors'] = [dict(id=f'M{index:02}', name=name, given=given, contract_section=section, expected=expected, independent_oracle=oracle, evidence_required=['accepted source snapshot and native identity rows','future target receipts or rejection receipt','independent set/digest comparison'], execution='DECLARATIVE_CONTRACT_VECTOR_NOT_RUNTIME_TEST', affected_scope='exact namespace and entity/episode/enrollment/user ownership key') for index,(name,given,section,expected,oracle) in enumerate(vector_rows,1)]
    write('config/v4_18_migration_replay_contract_v1.json', contract)
    mappings = dict(NAMESPACE_MATRIX='namespace_matrix', PRESTATE_INHERITANCE_GATE='prestate', OPEN_EPISODE_GATE='open_episode', PENDING_SETTLEMENT_GATE='pending_settlement', FOCUS_USER_STATE_GATE='focus_user_state', CUTOVER_GAP_POLICY='gap_policy', ROLLBACK_CONTRACT_GATE='rollback', MIGRATION_VECTOR_REGISTRY='vectors', IMPLEMENTATION_ENTRY_GATE='implementation_entry')
    for report, section in mappings.items():
        write('reports/r27/'+report+'.json', dict(contract='config/v4_18_migration_replay_contract_v1.json', contract_sha256=sha(ROOT/'config/v4_18_migration_replay_contract_v1.json'), section=section, scope='DESIGN_COMPLETENESS_ONLY_NOT_RUNTIME_ACCEPTANCE', definition=contract[section]))


if __name__ == '__main__':
    build()
