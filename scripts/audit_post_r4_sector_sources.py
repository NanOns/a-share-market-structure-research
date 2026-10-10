"""Read-only FIX-B source adjudication; no lifecycle publication or admission."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/v4_r4_post_audit_repair_20261010/03_B_SECTOR'

def binding(path):
    p = ROOT / path
    raw = p.read_bytes()
    return dict(path=str(path).replace('\\', '/'), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    temp = p.with_suffix(p.suffix + '.tmp')
    temp.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, p)

def main():
    head_path = 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    protected = binding(head_path)
    head = json.loads((ROOT / head_path).read_text(encoding='utf-8'))
    target = head['accepted_trade_date']
    owner = head['owners'][target]['sector']
    assert binding(owner['path']) == owner
    # Read three original real examples only; do not repeat 400-row null demo.
    with gzip.open(ROOT / owner['path'], 'rt', encoding='utf-8') as stream:
        samples = [json.loads(next(stream)) for _ in range(3)]
    ledger_root = ROOT / 'docs/evidence/v4_current_snapshot_r4_20261010'
    # Consult latest applicable ledgers and preserve their bytes identities.
    consulted = []
    for p in sorted(ledger_root.rglob('*')):
        if p.is_file() and p.suffix in ('.md', '.json'):
            raw = p.read_bytes()
            if p.suffix == '.json':
                json.loads(raw)
            else:
                raw.decode('utf-8-sig')
            consulted.append(binding(p.relative_to(ROOT)))
    matrix = json.loads((ledger_root / '02_B_SECTOR/B_SECTOR_PRODUCER_INPUT_MATRIX.json').read_text())
    reused = json.loads((ledger_root / '02_B_SECTOR/B_SECTOR_ORACLE_RESULT.json').read_text())
    for key in ('input', 'output', 'oracle', 'code'):
        assert binding(reused[key]['path']) == reused[key]
    prior_cases = {c['case']: c['pass_result'] for c in reused['negative_and_boundary_results']}
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    fields = []
    causes = {
        'CONFIRMED': 'No admitted V4-11 confirmation Producer. Exact valid-member, normal-rank and coverage receipt plus accepted legacy AST mapping required; Native quality PROXY_RECONSTRUCTED does not meet formal qualification.',
        'WARM': 'No admitted WARM Producer. Legacy SETUP/RECOVERY, q20/dq5_3 rank receipts absent; native dq5 not interchangeable. Amount A branch additionally requires strict H21 originals.',
        'frozen_invalidation': 'No SECTOR creation-frozen Episode with original contract hash and exact prior official session; stock structure events are not SECTOR Episodes.',
        'episode_invalidation_contract_id': 'No SECTOR creation-frozen invalidation contract ID/version/hash owner at exact T-1.',
        'followup_complete': 'No independently admitted SECTOR due_plan plus actually due settled Owner; future T+ sessions and right censoring cannot supply completion.',
        'scenario': 'No formally admitted V4-11/V4-12 SECTOR scenario Producer or frozen priority; Rotation and seed are not substitutes.',
    }
    for row in matrix['fields']:
        f = row['field']
        assert row['current_contract']['implemented'] is False
        fields.append(dict(field=f, producer_contract=row['current_contract'], accepted_source_owner=None,
            recovered=False, final_status='FORMAL_OWNER_BLOCKED', exact_missing=causes[f],
            development_action='STOP_UNSOURCED_FIELD; REQUEST_INDEPENDENT_SOURCE_AND_CONTRACT_ADMISSION'))
    source_bindings = {key: head['owners'][target][key] for key in ('sector', 'core', 'base_profile', 'seed', 'sector_receipt')}
    source_bindings['membership_snapshot'] = head['membership_snapshot']
    for b in source_bindings.values():
        assert binding(b['path']) == b
    samples_out = []
    for r in samples:
        chosen = {k: v for k, v in r['fields'].items() if k in ('dq5', 'sector_participation_proxy', 'breadth_ret1', 'ma20_width')}
        assert r['trade_date'] == target
        assert len(r['member_ids']) == len(set(r['member_ids']))
        for value in chosen.values():
            assert value['max_source_date'] <= target
            assert value['production_eligible_scope'] == 'DATED_OPERATIONAL_RESEARCH_REPROJECTION_ONLY'
            for b in value['source_publications'].values():
                assert binding(b['path']) == b
        samples_out.append(dict(sector_id=r['sector_id'], member_ids=r['member_ids'],
            member_count=len(r['member_ids']), member_set_asof=r.get('member_set_asof'), fields=chosen))
    common = dict(BASE_SHA=sha, code_binding=binding('scripts/audit_post_r4_sector_sources.py'),
        T0=target, accepted_head=protected, formal_owner='SECTOR_D2_OWNER_OPEN',
        external_acceptance='EXTERNAL_RECHECK_REQUESTED', head_changed=False)
    write('B_REAL_PRODUCER_RECOVERY_MATRIX.json', dict(common, fields=fields, consulted_ledgers=consulted,
        status='FORMAL_OWNER_BLOCKED', source_scope='CURRENT_ACCEPTED_HEAD_AND_LATEST_R4_LEDGERS_ONLY',
        formal_recovery_count=0, legacy_400_null_demo_rerun=False,
        unchanged_boundary_evidence=dict(binding=binding('docs/evidence/v4_current_snapshot_r4_20261010/02_B_SECTOR/B_SECTOR_ORACLE_RESULT.json'),
            code_and_inputs_SHA_verified=True, replayed=False, case_results=prior_cases,
            scope='Inherited synthetic candidate/reducer boundary evidence only; not formal real lifecycle'),
        source_tests=dict(exit_code=0, checked_real_examples=3, all_input_bindings_verified=True,
            cutoff_and_member_denominator_verified=True, independent_oracle='Raw accepted owner bytes and per-field source_publications; no factor recomputation')))
    write('B_SECTOR_ACCEPTABLE_EXTRACTIONS.json', dict(common,
        status='PASS_SCOPED_SOURCE_READBACK_ONLY', source_owner=owner, versioned_extraction='Existing V4_08_SECTOR_NATIVE_V1 / V4_08_ALGORITHM_PARAMETER_SET_R5',
        source_bindings=source_bindings, prior='Native dq5 prior membership_snapshot_id explicitly retained in sample',
        candidate='Existing operational read-only UI domain; no new D2 candidate fabricated',
        membership_mode=head['membership_mode'], first_available=head['observed_at'],
        first_available_scope='Operational owner publication only; does not prove historical field first availability',
        samples=samples_out, formal_lifecycle_enabled=False, strict_PIT=False))
    write('B_EXACT_UNAVAILABLE_INPUTS.md', '# FIX-B exact unavailable inputs\n\n' + '\n\n'.join('**'+f+'**: '+causes[f] for f in causes) +
        '\n\nThe search conclusion applies to current Head-bound Owner/registry and latest R4 ledgers. It is not a claim that no original exists anywhere. No future session is substituted. Strict H21 remains an independent audit gate.\n')
    write('B_SECTOR_FORMAL_ADMISSION_DIFF.md', '# FIX-B formal admission delta\n\n'
        'T0: '+target+'; BASE_SHA: '+sha+'.\n\n'
        'Before and after: all six formal lifecycle fields remain FORMAL_OWNER_BLOCKED. No source meets both current availability and formal Producer admission. The task card explicitly requires stopping false development when hard dependencies are absent; no lifecycle algorithm or Head was changed.\n\n'
        'Incremental result: actual Native source bytes, three original numeric examples, input SHAs, current member relationship version and operational publication timestamp verified. Available dq5, participation and member domains continue under existing operational research scope. PROXY_RECONSTRUCTED / AS_RECORDED=false is retained. This is source readback PASS_SCOPED only, not SECTOR_D2_FORMAL_OWNER_PASS or UI/browser acceptance.\n\n'
        'Matrix boundaries: prior state / missing history / original Episode / invalidation priority / confirmation-invalidated collision / re-entry / due settlement cannot be tested as real SECTOR production transitions without admitted inputs. Holiday order is supplied by published sessions (09/30 to 10/08); it is not inferred from calendar days. Missing/changing members preserve original snapshot IDs and unique denominators. No synthetic matrix is presented as recovered real output; existing independent candidate oracle evidence is reused unchanged.\n\n'
        'Next stage: independently accept exact Producer AST and source receipts, original prior SECTOR Episode, frozen invalidation and due/scenario Owners. EXTERNAL_RECHECK_REQUESTED; no developer formal signature.\n')
    assert binding(head_path) == protected
    print(json.dumps(dict(status='PASS_SCOPED_SOURCE_READBACK_ONLY', formal='FORMAL_OWNER_BLOCKED', examples=3, head_unchanged=True)))

if __name__ == '__main__':
    main()
