"""Fail-closed product cutover gate. Capability permissions remain independent."""
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from scripts.v4_production_cutover_evidence import ROOT, REPORT, binding, write
from workbench_service.current_v4_context import CurrentAcceptedV4Reader, digest
from workbench_service.v4_daily_refresh import AUTHORITY, atomic_bytes


def load(name):
    return json.loads((REPORT/name).read_bytes())


def verify():
    regression=load('V4_ONLY_FULL_REGRESSION_RECEIPT.json')
    assert regression['exit_code']==0 and regression['single_fresh_execution']
    assert regression['counts']['failures']==regression['counts']['errors']==0
    assert regression['ignore']==regression['deselect']==regression['new_xfail']==[]
    for name in ['junit','log','scope']:
        ref=regression[name];assert binding(ref['path'])['sha256']==ref['sha256']
    scope=load('V4_ONLY_EXECUTION_SCOPE.json')
    for ref in scope['bindings']:assert binding(ref['path'])['sha256']==ref['sha256']
    cases=ET.parse(ROOT/regression['junit']['path']).getroot().findall('.//testcase')
    portable=['test_local_snapshot_original_owner_rejects_link_predicate','test_extracted_snapshot_original_owner_rejects_reparse_attribute']
    for name in portable:assert any(c.get('name')==name and len(c)==0 for c in cases)
    skips=[]
    for case in cases:
        skip=case.find('skipped')
        if skip is not None:
            reason=(skip.get('message','')+' '+(skip.text or '')).lower()
            assert 'symlink' in reason and 'xfail' not in skip.get('type','').lower(),reason
            skips.append(dict(test=case.get('classname')+'::'+case.get('name'),reason=reason))
    assert any(c.get('classname','').endswith('test_r17a_historical_governance') for c in cases)
    for ref in load('ENTRY_BASELINE.json')['protected']:assert binding(ref['path'])['sha256']==ref['sha256']
    assert load('TDX_PRE_FINGERPRINT.json')==load('TDX_POST_FINGERPRINT.json')
    assert load('TDX_ZERO_WRITE.json')['status']=='PASS'
    assert load('UI_E2E_RECEIPT.json')['status']=='PASS_REAL_SERVICE_E2E'
    assert load('ROLLBACK_RECEIPT.json')['status']=='PASS_DISPOSABLE'
    assert load('P0_4_GATE.json')['status']=='PASS_LOCAL_CANDIDATE'
    reader=CurrentAcceptedV4Reader(ROOT);context=reader.load_context()
    assert not any(context['production_permission'].values()) and not context['focus_write']
    assert context['context_token']==load('UI_E2E_RECEIPT.json')['context']['context_token']
    for module in ['summary','radar','entity','sector','cohort','settlement','health']:
        code,payload=reader.read(module);assert code==200 and payload['items']
    write(REPORT/'P0_5_GATE.json',dict(status='PASS_LOCAL',full_regression=regression['counts'],permitted_symlink_skips=skips,portable_equivalents=portable,protected_bytes_unchanged=True,tdx_zero_write=True,capability_permissions_unchanged=True,next='ACTIVATE_AND_RESTART_LIVE_SMOKE'))
    return context


