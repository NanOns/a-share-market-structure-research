"""Sequential desktop functional readback, without performance or rollback tests."""
import hashlib,json,sys,urllib.error,urllib.request
from pathlib import Path
from urllib.parse import urlencode
BASE='http://127.0.0.1:28871'
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/formal_http_functional_r1')
def main():
    OUT.mkdir(parents=True,exist_ok=False);records=[];context={}
    routes=['/api/v4/desktop/status','/api/v4/context']
    routes+=['/v4/research/'+name for name in ('home','sectors','stocks','focus','market','diagnostics')]
    routes+=['/api/v4/'+name for name in ('home','sectors?limit=30','stocks?limit=30','focus?limit=30','market','diagnostics')]
    for original in routes:
        route=original
        if context and route.startswith('/api/v4/') and route not in ('/api/v4/context','/api/v4/desktop/status'):
            route+=('&' if '?' in route else '?')+urlencode(dict(context_token=context['context_token'],trade_date=context['context']['trade_date']))
        try:
            with urllib.request.urlopen(BASE+route,timeout=90) as response:code=response.status;raw=response.read()
        except urllib.error.HTTPError as error:code=error.code;raw=error.read()
        except OSError as error:code=None;raw=json.dumps(dict(error=type(error).__name__)).encode()
        sha=hashlib.sha256(raw).hexdigest();(OUT/(sha+'.response')).write_bytes(raw)
        row=dict(route=route,http=code,bytes=len(raw),sha256=sha)
        try:
            data=json.loads(raw);row.update({k:data.get(k) for k in ('status','reason','context_token','total','engine_state','WORKSPACE_ROOT','auto_daily_enabled') if k in data})
            if original=='/api/v4/context' and code==200:context=data
        except (ValueError,AttributeError):pass
        records.append(row);print(json.dumps(row),flush=True)
    result=dict(contract_id='FORMAL_DESKTOP_SEQUENTIAL_FUNCTIONAL_HTTP_R1',records=records,all_http_200=all(r['http']==200 for r in records),source_and_numeric_acceptance='SEPARATE_REQUIRED',performance_test=False,rollback_test=False,production_cutover=False)
    (OUT/'RESULT.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    if not result['all_http_200']:raise SystemExit(1)
if __name__=='__main__':main()
