"""Real HTTP against exact production bytes and isolated absence/rollback/restart."""
import json,sys,threading,time,shutil
from pathlib import Path
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from audit_r43_r2_ui_compatibility import isolate
from workbench_service.v4_control_server_v2 import make_v4_handler
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
OUT=ROOT/'docs/evidence/r43_r2_fp_entry_20261009'

def main():
    head=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';raw=head.read_bytes();candidate=json.loads(raw)
    before={p:sha(ROOT/p) for p in json.loads((OUT/'ENTRY_STAGE_CONTRACT.json').read_bytes())['protected']}
    folders=sorted(Path('E:/codex_tmp/r43_r1_ui').glob('tmp*'),key=lambda p:p.stat().st_mtime)
    store=isolate(candidate,str(folders[-1]) if folders else None)
    for path in ['config/v4_control_adapter_v2.json','src/workbench_service/v4_control_server_v2.py',
                 'src/workbench_service/operational_control_status.py','src/workbench_service/operational_gap_bff_v2.py',
                 'src/workbench_service/static/r43-control-v2/app.js']:
        dest=store/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/path,dest)
    auth=store/'data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json';auth.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json',auth)
    pointer=store/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    records=[]
    def run(state,present):
        if present:atomic(pointer,raw)
        elif pointer.exists():pointer.unlink()
        server=ThreadingHTTPServer(('127.0.0.1',0),make_v4_handler(store));worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        base='http://127.0.0.1:'+str(server.server_port)
        def read(path):
            with urlopen(base+path,timeout=180) as response:body=response.read();code=response.status
            value=json.loads(body) if path.startswith('/api/') else {'bytes':len(body)}
            records.append(dict(state=state,url=base+path,status=code,payload=value))
            return value
        try:
            context=read('/api/v4/context');status=read('/api/operations/status');old=read('/api/v4/original-0930/context');read('/v4')
            expected='2026-10-08' if present else '2026-09-30'
            assert context['context']['accepted_trade_date']==status['accepted_trade_date']==status['last_accepted_trade_date']==expected
            assert old['context']['accepted_trade_date']=='2026-09-30'
            assert status['legacy_strict_pit_context']['as_of']=='2026-09-30'
            assert all(v is False for v in status['production_permission'].values())
            if present:
                assert status['data_head_digest']==sha(head)
                assert status['operational_context']['context_token']==context['context_token']
                assert status['operational_context']['capability_permissions']['research_read'] is True
                assert status['operational_context']['capability_permissions']['trading_execution'] is False
                token=context['context_token']
                for path in ['home','stocks?limit=1','sectors?limit=1','focus?limit=1','market','diagnostics/sources','forward/statistics','forward/fep','replay','compare']:
                    separator='&' if '?' in path else '?';read('/api/v4/'+path+separator+'context_token='+token)
            with ThreadPoolExecutor(max_workers=4) as pool:
                for result in pool.map(lambda _:read('/api/operations/status'),range(8)):
                    assert result['last_accepted_trade_date']==expected
        finally:server.shutdown();server.server_close();worker.join()
    for state,present in [('HEAD_ABSENT',False),('HEAD_PRESENT',True),('ROLLBACK_ABSENT',False),('RESTART_PRESENT',True)]:
        run(state,present);print(state+' PASS',flush=True)
    after={p:sha(ROOT/p) for p in before};assert before==after
    atomic(OUT/'R43_R2_CONTROL_STATUS_NAMESPACE_QA.json',canonical(dict(contract_id='V4_CONTROL_STATUS_NAMESPACES_V2',
        status='ENGINEERING_HTTP_NAMESPACE_PASS',isolated_root=str(store),production_pointer_changed=False,
        protected_before=before,protected_after=after,records=records,independent_external_acceptance=False,
        next='FP_BROWSER_GAP_MATRIX_AND_SCOPED_ADAPTER_RESTART')))
    print(json.dumps(dict(result='PASS',HTTP=len(records))))

if __name__=='__main__':main()
