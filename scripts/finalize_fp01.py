"""FP-01 release evidence and scoped acceptance; no subsequent stage execution."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.request import urlopen

from fp01_evidence import ROOT, OUT, ref, write

sys.path.insert(0, str(ROOT / 'src'))
from v4.operational_release import AdmissionError, ReleaseStore


def main():
    entry = json.loads((OUT / 'ENTRY.json').read_bytes())
    protected = []
    for old in entry['protected']:
        actual = ref(old['path'])
        if actual != old:
            raise ValueError('FROZEN_BYTES_CHANGED:' + old['path'])
        protected.append(actual)
    pre = json.loads((OUT / 'TDX_PRE.json').read_bytes())
    post = json.loads((OUT / 'TDX_POST.json').read_bytes())
    assert pre == post
    phase0 = json.loads((ROOT / entry['phase0']['path']).read_bytes())
    assert phase0.get('phase0_status', phase0.get('status')) in ('FULL_PASS','DEGRADED_PASS')
    write(OUT / 'PROTECTED_READBACK.json', dict(status='PASS', protected_count=len(protected),
        baseline_bindings=ref(OUT / 'ENTRY.json'), tdx_pre=ref(OUT / 'TDX_PRE.json'), tdx_post=ref(OUT / 'TDX_POST.json'),
        tdx_file_count=post['file_count'], tdx_checksum_unchanged=True, legacy_contracts_unchanged=True))

    # A fresh directed run, with mandatory E/G-owned temporary storage.
    temp = Path('E:/codex_tmp/test_temp')
    temp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
               '--basetemp',str(temp / ('fp01_final_' + uuid.uuid4().hex)),
               'tests/test_fp01_operational_release.py','tests/v4_phase0/test_phase0_final_gate.py',
               'tests/test_v4_19_focus_cutover_contract.py','tests/test_v4_20_default_ui_contract.py',
               'tests/test_v4_current_accepted_reader.py','tests/test_v4_current_daily_refresh.py']
    run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    write(OUT / 'regression.txt', run.stdout + run.stderr)
    write(OUT / 'REGRESSION.json', dict(command=command, returncode=run.returncode, output=ref(OUT / 'regression.txt'),
        scope='New policy counterexamples + existing phase0, V4-19/20, exact current reader and daily refresh; not entire repository regression.'))
    print((run.stdout + run.stderr).decode('utf8', errors='replace'), flush=True)
    if run.returncode:
        raise ValueError('REGRESSION_FAILED')

    store = ReleaseStore(ROOT)
    release = store.read()
    previous = store.pointer.read_bytes()
    digest = store.current_digest()
    try:
        store.publish(dict(release, drill='STALE_CAS_MUST_NOT_ACTIVATE'), 'f'*64)
    except AdmissionError as exc:
        assert str(exc) == 'STALE_PREDECESSOR'
    else:
        raise ValueError('STALE_CAS_ACCEPTED')
    def fail_readback(_):
        raise RuntimeError('FP01_REAL_RELEASE_INJECTED_READBACK_FAILURE')
    try:
        store.publish(dict(release, drill='REAL_RETAINED_SOURCE_FAILURE_INJECTION'), digest, fail_readback)
    except RuntimeError:
        pass
    else:
        raise ValueError('READBACK_FAILURE_NOT_INJECTED')
    assert store.pointer.read_bytes() == previous
    green = store.publish(dict(release, drill='REAL_RETAINED_SOURCE_REVERSIBLE_GREEN'), digest)
    restored = store.rollback(digest, green['pointer_digest'])
    assert store.pointer.read_bytes() == previous and store.read() == release
    write(OUT / 'REAL_RELEASE_ROLLBACK.json', dict(status='PASS', stale_cas='REJECTED',
        failed_readback='EXACT_PREDECESSOR_RESTORED', green_receipt=green, rollback=restored,
        scope='Real retained profile source, operational registry only; legacy production pointer untouched.'))

    with urlopen('http://127.0.0.1:28765/api/operations/status', timeout=10) as response:
        service = json.load(response)
    assert service['service_state']=='READY' and service['service_mode']=='V4_DEFAULT_WORKBENCH'
    assert not any(service['production_permission'].values())
    write(OUT / 'SERVICE_COMPATIBILITY.json', dict(status='PASS', actual=service,
        browser='Codex in-app real browser; only IAB/MCP Apps connected, no Edge browser control available in this session.',
        screenshot=ref(OUT / 'browser_compatibility.png'), ax=ref(OUT / 'browser_compatibility_ax.txt'),
        limit='Compatibility evidence only. Six-page Edge E2E belongs to FP13, not claimed by FP01.'))

    inv = json.loads((OUT / 'producer_inventory.json').read_bytes())
    qa = json.loads((OUT / 'QA_V4_13_PROFILE_ADVANCED.json').read_bytes())
    backlog = [
        dict(id='FP01-GAP-01', scope='V4-13 advanced profile', classification='EXISTING_REAL_OUTPUT_NOT_READ_BY_FULL_UI', evidence=ref('data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'), next='FP02/03/07 read real profile, preserve field quality', acceptance='Exact field/identity/context readback and full pagination'),
        dict(id='FP01-GAP-02', scope='V4-12/13 owner-dependent signal, LOO, legacy B2', classification='REAL_INPUT_OR_IMPLEMENTATION_SCOPE_GAP', evidence=ref('data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'), next='FP02 targeted source/producer closure; do not blanket rerun foundations', acceptance='Each affected field has exact real source and independent QA; unknown remains unknown'),
        dict(id='FP01-GAP-03', scope='V4-22 final independent-audit business runtime', classification='CONTRACT_ONLY_NO_OWNED_RUNTIME_FOUND', evidence=ref('config/v4_22_independent_audit_contract_v1.json'), next='FP11 diagnostic contract and FP13/14 actual audit/release evidence', acceptance='Real runtime/receipts; never derive final PASS from design vectors'),
        dict(id='FP01-GAP-04', scope='Market Regime / sector rotation / core profiles', classification='EXISTING_PRODUCER_AND_OWNER_RESULTS_REQUIRE_DOMAIN_ADAPTER_QA', evidence=ref(OUT / 'producer_inventory.json'), next='FP02 source-version/date mapping, FP05/06/07 UI', acceptance='Four axes, actual sector state and per-stock profiles sampled against exact owner output'),
        dict(id='FP01-GAP-05', scope='Focus historical reader and V4 automatic tracking', classification='EXISTING_ENGINEERING_NEEDS_SOURCE_ROUTE_ADMISSION', evidence=ref('config/focus_core_release_gate_v1.json'), next='FP08 exact historical source and transaction/reentry QA; FP14 route CAS', acceptance='Episode history retained and not conflated with cohort'),
        dict(id='FP01-GAP-06', scope='FEP E1-E5', classification='EXISTING_ENGINEERING_OR_RECONSTRUCTION_NOT_AUTOMATIC_REAL_PRODUCTION_OUTPUT', evidence=ref('reports/fep_e5_r1r1c/STAGE_ACCEPTANCE_AND_NEXT.json'), next='FP02/10 bind real historical/current dataset vs engineering fixture lanes and QA', acceptance='No fixture/model priority/profit claim without scoped output QA'),
        dict(id='FP01-GAP-07', scope='M14 public sources', classification='EXISTING_OPTIONAL_PRODUCERS_REQUEST_BOUND_ADAPTER_REQUIRED', evidence=ref('config/m14_source_registry_v1.json'), next='FP09 per-dataset gates, bounded real requests; no hot-rank persistence', acceptance='Timestamps/cache boundaries/source failure isolation verified'),
        dict(id='FP01-GAP-08', scope='Forward pending maturity and later dates', classification='VALID_LIFECYCLE_AND_VALIDATION_DEBT', evidence=ref('data/v4/V4_15_ACCEPTED_HEAD.json'), next='FP10 retain cohort/outcomes, FP02 daily safe no-op', acceptance='PENDING/right censoring retained; maturity never fabricated'),
    ]
    write(OUT / 'TARGETED_REPAIR_BACKLOG.json', backlog)
    matrix = []
    for row in inv['modules']:
        matrix.append(dict(feature_id=row['feature_id'], owner=row['owner'], producer_code=row['code'],
            input_output_bindings=row['declared_input_output_bindings'], full_graph=row['full_reference_graph'],
            current_output=row['current_output'], retained_run_evidence=row['retained_run_evidence'],
            operational_state='ENGINEERING_NOT_READY',
            reason='New full-domain release adapter/real-output QA not yet executed in FP01; not a declaration that existing algorithms are absent.',
            evidence_state='VALIDATION_ONGOING', data_quality_state=None, quality_assessment_status='NOT_ASSESSED_FOR_NEW_RELEASE',
            quality_reason='No domain quality verdict invented from missing release QA; original owner field qualities remain authoritative.',
            engineering_qa=row['engineering_qa'], long_term_validation_debt=row['long_term_validation_debt'],
            api_current=row['api_current'], api_target=row['api_target'], ui_current=row['ui_current'], page_entry=row['page_entry'],
            next=row['action']))
    for item in release['admissions']:
        matrix.append(dict(feature_id=item['feature_id'], operational_state=item['operational_state'],
            evidence_state=item['evidence_state'], data_quality_state=item['data_quality_state'], metadata=item['metadata'],
            source=item['request']['output'], code=item['request']['code'], contract=item['request']['contract'],
            qa=item['request']['qa'], publication=ref(OUT / 'OPERATIONAL_PUBLISH_RECEIPT.json'),
            rows=qa['row_count'], page_entry='个股研究', api_current='FP02/03_NOT_YET_CONNECTED',
            long_term_validation_debt='Historical reconstruction not AS_RECORDED; field UNKNOWN and missing reasons retained; no statistical superiority asserted.'))
    write(OUT / 'release_readiness_matrix.json', dict(contract_id='V4_RELEASE_READINESS_MATRIX_V1',
        stage='FP-01', status='POLICY_AND_SCOPED_ADMISSION_PASS', full_product_release=False, modules=matrix,
        producer_inventory=ref(OUT / 'producer_inventory.json'), source_graph=ref(OUT / 'producer_inventory_full.json.gz'),
        repair_backlog=ref(OUT / 'TARGETED_REPAIR_BACKLOG.json')))

    conflict = []
    def add(path, pointer, old, migration):
        conflict.append(dict(source=ref(path), json_pointer=pointer, historical_semantics=old,
                             successor_rule=migration, original_bytes='PRESERVED', policy=ref('config/v4_operational_production_release_policy_v1.json')))
    add('config/v4_capability_cutover_policy_v1.json','/production_permission', 'Shadow AND Forward AND Migration', 'Keep as historical proof dimension; operational release uses exact real output, integrity, independent QA and reversible receipt')
    add('config/v4_capability_cutover_policy_v1.json','/shadow_stable_gate/accepted_consecutive_market_sessions',20,'Sample accumulation in evidence_state; no 20-session global operational delay')
    add('config/v4_capability_cutover_policy_v1.json','/sector_and_rotation_forward_gates/status','THRESHOLDS_UNSET_SHADOW_ONLY','No fabricated thresholds; operational integrity QA separate from unproved Forward efficacy')
    old19=json.loads((ROOT/'config/v4_19_focus_source_cutover_contract_v1.json').read_bytes())
    for key, value in old19['capability_registry'].items():
        add('config/v4_19_focus_source_cutover_contract_v1.json','/capability_registry/'+key,
            dict(production_permission=value['production_permission'], required_dependencies=value['required_dependencies'], accepted_receipts=value['accepted_receipts']),
            'Historical receipts remain null/false; successor operating receipt is separate. Dependency integrity remains capability-specific. Focus route CAS requires FP08 engineering QA, not fabricated historical gates.')
    for p in ['config/v4_20_default_ui_cutover_contract_v1.json','config/v4_20_default_ui_cutover_contract_v2.json']:
        add(p,'/','Old UI source modes resolve historical permission','FP03/04 consume three state dimensions; genuine operational-admitted output may display as normal research production; do not alter old permissions')
    add('config/v4_production_runtime_authority_v1.json','/read_authority','Frozen V4-15 seven-summary reader','v2 scoped operational registry; FP02 domain adapter then FP14 service switch; retain exact v1 rollback and Shadow')
    add('config/v4_current_stage_authority_v2.json','/production',False,'Historical stage authority is not rewritten; new operating release authority is explicit and separately scoped')
    add('config/v4_cross_stage_current_audit_authority_v4.json','/current_head','Scoped defects and evidence debt together in historical blockers','Each real source/engineering defect stays affected-scope blocking; maturity and historical availability debts cannot globally block unrelated operation')
    add('reports/fep_e5_r1r1c/STAGE_ACCEPTANCE_AND_NEXT.json','/','production/MODEL_DISPLAY/PRIORITY_USE false','Keep factual historical engineering scope; new model display/priority needs exact real dataset QA and successor receipt, no auto TRUE')
    write(OUT / 'AUTHORITY_CONFLICT_MAP.json', conflict)

    rows = ['# FP-01 功能→生产器→输入输出→API→页面矩阵', '',
            '完整代码声明、owner声明与来源图见 producer_inventory.json 及压缩全图；不是把1126个helper声明当成1126个已运行算法。', '',
            '|域|模块|代码文件数|owner来源边数（去重）|页面入口|本阶段处置|','|---|---|---:|---:|---|---|']
    for row in inv['modules']:
        rows.append(f"|{row['feature_id']}|{row['module']}|{len(row['code'])}|{row['full_declared_reference_count']}|{row['page_entry']}|已有代码/owner逐域适配QA；不沿用旧20日全局门|")
    write(OUT/'FEATURE_MATRIX.md', ('\n'.join(rows)+'\n').encode('utf8'))
    write(OUT/'STAGE_ACCEPTANCE.json', dict(stage='FP-01', stage_contract='V4_OPERATIONAL_PRODUCTION_RELEASE_POLICY_V1',
        result='PASS_LOCAL_SCOPED_READY_FOR_INDEPENDENT_REVIEW', external_acceptance='NOT_CLAIMED',
        inventory_modules=len(inv['modules']), producer_code_declarations=len(inv['producer_declarations']),
        independent_real_rows_scanned=qa['row_count'], operational_scopes=[r['feature_id'] for r in release['admissions']],
        tests=ref(OUT/'REGRESSION.json'), protected=ref(OUT/'PROTECTED_READBACK.json'),
        release_matrix=ref(OUT/'release_readiness_matrix.json'), conflicts=ref(OUT/'AUTHORITY_CONFLICT_MAP.json'),
        browser=ref(OUT/'SERVICE_COMPATIBILITY.json'), rollback=ref(OUT/'REAL_RELEASE_ROLLBACK.json'),
        full_product_release=False, next_stage='FP02_FP03_FP04_AFTER_SEPARATE_DISPATCH; NOT_EXECUTED_IN_THIS_FP01_TASK'))


if __name__ == '__main__':
    main()
