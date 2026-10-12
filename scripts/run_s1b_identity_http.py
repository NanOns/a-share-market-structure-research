"""S1-B bounded real-source regression and isolated default HTTP/Joint drill.

No production authority is changed. Does not admit other producers or S2.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
WORK = Path('G:/codex_tmp/r4_r3_pg_publication_v2')
OUT = ROOT / 'docs/audits/s1b_20261012'
RUN = Path('G:/codex_tmp/s1b_http_20261012_' + (sys.argv[1] if len(sys.argv) > 1 else 'R1'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic(path, value):
    from workbench_service.current_v4_context import canonical
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(canonical(value))
    os.replace(temp, path)


def checked(binding):
    path = (WORK / binding['path']).resolve()
    assert path.is_relative_to(WORK.resolve()) and sha(path) == binding['sha256']
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def main():
    import psycopg
    from focus_tracker.v4_exact_identity_adapter_r4 import AcceptedPaths, ACTION_CONTRACT
    from workbench_db.v4_series_pg_r1 import verified_series_scope
    from workbench_db.v4_snapshot_pg_r2 import Builder
    from workbench_db.v4_journal_pg_r1 import open_read
    from workbench_service.current_v4_context import canonical, digest, SourceInvalid
    from workbench_service.joint_release import activate, validate, AUTHORITY
    from workbench_service.production_v4 import ProductionV4ResearchReader, reference
    from workbench_service.v4_server import make_v4_handler

    OUT.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=False)
    source_paths = [Path(__file__).resolve(), ROOT / 'src/focus_tracker/v4_exact_identity_adapter_r4.py', ROOT / 'src/workbench_analysis/r43_focus_replay.py', ROOT / 'src/workbench_analysis/corrected_focus_replay.py']
    source_before = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as pg:
        directory = pg.execute('show data_directory').fetchone()[0]
        system = pg.execute('select system_identifier::text from pg_control_system()').fetchone()[0]
        assert directory.replace('\\', '/') == 'G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
        assert system == '7695278778933357404'
    prior = ROOT / 'docs/audits/r4_r3_local_delivery_20261012'
    record = json.loads((prior / 'S1_IDENTITY_REPAIR_R2/RESULT.json').read_bytes())
    old_record = json.loads((prior / 'S1_JOURNAL/RESULT.json').read_bytes())
    current = checked(record['result']['focus'])
    original = checked(old_record['source_projection'])
    delta = json.loads((prior / 'S1_IDENTITY_REPAIR_R2/NUMERICAL_DELTA.json').read_bytes())
    assert len(delta) == 101 and len({r['security'] for r in delta}) == 34
    protected = {p: sha(WORK / p) for p in record['protected_after']}
    assert protected == record['protected_after']
    bindings = current['source_bindings']
    samples = []
    episodes = {e['episode_id']: e for e in current['episodes']}
    with verified_series_scope():
        paths = AcceptedPaths(WORK, bindings)
        for row in delta:
            episode = episodes[row['episode']]
            obs = next(o for o in episode['observations'] if o['trade_date'] == row['date'])
            # The frozen path starts at the episode entry, including subsequent days.
            fact = paths.path(row['security'], episode['T0'], row['date'])
            assert fact['quality'] == 'READY' and fact['metrics'] == row['after']
            assert fact['metrics'] == obs['price_path']['metrics']
            samples.append(dict(row, T0=episode['T0'], actual=fact['metrics'], source_security_key=fact['source_security_key']))
    old_eps = {e['episode_id']: e for e in original['episodes']}
    assert old_eps.keys() == episodes.keys() and len(episodes) == 2805
    outcome_changes, predicate_changes = [], []
    for eid, ep in episodes.items():
        old = old_eps[eid]
        assert len(old['outcomes']) == len(ep['outcomes'])
        for left, right in zip(old['outcomes'], ep['outcomes']):
            assert left['anchor_id'] == right['anchor_id'] and left['horizon'] == right['horizon']
            assert left['outcome_status'] == right['outcome_status']
            if left['metrics'] != right['metrics']:
                outcome_changes.append(dict(episode=eid, before=left, after=right))
        for left, right in zip(old['observations'], ep['observations']):
            assert left['trade_date'] == right['trade_date']
            if left['predicate_evidence'] != right['predicate_evidence']:
                predicate_changes.append(dict(episode=eid, before=left, after=right))
    assert len(outcome_changes) == 49 and len(predicate_changes) == 4
    atomic(OUT / 'FROZEN_REGRESSION.json', dict(contract='S1B_FIXED_REAL_SOURCE_COUNTEREXAMPLES_V1',
        source_projection=record['result']['focus'], original_projection=old_record['source_projection'],
        observations=samples, outcome_changes=outcome_changes, predicate_changes=predicate_changes,
        outcome_proof='FROZEN_OUTPUT_DIFFERENCE_ONLY_NOT_NEW_SETTLEMENT_PRODUCER_ACCEPTANCE'))
    journal_receipt = json.loads((prior / 'S1_JOURNAL_REPAIRED/RESULT.json').read_bytes())
    journal = WORK / journal_receipt['journal']['path']
    assert sha(journal) == journal_receipt['journal']['sha256']
    with open_read(journal) as db:
        stored = json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0])
    provenance = set(('membership_mode taxonomy membership_snapshot_id membership_observed_at member_set_asof knowledge_lineage AS_RECORDED PIT_ELIGIBLE HISTORICAL_FIRST_AVAILABLE_PROVEN production_eligible_scope survivorship_bias_risk research_mainline_context').split())
    def normalized(value):
        if isinstance(value, dict):
            return {k: normalized(v) for k, v in value.items() if k not in provenance}
        if isinstance(value, list):
            return [normalized(v) for v in value]
        return value
    for eid in {r['episode'] for r in delta}:
        ep = next(e for e in stored['episodes'] if e['episode_id'] == eid)
        assert normalized(ep['outcomes']) == normalized(episodes[eid]['outcomes'])

    def candidate(version):
        release = 's1b-' + version
        folder = RUN / release
        folder.mkdir()
        scoped = [episodes[eid] for eid in sorted({r['episode'] for r in delta})]
        features = dict(current, episodes=scoped, events=[e for e in current['events'] if e['episode_id'] in {ep['episode_id'] for ep in scoped}])
        meta = dict(release_id=release, context=dict(accepted_trade_date='2026-10-09', data_updated_at='2026-10-09T15:00:00+08:00', knowledge_lineage='RECONSTRUCTED_CORRECTED'),
            source_contract_digest=digest(canonical(bindings)), quality='QUALITY_DEGRADED', sources={},
            domain_features=dict(focus=features), counts={'focus': 34}, gaps=[], field_registry={}, owners={},
            publication_scope='S1B_34_REAL_SECURITIES_ENGINEERING_ONLY', metadata=dict(owner='S1B_SCOPED_FROZEN_FOCUS_READ', release_id=release,
                source_snapshot=record['result']['focus']['sha256'], contract_version='1.0.0', source_as_of='2026-10-09T15:00:00+08:00',
                trading_date='2026-10-09', input_digest=digest(canonical(bindings)), published_at=datetime.now(timezone.utc).isoformat(),
                evidence_origin='REAL_ACCEPTED_SOURCE', evidence_state='VALIDATION_ONGOING', data_quality_state='QUALITY_DEGRADED', knowledge_lineage='RECONSTRUCTED_CORRECTED'))
        builder = Builder(folder, release)
        try:
            builder.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id));CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id));CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security));CREATE TABLE metadata(key text PRIMARY KEY,value text);')
            for ep in scoped:
                builder.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)', ('focus', ep['episode_id'], ep['entity_id'], paths.symbols[ep['entity_id']], 'UNKNOWN', canonical(ep).decode()))
            builder.execute('INSERT INTO metadata VALUES(?,?)', ('snapshot', canonical(meta).decode()))
            descriptor = builder.seal(meta)
            builder.commit()
        finally:
            builder.close()
        atomic(folder / 'snapshot.pg.json', descriptor)
        atomic(folder / 'journal.pg.json', json.loads(journal.read_bytes()))
        meta['database'] = reference(RUN, folder / 'snapshot.pg.json')
        meta['sources']['focus_journal'] = reference(RUN, folder / 'journal.pg.json')
        atomic(folder / 'manifest.json', meta)
        atomic(folder / 'index.html', dict(engineering_only=True))
        return dict(contract_id='V4_JOINT_RELEASE_V2_PG_CONTENT', snapshot=dict(manifest=reference(RUN, folder / 'manifest.json')),
            ui_assets={'index.html': reference(RUN, folder / 'index.html')}, trade_date='2026-10-09', operational_release_scope=['focus_read_corrected'], trading=False, production_admission=False)

    first, second = candidate('first'), candidate('second')
    activate(RUN, first, None, lambda c: {'pass': True})
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_v4_handler(RUN))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    requests = []

    def request(sid, kind='observations', token=None, day='2026-10-09'):
        reader = ProductionV4ResearchReader(RUN)
        query = dict(context_token=token or reader.token, trade_date=day, limit=200)
        url = 'http://127.0.0.1:%d/api/v4/focus/%s/%s?' % (server.server_address[1], sid, kind) + urllib.parse.urlencode(query)
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                code, raw = response.status, response.read()
        except urllib.error.HTTPError as exc:
            code, raw = exc.code, exc.read()
        body = json.loads(raw)
        requests.append(dict(sid=sid, kind=kind, query=query, status=code, body_sha256=digest(raw), body=body))
        return code, body

    try:
        for sid in sorted({r['security'] for r in delta}):
            code, body = request(sid)
            assert code == 200 and body['context']['accepted_trade_date'] == '2026-10-09'
            for sample in [r for r in samples if r['security'] == sid]:
                obs = next(o for o in body['items'] if o['trade_date'] == sample['date'])
                assert obs['price_path']['metrics'] == sample['actual']
            code, outcomes = request(sid, 'outcomes')
            assert code == 200
        old_token = ProductionV4ResearchReader(RUN).token
        code, _ = request(samples[0]['security'], token='stale')
        assert code == 409
        assert request(samples[0]['security'], day='2026-09-30')[0] == 409
        from unittest.mock import patch
        with patch('psycopg.connect', side_effect=psycopg.OperationalError('S1B_INJECTED_CONNECTION_OUTAGE')):
            code, unavailable = request(samples[0]['security'])
            assert code == 503 and unavailable['fallback'] is False
        before = (RUN / AUTHORITY).read_bytes()
        try:
            activate(RUN, second, '0' * 64, lambda c: {'pass': True})
        except SourceInvalid as exc:
            assert str(exc) == 'JOINT_CAS_CONFLICT'
        else:
            raise AssertionError('STALE_CAS_ACCEPTED')
        assert (RUN / AUTHORITY).read_bytes() == before
        def failed_health(c):
            code, _ = request(samples[0]['security'])
            assert code == 200
            return {'pass': False}
        try:
            activate(RUN, second, digest(before), failed_health)
        except SourceInvalid as exc:
            assert 'HEALTH' in str(exc)
        else:
            raise AssertionError('FAILED_HEALTH_ACCEPTED')
        assert (RUN / AUTHORITY).read_bytes() == before
        code, body = request(samples[0]['security'])
        assert code == 200 and body['context_token'] == old_token
        activate(RUN, second, digest(before), lambda c: {'pass': request(samples[0]['security'])[0] == 200})
        validate(RUN, second)
        code, body = request(samples[0]['security'])
        assert code == 200 and body['context_token'] != old_token
        assert request(samples[0]['security'], token=old_token)[0] == 409
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert protected == {p: sha(WORK / p) for p in protected}
    assert source_before == {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    atomic(OUT / 'HTTP_RECEIPTS.json', requests)
    atomic(OUT / 'RESULT.json', dict(contract='S1B_IDENTITY_DEFAULT_HTTP_JOINT_SCOPED_V1', status='SCOPED_PASS',
        run_utc=datetime.now(timezone.utc).isoformat(), base_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        database=dict(directory=directory, system_identifier=system), samples=101, securities=34, outcome_deltas=49, predicate_deltas=4,
        action_contract=ACTION_CONTRACT, default_handler='workbench_service.v4_server.make_v4_handler',
        scope='SCOPED_REAL_FROZEN_FOCUS_READ_NOT_FULL_BUILD_SNAPSHOT_OR_ALL_PRODUCERS', http_requests=len(requests),
        stale_token_rejected=True, stale_cas_rejected=True, wrong_T0_rejected=True, injected_pg_outage_no_fallback=True, failed_health_exact_rollback=True, publish_readback=True,
        protected_before=protected, protected_after=protected, production_changed=False, S1B='NOT_FULL_PASS', S2='NOT_ENTERED',
        source_sha256=source_before, source_bytes_stable=True,
        results_sha256={p.name: sha(p) for p in OUT.glob('*.json') if p.name != 'RESULT.json'}))
    print('S1-B SCOPED_PASS; S1-B NOT_FULL_PASS; S2 NOT_ENTERED', flush=True)


if __name__ == '__main__':
    from types import SimpleNamespace
    from tests import v4_native_isolation_plugin_r4 as guard
    OUT.mkdir(parents=True, exist_ok=True)
    os.environ['R4_CONNECTION_LEDGER'] = str(OUT / ('PG_INTENTS_' + RUN.name + '.jsonl'))
    config = SimpleNamespace()
    guard.pytest_configure(config)
    guard.ACTIVE = 'S1B_REAL_IDENTITY_DEFAULT_HTTP_JOINT'
    ledger = Path(os.environ['R4_CONNECTION_LEDGER']).open('x', encoding='utf8')
    class Streamed:
        count = 0
        def append(self, event):
            ledger.write(json.dumps(event, ensure_ascii=False) + '\n')
            self.count += 1
            if self.count % 100 == 0:
                ledger.flush()
    guard.EVENTS = Streamed()
    try:
        main()
    finally:
        guard.pytest_unconfigure(config)
        ledger.close()
        atomic(OUT / ('EXECUTION_' + RUN.name + '.json'), dict(command=sys.argv, cwd=str(ROOT),
            run_utc=datetime.now(timezone.utc).isoformat(), pg_intents=guard.EVENTS.count,
            source_sha256=sha(Path(__file__)), ledger_sha256=sha(Path(os.environ['R4_CONNECTION_LEDGER']))))
