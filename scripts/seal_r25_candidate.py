"""R25 clean detached full regression and evidence-only WAIT seal."""
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from scripts.r25_io import ROOT, BASE, atomic, read, ref
from scripts.validate_r25_preflight import selection, protected
from scripts.validate_r20_clean_detached import prepare_current, historical_representations
from scripts.run_r25_evidence import REPORTS, DOCUMENTS

SUITES = [
    'tests/test_pre16_governance.py', 'tests/test_r21_promotion.py', 'tests/test_r22_contracts.py',
    'tests/test_r22r1_contracts.py', 'tests/test_r23_runtime.py', 'tests/test_r23r1_runtime.py',
    'tests/test_r24_activation.py', 'tests/test_r24r1_authority.py', 'tests/test_r24r1_a20.py',
    'tests/test_r25_packet.py',
]


def summary(path):
    cases = list(ET.parse(path).iter('testcase'))
    assert cases and not any(c.find(k) is not None for c in cases for k in ('failure', 'error', 'skipped'))
    return dict(passed=len(cases), failures=0, errors=0, skipped=0, deselected=0, suites=SUITES)


def local():
    before = protected()
    xml = ROOT / 'reports/r25/local_tests.xml'
    staging_xml = xml.with_suffix('.junit-staging.xml')
    cmd = [sys.executable, '-m', 'pytest', *SUITES, '-q', '--junitxml='+str(staging_xml)]
    result = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, PYTHONPATH='src'+os.pathsep+'.'), capture_output=True)
    atomic('reports/r25/local_runner.log', result.stdout+result.stderr, raw=True)
    assert result.returncode == 0, 'LOCAL_REGRESSION_FAILED'
    assert b'deselected' not in result.stdout
    tests = summary(staging_xml)
    atomic('reports/r25/local_tests.xml', staging_xml.read_bytes(), raw=True)
    staging_xml.unlink()
    assert before == protected()
    atomic('reports/r25/LOCAL_TEST_SUMMARY.json', dict(tests, status='PASS_LOCAL_ENGINEERING_ONLY', command=cmd,
                                                   protected_unchanged=True, real_packet_ready=False, no_broad_deselection=True))
    print(dict(status='PASS_LOCAL', **summary(xml)), flush=True)


def clean(source, tag):
    assert subprocess.check_output(['git', 'rev-parse', tag], cwd=ROOT, text=True).strip() == source
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, source], cwd=ROOT, check=True)
    print('Preparing exact clean detached R25 source and LFS objects', flush=True)
    directory, lfs = prepare_current(source)
    representations = historical_representations(directory, read('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json'))
    assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=directory) == b''
    print('Running all ten stage suites without deselection', flush=True)
    xml = ROOT / 'reports/r25/clean_tests.xml'
    staging_xml = xml.with_suffix('.junit-staging.xml')
    cmd = [sys.executable, '-m', 'pytest', *SUITES, '-q', '--junitxml='+str(staging_xml)]
    result = subprocess.run(cmd, cwd=directory, env=dict(os.environ, PYTHONPATH='src'+os.pathsep+'.'), capture_output=True)
    atomic('reports/r25/clean_runner.log', result.stdout+result.stderr, raw=True)
    assert result.returncode == 0, 'CLEAN_REGRESSION_FAILED'
    assert b'deselected' not in result.stdout
    assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=directory) == b''
    tests = summary(staging_xml)
    atomic('reports/r25/clean_tests.xml', staging_xml.read_bytes(), raw=True)
    staging_xml.unlink()
    inventory = selection(directory)
    assert inventory == read('reports/r25/INDEPENDENT_R25_PREFLIGHT_ORACLE.json')['persisted_exact_inventory']
    assert protected(directory) == protected()
    atomic('reports/r25/CLEAN_REGRESSION.json', dict(tests, status='PASS_LOCAL_ENGINEERING_ONLY', tested_source=source, immutable_tag=tag,
           checkout=str(directory), git_status_before='', git_status_after='', command=cmd, verified_lfs_objects=lfs,
           registered_representations=representations, independent_selection=inventory, no_broad_deselection=True, real_packet_ready=False))
    disposition = read('reports/r25/CLEAN_ATTEMPT_R1_DISPOSITION.json')
    disposition.update(status='CLOSED_LOCAL_FINAL_CLEAN_RETEST_PASSED_PENDING_EXTERNAL_REVIEW',
                       final_tested_source=source, final_immutable_tag=tag, final_passed=tests['passed'],
                       final_clean_regression=ref('reports/r25/CLEAN_REGRESSION.json'))
    atomic('reports/r25/CLEAN_ATTEMPT_R1_DISPOSITION.json', disposition)
    evidence = [ref('reports/r25/'+name+'.json') for name in REPORTS+['LOCAL_TEST_SUMMARY', 'CLEAN_REGRESSION']]
    evidence += [ref('reports/r25/DEVELOPMENT_CHECK_DISPOSITION.json'), ref('docs/evidence/r25/R25_EXECUTION_DISPOSITION_20261004.md'), ref('config/v4_16_r25_packet_preflight_v1.json')]
    evidence += [ref('reports/r25/CLEAN_ATTEMPT_R1_DISPOSITION.json')]
    evidence += [ref('reports/r25/'+name) for name in ['local_tests.xml', 'local_runner.log', 'clean_tests.xml', 'clean_runner.log']]
    seal = dict(status='WAIT_ACCEPTED_DAILY_INPUT', R25_REAL_ACTIVATION_PACKET='WAIT_ACCEPTED_DAILY_INPUT', execution_baseline=BASE,
                tested_source=source, immutable_tag=tag, post_test_changes='EVIDENCE_ONLY', target_trade_date=None,
                AUTHORITY_PACKET_EXECUTION='NOT_CONSTRUCTED_WAIT_ACCEPTED_DAILY_INPUT', REAL_SHADOW_EXECUTION='NOT_STARTED',
                external_acceptance=None, runtime_authorized=False, real_shadow_authorized=False, grant=None,
                REAL_SHADOW_OBSERVATIONS=0, PIT_OBSERVED_REAL_SAMPLES=0, Production=False, Shadow=False, Focus=False, V4_16=False,
                Stage='V4_00_TO_V4_15_ACCEPTED', Data='2026-09-30', V4_16_ACCEPTED_HEAD='NOT_CREATED', real_database_created=False,
                local_regression=read('reports/r25/LOCAL_TEST_SUMMARY.json'), clean_regression=tests, evidence=evidence,
                upstream_external_audit=ref('docs/evidence/r25/'+DOCUMENTS[2]),
                acceptance_scope='LOCAL_PREPARATION_ENGINEERING_ONLY; NO_TARGET_REAL_PACKET; NO_REAL_EXECUTION_AUTHORIZATION',
                unrelated_v4_17_engineering='NOT_BLOCKED_BY_WAIT', v4_17_acceptance_v4_17g='REQUIRES_REAL_SHADOW_EVIDENCE',
                NEXT='RETRY_ON_NEXT_ELIGIBLE_ACCEPTED_MARKET_SESSION')
    atomic('reports/r25/R25_CANDIDATE_SEAL.json', seal)
    print(dict(status=seal['status'], tested_source=source, passed=tests['passed']), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['local']:
        local()
    else:
        clean(*sys.argv[1:])
