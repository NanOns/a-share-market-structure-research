import json,sys,time,hashlib,urllib.request
from pathlib import Path
from urllib.parse import urlencode
base=Path(__file__).parent;folder=base/sys.argv[1];assert not folder.exists();folder.mkdir()
port=int(sys.argv[2]);opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));token='d86b5a003704b52e72fefb81a23dc9d96c73df4db79d6c22f86ba08e7c6fcbfc';day='2026-10-12'
records=[]
for name in ('context','home','stocks','sectors','focus','market','diagnostics'):
 query=urlencode(dict(context_token=token,trade_date=day,limit=30));started=time.monotonic()
 with opener.open(f'http://127.0.0.1:{port}/api/v4/{name}?{query}',timeout=90) as response:raw=response.read();code=response.status
 data=json.loads(raw);baseline=json.loads((base/'COMPILED_HTTP_R4'/(name+'.json')).read_bytes())
 selected={k:v for k,v in data.items() if k!='context'};expected={k:v for k,v in baseline.items() if k!='context'}
 checks=dict(http=code==200,token=data.get('context_token')==token,date=data.get('context',{}).get('trade_date')==day,business_payload_equal_to_frozen_verified_staging=selected==expected,current_joint=data['current_native_joint']['business_token']==token and data['current_native_joint']['T0']==day)
 if name in ('stocks','sectors','focus','diagnostics'):checks['exact_count']=data['total']==dict(stocks=5224,sectors=400,focus=3025,diagnostics=1)[name]
 (folder/(name+'.json')).write_bytes(raw)
 row=dict(path=name,T0=data['context']['trade_date'],business_token=data['context_token'],http=code,total=data.get('total'),response_sha256=hashlib.sha256(raw).hexdigest(),checks=checks,response_seconds=time.monotonic()-started)
 records.append(row);print(json.dumps(dict(path=name,checks=checks)),flush=True)
result=dict(contract_id='V4_REAL_ORIGINAL_PORT_BUSINESS_PAYLOAD_CONSERVATION_R4',acceptance='PASS' if all(all(r['checks'].values()) for r in records) else 'FAIL',records=records,port=port,full_values_and_field_metadata_compared=True,numerical_recalculation=False,performance_test=False)
(folder/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert result['acceptance']=='PASS',result
