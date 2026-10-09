"""Real HTTP, three isolated head states; never changes the production head."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,threading,time
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
from workbench_analysis.r43_operational_publication import digest,validate
from workbench_service.v4_server import make_v4_handler
OUT=ROOT/'docs/evidence/r4_3_r1_targeted_repair_20261009'
def junction(source,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    statement="New-Item -ItemType Junction -Path '"+str(dest).replace("'","''")+"' -Target '"+str(source).replace("'","''")+"' | Out-Null"
    subprocess.run(['powershell','-NoProfile','-Command',statement],check=True,capture_output=True)
def isolate(candidate,reuse=None):
    parent=Path('E:/codex_tmp/r43_r1_ui');parent.mkdir(parents=True,exist_ok=True)
    store=Path(reuse).resolve() if reuse else Path(tempfile.mkdtemp(dir=parent))
    assert store.is_relative_to(parent.resolve())
    for tree in ('src','config'):shutil.copytree(ROOT/tree,store/tree,dirs_exist_ok=True)
    visited=set()
    def copy(binding):
        path=binding['path'];source=(ROOT/path).resolve()
        assert source.is_relative_to(ROOT) and source.is_file()
        if path not in visited:
            visited.add(path);dest=store/path;dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists() or sha(dest)!=binding['sha256']:shutil.copy2(source,dest)
        return json.loads(source.read_bytes()) if source.suffix=='.json' else None
    def refs(value):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and value.get('sha256'):copy(value)
            else:
                for key,child in value.items():
                    if key not in ('previous','predecessor','catalog'):refs(child)
        elif isinstance(value,list):
            for child in value:refs(child)
    # Exact candidate closure; immutable owner data is reused byte for byte.
    refs(candidate);snapshot=copy(candidate['membership_snapshot']);refs(snapshot)
    registry=copy(candidate['registry']);refs(registry)
    # Existing UI entry, actual SQLite snapshot and explicit current context heads.
    joint=json.loads((ROOT/'config/v4_joint_release_authority_v1.json').read_bytes())
    refs(joint['ui_assets']);manifest=copy(joint['snapshot']['manifest']);refs(manifest['database']);refs(manifest.get('domain_features',{}))
    runtime=json.loads((ROOT/'config/v4_production_runtime_authority_v1.json').read_bytes())
    contract=copy(runtime['read_authority']);refs(contract['anchors']);refs(contract['owner_heads'])
    stage=copy(contract['anchors']['stage_authority']);refs(stage['calendar'])
    permission=copy(contract['anchors']['permission_authority'])
    for capability in permission['capability_registry'].values():
        if capability['production_permission']:refs(capability['accepted_receipts'])
    source=ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json';dest=store/'data/v4/V4_DATA_ACCEPTED_HEAD.json';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    print(json.dumps(dict(state='ISOLATED_REAL_BYTES_COPIED',root=str(store),files=len(visited))),flush=True)
    return store
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',required=True);parser.add_argument('--refresh-code-for-simulation',action='store_true');parser.add_argument('--reuse-isolation');args=parser.parse_args()
    candidate_path=Path(args.candidate).resolve();candidate=json.loads(candidate_path.read_bytes())
    store=isolate(candidate,args.reuse_isolation)
    if args.refresh_code_for_simulation:
        registry=json.loads((store/candidate['registry']['path']).read_bytes())
        for binding in registry['bindings']:
            path=store/binding['path']
            if binding['path'].startswith(('src/','scripts/')):
                if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/binding['path'],path)
                binding.update(sha256=sha(path),bytes=path.stat().st_size)
        for p in [store/'src/workbench_service/r43_operational_bff.py',store/'src/workbench_service/static/r43-compat/api.js',store/'src/workbench_service/static/r43-compat/components.js',store/'src/workbench_service/static/r43-compat/app.js']:
            registry['bindings'].append(dict(path=p.relative_to(store).as_posix(),sha256=sha(p),bytes=p.stat().st_size))
        path=store/'data/v4/R43_ISOLATED_REGISTRY.json';atomic(path,canonical(registry))
        candidate['registry']=dict(path=path.relative_to(store).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
    validate(store,candidate)
    head=store/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';authority=store/'data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json'
    for pointer in (head,authority):
        if pointer.exists():pointer.unlink()
    protected=ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json';old=sha(protected)
    server=ThreadingHTTPServer(('127.0.0.1',0),make_v4_handler(store));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    origin='http://127.0.0.1:'+str(server.server_port);records=[];html_hash=None
    def read(state,path,expected=200):
        started=time.time()
        try:
            with urlopen(origin+path,timeout=180) as response:body=response.read();status=response.status;content=response.headers.get('Content-Type')
        except HTTPError as error:body=error.read();status=error.code;content=error.headers.get('Content-Type')
        record=dict(state=state,url=origin+path,status=status,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),seconds=round(time.time()-started,3),content_type=content)
        if 'json' in content:
            value=json.loads(body);record.update(context_token=value.get('context_token'),trade_date=value.get('context',{}).get('accepted_trade_date'),status_label=value.get('status'),reason=value.get('reason'),total=value.get('total'),item_identity=(value.get('items') or [{}])[0].get('entity_id'))
        else:value=body
        records.append(record);assert status==expected,(path,status,body[:1000]);return value
    try:
        for state in ('NO_OPERATIONAL_HEAD','LEGAL_HEAD_SIMULATION','ROLLBACK_OLD_HEAD'):
            if state=='LEGAL_HEAD_SIMULATION':
                atomic(head,canonical(candidate));atomic(authority,canonical(dict(status='EXTERNALLY_ACCEPTED_R43_OPERATIONAL',candidate_digest=digest(candidate),historical_PIT_permission=False,simulation_only=True,scope='E_DRIVE_HTTP_TEST_ONLY_NOT_EXTERNAL_ACCEPTANCE')))
            elif state=='ROLLBACK_OLD_HEAD':
                head.unlink();authority.unlink()
            for page in ('/','/v4','/v4/'):
                body=read(state,page)
                assert b'R4.3 operational candidate' not in body and b'R4.3' not in body[:100]
                signature=hashlib.sha256(body).hexdigest()
                if html_hash is None:html_hash=signature
                assert signature==html_hash,'PRODUCT_HTML_CHANGED_ON_OPERATIONAL_HEAD'
            preview=read(state,'/v4/operational-preview');assert len(preview)>1000
            for asset in ('api.js','components.js','app.js'):
                asset_bytes=read(state,'/v4/assets/'+asset)
                if state=='LEGAL_HEAD_SIMULATION':assert (b'SOURCE_INCOMPLETE' if asset=='api.js' else b'read_source_label' if asset=='components.js' else b"e.data?.status==='SOURCE_INCOMPLETE'") in asset_bytes
            context=read(state,'/api/v4/context');token=context['context_token'];date=context['context']['accepted_trade_date']
            assert date==('2026-10-08' if state=='LEGAL_HEAD_SIMULATION' else '2026-09-30')
            original=read(state,'/api/v4/original-0930/context');assert original['context']['accepted_trade_date']=='2026-09-30'
            suffix='?context_token='+token+'&limit=2'
            for domain in ('home','stocks','sectors','focus','diagnostics','sources'):
                response=read(state,'/api/v4/'+domain+suffix)
                assert response['context_token']==token and response['context']['accepted_trade_date']==date
                if domain in ('stocks','sectors','focus'):
                    assert response['total']>0
                    identity=response['items'][0]['entity_id']
                    detail=read(state,'/api/v4/'+domain+'/'+identity+('/episodes' if domain=='focus' else '')+suffix)
                    assert detail['context_token']==token
                    page=read(state,'/api/v4/'+domain+suffix+'&offset=2');assert page['offset']==2
            stocks=read(state,'/api/v4/stocks'+suffix);symbol=stocks['items'][0]['symbol']
            search=read(state,'/api/v4/stocks'+suffix+'&q='+symbol);assert search['total']>0
            if state=='LEGAL_HEAD_SIMULATION':
                real_search=read(state,'/api/v4/stocks'+suffix+'&q=600000')
                sh600000=next(x for x in real_search['items'] if x['symbol']=='SH.600000')
                assert sh600000['fields']['primary_industry']['quality']=='KNOWN' and sh600000['fields']['primary_industry']['value'].startswith('INDUSTRY:')
                assert sh600000['fields']['close']['source_digest']==candidate['owners']['2026-10-08']['raw']['sha256']
                assert sh600000['fields']['scenario']['source_digest']==candidate['owners']['2026-10-08']['focus']['sha256']
                real_detail=read(state,'/api/v4/stocks/'+sh600000['entity_id']+suffix)
                assert real_detail['item']['symbol']=='SH.600000'
                profile=read(state,'/api/v4/stocks/'+sh600000['entity_id']+'/profile'+suffix)
                assert profile['F']['close']['source_digest']==candidate['owners']['2026-10-08']['raw']['sha256']
                assert any(x['role']=='primary_industry' for x in profile['membership_relations']['items'])
                focus_search=read(state,'/api/v4/focus'+suffix+'&q=600000')
                assert all(x['symbol']=='SH.600000' for x in focus_search['items'])
                for path in ('stocks/'+stocks['items'][0]['entity_id']+'/chart','forward/statistics','replay'):
                    missing=read(state,'/api/v4/'+path+suffix);assert missing['status']=='SOURCE_INCOMPLETE' and missing['reason'] and not missing['mixed_date_fallback']
                read(state,'/api/v4/stocks?context_token=wrong',409)
                for day in candidate['dates']:
                    for domain in ('stocks','sectors','focus','raw','core','relative_sector','rotation','market','forward'):
                        response=read(state,'/api/v4/'+domain+'?context_token='+token+'&trade_date='+day+'&limit=1')
                        assert response['context_token']==token and response['context']['trade_date']==day
                        if domain=='forward':
                            for episode in response.get('rows',{}).get('episodes',[]):
                                assert episode['T0']<=day and all(o['trade_date']<=day for o in episode.get('observations',[]))
                diagnostic_path=store/candidate['owners']['2026-10-08']['diagnostic']['path'];exact=diagnostic_path.read_bytes()
                try:
                    diagnostic_path.write_bytes(exact+b' ')
                    read(state,'/api/v4/context',503)
                finally:atomic(diagnostic_path,exact)
                recovered=read(state,'/api/v4/context');assert recovered['context_token']==token
                read(state,'/api/v4/stocks'+suffix+'&limit=2',400)
                read(state,'/api/v4/stocks.csv'+suffix,501)
        assert sha(protected)==old
        result=dict(contract_id='R43_PRODUCTION_UI_ROUTE_AND_BFF_COMPATIBILITY_QA_V2',status='PASS_ISOLATED_REAL_HTTP',command=[sys.executable]+sys.argv,exit_code=0,candidate_code_rebound_for_simulation=args.refresh_code_for_simulation,candidate_digest=digest(candidate),candidate_path=str(candidate_path),candidate_sha256=sha(candidate_path),production_CAS_executed=False,external_acceptance_created=False,simulation_authority_scope='E_DRIVE_ONLY_NO_PRODUCTION_PERMISSION',isolation_root=str(store),production_old_head_sha256=old,production_old_head_preserved=True,states=['NO_OPERATIONAL_HEAD','LEGAL_HEAD_SIMULATION','ROLLBACK_OLD_HEAD'],product_html_sha256=html_hash,source_code=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in [ROOT/'src/workbench_service/v4_server.py',ROOT/'src/workbench_service/r43_operational_bff.py',Path(__file__)]],actual_http_readbacks=records,excluded_domains=['HISTORICAL_CHART','STRICT_PIT_REPLAY','FORWARD_ENROLLMENT_STATISTICS','FP_FULL_FRONTEND'],next_stage='INDEPENDENT_EXTERNAL_SCOPED_ADMISSION')
        atomic(OUT/'R43_PRODUCTION_UI_ROUTE_AND_BFF_COMPATIBILITY_QA.json',canonical(result));print(json.dumps(dict(status=result['status'],requests=len(records),store=str(store))))
    finally:server.shutdown();server.server_close()
if __name__=='__main__':
    try:main()
    except BaseException:
        import traceback
        failure=dict(status='FAIL',command=sys.argv,exit_code=1,traceback=traceback.format_exc())
        atomic(OUT/('P0_B_HTTP_FAILED_'+str(time.time_ns())+'.json'),canonical(failure))
        atomic(OUT/'P0_B_HTTP_LAST_FAILED_ATTEMPT.json',canonical(failure))
        raise
