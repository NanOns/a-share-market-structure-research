"""Bind real project positive/negative controls; no fresh provider or market assertions."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def main():
    contract=read('config/source_authority_governance_r1.json');assert bind(contract['runtime']['path'])['sha256']==contract['runtime']['sha256']
    roster_path='reports/v4_01/V4_01_MISSING_DAY_REQUERY_R6_1.json';roster=read(roster_path)
    v6_path='reports/v4_06/V4_06_LIVE_PROBE_RECEIPT.json';v6=read(v6_path)
    v5_path='data/v4/V4_05_ACCEPTED_HEAD.json';v5=read(v5_path)
    v8_path='data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json';v8=read(v8_path)
    old_path='scripts/accept_v4_dm01_baostock_runtime.py';old=(ROOT/old_path).read_text(encoding='utf8')
    from scripts.scan_source_authority_governance_r1 import inspect_file
    controls={
      'V4_01_HISTORICAL_ROSTER_REQUERY':dict(status='PASS',binding=bind(roster_path),
        observed_at=roster['observed_at_utc'],historical_targets=[r['trade_date'] for r in roster['requeried_dates']],
        assertion=bool(roster['requeried_dates']) and all(r['trade_date']<roster['observed_at_utc'][:10] and r['daily_market_provider_error_code']=='0' for r in roster['requeried_dates'])),
      'V4_06_HISTORICAL_TARGET_PROVIDER_QUERY':dict(status='PASS',binding=bind(v6_path),
        target_date=v6['request_range']['end'],observed_at=v6['observed_at_utc'],request_count=v6['request_count']['delta'],
        assertion=v6['request_count']['delta']>0 and v6['request_range']['end']<v6['observed_at_utc'][:10] and v6['completed_security_count']==4 and v6['failure'] is None),
      'V4_05_UNPROVEN_AS_RECORDED_REMAINS_BLOCKED':dict(status='PASS',binding=bind(v5_path),assertion=v5['historical_as_recorded_adjusted_price']=='BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE'),
      'V4_08_FIRST_OBSERVED_CURRENT_MEMBERSHIP_NOT_BACKDATED':dict(status='PASS',binding=bind(v8_path),assertion=v8['membership_acceptance_scope']=='FORWARD_PIT_MEMBERSHIP_ONLY' and v8['first_accepted_trade_date']=='2026-09-30',
        first_observed_owner='PROJECT_FIRST_OBSERVED_PROVIDER_BYTES',full_temporal_vectors='tests/v4_08'),
      'DM01_OLD_SAME_DAY_RUNTIME_GATE_NEGATIVE_CONTROL':dict(status='PASS',binding=bind(old_path),assertion=any(f['category']=='C3_HISTORICAL_QUERY_SAME_DAY_ONLY_GATE' for f in inspect_file(old_path,(ROOT/old_path).read_bytes())))}
    assert all(v['assertion'] for v in controls.values())
    atomic_json(ROOT/'reports/audits/A10_PROJECT_GOVERNANCE_CONTROLS_R1.json',dict(status='PASS',controls=controls,source_values_not_rewritten=True,external_acceptance=None))
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in contract['protected_bindings'])
    scan=read('reports/audits/V4_SOURCE_AUTHORITY_GOVERNANCE_SCAN_R1.json')
    assert not scan['parse_errors']
    gates={f'A10-G{i:02d}':'PASS_ENGINEERING' for i in range(1,12)};gates['A10-G11']='PENDING_CLEAN_DETACHED';gates['A10-G12']='PENDING_INDEPENDENT_EXTERNAL_AUDIT'
    atomic_json(ROOT/'reports/audits/A10_ENGINEERING_GATES_R1.json',dict(contract_id='A10_ENGINEERING_GATES_R1',status='PENDING_CLEAN_DETACHED',gates=gates,
        source_contract=bind('config/source_authority_governance_r1.json'),project_controls=bind('reports/audits/A10_PROJECT_GOVERNANCE_CONTROLS_R1.json'),
        scan=bind('reports/audits/V4_SOURCE_AUTHORITY_GOVERNANCE_SCAN_R1.json'),open_findings=len(scan['findings']),
        findings_do_not_grant_source_authority=True,accepted_heads_unchanged=True,external_acceptance=None))
    print(json.dumps(dict(status='PASS_A10_PROJECT_CONTROLS',controls=len(controls),findings=len(scan['findings']))))

if __name__=='__main__':main()
