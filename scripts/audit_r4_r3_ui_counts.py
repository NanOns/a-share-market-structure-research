"""Compare browser-observed totals with the running isolated default HTTP API."""
import hashlib,json,re,urllib.request,urllib.parse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_integration_20261011'

def main():
    server=json.loads((OUT/'UI_SERVER.json').read_bytes())
    if server.get('production') is not False:raise ValueError('ISOLATED_SERVER_REQUIRED')
    base=server['url'].split('/v4/')[0]
    observations=json.loads((OUT/'UI_BROWSER_INCREMENTAL_R3.json').read_bytes())['rows']
    rows=[]
    def get(path):
        with urllib.request.urlopen(base+path,timeout=120) as response:raw=response.read()
        return json.loads(raw),hashlib.sha256(raw).hexdigest()
    for observed in observations:
        text=observed.get('text','');match=re.search(r'共\s+(\d+)\s+条',text)
        if not match or not observed.get('url'):continue
        url=urllib.parse.urlparse(observed['url']);day=urllib.parse.parse_qs(url.query)['trade_date'][0]
        route=url.path.rsplit('/',1)[-1]
        if route not in ('stocks','sectors'):continue
        context,_=get('/api/v4/context?trade_date='+day)
        params={'trade_date':day,'context_token':context['context_token'],'limit':30}
        if observed.get('case')=='sector_concept_filter':params['type']='THEME'
        if observed.get('case')=='empty_filter_negative':params['q']='不存在代码ZZZ'
        path='/api/v4/'+route+'?'+urllib.parse.urlencode(params)
        payload,digest=get(path)
        expected=int(match.group(1));actual=payload.get('total')
        rows.append(dict(case=observed.get('case'),path=path,browser_total=expected,api_total=actual,api_sha256=digest,equal=actual==expected,raw=payload))
    result=dict(contract_id='R4_R3_BROWSER_HTTP_COUNT_ORACLE',rows=rows,status='PASS' if rows and all(x['equal'] for x in rows) else 'FAIL',limits=['Browser/UI default handler on isolated frozen root; does not establish integrated publication acceptance'])
    dest=OUT/'UI_HTTP_COUNT_ORACLE_R3.json';temp=dest.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');temp.replace(dest)
    print(json.dumps(dict(status=result['status'],rows=[{k:v for k,v in x.items() if k!='raw'} for x in rows]),ensure_ascii=False))
    if result['status']!='PASS':raise ValueError('BROWSER_HTTP_COUNT_MISMATCH')

if __name__=='__main__':main()
