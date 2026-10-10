"""Bounded read-only runtime checks and independent production/deployment verdicts."""
from pathlib import Path
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_service.core_product_bff_r1 import CoreProductBFFR1
from replay_r4_post_audit_runtime import read, ROUTES

def main():
    evidence = ROOT / 'docs/evidence/v4_r4_post_audit_repair_20261010/01_E_RUNTIME'
    context = json.loads(read('context')['response_body'])
    token = context['context_token']
    sample_requests = [
        ('stocks', dict(q='688349', trade_date='2026-09-30')),
        ('stocks/SEC-C08B6C24E4F39D8E85C03F8588661538', {}),
        ('market/breadth', {}), ('market/axes', {}), ('forward', {})]
    actual = [dict(route=route, **read(route, dict(context_token=token, **q)))
              for route, q in sample_requests]
    atomic_json(ROOT, evidence / 'E_LIVE_28765_EXTRA_REQUESTS.json', actual)
    bff = CoreProductBFFR1(accepted_api(ROOT), None)
    new = []
    for route in ('context',) + ROUTES + ('market/breadth', 'market/axes'):
        query = {} if route == 'context' else dict(context_token=token)
        code, data = bff.get('/api/v4/' + route, query)
        new.append(dict(route=route, code=code, status=data.get('status'),
                        reason=data.get('reason'), reason_text=data.get('reason_text'),
                        context_token=data.get('context_token'), payload=data))
    code, old = bff.get('/api/v4/stocks', dict(context_token=token, q='688349', trade_date='2026-09-30'))
    new.append(dict(route='stocks historical 688349', code=code, payload=old))
    atomic_json(ROOT, evidence / 'E_NEW_CODE_READBACK_SEPARATE_FROM_PROD.json', dict(
        scope='IN_PROCESS_NEW_CODE_READ_ONLY_NOT_28765_OR_DOM', records=new))
    ps = ['powershell', '-NoProfile', '-Command',
          "Get-CimInstance Win32_Process -Filter 'ProcessId = 41528' | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"]
    process = json.loads(subprocess.check_output(ps, text=True))
    protected = {name:hashlib.sha256((ROOT/'data/v4'/name).read_bytes()).hexdigest()
                 for name in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json')}
    atomic_json(ROOT, evidence / 'E_NORMAL_CLOSE_AND_NEW_PID_RECEIPT.json', dict(
        captured_at=datetime.now(timezone.utc).isoformat(), old_process=process,
        old_process_main_window_handle=0, production_port=28765, new_pid=None,
        status='NORMAL_CLOSE_BLOCKER', startup_attempt_exit_code=1,
        startup_attempt_output='PORT_OCCUPIED: previous service must exit normally; no process stopped',
        current_runtime_contract=context['context'].get('bff_contract_id'), protected_heads=protected,
        normal_close_mechanism='NO_WINDOW_NO_STOP_ENDPOINT_PARENT_NO_LONGER_PRESENT',
        user_steps=[
            'If the original launcher still exposes a documented Stop/Exit action, use it and verify PID 41528 exits. The observed process itself has no console/window and no stop HTTP endpoint; Ctrl+C on a different terminal cannot close it.',
            'Do not use taskkill, Stop-Process, ACL changes, logout, restart or an injected shutdown helper under this task.',
            'After normal exit, verify Get-NetTCPConnection -LocalPort 28765 -State Listen returns no listener, then in G:/codex work/大A交易 run E:/python/python.exe -B scripts/start_product_attested_r4.py in a console. Stop this future console with Ctrl+C.',
            'Read runtime/r4_product_loaded_modules.json and replay scripts/replay_r4_post_audit_runtime.py; repeat browser acceptance before requesting external sign-off.'],
        attestation_available=False, loaded_module_bytes='NOT_PROVEN_IN_OLD_PROCESS'))
    print(json.dumps(dict(actual=[dict(route=x['route'],code=x['http_status']) for x in actual],
                          isolated=[dict(route=x['route'],code=x['code']) for x in new], protected=protected)))

if __name__ == '__main__':
    for key in ('TMP','TEMP','TMPDIR'):
        os.environ[key]='G:/codex_tmp'
    main()
