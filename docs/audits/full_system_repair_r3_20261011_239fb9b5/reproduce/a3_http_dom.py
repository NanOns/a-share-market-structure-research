from pathlib import Path
import sys,os,json,hashlib,threading,time,urllib.request,urllib.parse
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from http.server import ThreadingHTTPServer
from workbench_service.core_product_server_r1 import make_product_handler
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_service.core_product_bff_r1 import CoreProductBFFR1
api=accepted_api(ROOT);token=api.token;bff=CoreProductBFFR1(api,None)
protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/v4').glob('*HEAD.json')}
base=make_product_handler(ROOT,None)
class ReadOnly(base):
    def do_POST(self):self.send(405,{'code':'AUDIT_GET_ONLY'})
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),ReadOnly);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
url=f'http://127.0.0.1:{server.server_port}'
def read(params):
    start=time.perf_counter()
    with urllib.request.urlopen(url+'/api/v4/compare?'+urllib.parse.urlencode(dict(context_token=token,trade_date='2026-10-09',**params)),timeout=120) as response:raw=response.read();status=response.status
    return json.loads(raw),dict(status=status,bytes=len(raw),seconds=time.perf_counter()-start,response_sha256=hashlib.sha256(raw).hexdigest())
receipts=[]
try:
    for day in api.candidate['published_sessions']:
        old,r1=read(dict(as_of=day,mode='stock-stock',left='300114',right='302132'))
        assert old['status']=='READY' and old['left']['entity_id']==old['right']['entity_id']
        unknown,r2=read(dict(as_of=day,mode='stock-stock',left='AUDIT_UNKNOWN',right='302132'))
        assert unknown['status']=='SOURCE_INCOMPLETE' and unknown.get('code')=='COMPARE_OBJECT_NOT_PRESENT',unknown
        rows=bff.project('stocks',day);other=next(r for r in rows if r['entity_id']!=old['left']['entity_id'])
        different,r3=read(dict(as_of=day,mode='stock-stock',left='300114',right=other['entity_id']))
        assert different['left']['entity_id']!=different['right']['entity_id']
        receipts.append(dict(day=day,identity=old['left']['entity_id'],alias=r1,unknown=r2,different=r3))
    from playwright.sync_api import sync_playwright
    dom=[]
    with sync_playwright() as p:
        context=p.chromium.launch_persistent_context(str(BASE/'edge_profile'),channel='msedge',headless=True,viewport={'width':1366,'height':768})
        page=context.new_page()
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        sector=bff.project('sectors','2026-10-09')[0]['entity_id']
        for mode in ('stock-stock','sector-sector','stock-market','sector-market'):
            key='302132' if mode.startswith('stock') else sector
            query=urllib.parse.urlencode(dict(as_of='2026-10-09',mode=mode,left=key,right=key))
            page.goto(url+'/v4/research/compare?'+query,wait_until='networkidle',timeout=120000)
            page.get_by_role('heading',name='事后重建比较 · 非严格 PIT').wait_for(timeout=120000)
            headers=page.locator('table thead').all_text_contents();values=page.locator('table tbody').all_text_contents()
            assert headers and all('五会话相对强度分位' in text for text in headers) if mode.startswith('stock') else bool(headers)
            expected,_=read(dict(as_of='2026-10-09',mode=mode,left=key,right=key))
            keys=('rps5','rps20') if mode.startswith('stock') else ('sector_rs5','sector_rs20')
            for k in keys:
                value=expected['left']['fields'][k]['value']
                if isinstance(value,(int,float)):
                    displayed=str(value) if float(value).is_integer() else f'{value:.3f}'
                    assert displayed in values[0],(mode,k,displayed,values)
                else:
                    assert value is None or str(value)=='UNKNOWN',(mode,k,value)
            assert '0～100 分位点' in page.locator('main').inner_text()
            image=OUT/f'A3_{mode}.png';page.screenshot(path=str(image),full_page=True)
            dom.append(dict(mode=mode,headers=headers,values=values,fields={k:expected['left']['fields'][k] for k in keys},screenshot=image.name,status='PASS'))
        assert not errors,errors
        context.close()
    receipt=dict(contract_id='DATED_COMPARE_ALIAS_AND_DOMAIN_FIELDS_R2',token=token,source_root_read_only=True,isolated_http_port=server.server_port,production_restart=False,alias_dates=receipts,dom=dom,page_errors=errors,protected_heads_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in protected.items()),acceptance='ENGINEERING_PASS_EXTERNAL_PENDING')
    path=OUT/'A3_HTTP_DOM_READBACK.json';temp=path.with_suffix('.tmp');temp.write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode());os.replace(temp,path)
    print(json.dumps(dict(port=server.server_port,dates=len(receipts),modes=len(dom),acceptance=receipt['acceptance'])))
finally:server.shutdown();server.server_close()