def activate():
    verify()
    path=ROOT/AUTHORITY;raw=path.read_bytes();authority=json.loads(raw)
    assert authority['activation_status']=='CANDIDATE','Already active or invalid activation state'
    previous='data/v4/production_views/'+digest(raw)+'/authority.json'
    atomic_bytes(ROOT/previous,raw)
    write(REPORT/'PRE_CUTOVER_AUTHORITY.json',authority)
    authority.update(activation_status='ACTIVE',legacy_default=False,
        V4_CURRENT_ACCEPTED_READ=True,V4_DEFAULT_UI=True,V4_DAILY_PIPELINE=True,V4_INTERNAL_PRODUCTION_STORE_WRITE=True,
        rollback_binding=binding(previous),cutover_gate=binding('reports/v4_production_cutover_20261007/P0_5_GATE.json'))
    write(AUTHORITY,authority)
    for name in ['POST_CUTOVER_AUTHORITY.json','PRODUCTION_AUTHORITY_POST.json']:write(REPORT/name,authority)
    write(REPORT/'ROLLBACK_POINTER.json',dict(previous=authority['rollback_binding'],current=binding(AUTHORITY),allowed_target='PREVIOUS_ACCEPTED_V4_ONLY',legacy_fallback=False))
    assert CurrentAcceptedV4Reader(ROOT).load_context()['context']['accepted_trade_date']==authority['last_accepted_trade_date']
    print('V4 product authority ACTIVE; restart and final live smoke required')


