"""Independent cross-section tie-rank and exact frozen endpoint oracle."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from workbench_analysis.corrected_owner_replay import load, checked, gzrows, ref
from workbench_analysis.market_source_acquisition import write

OUT = ROOT / 'docs/evidence/r4_3_four_session_closeout_20261009'
TOLERANCE = 1e-8


def main():
    write(OUT / 'CROSS_SECTION_ORACLE_STAGE_ENTRY.json', dict(
        contract_id='R43_INDEPENDENT_RPS_ORACLE_V1', absolute_tolerance=TOLERANCE,
        producer_rank_function_called=False, next_stage='SOURCE_AND_NUMERIC_ACCEPTANCE',
        evidence='All current-day return cross-sections and available exact predecessor scores', acceptance='IN_PROGRESS'))
    owners = load(OUT / 'owner_v3/CORE_REPLAY.json')['owners']
    byday = {}
    results, errors = [], []
    for owner in owners:
        rows = gzrows(checked(ROOT, owner['core']))
        byday[owner['trade_date']] = {r['security_id']: r['fields'] for r in rows}
        checks = 0
        for horizon in (5, 20):
            distribution = Counter(r['fields'][f'ret{horizon}']['value'] for r in rows if r['fields'][f'ret{horizon}']['value'] is not None)
            n = sum(distribution.values())
            rank, expected = 0, {}
            for value, count in sorted(distribution.items()):
                expected[value] = 100 * (rank + (count - 1) / 2) / (n - 1) if n >= 2 else None
                rank += count
            for row in rows:
                fields = row['fields']
                want = expected.get(fields[f'ret{horizon}']['value'])
                actual = fields[f'rps{horizon}']['value']
                if (want is None) != (actual is None) or want is not None and abs(want - actual) > TOLERANCE:
                    errors.append(dict(date=owner['trade_date'], security_id=row['security_id'], field=f'rps{horizon}', expected=want, actual=actual))
                checks += 1
        results.append(dict(trade_date=owner['trade_date'], full_rank_checks=checks, core=owner['core']))
    endpoint_checks, unavailable = [], []
    for day, fields_by_id in byday.items():
        for sid, fields in fields_by_id.items():
            for field, score in [('rps5_delta1', 'rps5'), ('rps5_delta3', 'rps5'), ('rps20_delta3', 'rps20')]:
                cell = fields[field]
                endpoint = cell['prior_endpoint']
                if endpoint not in byday:
                    continue
                prior = byday[endpoint].get(sid, {}).get(score, {}).get('value')
                current = fields[score]['value']
                want = current - prior if current is not None and prior is not None else None
                actual = cell['value']
                if (want is None) != (actual is None) or want is not None and abs(want - actual) > TOLERANCE:
                    errors.append(dict(date=day, security_id=sid, field=field, endpoint=endpoint, expected=want, actual=actual))
                endpoint_checks.append((day, field, endpoint))
    counts = Counter(endpoint_checks)
    write(OUT / '05_INDEPENDENT_FULL_RPS_AND_EXACT_ENDPOINT_ORACLE.json', dict(
        contract_id='R43_INDEPENDENT_RPS_ORACLE_V1', absolute_tolerance=TOLERANCE,
        independent_formula='Sorted return frequency groups; cumulative smaller count plus half tie positions, divided by N-1',
        full_cross_sections=results, exact_endpoint_checks=[dict(trade_date=d, field=f, predecessor=p, checks=n) for (d, f, p), n in sorted(counts.items())],
        errors=errors, unknown_reason='Return unavailable remains unknown; predecessors outside four target owners are validated by the separate raw-window oracle',
        acceptance='PASS_FULL_CURRENT_RANK_AND_AVAILABLE_EXACT_PREDECESSORS' if not errors else 'FAIL'))
    print(json.dumps(dict(rank_checks=sum(r['full_rank_checks'] for r in results), endpoint_checks=len(endpoint_checks), errors=len(errors))))
    if errors:
        raise ValueError('INDEPENDENT_RPS_MISMATCH')


if __name__ == '__main__':
    main()
