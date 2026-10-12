"""Reuse frozen D2/Core; rebuild only the isolated Focus path projection."""
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
WORK = Path('G:/codex_tmp/r4_r3_pg_publication_v2')
OUT = ROOT / 'docs/audits/r4_r3_local_delivery_20261012/S1_IDENTITY_REPAIR'


def main():
    global OUT
    run = sys.argv[1] if len(sys.argv) > 1 else 'R1'
    assert run in ('R1', 'R2', 'R3')
    if run != 'R1':
        OUT = OUT.with_name('S1_IDENTITY_REPAIR_' + run)
    from scripts.r4_readonly_source_guard import install
    install(['G:/codex work/大A交易', 'D:/new_tdx'])
    from workbench_db.v4_series_pg_r1 import build, verified_series_scope, verified_series_read
    from workbench_service.current_v4_context import canonical
    from focus_tracker.v4_exact_identity_adapter_r4 import AcceptedPaths, CONTRACT
    from focus_tracker.v4_native_core_adapter import enriched_project
    OUT.mkdir(parents=True, exist_ok=False)
    folder = WORK / ('runtime/local_focus_identity_s1_20261012_' + run)
    folder.mkdir(parents=True, exist_ok=False)
    receipt = json.loads((ROOT / 'docs/audits/r4_r3_consumers_20261011/FOCUS_RESUME_R1/RESULT.json').read_bytes())
    ref = receipt['result']['focus']

    def checked(binding):
        p = (WORK / binding['path']).resolve()
        assert p.is_relative_to(WORK.resolve())
        raw = p.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == binding['sha256']
        return raw

    def binding(path):
        return dict(path=path.relative_to(WORK).as_posix(), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    original = json.loads(gzip.decompress(checked(ref)))
    bindings = original['source_bindings']
    source_file = WORK / receipt['result']['owners'][0]['D2']['path']
    sources = json.loads((source_file.parents[2] / 'SOURCE_BINDINGS.json').read_bytes())['sources']
    identity = sources['identity']
    rows = json.loads(checked(identity))['rows']
    symbols = {r['security_id']: r['source_security_key'] for r in rows}
    assert len(symbols) == len(rows) and len(set(symbols.values())) == len(rows)
    descriptor = json.loads(checked(bindings['series']))
    bars = []
    with verified_series_read(descriptor) as db:
        for sid, day, payload in db.execute('SELECT security,day,payload FROM bars ORDER BY security,day'):
            row = json.loads(payload)
            assert sid in symbols
            bars.append((sid, day.isoformat() if hasattr(day, 'isoformat') else day, dict(row, symbol=symbols[sid])))
    series = folder / 'series.pg.json'
    build(WORK, series, bars, t0=descriptor['T0'], source_digest=hashlib.sha256(canonical(dict(original_series=bindings['series'], identity=identity, repair_contract=CONTRACT))).hexdigest())
    repaired = dict(bindings, series=binding(series), security_identity=identity, path_contract=CONTRACT)
    repaired['native_core'] = {d: dict(owner, series=repaired['series']) for d, owner in bindings['native_core'].items()}
    repaired['implementation'] = dict(bindings.get('implementation', {}))
    for name in ('v4_exact_identity_adapter_r4', 'v4_native_core_adapter', 'v4_path_adapter', 'v4_native_core_journal', 'v4_successor', 'states', 'path_state_v2', 'outcomes', 'price_path'):
        blob = (ROOT / 'src/focus_tracker' / (name + '.py')).read_bytes()
        path = folder / 'implementation' / (name + '.py')
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(blob)
        repaired['implementation'][name] = binding(path)
    days = {}
    for owner in receipt['result']['owners']:
        days[owner['trade_date']] = json.loads(gzip.decompress(checked(owner['D2'])))['rows']
    with verified_series_scope():
        projection = enriched_project(days, AcceptedPaths(WORK, repaired))
    old = {e['episode_id']: e for e in original['episodes']}
    provenance = ('membership_mode', 'taxonomy', 'membership_snapshot_id', 'membership_observed_at', 'member_set_asof', 'knowledge_lineage', 'AS_RECORDED', 'PIT_ELIGIBLE', 'HISTORICAL_FIRST_AVAILABLE_PROVEN', 'production_eligible_scope', 'survivorship_bias_risk')
    for episode in projection['episodes']:
        previous = old[episode['episode_id']]
        episode.update({k: previous[k] for k in provenance})
        episode['research_mainline_context'] = previous.get('research_mainline_context')
        obs = {o['trade_date']: o for o in previous['observations']}
        for value in episode['observations'] + episode['outcomes'] + episode['anchors']:
            value.update({k: previous[k] for k in provenance})
            if 'trade_date' in value and value in episode['observations']:
                value['research_mainline_context'] = obs[value['trade_date']].get('research_mainline_context')
    projection.update({k: original[k] for k in provenance})
    projection.update(contract_id='V4_R4_CORRECTED_FOCUS_EXACT_IDENTITY_CANDIDATE_V1', source_bindings=repaired, production_admission=False, research_mainline_source_bindings=original['research_mainline_source_bindings'])
    target = folder / 'CORRECTED_FOCUS_FORWARD.json.gz'
    temp = target.with_suffix('.tmp')
    temp.write_bytes(gzip.compress(canonical(projection), mtime=0))
    os.replace(temp, target)
    result = dict(receipt, contract='R4_R3_FOCUS_SOURCE_IDENTITY_REPAIR_S1_V1', result=dict(receipt['result'], status='ENGINEERING_FOCUS_IDENTITY_REPAIRED', focus=binding(target), episodes=len(projection['episodes'])), repaired_series_rows=len(bars), source_projection=ref, source_identity=identity, actual_source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ('scripts/repair_r4_r3_focus_identity_s1.py', 'src/focus_tracker/v4_exact_identity_adapter_r4.py', 'src/focus_tracker/v4_native_core_journal.py')}, production_changed=False)
    (OUT / 'RESULT.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(dict(status=result['result']['status'], episodes=len(projection['episodes']), repaired_series_rows=len(bars))), flush=True)


if __name__ == '__main__':
    main()
