"""Offline governance seal; reuses existing evidence and hashes only consumed inputs."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
import json
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from validation.phase0_2b import atomic, encoded, read_frozen, raw_gate
from validation.phase0_2c import release_gate
from tdx.gbbq_reader import file_sha256

ROOT = Path(__file__).resolve().parents[1]
TDX = Path('D:/new_tdx')
OUT = ROOT / 'reports/phase0_2c'


def seal():
    used = {}
    def read(rel):
        p = ROOT / rel
        used[rel] = file_sha256(p)
        return json.loads(p.read_text('utf8'))
    def frozen(run, name):
        rel = f'reports/phase0_2b/{run}'
        value = read_frozen(ROOT/rel, name)
        used[f'{rel}/{name}'] = file_sha256(ROOT/rel/name)
        used[f'{rel}/FROZEN.json'] = file_sha256(ROOT/rel/'FROZEN.json')
        return value
    dec = frozen('run_001', 'decode_audit.json')
    local = frozen('run_001', 'local.json')
    external = frozen('run_001', 'external.json')
    integrity = frozen('run_004', 'source_integrity.json')
    regression = frozen('run_004', 'tests.json')
    phase2 = read('reports/phase0_2/PHASE0_2_FINAL_RECEIPT.json')
    validation = read('reports/phase0_2/QFQ_VALIDATION.json')
    phase1 = read('reports/phase0_1/PHASE0_1_FINAL_RECEIPT.json')
    calendar = read('reports/phase0_1/TRADING_CALENDAR_AUDIT.json')
    previous = read('reports/phase0_2b/PHASE0_2B_FINAL_RECEIPT.json')
    cause = read('reports/phase0_2b/ROOT_CAUSE_ANALYSIS.json')
    current_hashes = {p:file_sha256(Path(p)) for p in integrity['before']}
    exact = 0
    for row in external:
        sample = next(s for s in local if (s['security_id'],s['date']) == (row['security_id'],row['date']))
        exact += raw_gate(sample['raw'],row['0'])['raw_match'] is True
    assert len({(r['security_id'],r['date'],r['external_source']) for r in external}) == 10
    tests_required = {'test_tdx_adjustment_reference_cases.py','test_suspension_compound_actions.py',
                      'test_future_exday.py','test_round_half_up.py','test_fixed_qfq_samples.py'}
    coverage = all(validation[k] for k in ('cash_dividend_samples','bonus_transfer_samples',
                   'rights_issue_samples','compound_suspension_samples','future_exday_samples'))
    gates = {'local_raw': exact == len(external) == 10,
        'gbbq': dec['declared_count'] == dec['parsed_count'] == 192544 and dec['gbbq_parse_status'] == 'PASS'
                and all(dec[k] == 0 for k in ('invalid_code_count','invalid_date_count','invalid_parameter_count')),
        'xrxd': dec['category_distribution']['1'] == 63179 and dec['invalid_xrxd_semantics_count'] == 0,
        'affine': coverage and regression['exit_code'] == 0 and tests_required <= set(regression['command'])
                  and phase2['local_validation_status'] == 'PASS' and validation['reference_test_passed']
                  and len(validation['local_security_validations']) == 3
                  and all(s['status'] == 'PASS' for s in validation['local_security_validations'])
                  and len(local) == 5 and all(s['chain_reproducible'] for s in local),
        'source_unchanged': current_hashes == integrity['before']}
    assert phase2['reference_commit'] == dec['reference_commit'] == '7ec113c38bf62e8d04aabd8be04df09b9c94ac65'
    assert calendar['master_trading_calendar_status'] == phase1['master_trading_calendar_status'] == 'PASS'
    assert calendar['normal_universe']['count_after'] == phase1['normal_universe_count_after'] == 5461
    proven_bug = cause['root_cause'] in {'ROOT_CAUSE_LOCAL_RAW','ROOT_CAUSE_LOCAL_GBBQ_EVENT','ROOT_CAUSE_LOCAL_AFFINE_IMPLEMENTATION'} and cause['local_code_change_required'] is True
    decision = release_gate(gates, proven_local_systematic_bug=proven_bug)
    if decision['final_status'] != 'FULL_PASS_TDX_NATIVE':
        atomic(OUT/'PHASE0_2C_RELEASE_SEAL.json',encoded(decision),TDX)
        return decision
    result = subprocess.run([sys.executable,'-m','pytest','-q','tests/test_phase0_2c_release_gate.py',
                             'tests/test_adjustment_contract_status.py'],cwd=ROOT,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    # The final status update is narrowly scoped; historical reports remain immutable.
    spec_path = ROOT/'PROJECT_SPEC.md'
    spec = spec_path.read_text('utf8')
    spec = spec.replace('This workspace implements Phase 0 through Phase 0.2A.', 'This workspace implements Phase 0 through Phase 0.2C.')
    spec = spec.replace('See `docs/DATA_FACTOR_SPEC.md`, `docs/PHASE0_2A_REPORT.md`, and `reports/phase0_2a/PHASE0_2A_FINAL_RECEIPT.json` for the implemented contracts and current decision.',
        'See `docs/DATA_FACTOR_SPEC.md`, `docs/ADJUSTMENT_CONTRACT_V0_3.md`, and `reports/phase0_2c/PHASE0_2C_RELEASE_SEAL.json` for the implemented contracts and current decision. Older phase receipts are historical evidence.')
    spec = spec.replace('Its final status remains `DEGRADED_PASS`', 'Its historical final status was `DEGRADED_PASS`')
    spec = spec.replace('Its final gate supersedes Phase 0.2:', 'Its historical gate superseded Phase 0.2:')
    marker = '\n## Current release status — Phase 0.2C\n'
    if marker in spec:
        spec = spec.split(marker)[0]
    spec += marker + '''
This section supersedes the historical RAW/manual-UI/external-exact-match release restrictions above and in earlier phase documents. Historical scientific findings remain unchanged. Production inputs remain LOCAL_TDX_ONLY; earlier authorized provider snapshots are validation references only.

```text
CURRENT_DATA_STATUS = TDX_NATIVE_ADJUSTMENT_RELEASED
PHASE_0_STATUS = FULL_PASS
PHASE_0_CLOSED = TRUE
ADJUSTMENT_IDENTITY = TDX_NATIVE_AFFINE_QFQ
PROJECT_PRICE_BASIS = FORWARD_ADJUSTED
ADJUSTMENT_STATUS = VERIFIED_REPRODUCIBLE_TDX_NATIVE
FORMAL_TREND_SCANNERS_ALLOWED = TRUE
NEXT_PHASE = PHASE_1_NORMALIZATION_AND_FORMAL_FACTOR_ENGINE
```

The current release authority is Phase0.2C, adjustment-contract-v0.3, adjusted-daily-contract-v0.3, and known-limitations-v0.3. Phase 1 may generate adjusted_daily.parquet and formal factors under their individual contracts. Neither data generation, factors nor scanners were implemented by this release seal. Cross-vendor QFQ discrepancies and provider-sensitive deep history are known limitations, not current production blockers.
'''
    atomic(spec_path,spec.encode('utf8'),TDX)
    receipt = {'phase':'PHASE0.2C','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE',
        'sealed_at':datetime.now(timezone.utc).isoformat(),**decision,
        'source_raw_status':'VERIFIED','local_tdx_day_raw_status':'VERIFIED',
        'raw_verification_scope':'5 fixed points x 2 providers; 10/10 exact OHLC, not a whole-market crosscheck',
        'gbbq_decoder_status':'VERIFIED','xrxd_status':'VERIFIED','affine_engine_status':'VERIFIED',
        'declared_count':192544,'parsed_count':192544,'xrxd_count':63179,
        'invalid_code':0,'invalid_date':0,'invalid_float':0,
        'cross_vendor_status':'VALIDATION_REFERENCE_ONLY_EXACT_EQUALITY_NOT_REQUIRED',
        'cross_vendor_qfq_exact_equality_not_guaranteed':True,
        'deep_history_limitation':'PROVIDER_BASIS_SENSITIVE_DEEP_HISTORY',
        'reference_repository':phase2['reference_repository'],'reference_commit':phase2['reference_commit'],
        'adjustment_name':'TDX_NATIVE_QFQ','adjustment_contract_version':'adjustment-contract-v0.3',
        'adjustment_version':'tdx-affine-qfq-v0.2','known_limitations_version':'known-limitations-v0.3',
        'adjusted_dataset_contract_version':'adjusted-daily-contract-v0.3',
        'adjusted_dataset_path':'data/normalized/adjusted_daily.parquet','adjusted_dataset_generated':False,
        'volume_basis':'RAW','amount_basis':'RAW','production_use':'CURRENT_MARKET_STRUCTURE_SCANNING',
        'master_trading_calendar_status':'PASS','normal_universe_status':'VERIFIED_INHERITED_PHASE0_1',
        'normal_universe_count':5461,'calendar_end_date':calendar['calendar_end_date'],
        'tdx_source_unchanged':True,'integrity_scope':integrity['scope'],
        'input_and_protected_core_hashes':current_hashes,'release_gates':gates,
        'new_local_systematic_bug_found':False,'core_code_changed':False,'network_requests':0,
        'scanner_started':False,'factor_engine_started':False,'phase0_closed':True,
        'prior_phase0_2b_status':previous['final_status'],'prior_external_root_cause':cause['root_cause'],
        'governance_change':'TDX-native authority released by Phase0.2C task card; unresolved vendor details retained as limitations',
        'tests':{'exit_code':result.returncode,'output':result.stdout,'scope':'2 minimal offline governance test files'},
        'evidence_sha256':used}
    assert all(file_sha256(Path(p)) == h for p,h in current_hashes.items())
    for rel in ('PROJECT_SPEC.md','docs/ADJUSTMENT_CONTRACT_V0_3.md','docs/ADJUSTED_DATASET_CONTRACT_V0_3.md','docs/KNOWN_LIMITATIONS.md'):
        receipt.setdefault('release_artifact_sha256',{})[rel]=file_sha256(ROOT/rel)
    atomic(OUT/'PHASE0_2C_RELEASE_SEAL.json',encoded(receipt),TDX)
    return receipt

if __name__ == '__main__':
    r = seal()
    print(r['final_status'])
    print(r.get('tests',{}).get('output',''))
