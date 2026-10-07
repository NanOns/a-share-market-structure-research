"""Actual HTTP readback of the restarted default V4 service; no fixtures."""
import argparse
import json
import urllib.error
import urllib.request
from scripts.v4_production_cutover_evidence import ROOT, REPORT, write
from workbench_service.current_v4_context import CurrentAcceptedV4Reader


def main(base):
    rows=[];payloads={}
    paths=['/','/v4','/api/operations/status','/api/v4/current/context']
    paths+=['/api/v4/current/'+m for m in ['summary','radar','entity','sector','cohort','settlement','health']]
    paths+=['/v4/shadow','/api/v4/shadow/context','/v3']
    for path in paths:
        with urllib.request.urlopen(base+path,timeout=30) as response:
            raw=response.read();assert response.status==200
            payload=json.loads(raw) if path.startswith('/api/') else dict(bytes=len(raw))
            rows.append(dict(path=path,status=response.status,body=payload));payloads[path]=payload
    context=payloads['/api/v4/current/context']
    assert context==CurrentAcceptedV4Reader(ROOT).load_context()
    assert context['status']=='READY_CURRENT_ACCEPTED'
    assert not any(context['production_permission'].values()) and not context['focus_write']
    status=payloads['/api/operations/status']
    assert status['service_mode']=='V4_DEFAULT_WORKBENCH' and status['service_state']=='READY'
    assert not status['legacy_v3_default']
    for path,payload in payloads.items():
        if path.startswith('/api/v4/current/') and path!='/api/v4/current/context':
            assert payload['context_token']==context['context_token'] and payload['items']
            assert any(cell['quality'] in ('KNOWN','DEGRADED') for item in payload['items'] for cell in item['fields'].values())
    shadow=payloads['/api/v4/shadow/context'];assert shadow['status']=='NO_REAL_SHADOW_DATA' and shadow['context'] is None
    for method in ['POST','PUT','PATCH','DELETE']:
        request=urllib.request.Request(base+'/api/v4/current/entity',method=method,data=b'{}')
        try:urllib.request.urlopen(request,timeout=5)
        except urllib.error.HTTPError as error:assert error.code==405
        else:raise AssertionError('UI write allowed')
    receipt=dict(status='PASS_REAL_SERVICE_HTTP',base=base,fixture=False,checks=rows,context=context,all_ui_write_methods_rejected=True)
    for name in ['LIVE_HTTP_RECEIPT.json','SERVICE_E2E_RECEIPT.json']:write(REPORT/name,receipt)
    write(REPORT/'SHADOW_SEPARATION_RECEIPT.json',dict(status='PASS',base=base,current=context,shadow=shadow,current_does_not_require_real_shadow=True,shadow_does_not_fallback=True))
    print('PASS actual V4 HTTP routes, known fields, context, writes and Shadow isolation')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='http://127.0.0.1:28765');args=parser.parse_args();main(args.base)
