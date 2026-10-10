"""Read-only current research evidence; never schedules or triggers a future day."""
import csv
import gzip
import hashlib
import io
import json
import sys
import urllib.request
import urllib.parse
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from workbench_analysis.r43_owner_replay import checked, ref
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.full_market_state_publisher_v1 import build
from workbench_analysis.full_state_first_observed_v1 import quarantine_publisher
from sector.d2_research_source_matrix_v1 import build as matrix
from sector.valid_member_qualification_v3 import compare
from sector.legacy_valid_member_a05_v1 import exact_value
from sector.phase2 import prepare, validity
from workbench_analysis.fep_e5.admission import current_gate
OUT = 'docs/evidence/pre_next_t0_execution_r1_20261010/final'


def main():
    import pandas as pd
    heads = ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json', 'data/v4/V4_DATA_ACCEPTED_HEAD.json']
    before = {p: ref(ROOT, ROOT/p) for p in heads}
    head = json.loads(checked(ROOT, before[heads[0]]).read_bytes())
    output = build(ROOT, candidate_binding=before[heads[0]], trade_date='2026-10-09', revision='delivery-r1')
    state = json.loads(gzip.decompress(checked(ROOT, output).read_bytes()))
    quarantine = quarantine_publisher(ROOT, publisher_binding=output, candidate_directory=OUT+'/quarantine')
    publish(ROOT, OUT+'/STATE_PUBLISHER_ISOLATED_RUN.json', dict(source=output, quarantine=quarantine,
        decompressed_sha256=hashlib.sha256(gzip.decompress(checked(ROOT, output).read_bytes())).hexdigest(),
        universe_count=len({r['security_id'] for r in state['scenario_outputs']}),
        signal_count=len(state['scenario_outputs']), counts=dict(Counter(r['state'] for r in state['scenario_outputs'])),
        first_available=state['first_available'], frozen_at=state['frozen_at'],
        evidence_class=state['evidence_class'], production=False, model=state['model']))
    index = json.loads((ROOT/'data/v4/producer_candidate_index_v2.json').read_bytes())
    sector_binding = index['sessions']['2026-10-09']['sector']
    publish(ROOT, OUT+'/D2_PRODUCER_SOURCE_MATRIX.json', matrix(ROOT, candidate_binding=sector_binding,
        cutoff='2026-10-10T18:35:00+08:00'))
    golden = json.loads((ROOT/'reports/audits/A05_REAL_GOLDEN_SAMPLE_READBACK_R1.json').read_bytes())
    observations = []
    for item in golden['archives']:
        source = item['archive']
        raw = checked(ROOT, source).read_bytes()
        for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
            if 'valid_member' not in row or 'missing_state' not in row:
                continue
            key, missing = row['security_id'], row['missing_state'] or None
            scalar = exact_value(key, missing)
            factors = pd.DataFrame([dict(security_id=key, MA20=1., MA60=1., AMOUNT_MA5=1., AMOUNT_MA20=1.)])
            latest = pd.DataFrame([dict(security_id=key, missing_state=missing, aligned_close=1.)])
            pandas_value = bool(prepare(factors, latest).valid_member.iloc[0])
            original = row['valid_member'].lower() == 'true'
            assert scalar == pandas_value == original
            # Lifecycle is absent in these original archives: do not manufacture it.
            audit = compare(dict(source_security_key=key, missing_state=missing, trade_date='2026-09-24'),
                            trade_date='2026-09-24')
            observations.append(dict(security_id=key, missing_state=missing, source=source,
                legacy_value=original, exact_value=scalar, phase2_prepare=pandas_value,
                exact_oracle='PASS', lifecycle_comparison=audit['comparison'], normal_universe='UNKNOWN'))
    from scripts.verify_a02_a05_candidate_readback_r1 import verify_a05
    sector_oracle = verify_a05()
    from v4.rps_pit_history_a02_v1 import read_bound
    recovery = json.loads((ROOT/'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json').read_bytes())
    recovered = read_bound(ROOT, recovery['input_binding'])
    facts = {r['source_security_id']: r for r in recovered['observations']}
    groups = {}
    for row in recovered['membership']:
        if row['security_id'] is not None:
            groups.setdefault(row['sector_id'], set()).add(row['security_id'])
    field_oracle = []
    for row in recovered['legacy_outputs']:
        members = groups.get(row['sector_id'], set())
        count = sum(exact_value(sid, facts[sid]['missing_state']) for sid in members if sid in facts)
        good, reason = validity(len(members), count, row['sector_role'])
        expected = dict(total_member_count=len(members), valid_member_count=count,
            invalid_member_count=len(members)-count, coverage=count/len(members) if members else 0,
            sector_valid=good, invalid_reason=reason)
        cells = {k: dict(original=row[k], recomputed=v, status='PASS' if row[k] == v else 'DIFFERENCE')
                 for k, v in expected.items()}
        assert all(c['status'] == 'PASS' for c in cells.values())
        field_oracle.append(dict(sector_id=row['sector_id'], source=recovery['input_binding'], fields=cells))
    publish(ROOT, OUT+'/D2_SECTOR_FIELD_ORACLE.json', dict(T0=recovered['trade_date'],
        sectors=field_oracle, normal_universe='NOT_IN_THIS_ORIGINAL_QUALIFICATION_SOURCE_UNKNOWN',
        formal_cross_date_admission=False))
    publish(ROOT, OUT+'/D2_LEGACY_GOLDEN_FIELD_READBACK.json', dict(original_date='2026-09-24',
        observations=observations, counts=dict(Counter(r['exact_oracle'] for r in observations)),
        sector_oracle=sector_oracle, lifecycle_comparison='UNKNOWN_WHEN_LEGACY_HAS_NO_LIFECYCLE',
        current_1009_missing_state='HISTORICAL_NOT_VERIFIABLE', formal_A05_cross_date=False))
    def get(path, query=None):
        url = 'http://127.0.0.1:28765'+path
        if query: url += '?'+urllib.parse.urlencode(query)
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                raw = response.read(); code = response.status
        except urllib.error.HTTPError as error:
            code, raw = error.code, error.read()
        return dict(url=url, status=code, body=json.loads(raw), raw_sha256=hashlib.sha256(raw).hexdigest())
    context = get('/api/v4/context')
    token = context['body']['context_token']
    cases = [('sector_1009', '/api/v4/candidates/sectors/INDUSTRY:T0706', '2026-10-09', token, 0),
             ('cohort_1009', '/api/v4/candidates/cohort', '2026-10-09', token, 0),
             ('missing_1008', '/api/v4/candidates/cohort', '2026-10-08', token, 0),
             ('future_1012', '/api/v4/candidates/cohort', '2026-10-12', token, 0),
             ('old_token', '/api/v4/candidates/cohort', '2026-10-09', '0'*64, 0),
             ('stocks_history_page1', '/api/v4/stocks', '2026-10-08', token, 0),
             ('stocks_history_page2', '/api/v4/stocks', '2026-10-08', token, 3)]
    responses = {name: get(path, dict(trade_date=day, context_token=t, limit=3, offset=offset))
                 for name, path, day, t, offset in cases}
    assert responses['future_1012']['status'] == 400
    assert responses['old_token']['status'] == 409
    assert responses['sector_1009']['body']['candidate_research']['candidate_status'] == 'AVAILABLE'
    assert responses['cohort_1009']['body']['candidate_research']['evidence_class'] == 'RECONSTRUCTED_RESEARCH_ONLY'
    assert responses['missing_1008']['body']['candidate_research']['candidate_status'] == 'NOT_CAPTURED'
    assert all(responses[k]['status'] == 200 for k in ('stocks_history_page1', 'stocks_history_page2'))
    publish(ROOT, OUT+'/PRODUCTION_HTTP_READBACK.json', dict(context=context, cases=responses,
        production_restart=False, independent_external_acceptance=False))
    publish(ROOT, OUT+'/FEP_CURRENT_SOURCE_READBACK.json', current_gate(ROOT))
    after = {p: ref(ROOT, ROOT/p) for p in heads}
    assert before == after
    publish(ROOT, OUT+'/PROTECTED_HEAD_READBACK.json', dict(before=before, after=after, unchanged=True))
    print(json.dumps(dict(output=output, state_counts=dict(Counter(r['state'] for r in state['scenario_outputs'])),
        golden_observations=len(observations), sector_oracle=sector_oracle,
        HTTP={k: v['status'] for k, v in responses.items()}, heads_unchanged=True)))


if __name__ == '__main__': main()
