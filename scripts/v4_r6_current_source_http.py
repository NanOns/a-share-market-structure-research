"""R6 read-only HTTP smoke through the actual current V4 BFF and PG owners."""
import argparse,hashlib,json,os,psutil,threading,time,urllib.error,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode
ROOT=Path(r'G:\\codex work\\v4-production-20261012');SOURCE=Path(__file__).resolve().parents[1];PORT=28771

def inherit():
    for process in psutil.process_iter(['pid','name','cmdline']):
        try:
            if (process.info.get('name') or '').lower()!='daav4.exe':continue
            argv=process.info.get('cmdline') or []
            if '--port' not in argv or argv[argv.index('--port')+1]!='28765':continue
            env=process.environ();os.environ['V4_NATIVE_PG_DSN']=env['V4_NATIVE_PG_DSN'];os.environ['V4_NATIVE_PG_READER_DSN']=env['V4_NATIVE_PG_READER_DSN'];return process.pid
        except (psutil.Error,ValueError,IndexError,KeyError):continue
    raise RuntimeError('LIVE_28765_CONTROLLED_PG_ENVIRONMENT_UNAVAILABLE')

def main():
    owner_pid=inherit();head_path=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head_path.read_bytes();candidate=json.loads(before)
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    api=OperationalSuccessorReaderV1(ROOT,candidate)
    class NoLegacy:
        def __getattr__(self,name):raise ValueError('R6_HTTP_LEGACY_READ_FORBIDDEN:'+name)
    bff=CoreProductBFFR1(api,NoLegacy());day=candidate['accepted_trade_date'];records=[];errors=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):self.send_error(403,'R6_CANDIDATE_READ_ONLY')
        def do_GET(self):
            parsed=urlsplit(self.path);query={k:v[-1] for k,v in parse_qs(parsed.query,keep_blank_values=True).items()}
            if parsed.path.startswith('/api/v4/'):
                code,payload=bff.get(parsed.path,query);raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
                self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            if parsed.path in ('/','/v4/research','/v4/research/') or parsed.path.startswith('/v4/research/'):
                asset=SOURCE/'src/workbench_service/static/research/index.html';ctype='text/html; charset=utf-8'
            elif parsed.path.startswith('/v4/assets/'):
                name=parsed.path.rsplit('/',1)[-1]
                asset=(SOURCE/'src/workbench_service/static/research/style.css' if name=='style.css' else SOURCE/'src/workbench_service/static/core-product-r1'/name)
                ctype='text/css; charset=utf-8' if name.endswith('.css') else 'application/javascript; charset=utf-8'
            else:asset=SOURCE/'src/workbench_service/static'/parsed.path.lstrip('/');ctype='application/octet-stream'
            try:raw=asset.read_bytes();status=200
            except OSError:raw=b'not found';status=404
            self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        base=f'http://127.0.0.1:{PORT}';checks=[('context','/api/v4/context',{'trade_date':day}),('home','/api/v4/home',{'trade_date':day}),('market_indices','/api/v4/market/indices',{'trade_date':day,'limit':'10'}),('radar_p1','/api/v4/radar',{'trade_date':day,'limit':'30','offset':'0'}),('radar_p2','/api/v4/radar',{'trade_date':day,'limit':'30','offset':'30'}),('priority_sectors_p1','/api/v4/radar/priority',{'trade_date':day,'scope':'sectors','limit':'10','offset':'0'}),('priority_stocks_p1','/api/v4/radar/priority',{'trade_date':day,'scope':'stocks','limit':'30','offset':'0'}),('priority_stocks_p2','/api/v4/radar/priority',{'trade_date':day,'scope':'stocks','limit':'30','offset':'30'}),('sector_list','/api/v4/sectors',{'trade_date':day,'limit':'5'}),('sector_detail','/api/v4/sectors/INDUSTRY:T0101',{'trade_date':day}),('focus','/api/v4/focus',{'trade_date':day,'limit':'5'}),('forward_candidate','/api/v4/candidates/cohort',{'trade_date':day}),('forward_statistics','/api/v4/forward/statistics',{'trade_date':day,'context_token':api.token}),('identity_600703','/api/v4/stocks/SH.600703',{'trade_date':day}),('identity_600703_list','/api/v4/stocks',{'trade_date':day,'q':'SH.600703','limit':'5'}),('identity_301660','/api/v4/stocks/SZ.301660',{'trade_date':day}),('identity_301660_list','/api/v4/stocks',{'trade_date':day,'q':'SZ.301660','limit':'5'}),('identity_old_alias','/api/v4/stocks/SZ.300114',{'trade_date':day}),('identity_new_symbol_list','/api/v4/stocks',{'trade_date':day,'q':'SZ.302132','limit':'5'}),('historical_20261012','/api/v4/context',{'trade_date':'2026-10-12'})]
        for name,path,q in checks:
            q=dict(q,context_token=api.token);url=base+path+'?'+urlencode(q)
            try:
                with urllib.request.urlopen(url,timeout=120) as response:code=response.status;raw=response.read()
            except urllib.error.HTTPError as exc:code=exc.code;raw=exc.read()
            except Exception as exc:code=599;raw=json.dumps({'status':'TRANSPORT_ERROR','reason':type(exc).__name__+':'+str(exc)}).encode()
            try:data=json.loads(raw)
            except Exception:data={}
            rec=dict(name=name,path=path,http=code,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),status=data.get('status'),T0=data.get('context',{}).get('trade_date'),token_match=data.get('context_token')==api.token)
            if name=='home':rec['under_512KiB']=len(raw)<=512*1024
            if name=='home':
                rec['risk_families']={k:{'status':v.get('status'),'numerator':v.get('numerator'),'denominator':v.get('denominator'),'coverage':v.get('coverage'),'change_total':v.get('change_total')} for k,v in data.get('risk_families',{}).items()}
                rec['focus_risk_events']=len(data.get('focus_risk_events',[]));rec['risk_owner_source']=data.get('risk_owner_source')
            if name.startswith('identity_') and data.get('item'):
                f=data['item'].get('fields',{});rec['symbol']=data['item'].get('symbol');rec['identity']={k:(f.get(k) or {}).get('value') for k in ('code_status','owner_code_status','listing_status','first_seen_status','ipo_confirmation_status','identity_link_status')}
            if name.endswith('_list') and data.get('items'):
                item=data['items'][0];f=item.get('fields',{});rec['symbol']=item.get('symbol');rec['identity']={k:(f.get(k) or {}).get('value') for k in ('code_status','owner_code_status','listing_status','first_seen_status','ipo_confirmation_status','identity_link_status')}
            if name=='sector_detail' and data.get('item'):
                f=data['item'].get('fields',{});rec['lifecycle']={k:(f.get(k) or {}).get('value') for k in ('maturity','health')};rec['lifecycle_contract']=data['item'].get('lifecycle',{}).get('contract_id')
            if name=='radar_p2':rec['items']=[r.get('entity_id') for r in data.get('items',[])];rec['total']=data.get('total')
            if name.startswith('priority_'):
                rec.update(scope=data.get('scope'),total=data.get('total'),rankable_total=data.get('rankable_total'),not_rankable_total=data.get('not_rankable_total'),priority_owner=data.get('priority_owner'),items=[r.get('entity_id') for r in data.get('items',[])])
            records.append(rec);print(json.dumps(rec,ensure_ascii=False),flush=True)
            if code!=200 or not rec['token_match'] or (name=='home' and not rec['under_512KiB']):errors.append(dict(name=name,http=code,status=rec['status']))
        hold=int(os.environ.get('R6_BROWSER_HOLD_SECONDS','0'))
        if hold:time.sleep(min(max(hold,1),60))
        req=urllib.request.Request(base+'/api/v4/operations/daily-update',data=b'{}',method='POST')
        try:urllib.request.urlopen(req,timeout=5);errors.append({'name':'post','reason':'NOT_REFUSED'})
        except urllib.error.HTTPError as exc:
            if exc.code!=403:errors.append({'name':'post','http':exc.code})
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    if head_path.read_bytes()!=before:raise ValueError('R6_CANDIDATE_HTTP_HEAD_CHANGED')
    p1=next((set(r.get('items',[])) for r in records if r['name']=='priority_stocks_p1'),set());p2=next((set(r.get('items',[])) for r in records if r['name']=='priority_stocks_p2'),set())
    if p1&p2:errors.append({'name':'priority_stock_pages','reason':'DUPLICATE_ENTITY_ACROSS_PAGES','entities':sorted(p1&p2)})
    result=dict(contract_id='V4_R6_CURRENT_SOURCE_HTTP_R1',port=PORT,production_service_pid_used_for_environment=owner_pid,T0=day,head_sha256=hashlib.sha256(before).hexdigest(),context_token_sha256=hashlib.sha256(api.token.encode()).hexdigest(),records=records,errors=errors,priority_stock_pages_disjoint=not bool(p1&p2),head_unchanged=True,auto_daily_changed=False,server_stopped=True,acceptance='PASS_CURRENT_SOURCE_HTTP' if not errors else 'FAIL')
    out=SOURCE/'reports/audits/v4_r6_closeout_20261014/CURRENT_SOURCE_HTTP.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf8');print(json.dumps({'acceptance':result['acceptance'],'errors':errors},ensure_ascii=False))
if __name__=='__main__':main()
