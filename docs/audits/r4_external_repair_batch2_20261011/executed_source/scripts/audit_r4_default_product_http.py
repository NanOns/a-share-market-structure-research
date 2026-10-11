"""Freeze bound inputs into a G root and exercise default product HTTP, no injection."""
from collections import deque
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from urllib.parse import urlencode, quote
from urllib.error import HTTPError
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
SOURCE = Path('G:/codex work/大A交易').resolve()
CANDIDATE = Path('G:/codex_tmp/test_temp/r4_batch2_default_product').resolve()
OUT = ROOT / 'docs/audits/r4_external_repair_batch2_20261011'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while part := stream.read(8 * 1024 * 1024): h.update(part)
    return h.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temporary, path)


def freeze(reuse=False):
    if not CANDIDATE.is_relative_to(Path('G:/codex_tmp/test_temp').resolve()):
        raise ValueError('G_DISPOSABLE_ROOT_REQUIRED')
    CANDIDATE.mkdir(parents=True, exist_ok=True)
    if reuse:
        receipt=json.loads((OUT/'DEFAULT_PRODUCT_FROZEN_INPUTS.json').read_bytes())
        protected_heads={'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json'}
        for item in receipt['files']:
            if item['path'] in protected_heads and (sha(SOURCE/item['path'])!=item['sha256'] or sha(CANDIDATE/item['path'])!=item['sha256']):
                raise ValueError('FROZEN_HEAD_CHANGED')
        pending=deque(['data/v4/DM01_R4_CALENDAR_HEAD_V1.json'])
        seen=set()
        def add_refs(value):
            if isinstance(value,dict):
                if isinstance(value.get('path'),str) and value.get('sha256') and not Path(value['path']).is_absolute():pending.append(value['path'])
                for child in value.values():add_refs(child)
            elif isinstance(value,list):
                for child in value:add_refs(child)
        while pending:
            name=pending.popleft()
            if name in seen:continue
            seen.add(name);source=(SOURCE/name).resolve();source.relative_to(SOURCE)
            destination=CANDIDATE/name;destination.parent.mkdir(parents=True,exist_ok=True)
            temporary=destination.with_suffix(destination.suffix+'.tmp');shutil.copyfile(source,temporary);os.replace(temporary,destination)
            if source.suffix=='.json':add_refs(json.loads(source.read_bytes()))
        # Existing source-linked large inputs remain readonly in reuse mode.
        linked=receipt.get('hardlinks_with_write_refusal',[])
        if linked:
            def refuse(event,args):
                if event=='open' and isinstance(args[0],(str,bytes)) and str(Path(os.fsdecode(args[0])).resolve()) in linked:
                    mode,flags=args[1:3]
                    if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_TRUNC|os.O_CREAT)):
                        raise PermissionError('FROZEN_BOUND_HARDLINK_WRITE_FORBIDDEN')
            sys.addaudithook(refuse)
        print(json.dumps(dict(reused_frozen_root=True,added_calendar_files=len(seen))),flush=True)
        return
    for folder in ('config', 'src/workbench_service/static'):
        for path in (SOURCE / folder).rglob('*'):
            if path.is_file():
                destination = CANDIDATE / path.relative_to(SOURCE)
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix(destination.suffix + '.tmp')
                shutil.copyfile(path, temporary)
                os.replace(temporary, destination)
    old_authority = json.loads((SOURCE / 'config/core_product_read_authority_r1.json').read_bytes())
    old_manifest = json.loads((SOURCE / old_authority['manifest']['path']).read_bytes())
    prior = json.loads((ROOT / 'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_03_REAL_HISTORY_ORACLE.json').read_bytes())
    if sha(SOURCE / old_manifest['history_index']['path']) != prior['original_binding']['sha256']:
        raise ValueError('ORIGINAL_HISTORY_INDEX_CHANGED')
    candidate_manifest = dict(old_manifest, history_index=prior['pg_binding'],
                              authority_scope='ISOLATED_ENGINEERING_ONLY', external_acceptance='NOT_GRANTED')
    manifest_path = CANDIDATE / 'data/v4/core_product_candidate_r4/MANIFEST.json'
    write(manifest_path, candidate_manifest)
    write(CANDIDATE / 'config/core_product_read_authority_r1.json',
          dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R1', manifest=dict(
              path=manifest_path.relative_to(CANDIDATE).as_posix(), sha256=sha(manifest_path), bytes=manifest_path.stat().st_size)))
    seeds = ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json', 'data/v4/V4_DATA_ACCEPTED_HEAD.json',
             'data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json',
             'config/v4_control_adapter_v2.json', 'config/v4_production_runtime_authority_v1.json',
             'config/core_product_focus_read_authority_r2.json', 'config/v4_display_names_authority_v1.json']
    queue = deque((p,0) for p in seeds)
    visited, copied, external, omitted, linked = set(), [], [], [], []
    total = 0
    def references(value, depth=0):
        if isinstance(value, dict):
            if isinstance(value.get('path'), str) and value.get('sha256'):
                queue.append((value['path'], depth))
            for child in value.values(): references(child,depth)
        elif isinstance(value, list):
            for child in value: references(child,depth)
    references(candidate_manifest)
    while queue:
        relative, depth = queue.popleft()
        if relative in visited: continue
        visited.add(relative)
        if Path(relative).is_absolute():
            external.append(relative)
            continue  # retained provenance metadata; never copy/mutate external roots
        path = (SOURCE / relative).resolve()
        if not path.is_relative_to(SOURCE): raise ValueError('FROZEN_SOURCE_PATH_ESCAPE')
        if not path.is_file(): raise ValueError('FROZEN_SOURCE_MISSING:' + relative)
        total += path.stat().st_size
        if total > 64 * 1024 ** 3 or len(visited)>20000: raise ValueError('FROZEN_INPUT_SIZE_BOUND_EXCEEDED:'+relative)
        destination = CANDIDATE / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + '.tmp')
        large=path.stat().st_size>64*1024**2
        if large and not destination.exists():
            os.link(path,destination)
            linked.append(str(destination.resolve()))
        elif not destination.exists() or (not large and sha(destination)!=sha(path)):
            shutil.copyfile(path, temporary)
            os.replace(temporary, destination)
        if large and os.path.samefile(path,destination) and str(destination.resolve()) not in linked:
            linked.append(str(destination.resolve()))
        copied.append(dict(path=relative, sha256=None if large else sha(path), bytes=path.stat().st_size,
            large_source_hash='DEFERRED_TO_ACTUAL_CONSUMER' if large else 'VERIFIED',
            storage='READ_ONLY_AUDITED_HARDLINK' if str(destination.resolve()) in linked else 'COPY'))
        if path.suffix.lower() == '.json':
            if depth < 3 and not large: references(json.loads(path.read_bytes()),depth+1)
            else: omitted.append(relative)
    write(OUT / 'DEFAULT_PRODUCT_FROZEN_INPUTS.json', dict(contract_id='R4_DEFAULT_PRODUCT_FROZEN_INPUTS_R1',
        files=copied, deep_provenance_not_recursed=omitted, external_metadata_references_not_relocated=external, bytes=total, source_root=str(SOURCE), candidate_root=str(CANDIDATE),
        old_history_index=old_manifest['history_index'], pg_history_index=prior['pg_binding'],
        production_changed=False,hardlinks_with_write_refusal=linked,
        limitations=['Unconsumed large source hashes not re-attested; actual consumers enforce their bound digests']))
    if linked:
        protected=set(linked)
        def reject_link_write(event,args):
            if event=='open' and isinstance(args[0],(str,bytes)):
                target=str(Path(os.fsdecode(args[0])).resolve())
                mode=args[1];flags=args[2]
                if target in protected and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_TRUNC|os.O_CREAT))):
                    raise PermissionError('FROZEN_BOUND_HARDLINK_WRITE_FORBIDDEN')
            if event in ('os.remove','os.rename'):
                for name in args[:2]:
                    if isinstance(name,(str,bytes)) and str(Path(os.fsdecode(name)).resolve()) in protected:
                        raise PermissionError('FROZEN_BOUND_HARDLINK_MUTATION_FORBIDDEN')
        sys.addaudithook(reject_link_write)
    print(json.dumps(dict(frozen_files=len(copied), bytes=total)), flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reuse-frozen',action='store_true');args=parser.parse_args()
    freeze(args.reuse_frozen)
    from tests import v4_native_isolation_plugin_r4 as guard
    from workbench_service.core_product_server_r1 import make_product_handler
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    from workbench_analysis.operational_successor_v1 import accepted_api
    os.environ['R4_PG_DATA_DIRECTORY'] = 'G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
    os.environ['R4_CONNECTION_LEDGER'] = str(OUT / 'DEFAULT_PRODUCT_CONNECTIONS.jsonl')
    config = SimpleNamespace()
    guard.pytest_configure(config)
    guard.ACTIVE = 'DEFAULT_PRODUCT_HANDLER_NO_INJECTION'
    jobs = server = thread = None
    results = []; product_routes=[]
    code = 1
    try:
        # A PG index is tied to its workspace namespace. Copy its immutable
        # version into this root instead of relaxing the reader's root check.
        from workbench_db.v4_native import connection,create_schema,workspace_schema,configured_dsn
        from workbench_db.v4_history_pg_r1 import DDL
        import psycopg
        from psycopg import sql
        authority=json.loads((CANDIDATE/'config/core_product_read_authority_r1.json').read_bytes())
        manifest_path=CANDIDATE/authority['manifest']['path']
        manifest=json.loads(manifest_path.read_bytes());binding=manifest['history_index']
        target=workspace_schema(CANDIDATE,'history')
        if binding['schema']!=target:
            with psycopg.connect(configured_dsn()) as pg:
                if Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve()!=Path(os.environ['R4_PG_DATA_DIRECTORY']).resolve():raise ValueError('ISOLATED_PG_REQUIRED')
                create_schema(pg,target)
            with connection(target) as pg:
                pg.execute(DDL)
                expected=(binding['head_token'],binding['T0'],binding['source_digest'],binding['logical_digest'],binding['symbol_count'],binding['bar_count'])
                actual=pg.execute(sql.SQL('SELECT head_token,t0::text,source_digest,logical_digest,symbol_count,bar_count FROM {}.history_versions WHERE version=%s').format(sql.Identifier(binding['schema'])),(binding['version'],)).fetchone()
                if actual!=expected:raise ValueError('SOURCE_HISTORY_VERSION_IDENTITY_MISMATCH')
                if not pg.execute('SELECT 1 FROM history_versions WHERE version=%s',(binding['version'],)).fetchone():
                    pg.execute(sql.SQL('INSERT INTO history SELECT * FROM {}.history WHERE version=%s').format(sql.Identifier(binding['schema'])),(binding['version'],))
                    pg.execute(sql.SQL('INSERT INTO history_versions SELECT * FROM {}.history_versions WHERE version=%s').format(sql.Identifier(binding['schema'])),(binding['version'],))
            manifest['history_index']=dict(binding,schema=target)
            write(manifest_path,manifest)
            authority['manifest'].update(sha256=sha(manifest_path),bytes=manifest_path.stat().st_size)
            write(CANDIDATE/'config/core_product_read_authority_r1.json',authority)
        api = accepted_api(CANDIDATE)
        jobs = DailyJobs(CANDIDATE)
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_product_handler(CANDIDATE, jobs))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def get(path, query):
            url = f'http://127.0.0.1:{server.server_port}' + path + '?' + urlencode(query)
            try:
                with urlopen(url, timeout=60) as response: return response.status, json.loads(response.read())
            except HTTPError as exc: return exc.code, json.loads(exc.read())
        status, context = get('/api/v4/context', {})
        if status != 200: raise ValueError('DEFAULT_CONTEXT_FAILED:' + str(context))
        for route in ('home','stocks','sectors','focus','events','forward'):
            status,data=get('/api/v4/'+route,dict(context_token=api.token,trade_date=api.candidate['accepted_trade_date'],limit=20))
            if status!=200:raise ValueError('DEFAULT_PRODUCT_ROUTE_FAILED:'+str((route,status,data)))
            product_routes.append(dict(route=route,code=status,status=data.get('status'),total=data.get('total'),
                response_sha256=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()))
        with connection(target,read_only=True) as pg:
            sid = pg.execute('SELECT security FROM history WHERE version=%s ORDER BY security LIMIT 1',(binding['version'],)).fetchone()[0]
        for period in ('D', 'W', 'M'):
            for basis in ('RAW', 'QFQ'):
                query = dict(context_token=api.token, trade_date=api.candidate['accepted_trade_date'],
                             period=period, price_basis=basis, limit=120)
                status, data = get('/api/v4/stocks/' + quote(sid, safe='') + '/chart', query)
                if status != 200 or data.get('production_accepted') is not False:
                    raise ValueError('DEFAULT_CHART_FAILED:' + str((status, data)))
                if data.get('status') == 'READY' and data.get('series_index', {}).get('engine') != 'postgresql':
                    raise ValueError('DEFAULT_CHART_NOT_PG')
                results.append(dict(query=query, code=status, status=data.get('status'), total=data.get('total'),
                                    reason=data.get('gap', {}).get('reason'), items=data.get('items')))
        status, bad = get('/api/v4/stocks/' + quote(sid, safe='') + '/chart', dict(query, context_token='wrong'))
        if status != 409: raise ValueError('DEFAULT_BAD_TOKEN_NOT_REJECTED')
        # Original SQLite chart oracle runs only in its explicitly separate,
        # readonly migration process, never inside the V4 runtime guard.
        request=CANDIDATE/'ORIGINAL_CHART_ORACLE_REQUEST.json';oracle_path=CANDIDATE/'ORIGINAL_CHART_ORACLE.json'
        oracle_queries=[{k:v for k,v in r['query'].items() if k!='context_token'} for r in results]
        write(request,dict(security_id=sid,queries=oracle_queries))
        temporary=oracle_path.with_suffix('.tmp')
        subprocess.run([sys.executable,'-B',str(ROOT/'scripts/r4_frozen_chart_oracle.py'),str(request),str(temporary)],check=True)
        os.replace(temporary,oracle_path)
        oracle=json.loads(oracle_path.read_bytes())
        for actual,expected in zip(results,oracle):
            if any(actual[k]!=expected[k] for k in ('code','items','total')):raise ValueError('DEFAULT_HTTP_ORIGINAL_ORACLE_DIFF')
        if len(results)!=len(oracle):raise ValueError('DEFAULT_HTTP_ORACLE_COUNT_DIFF')
        # Tamper only the disposable default authority, then restore exact bytes.
        manifest_before=manifest_path.read_bytes();authority_path=CANDIDATE/'config/core_product_read_authority_r1.json';authority_before=authority_path.read_bytes()
        try:
            bad_manifest=json.loads(manifest_before);bad_manifest['history_index']['engine']='sqlite3';write(manifest_path,bad_manifest)
            bad_authority=json.loads(authority_before);bad_authority['manifest'].update(sha256=sha(manifest_path),bytes=manifest_path.stat().st_size);write(authority_path,bad_authority)
            engine_status,engine_bad=get('/api/v4/stocks/'+quote(sid,safe='')+'/chart',query)
            if engine_status!=400 or 'PG_HISTORY_BINDING_REQUIRED' not in engine_bad.get('reason',''):raise ValueError('DEFAULT_NON_PG_AUTHORITY_NOT_REJECTED')
        finally:
            for path,raw in ((manifest_path,manifest_before),(authority_path,authority_before)):
                temporary=path.with_suffix('.tmp');temporary.write_bytes(raw);os.replace(temporary,path)
        code = 0
        write(OUT / 'DEFAULT_PRODUCT_HTTP_RESULT.json', dict(contract_id='R4_DEFAULT_PRODUCT_HTTP_R1',
            current_status='SCOPED_DEFAULT_HANDLER_PASS', denominator=len(results), security_id=sid, results=results,
            context_status=context.get('status'),product_routes=product_routes,
            original_chart_oracle=dict(cases=len(oracle),differences=0,sha256=sha(oracle_path)),
            negative_vectors=[dict(code=status, body=bad),dict(code=engine_status,body=engine_bad)],
            limitations=['One frozen T0 and one security; no accepted PG authority or production restart',
                         'Period Owner gaps preserved; broad samples, capacity, browser and five-default-date gates open'],
            production_changed=False, constructor_history_injection=False))
        print(json.dumps(dict(cases=len(results), negative_code=status, results=[r['status'] for r in results])), flush=True)
    finally:
        if server: server.shutdown(); server.server_close()
        if thread: thread.join(2)
        if jobs: jobs.close()
        guard.pytest_sessionfinish(None, code)
        guard.pytest_unconfigure(config)


if __name__ == '__main__': main()
