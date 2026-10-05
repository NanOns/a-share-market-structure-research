"""Static design checks; no migration runtime or production database access."""
import json
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
C = json.loads((ROOT/'config/v4_18_migration_replay_contract_v1.json').read_text(encoding='utf8'))


def test_permissions_are_design_only():
    assert C['mode'] == 'CONTRACT_DESIGN_ONLY'
    assert not any(C['permissions'][k] for k in ('runtime_implemented','production_writer','migration_execution','production_focus_cutover'))
    assert C['permissions']['migration_replay_pass'] == 'NOT_GRANTED'
    assert C['permissions']['v4_18_accepted_head'] is None
    assert C['implementation_entry']['receipts'] == [None]*5
    assert C['implementation_entry']['status'] == 'BLOCKED_WAIT_REAL_SHADOW_GATE'


def test_all_declared_tables_have_explicit_namespace_rules():
    sources = list((ROOT/'src/workbench_db').rglob('*.sql'))+[ROOT/'migrations/v4_16_r24_real_shadow_v1.sql']
    actual = {(p.relative_to(ROOT).as_posix(), t) for p in sources for t in re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)', p.read_text(encoding='utf8'), re.I)}
    rows = C['namespace_matrix']
    assert actual == {(r['declaration'],r['state_or_table']) for r in rows if r['declaration'] != 'DESIGN_ONLY_NOT_CREATED'}
    for r in rows:
        assert r['read_source'] in C['namespaces']
        assert r['write_target'] is None or r['write_target'] == 'V4_PRODUCTION_FUTURE'
        assert r['disposition'] in ('REFERENCE','CARRY','NOT_MIGRATED','COPY')
        assert r['immutable_source_identity'] and r['target_identity_rule'] and r['rollback']


@pytest.mark.parametrize('vector', C['vectors'], ids=lambda v:v['id'])
def test_declarative_vectors_bind_independent_oracle(vector):
    assert vector['contract_section'] in C
    assert vector['given'] and vector['independent_oracle'] and vector['affected_scope']
    assert len(vector['evidence_required']) == 3
    assert vector['execution'] == 'DECLARATIVE_CONTRACT_VECTOR_NOT_RUNTIME_TEST'


def test_vectors_and_future_interfaces_complete():
    assert [v['id'] for v in C['vectors']] == [f'M{i:02}' for i in range(1,21)]
    assert {v['id'] for v in C['vectors'] if v['expected']=='BLOCKED_AFFECTED_SCOPE'} == {'M04','M09','M11','M12','M20'}
    assert {v['name'] for v in C['future_interfaces']} == {'MigrationSnapshotReader','MigrationPlanBuilder','MigrationReplayWriter','MigrationGapReconciler','MigrationRollbackController','MigrationIndependentOracle'}
    assert all(not v['implemented'] and v['inputs'] and v['outputs'] for v in C['future_interfaces'])


def test_inheritance_obligations_and_rollback_are_explicit():
    assert {'logical_event_id','episode_id','T0','enrollment_id','control_assignment_ids','benchmark_ids','source_lineage'} <= set(C['open_episode']['preserve'])
    assert {'enrollment_id','horizon','due_date','frozen_T0','outcome_status','evaluation_revision','future_source_policy'} <= set(C['pending_settlement']['preserve'])
    assert len(C['historical_context']['identity_fields']) == 11
    assert C['focus_user_state']['preserve_user_work']
    assert 'user_pin' in C['focus_user_state']['algorithm_evidence_excludes']
    assert set(C['rollback']['retain']) == {'accepted V4 history','Shadow history and context tokens','pending settlements and revisions','user pins notes followup','outbox and accepted receipts'}
    assert 'missing_gap_range' in C['unknown_conflicts']
    assert all(v == 'BLOCKED_AFFECTED_SCOPE' for v in C['unknown_conflicts'].values())
