"""Normal native Focus journal append/readback in a new isolated namespace."""
import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
WORK = Path('G:/codex_tmp/r4_r3_pg_publication_v2')
OUT = ROOT / 'docs/audits/r4_r3_local_delivery_20261012/S1_JOURNAL'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    global OUT
    repaired = '--repaired' in sys.argv[1:]
    if repaired:
        OUT = OUT.with_name('S1_JOURNAL_REPAIRED')
    OUT.mkdir(parents=True, exist_ok=False)
    record = json.loads((ROOT / ('docs/audits/r4_r3_local_delivery_20261012/S1_IDENTITY_REPAIR_R2/RESULT.json' if repaired else 'docs/audits/r4_r3_consumers_20261011/FOCUS_RESUME_R1/RESULT.json')).read_bytes())
    oracle = json.loads((ROOT / 'docs/audits/r4_r3_local_delivery_20261012' / ('S1_ORACLE_REPAIRED' if repaired else 'S1_ORACLE') / 'RESULT.json').read_bytes())
    assert oracle['status'] == 'PASS_SCOPED'
    reference = WORK / record['result']['focus']['path']
    assert sha(reference) == record['result']['focus']['sha256']
    frozen = json.loads(gzip.decompress(reference.read_bytes()))
    bindings = frozen['source_bindings']
    protected = {p: sha(WORK / p) for p in record['protected_after']}
    for p, expected in record['protected_after'].items():
        assert protected[p] == expected
    os.environ.update(V4_NATIVE_PG_DSN='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres', R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data', R4_CONNECTION_LEDGER=str(OUT / 'PG_INTENTS.jsonl'))
    from tests import v4_native_isolation_plugin_r4 as guard
    config = SimpleNamespace()
    guard.pytest_configure(config)
    guard.ACTIVE = 'ACTUAL_FOCUS_NATIVE_JOURNAL_S1_LOCAL_RESUME'
    ledger = (OUT / 'PG_INTENTS.jsonl').open('x', encoding='utf8')

    class Streamed:
        count = 0

        def append(self, event):
            ledger.write(json.dumps(event, ensure_ascii=False) + '\n')
            self.count += 1
            if self.count % 100 == 0:
                ledger.flush()

    guard.EVENTS = Streamed()
    from focus_tracker.v4_native_core_journal import append
    from workbench_db.v4_journal_pg_r1 import open_read
    from workbench_db.v4_snapshot_pg_r2 import read
    from workbench_db.v4_series_pg_r1 import verified_series_scope
    from workbench_service.current_v4_context import canonical, SourceInvalid
    source_paths = ['src/focus_tracker/v4_native_core_journal.py', 'src/focus_tracker/v4_native_core_adapter.py', 'src/focus_tracker/v4_exact_identity_adapter_r4.py', 'scripts/publish_r4_r3_focus_journal_s1.py']
    source_before = {p: sha(ROOT / p) for p in source_paths}
    (OUT / 'ACTUAL_SOURCE_BINDINGS.json').write_text(json.dumps(source_before, indent=2) + '\n', encoding='utf8')
    path = WORK / ('runtime/local_focus_s1_repaired_20261012/journal.pg.json' if repaired else 'runtime/local_focus_s1_20261012/journal.pg.json')
    assert not path.exists()
    head, receipts, rollback, fail = None, [], None, None
    start = time.monotonic()
    try:
        for owner in record['result']['owners']:
            day = owner['trade_date']
            print(json.dumps(dict(phase='NATIVE_APPEND', day=day)), flush=True)
            before = path.read_bytes() if path.exists() else None
            if before is not None and (not repaired or day == record['result']['owners'][-1]['trade_date']):
                try:
                    with verified_series_scope():
                        append(path, WORK, owner['D2'], head, path_inputs=bindings, fail_after_append=True)
                except SourceInvalid as exc:
                    assert str(exc) == 'JOURNAL_INJECTED_FAILURE'
                else:
                    raise AssertionError('FAILURE_NOT_INJECTED')
                assert path.read_bytes() == before
                with open_read(path) as db:
                    assert db.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0] == head
                rollback = dict(status='PASS', descriptor_unchanged=True, pg_head_unchanged=True, day=day)
            with verified_series_scope():
                result = append(path, WORK, owner['D2'], head, path_inputs=bindings)
            head = result['head']
            receipts.append(result)
            # Replay must be an actual no-op on the same frozen input.
            repeated = append(path, WORK, owner['D2'], head, path_inputs=bindings)
            assert repeated['status'] == 'NOOP' and repeated['head'] == head
        with open_read(path) as db:
            actual = json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0])
            persisted_days = db.execute('SELECT day,source_digest FROM days ORDER BY day').fetchall()
        # The original replay adds explicit membership provenance and sector LOO
        # context after core projection. Compare every core field recursively,
        # retaining those additive source fields separately as immutable inputs.
        extra = set(('membership_mode taxonomy membership_snapshot_id membership_observed_at member_set_asof knowledge_lineage AS_RECORDED PIT_ELIGIBLE HISTORICAL_FIRST_AVAILABLE_PROVEN production_eligible_scope survivorship_bias_risk research_mainline_context').split())

        def normalized(value):
            if isinstance(value, dict):
                return {k: normalized(v) for k, v in value.items() if k not in extra}
            if isinstance(value, list):
                return [normalized(v) for v in value]
            return value

        expected = {k: frozen[k] for k in ('episodes', 'events')}
        expected_digest = hashlib.sha256(canonical(normalized(expected))).hexdigest()
        actual_digest = hashlib.sha256(canonical(normalized(actual))).hexdigest()
        assert expected_digest == actual_digest, 'NATIVE_JOURNAL_FULL_CORE_PROJECTION_DIFF'
        # Stale expected head must reject before publishing anything.
        before = path.read_bytes()
        try:
            append(path, WORK, record['result']['owners'][-1]['D2'], '0' * 64, path_inputs=bindings)
        except SourceInvalid as exc:
            assert str(exc) == 'JOURNAL_CAS_CONFLICT'
        else:
            raise AssertionError('STALE_CAS_ACCEPTED')
        assert path.read_bytes() == before
        with read(json.loads(before)) as db:
            assert json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0]) == actual
        result = dict(contract='R4_R3_FOCUS_NATIVE_JOURNAL_S1_V1', status='PASS_SCOPED', receipts=receipts, persisted_days=persisted_days, core_projection_sha256=actual_digest, reference_core_sha256=expected_digest, episodes=len(actual['episodes']), events=len(actual['events']), rollback=rollback, stale_cas_rejected=True, source_projection=record['result']['focus'], journal=dict(path=path.relative_to(WORK).as_posix(), bytes=path.stat().st_size, sha256=sha(path)), production_changed=False, external_acceptance='BLOCKED', full_semantics='OPEN_PREDICATE_INPUTS_AND_COMPANY_ACTION_REAL_CONSUMER_COVERAGE', normal_http_joint_head='OPEN_SEPARATE_CANDIDATE_STAGE')
    except BaseException as exc:
        import traceback
        result = dict(contract='R4_R3_FOCUS_NATIVE_JOURNAL_S1_V1', status='FAIL', error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc(), receipts=receipts, production_changed=False)
        fail = exc
    finally:
        guard.pytest_unconfigure(config)
        ledger.close()
    result.update(seconds=time.monotonic() - start, pg_intents=guard.EVENTS.count, protected_before=protected, protected_after={p: sha(WORK / p) for p in protected})
    result['source_before'] = source_before
    result['source_bytes_stable'] = source_before == {p: sha(ROOT / p) for p in source_paths}
    assert result['protected_before'] == result['protected_after']
    temp = OUT / 'RESULT.json.tmp'
    temp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    os.replace(temp, OUT / 'RESULT.json')
    print(json.dumps({k: result.get(k) for k in ('status', 'error', 'episodes', 'events', 'seconds', 'pg_intents')}), flush=True)
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(main())
