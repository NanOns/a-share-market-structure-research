"""Current action-contract five-session Focus replay and new PG journal evidence."""
import concurrent.futures
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
WORK = Path('G:/codex_tmp/r4_r3_pg_publication_v2')
LABEL=sys.argv[1] if len(sys.argv)>1 else 'R1'
if not LABEL.isalnum():raise ValueError('VERSIONED_RUN_LABEL_REQUIRED')
OUT = ROOT / ('docs/audits/v4_full_closeout_20261012/focus' if LABEL=='R1' else 'docs/audits/v4_full_closeout_20261012/focus_'+LABEL)
RUN = WORK / ('runtime/v4_full_closeout_focus_20261012' if LABEL=='R1' else 'runtime/v4_full_closeout_focus_20261012_'+LABEL)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    from scripts.r4_readonly_source_guard import install
    install(['G:/codex work/大A交易', 'D:/new_tdx'])
    from focus_tracker.v4_exact_identity_adapter_r4 import AcceptedPaths, ACTION_CONTRACT
    from focus_tracker.v4_native_core_adapter import enriched_project
    from focus_tracker.v4_native_core_journal import append
    from workbench_db.v4_series_pg_r1 import verified_series_scope
    from workbench_db.v4_journal_pg_r1 import open_read
    from workbench_service.current_v4_context import canonical, SourceInvalid
    OUT.mkdir(parents=True, exist_ok=False)
    RUN.mkdir(parents=True, exist_ok=False)
    record = json.loads((ROOT/'docs/audits/r4_r3_local_delivery_20261012/S1_IDENTITY_REPAIR_R2/RESULT.json').read_bytes())
    def load(binding):
        p = (WORK/binding['path']).resolve()
        assert p.is_relative_to(WORK.resolve()) and sha(p) == binding['sha256']
        return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())
    frozen = load(record['result']['focus'])
    bindings = dict(frozen['source_bindings'])
    bindings['implementation'] = dict(bindings.get('implementation', {}))
    for name in bindings['implementation']:
        source = ROOT/'src/focus_tracker'/f'{name}.py'
        dest = RUN/'implementation'/f'{name}.py'
        dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(source.read_bytes())
        bindings['implementation'][name] = dict(path=dest.relative_to(WORK).as_posix(), bytes=dest.stat().st_size, sha256=sha(dest))
    owners = record['result']['owners']
    days = {owner['trade_date']: load(owner['D2'])['rows'] for owner in owners}
    source_before = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT/'src/focus_tracker').glob('*.py')}
    (OUT/'SOURCE_BEFORE.json').write_text(json.dumps(source_before,indent=2),encoding='utf8')
    start = time.monotonic()
    with verified_series_scope():
        projection = enriched_project(days, AcceptedPaths(WORK, bindings))
    target = RUN/'CURRENT_ACTION_FOCUS.json.gz'
    target.write_bytes(gzip.compress(canonical(projection), mtime=0))
    journal = RUN/'journal.pg.json'
    receipts = []
    head = None
    for owner in owners:
        print(json.dumps(dict(phase='APPEND', day=owner['trade_date'])), flush=True)
        with verified_series_scope():
            receipt = append(journal, WORK, owner['D2'], head, path_inputs=bindings)
            head = receipt['head']
            repeated = append(journal, WORK, owner['D2'], head, path_inputs=bindings)
            assert repeated['status'] == 'NOOP' and repeated['head'] == head
        receipts.append(receipt)
    with open_read(journal) as db:
        actual = json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0])
        persisted = db.execute('SELECT day,source_digest FROM days ORDER BY day').fetchall()
    assert canonical(actual) == canonical(projection), 'FULL_JOURNAL_PROJECTION_MISMATCH'
    before = journal.read_bytes()
    try:
        append(journal, WORK, owners[-1]['D2'], '0'*64, path_inputs=bindings)
    except SourceInvalid as exc:
        assert str(exc) == 'JOURNAL_CAS_CONFLICT'
    else:
        raise AssertionError('STALE_CAS_ACCEPTED')
    assert journal.read_bytes() == before
    assert source_before == {str(p.relative_to(ROOT)): sha(p) for p in (ROOT/'src/focus_tracker').glob('*.py')}
    result = dict(contract_id='V4_FULL_CLOSEOUT_FOCUS_CURRENT_ACTION_V1', status='FIVE_SESSION_PROJECTION_JOURNAL_PASS',
                  action_contract=ACTION_CONTRACT, receipts=receipts, persisted_days=persisted,
                  episodes=len(projection['episodes']), events=len(projection['events']),
                  source_sha256=source_before, projection_sha256=sha(target), journal_sha256=sha(journal),
                  bindings=bindings, seconds=time.monotonic()-start,
                  limitations=['Independent oracle, full producer replay, concurrent CAS and restart evidence remain separate gates'],
                  production_changed=False)
    (OUT/'RESULT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','episodes','events','seconds')}), flush=True)

if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    # The entry itself owns its output directory, main refuses prior runs.
    OUT.rmdir()
    from scripts.r4_r3_consumer_trace import ConsumerTrace
    trace=ConsumerTrace(ROOT/'docs/audits/v4_full_closeout_20261012'/('FOCUS_56_TRACE_'+LABEL+'.json'),'Current exact action contract five-day projection and PG journal')
    trace.start()
    try:main()
    finally:trace.close()
