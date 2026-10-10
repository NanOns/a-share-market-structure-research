"""Bounded real-owner readback; no scoring, enrollment or publication."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_service.core_product_bff_r1 import CoreProductBFFR1


def main():
    output = ROOT / 'docs/evidence/v4_r4_post_audit_repair_20261010/12_BCD_DEVELOPMENT'
    paths = [ROOT / 'data/v4' / name for name in
             ('V4_OPERATIONAL_RESEARCH_HEAD.json', 'V4_DATA_ACCEPTED_HEAD.json')]
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    api = accepted_api(ROOT)
    bff = CoreProductBFFR1(api, None)
    records = []
    for route in ('sectors', 'forward/statistics', 'forward/settlement', 'forward/fep'):
        code, payload = bff.get('/api/v4/' + route,
                                dict(context_token=api.token, limit='1'))
        assert code == 200
        if route != 'sectors':
            assert payload['status'] == 'SOURCE_INCOMPLETE'
        if route == 'forward/fep':
            data = payload['data']
            assert 'model_revision' in data['required_grant_key']
            assert data['prediction'] is None and not data['training_authorized']
            assert not data['admission_gate']['production_authorized']
            assert all(cell['value'] is None for cell in data['admission_gate']['fields'].values())
        records.append(dict(route=route, http_status=code, payload=payload))
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    assert before == after
    atomic_json(ROOT, output / 'REAL_BFF_SOURCE_BOUNDARY_READBACK.json', dict(
        contract_id='BCD_DEVELOPMENT_REAL_READBACK_R1', scope='IN_PROCESS_REAL_OWNER_NOT_BROWSER',
        T0=api.candidate['accepted_trade_date'], protected_heads=after,
        future_data_used=False, model_scoring=False, enrollment_written=False,
        acceptance='PASS_SCOPED_REAL_CURRENT_FAIL_CLOSED', records=records))
    print('PASS_SCOPED_REAL_CURRENT_FAIL_CLOSED; protected Heads unchanged')


if __name__ == '__main__':
    main()
