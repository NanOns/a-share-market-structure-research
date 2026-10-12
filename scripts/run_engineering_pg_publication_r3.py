"""Copy the accepted source reference closure; execute normal isolated PG producer."""
from collections import deque
from pathlib import Path
import gzip,hashlib,json,os,re,shutil,sys,threading,time,traceback
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
SOURCE=Path('G:/codex work/大A交易')
TARGET=Path('G:/codex_tmp/r4_r3_pg_publication')
OUT=ROOT/'docs/audits/r4_r3_consumers_20261011'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        while part:=stream.read(1024*1024):h.update(part)
    return h.hexdigest()
def freeze():
    pending=deque();seen=set();rows=[];missing=[]
    for folder in ('src','scripts'):
        pending.extend(p.relative_to(SOURCE).as_posix() for p in (SOURCE/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    config_modules=['production_v4.py','current_v4_context.py','research_bff.py','shadow_server.py','v4_server.py','joint_release.py']
    for module in config_modules:
        pending.extend(re.findall(r'config/[a-zA-Z0-9_]+\.json',(SOURCE/'src/workbench_service'/module).read_text(encoding='utf8')))
    pending.extend(['data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'])
    # Context refresh consumes the official runtime calendar beyond the
    # snapshot's direct owner bindings; freeze its transitive raw evidence too.
    from workbench_analysis.dm01_runtime_r4 import CALENDAR
    pending.append(CALENDAR)
    def refs(value):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and (value.get('sha256') or value.get('bytes')):
                p=Path(value['path'])
                if not p.is_absolute():pending.append(value['path'])
            for child in value.values():refs(child)
        elif isinstance(value,list):
            for child in value:refs(child)
    while pending:
        name=pending.popleft()
        if name in seen:continue
        seen.add(name);source=(SOURCE/name).resolve()
        if not source.is_relative_to(SOURCE.resolve()):raise ValueError('SOURCE_REFERENCE_ESCAPE')
        if not source.is_file():missing.append(name);continue
        target=TARGET/name;target.parent.mkdir(parents=True,exist_ok=True)
        before=sha(source)
        if not target.is_file() or sha(target)!=before:
            temp=target.with_suffix(target.suffix+'.freeze.tmp');shutil.copyfile(source,temp);os.replace(temp,target)
        if sha(source)!=before or sha(target)!=before:raise ValueError('SOURCE_CHANGED_DURING_COPY:'+name)
        rows.append(dict(path=name,sha256=before,bytes=source.stat().st_size))
        if len(rows)%100==0:print(json.dumps(dict(closure_files=len(rows),bytes=sum(r['bytes'] for r in rows),pending=len(pending))),flush=True)
        if source.suffix=='.json':
            try:refs(json.loads(source.read_bytes()))
            except (ValueError,UnicodeDecodeError):pass
    (OUT/'ENGINEERING_FROZEN_SOURCE_CLOSURE.json').write_text(json.dumps(dict(files=rows,missing_references=missing,hardlinks=False,source=str(SOURCE),target=str(TARGET)),ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(frozen_files=len(rows),bytes=sum(r['bytes'] for r in rows),missing=len(missing))),flush=True)
def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--reuse-frozen',action='store_true');parser.add_argument('--run-id',default='R3');parser.add_argument('--target');args=parser.parse_args()
    global OUT,TARGET
    if args.target:TARGET=Path(args.target).resolve()
    OUT=OUT/args.run_id;OUT.mkdir(parents=True,exist_ok=True)
    if not args.reuse_frozen:freeze()
    else:
        receipt=json.loads((OUT.parent/'ENGINEERING_FROZEN_SOURCE_CLOSURE.json').read_bytes())
        if receipt['target']!=str(TARGET) and not (TARGET/'ENGINEERING_FORK_RECEIPT.json').is_file():raise ValueError('FROZEN_ROOT_REQUIRED')
    fork=TARGET/'ENGINEERING_FORK_RECEIPT.json'
    if fork.exists():
        binding=json.loads(fork.read_bytes());linked=set(binding['linked_readonly_files'])
        linked.update(str((Path(binding['source'])/Path(p).relative_to(TARGET)).resolve()) for p in list(linked))
        def forbid_linked_mutation(event,args):
            paths=[];mutation=False
            if event=='open':
                mode=args[1] or '';flags=args[2]
                mutation=any(c in mode for c in 'wax+') or bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
                paths=args[:1]
            elif event in ('os.remove','os.rmdir','os.rename'):
                mutation=True;paths=args[:2] if event=='os.rename' else args[:1]
            if mutation and any(isinstance(p,(str,bytes,os.PathLike)) and str(Path(os.fsdecode(p)).resolve()) in linked for p in paths):raise PermissionError('ENGINEERING_SHARED_FROZEN_INPUT_WRITE_FORBIDDEN')
        sys.addaudithook(forbid_linked_mutation)
    import psycopg
    from workbench_db.v4_native import configured_dsn
    from workbench_service.engineering_pg_publication_r3 import CONTRACT,ADMISSION,publish
    from workbench_service.v4_server import make_v4_handler
    from workbench_service.v4_daily_refresh import atomic_bytes
    with psycopg.connect(configured_dsn()) as pg:
        identity=pg.execute("SELECT current_database(),(pg_control_system()).system_identifier,current_setting('data_directory')").fetchone()
    admission=dict(contract_id=CONTRACT,scope='ENGINEERING_ONLY',production_permission=False,workspace_root=str(TARGET),pg_database=identity[0],pg_system_identifier=str(identity[1]),pg_data_directory=identity[2])
    atomic_bytes(TARGET/ADMISSION,json.dumps(admission).encode())
    source_paths=['src/workbench_service/engineering_pg_publication_r3.py','src/workbench_service/production_v4.py','src/workbench_service/joint_release.py','src/workbench_service/v4_server.py','scripts/run_engineering_pg_publication_r3.py','tests/v4_native_isolation_plugin_r4.py']
    import subprocess
    atomic_bytes(OUT/'ENGINEERING_PUBLICATION_SOURCE_BINDINGS.json',json.dumps(dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),actual_loaded_source_sha256={p:sha(ROOT/p) for p in source_paths},database_identity=dict(database=identity[0],system_identifier=str(identity[1]),data_directory=identity[2]),scope='ENGINEERING_ONLY'),indent=2).encode())
    from types import SimpleNamespace
    from tests import v4_native_isolation_plugin_r4 as guard
    os.environ['R4_PG_DATA_DIRECTORY']=identity[2]
    os.environ['R4_CONNECTION_LEDGER']=str(OUT/'ENGINEERING_PUBLICATION_PG_INTENTS.jsonl')
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='TRUE_PRODUCER_PG_JOINT_HEAD_NORMAL_HTTP'
    ledger=Path(os.environ['R4_CONNECTION_LEDGER']).open('w',encoding='utf8')
    class StreamedIntents:
        count=0
        def append(self,event):
            ledger.write(json.dumps(event,ensure_ascii=False)+'\n');self.count+=1
            if self.count%100==0:ledger.flush()
    guard.EVENTS=StreamedIntents()
    from scripts.r4_r3_consumer_trace import ConsumerTrace
    trace=ConsumerTrace(OUT/'ACTUAL_PRODUCER_56_TRACE.json','normal producer -> PG staged snapshot -> joint CAS -> normal HTTP -> rollback or accept')
    trace.start()
    print(json.dumps(dict(phase='NORMAL_HANDLER_INIT',at=time.time(),target=str(TARGET))),flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),make_v4_handler(TARGET));worker=threading.Thread(target=server.serve_forever);worker.start()
    print(json.dumps(dict(phase='PRODUCER_BUILD_AND_JOINT_VALIDATE',at=time.time())),flush=True)
    results=[]
    def health(candidate):
        from decimal import Decimal
        manifest=json.loads((TARGET/candidate['snapshot']['manifest']['path']).read_bytes())
        raw_binding=manifest['sources']['RAW_DAILY']
        raw_path=TARGET/raw_binding['path'];raw_bytes=raw_path.read_bytes()
        expected={r['security_id']:r for r in json.loads(gzip.decompress(raw_bytes) if raw_path.suffix=='.gz' else raw_bytes)['rows']}
        token='research-v4-'+candidate['snapshot']['manifest']['sha256']
        for route in ('context','home','stocks?limit=1','sectors?limit=1','focus?limit=1','market','diagnostics'):
            print(json.dumps(dict(phase='NORMAL_HTTP',route=route,at=time.time())),flush=True)
            # The supported historical research route bypasses the distinct
            # operational Owner dispatch, not the normal PG BFF or authority.
            with urlopen(f'http://127.0.0.1:{server.server_port}/api/v4/original-0930/'+route,timeout=120) as response:data=json.load(response)
            atomic_bytes(OUT/('HTTP_'+route.split('?')[0]+'.json'),json.dumps(data,ensure_ascii=False).encode())
            results.append(dict(route=route,http=200,status=data.get('status'),context_token=data.get('context_token')))
            if data.get('context_token')!=token:raise ValueError('ENGINEERING_NORMAL_HTTP_TOKEN_MISMATCH')
            if data.get('status') not in (None,'READY'):raise ValueError('ENGINEERING_NORMAL_HTTP_DOMAIN_NOT_READY:'+route)
            if route.startswith('stocks?'):
                if data['total']!=manifest['counts']['stocks']:raise ValueError('NORMAL_HTTP_STOCK_DENOMINATOR_MISMATCH')
                for row in data['items']:
                    # List summaries expose close; full OHLC belongs to the
                    # supported stock detail response on the same context.
                    with urlopen(f'http://127.0.0.1:{server.server_port}/api/v4/original-0930/stocks/'+row['entity_id'],timeout=120) as response:detail=json.load(response)
                    if detail.get('context_token')!=token:raise ValueError('NORMAL_HTTP_DETAIL_CONTEXT_MISMATCH')
                    atomic_bytes(OUT/'HTTP_STOCK_DETAIL.json',json.dumps(detail,ensure_ascii=False).encode())
                    for field in ('open','high','low','close'):
                        if Decimal(str(detail['item']['fields'][field]['value']))!=Decimal(str(expected[row['entity_id']][field])):raise ValueError('NORMAL_HTTP_RAW_SOURCE_ORACLE_MISMATCH:'+field)
                results[-1]['independent_numeric_comparisons']=4*len(data['items'])
                results[-1]['independent_raw_source_sha256']=raw_binding['sha256']
        return {'pass':True,'routes':results,'context_token':token}
    try:
        result=publish(TARGET,health=health)
        result['normal_http']=results
    except BaseException as exc:
        result=dict(status='ENGINEERING_BLOCKED',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),normal_http=results)
    finally:
        server.shutdown();worker.join();server.server_close()
        ledger.close();guard.pytest_unconfigure(config)
        trace.close()
    atomic_bytes(OUT/'ENGINEERING_PUBLICATION_RESULT.json',json.dumps(result,ensure_ascii=False,indent=2).encode())
    print(json.dumps(dict(status=result['status'],error=result.get('error'))),flush=True)
if __name__=='__main__':main()
