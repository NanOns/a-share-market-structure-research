"""Current-source candidate HTTP readback, formal read-only PG, no Head publication."""
import json,os,threading,hashlib,urllib.request,urllib.error
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from scripts.v4_closeout_sealed_bff_readback import NoLegacyFacts
from scripts.r4_r3_consumer_trace import ConsumerTrace
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1

def main():
    folder=OUT/'CURRENT_SOURCE_CANDIDATE_HTTP_R6_R1';folder.mkdir(exist_ok=False)
    preparation=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());day=candidate['accepted_trade_date']
    before={name:(ROOT/'data/v4'/name).read_bytes() for name in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    api=OperationalSuccessorReaderV1(ROOT,candidate)
    import workbench_analysis.operational_successor_v1 as successor
    original=successor.accepted_api
    successor.accepted_api=lambda root:api if root.resolve()==ROOT.resolve() else (_ for _ in ()).throw(ValueError('CANDIDATE_HTTP_ROOT_MISMATCH'))
    server=None;thread=None;errors=[];records=[];checks=0
    trace=ConsumerTrace(folder/'EXACT56_TRACE.json','Previously unverified current-source candidate HTTP, formal SELECT-only PG; no release authority')
    try:
        from workbench_service.core_product_server_r1 import make_product_handler
        parent=make_product_handler(ROOT,NoLegacyFacts())
        class ReadOnlyCandidate(parent):
            def do_POST(self):return self.send(403,dict(status='FORBIDDEN',reason='CANDIDATE_HTTP_READ_ONLY_NO_PUBLICATION'))
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',28873),ReadOnlyCandidate);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();trace.start()
        routes=['/api/v4/context']+['/api/v4/'+x for x in ('home','stocks','sectors','focus','market','diagnostics')]
        for path in routes:
            query=urlencode(dict(trade_date=day,context_token=api.token,limit='30'));url='http://127.0.0.1:28873'+path+'?'+query
            try:
                with urllib.request.urlopen(url,timeout=60) as response:code=response.status;raw=response.read()
            except urllib.error.HTTPError as exc:code=exc.code;raw=exc.read()
            data=json.loads(raw);sha=hashlib.sha256(raw).hexdigest();atomic_json(folder,folder/(sha+'.json'),data)
            checks+=1
            if code!=200 or data.get('context_token')!=api.token or data.get('context',{}).get('trade_date')!=day:errors.append(dict(path=path,http=code,status=data.get('status'),reason=data.get('reason')))
            records.append(dict(path=path,http=code,T0=data.get('context',{}).get('trade_date'),token=data.get('context_token'),total=data.get('total'),response_sha256=sha));print(json.dumps(records[-1]),flush=True)
        request=urllib.request.Request('http://127.0.0.1:28873/api/v4/operations/daily-update',data=b'{}',method='POST',headers={'Content-Type':'application/json'})
        try:urllib.request.urlopen(request,timeout=10);errors.append(dict(scope='POST_NOT_REFUSED'))
        except urllib.error.HTTPError as exc:
            checks+=1
            if exc.code!=403:errors.append(dict(scope='POST_REFUSAL',http=exc.code))
    finally:
        trace.close()
        if server:server.shutdown();server.server_close()
        if thread:thread.join(timeout=3)
        successor.accepted_api=original
    if any((ROOT/'data/v4'/name).read_bytes()!=value for name,value in before.items()):raise ValueError('CANDIDATE_HTTP_HEAD_MUTATION')
    result=dict(contract_id='V4_CURRENT_SOURCE_FORMAL_PG_CANDIDATE_HTTP_R1',acceptance='PASS_CURRENT_HTTP_SCOPE' if not errors else 'FAIL',candidate=preparation['candidate'],T0=day,records=records,checks=checks,errors=errors,reader_role=ROLES[0],port=28873,server_stopped=True,publication=False,production_cutover=False,actual_current_source_http=True,existing_numeric_pass_reexecuted=False,scope='First current-source corrected candidate six-entry HTTP with exact token/date identity. Independent full payload/value checks retained in prior field and bounded correction receipts; production current Snapshot/Joint and Windows still separate.')
    atomic_json(folder,folder/'RESULT.json',result);print(json.dumps(dict(acceptance=result['acceptance'],checks=checks,errors=len(errors))),flush=True)
if __name__=='__main__':main()