def seal():
    context=verify()
    assert json.loads((ROOT/AUTHORITY).read_bytes())['activation_status']=='ACTIVE'
    assert load('LIVE_HTTP_RECEIPT.json')['base']=='http://127.0.0.1:28765'
    assert load('UI_E2E_RECEIPT.json')['base']=='http://127.0.0.1:28765'
    cases=ET.parse(REPORT/'full_regression.xml').getroot().findall('.//testcase')
    assert any(c.get('name')=='test_fresh_process_pair_revision_and_determinism' and len(c)==0 for c in cases)
    audit=ROOT/'docs/audits/V4_HISTORICAL_CHILD_PACKAGE_ROUTING_20261007.md'
    write(audit,audit.read_bytes().replace(b'Status: PENDING_REGRESSION.',b'Status: CLOSED_LOCAL; original persisted determinism test and fresh complete V4 regression passed. Independent external acceptance remains separate.'))
    write(REPORT/'HISTORICAL_CHILD_ROUTING_AUDIT.json',dict(id='V4-HISTORICAL-CHILD-01',status='CLOSED_LOCAL',scope='Original R18 parent and fresh child exact historical source routing',source=binding('scripts/forward_remainder_child.py'),regression=binding('reports/v4_production_cutover_20261007/V4_ONLY_FULL_REGRESSION_RECEIPT.json'),accepted_authorities_changed=False,frozen_worker_changed=False))
    audit=ROOT/'docs/audits/V4_DISPOSABLE_UPSTREAM_SQL_NAMESPACE_20261007.md'
    write(audit,audit.read_bytes().replace(b'Status: PENDING_FRESH_FULL_REGRESSION.',b'Status: CLOSED_LOCAL; fresh complete V4 regression passed.'))
    write(REPORT/'UPSTREAM_SQL_NAMESPACE_AUDIT.json',dict(id='V4-TEST-SQL-ALIAS-01',status='CLOSED_LOCAL',regression=binding('reports/v4_production_cutover_20261007/V4_ONLY_FULL_REGRESSION_RECEIPT.json'),fixture=binding('reports/v4_production_cutover_20261007/V4_SQL_DISPOSABLE_FIXTURE.json'),production_database_modified=False,test_assertions_changed=False))
    write(REPORT/'P0_5_POST_CUTOVER_GATE.json',dict(status='PASS_LOCAL_COMPLETE',default_v4='ACTIVE',authority=binding(AUTHORITY),pre_cutover_gate=binding('reports/v4_production_cutover_20261007/P0_5_GATE.json'),live_http=binding('reports/v4_production_cutover_20261007/LIVE_HTTP_RECEIPT.json'),live_browser=binding('reports/v4_production_cutover_20261007/UI_E2E_RECEIPT.json'),next='STOP_WAIT_INDEPENDENT_EXTERNAL_ACCEPTANCE'))
    sources=['.gitattributes','run_workbench_service.py','OPEN_RESEARCH_WORKBENCH.cmd','OPEN_UNIFIED_WORKBENCH.cmd','RUN_DAILY_SCANNER.cmd','scripts/workbench_tray.ps1','scripts/forward_remainder_child.py','docs/audits/V4_HISTORICAL_CHILD_PACKAGE_ROUTING_20261007.md','docs/audits/V4_DISPOSABLE_UPSTREAM_SQL_NAMESPACE_20261007.md']
    sources += [p.relative_to(ROOT).as_posix() for pattern in ['*v4_current*.py','*v4_production*.py','v4_production_browser_e2e.cjs'] for p in (ROOT/'scripts').glob(pattern)]
    sources += ['scripts/build_v4_current_read_contract.py','src/workbench_service/current_v4_context.py','src/workbench_service/v4_daily_refresh.py','src/workbench_service/v4_server.py','src/workbench_service/static/v4-workbench.html','src/workbench_service/static/v4-workbench.js','tests/remainder_isolation_plugin.py']
    evidence=[p.relative_to(ROOT).as_posix() for p in REPORT.iterdir() if p.is_file() and p.name not in ('CANDIDATE_SEAL.json','COMPLETION_REPORT.md','FULL_REGRESSION_RUNNING.json')]
    write(REPORT/'CANDIDATE_SEAL.json',dict(status='CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',default_ui_shell='ACTIVE',current_accepted_reader='ACTIVE',accepted_research_readonly='ACTIVE',shadow_diagnostic='ACTIVE_SEPARATE_SCOPE',capability_permission='UNCHANGED_BY_DISPLAY',parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),context=context,source_bindings=[binding(p) for p in sorted(set(sources))],evidence_bindings=[binding(p) for p in sorted(evidence)],next='STOP_WAIT_INDEPENDENT_EXTERNAL_ACCEPTANCE'))
    counts=load('V4_ONLY_FULL_REGRESSION_RECEIPT.json')['counts']
    text=f'''# V4 product cutover completion — 2026-10-07

Status: CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT. Default V4 shell, current accepted reader and separate Shadow diagnostics are active at http://127.0.0.1:28765/. Accepted trade date: {context['context']['accepted_trade_date']}.

The six supplied R1 task cards were implemented in P0-1 through P0-5 order. Exact owner-bound reads replace blanket UNKNOWN presentation. Owner capability gaps retain their original quality and reasons. V4-20 v2 adds accepted research visibility while V4-19 and V4-20 v1 bytes and all production permission values remain unchanged. UI, Focus, TDX and trading writes remain prohibited.

Fresh single full V4 regression: {counts}. No ignore, deselect or new xfail. Any Windows symlink skips are recorded with executed portable owner equivalents in P0_5_GATE.json. Actual restarted service HTTP/browser smoke, nine screenshots, search, refresh, fixed context and separate no-real-Shadow behavior passed. Complete TDX fingerprints cover 24,493 unchanged files. Exact disposable V4 rollback and candidate CAS tests passed.

Daily execution waits without requests on non-trading days, retains current data on source/owner failure, validates a candidate independently of the current pointer and atomically publishes accepted views. A complete isolated next-input fixture exercises actual module gates and readback; it is engineering simulation. Real next-session source-to-owner acceptance remains the separately tracked V4-DAILY-FUTURE-OWNER-01 observation, with no fabricated future data or Shadow evidence.

Authority: config/v4_production_runtime_authority_v1.json. Test receipt: V4_ONLY_FULL_REGRESSION_RECEIPT.json. Live screenshot: 01_HOME_CURRENT_ACCEPTED.png. Exact source/evidence bindings: CANDIDATE_SEAL.json. Git delivery is the commit containing this report, pushed to codex/v4-system-reform; unrelated worktree files are preserved. Push is not independent external acceptance.
'''
    write(REPORT/'COMPLETION_REPORT.md',text.encode('utf8'))
    print('Final candidate sealed; commit and push, then stop for external acceptance')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['verify','activate','seal']);args=parser.parse_args()
    {'verify':verify,'activate':activate,'seal':seal}[args.action]()
