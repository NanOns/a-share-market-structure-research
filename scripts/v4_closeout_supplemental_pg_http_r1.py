"""Previously uncovered dated product reads through actual localhost HTTP/PG."""
import gzip
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlencode

REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO),str(REPO/'src')]
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from scripts.v4_closeout_sealed_bff_readback import NoLegacyFacts
from scripts.r4_r3_consumer_trace import ConsumerTrace
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1

ROOT=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/SUPPLEMENTAL_CURRENT_PG_HTTP_R1')
CANDIDATE='data/v4/sealed_numeric_preparations_v1/412bb713abc87cd16cf2cb0bff5653971dcd97909609b6a7c574c616f18ca858/CANDIDATE.json'


def load(path):
    if path.suffix=='.gz':return json.loads(gzip.decompress(path.read_bytes()))
    return json.loads(path.read_bytes())


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='R1');parser.add_argument('--continue-from');args=parser.parse_args()
    if not args.label.isalnum():raise ValueError('VERSIONED_HTTP_LABEL_REQUIRED')
    if args.continue_from and not args.continue_from.isalnum():raise ValueError('VERSIONED_PREVIOUS_LABEL_REQUIRED')
    OUT=OUT.with_name('SUPPLEMENTAL_CURRENT_PG_HTTP_'+args.label)
    OUT.mkdir(exist_ok=False)
    raw=(ROOT/CANDIDATE).read_bytes();candidate=json.loads(raw);day=candidate['accepted_trade_date']
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    api=OperationalSuccessorReaderV1(ROOT,candidate)
    import workbench_analysis.operational_successor_v1 as successor
    accepted_api=successor.accepted_api
    successor.accepted_api=lambda root:api if root.resolve()==ROOT.resolve() else (_ for _ in ()).throw(ValueError('CANDIDATE_ROOT_MISMATCH'))
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    selector=CoreProductBFFR1(api,NoLegacyFacts())
    stocks=selector.source('core',day)
    old_alias=selector.resolve_dated_object('stocks',day,'300114')
    new_alias=selector.resolve_dated_object('stocks',day,'302132')
    if old_alias is None or new_alias is None or old_alias['entity_id']!=new_alias['entity_id']:
        raise ValueError('REAL_CODE_CHANGE_DATED_ALIAS_IDENTITY_REQUIRED')
    stock=old_alias['entity_id']
    other=next(r['security_id'] for r in stocks if r['security_id']!=stock)
    sector=selector.source('sector',day)[0]['sector_id']
    forward=selector.source('forward',day)
    focus=next(e['entity_id'] for e in forward['episodes'] if e.get('observations'))
    protected={n:(ROOT/'data/v4'/n).read_bytes() for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    original_sqlite=sqlite3.connect
    legacy_calls=[]
    def denied(*args,**kwargs):
        legacy_calls.append('CONNECT_ATTEMPT')
        raise AssertionError('LEGACY_SQLITE_DUCKDB_CURRENT_READ_FORBIDDEN')
    sqlite3.connect=denied
    duckdb=None;original_duckdb=None
    try:
        import duckdb
        original_duckdb=duckdb.connect;duckdb.connect=denied
    except ImportError:pass
    server,thread=None,None
    records,errors=[],[]
    retained=None;metadata_repairs=[]
    if args.continue_from:
        old_folder=OUT.with_name('SUPPLEMENTAL_CURRENT_PG_HTTP_'+args.continue_from)
        retained=load(old_folder/'RESULT.json')
        for record in retained['records']:
            if record['path'] not in ('/api/v4/forward/fep','/api/v4/forward/settlement'):continue
            response=load(old_folder/(record['response_sha256']+'.json'))
            context=response['context'];data=response['data']
            if context.get('PIT_ELIGIBLE') is not False or context.get('historical_PIT_permission') is not False:
                raise ValueError('RETAINED_FORWARD_CONTEXT_SCOPE_ESCALATION')
            if record['path'].endswith('/fep'):
                if data['prediction'] is not None or any(v!='NOT_GRANTED' for v in data['capabilities'].values()) or data['training_authorized'] is not False or data['focus_write_authorized'] is not False:
                    raise ValueError('RETAINED_FEP_PERMISSION_ESCALATION')
            elif data['write_authorized'] is not False or response['focus_is_validation_cohort'] is not False:
                raise ValueError('RETAINED_SETTLEMENT_PERMISSION_ESCALATION')
            metadata_repairs.append(dict(path=record['path'],response_sha256=record['response_sha256'],PIT_ELIGIBLE=False,correction='Read the inherited context scope and explicit denied capabilities; absent top-level duplicate is not a grant.'))
    trace=ConsumerTrace(OUT/'EXACT56_TRACE.json','Current supplemental stock/chart/replay/compare/Focus/Forward/market actual HTTP; formal PG only')
    try:
        from workbench_service.core_product_server_r1 import make_product_handler
        parent=make_product_handler(ROOT,NoLegacyFacts())
        class ReadOnly(parent):
            def do_POST(self):return self.send(403,dict(status='FORBIDDEN'))
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',28873),ReadOnly)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();trace.start()
        routes=[]
        routes.append(('/api/v4/stocks/300114/profile',{},'READY'))
        routes.append(('/api/v4/stocks/302132/profile',{},'READY'))
        for name in ('profile','why-not','evidence','timeline'):
            routes.append(('/api/v4/stocks/'+quote(stock,safe='')+'/'+name,{},'READY'))
        for name in ('members','overlap','rotation-timeline'):
            routes.append(('/api/v4/sectors/'+quote(sector,safe='')+'/'+name,{},'READY'))
        for name in ('episodes','timeline','anchors','observations','outcomes'):
            routes.append(('/api/v4/focus/'+quote(focus,safe='')+'/'+name,{},'READY'))
        for name in ('breadth','indices','limits','ladders'):
            routes.append(('/api/v4/market/'+name,{},'READY'))
        for name in ('statistics','fep','settlement'):
            routes.append(('/api/v4/forward/'+name,{},'SOURCE_INCOMPLETE'))
        routes.append(('/api/v4/compare',dict(mode='stock-stock',left=stock,right=other,as_of=day),'READY'))
        # Historical reads and RAW/QFQ chart are distinct previously uncovered
        # HTTP resources. Do not repeat the seven main entry GETs.
        routes.append(('/api/v4/stocks/'+quote(stock,safe='')+'/chart',dict(price_basis='RAW'),'READY'))
        routes.append(('/api/v4/stocks/'+quote(stock,safe='')+'/profile',dict(trade_date='2026-10-09'),'READY'))
        if retained is not None:
            routes=[r for r in routes if r[0]=='/api/v4/compare']
        for path,extra,expected in routes:
            query=dict(trade_date=day,context_token=api.token,limit=30);query.update(extra)
            url='http://127.0.0.1:28873'+path+'?'+urlencode(query)
            try:
                with urllib.request.urlopen(url,timeout=60) as response:code=response.status;body=response.read()
            except urllib.error.HTTPError as exc:code=exc.code;body=exc.read()
            value=json.loads(body);body_sha=hashlib.sha256(body).hexdigest();atomic_json(OUT,OUT/(body_sha+'.json'),value)
            actual_day=value.get('context',{}).get('trade_date')
            record=dict(path=path,query_scope=extra,http=code,status=value.get('status'),T0=actual_day,token=value.get('context_token'),total=value.get('total'),response_sha256=body_sha)
            records.append(record)
            if code!=200 or actual_day!=query['trade_date'] or value.get('context_token')!=api.token or value.get('status')!=expected:
                errors.append(dict(**record,expected_status=expected,reason=value.get('reason')))
            if expected=='SOURCE_INCOMPLETE':
                # Validation cohort/FEP is a separately authorized future-data
                # capability, never inferred from reconstructed Focus episodes.
                if value.get('PIT_ELIGIBLE',value.get('context',{}).get('PIT_ELIGIBLE')) is not False:errors.append(dict(path=path,scope='FUTURE_SCOPE_ESCALATION'))
            print(json.dumps(dict(path=path,http=code,status=value.get('status'))),flush=True)
    finally:
        trace.close()
        if server:server.shutdown();server.server_close()
        if thread:thread.join(timeout=3)
        successor.accepted_api=accepted_api;sqlite3.connect=original_sqlite
        if duckdb is not None:duckdb.connect=original_duckdb
    if any((ROOT/'data/v4'/n).read_bytes()!=v for n,v in protected.items()):raise ValueError('SUPPLEMENTAL_HTTP_HEAD_CHANGED')
    if legacy_calls:errors.append(dict(scope='LEGACY_CONNECT_ATTEMPTS',count=len(legacy_calls)))
    result=dict(contract_id='V4_SUPPLEMENTAL_CURRENT_FORMAL_PG_HTTP_R1',acceptance='PASS_SUPPLEMENTAL_HTTP_SCOPE' if not errors else 'FAIL',candidate=dict(path=CANDIDATE,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),T0=day,records=records,checks=len(records),errors=errors,legacy_connect_attempts=len(legacy_calls),reader_role=ROLES[0],server_stopped=True,publication=False,production_cutover=False,previous_main_routes_reexecuted=False,
        scope='Additional actual stock detail, history/chart, sector, layered Focus, compare, market and fail-closed validation-cohort/FEP HTTP resources. No independent numerical producer reexecution.')
    result['dated_code_change_alias_proof']=dict(old_code='300114',new_code='302132',entity_id=stock,symbol=new_alias['symbol'],same_dated_identity=True)
    if retained is not None:
        if len(retained['records'])!=24 or len(retained['errors'])!=3 or len(metadata_repairs)!=2 or len(records)!=1:
            raise ValueError('SUPPLEMENTAL_FAILED_SCOPE_DENOMINATOR_DRIFT')
        result.update(acceptance='PASS_FAILED_SCOPE_CONTINUATION' if not errors else 'FAIL',retained_original=dict(path=str(old_folder/'RESULT.json'),sha256=hashlib.sha256((old_folder/'RESULT.json').read_bytes()).hexdigest()),retained_http_pass=23,metadata_failed_assertion_repairs=metadata_repairs,previous_http_pass_reexecuted=False,compare_parameter_correction='as_of is the contracted query key; original UNKNOWN_PARAMETER response retained as a fail-closed negative observation.')
    atomic_json(OUT,OUT/'RESULT.json',result)
    print(json.dumps(dict(acceptance=result['acceptance'],checks=len(records),errors=len(errors))))
    return bool(errors)


if __name__=='__main__':raise SystemExit(main())
