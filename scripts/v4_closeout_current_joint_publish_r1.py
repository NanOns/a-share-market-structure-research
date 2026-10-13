"""Authorized real staging CAS with normal accepted reader and HTTP readback."""
import json,os,threading,urllib.request,hashlib
from pathlib import Path
from http.server import ThreadingHTTPServer
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from scripts.v4_closeout_sealed_bff_readback import NoLegacyFacts
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_successor_release_v1 import promote,verify_policy
from workbench_analysis.operational_successor_v1 import digest
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_service.native_current_snapshot_v3 import current
from workbench_service.core_product_server_r1 import make_product_handler

ROOT=Path('G:/codex work/v4-production-20261012')
DOC=Path(__file__).resolve().parents[1]/'docs/audits/v4_full_closeout_20261012/continuation_20261013/CURRENT_PUBLICATION_JOINT_AUDIT_R1'

def main():
    output=DOC/'ACTUAL_JOINT_PUBLICATION_R1.json'
    if output.exists():raise ValueError('PRESERVE_COMPLETED_PUBLICATION')
    admission=json.loads((DOC/'FOUR_GATE_ADMISSION_R1.json').read_bytes());candidate=json.loads(checked(ROOT,admission['candidate']).read_bytes())
    verify_policy(ROOT,candidate)
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    head=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    preserved=[ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json',ROOT/'config/read_only_operational_daily_release_policy_v1_1.json',ROOT/'config/v4_joint_release_authority_v1.json']
    protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in preserved}
    predecessor_sha=hashlib.sha256(head.read_bytes()).hexdigest()
    parent=make_product_handler(ROOT,NoLegacyFacts())
    class ReadOnly(parent):
        def do_POST(self):return self.send(403,{'status':'FORBIDDEN'})
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',28873),ReadOnly)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    records=[]
    def readback(c):
        joint=current(ROOT,c)
        for path in ('context','home','stocks','sectors','focus','market','diagnostics'):
            url='http://127.0.0.1:28873/api/v4/'+path+'?trade_date='+c['accepted_trade_date']+'&context_token='+digest(c)+'&limit=3'
            with urllib.request.urlopen(url,timeout=90) as response:
                status=response.status;raw=response.read();data=json.loads(raw)
            assert status==200 and data['context_token']==digest(c) and data['context']['trade_date']==c['accepted_trade_date']
            assert data['current_native_joint']['business_token']==digest(c) and data['current_native_joint']['T0']==c['accepted_trade_date']
            record=dict(path=path,http=status,T0=data['context']['trade_date'],business_token=data['context_token'],joint=data['current_native_joint'],total=data.get('total'),response_sha256=hashlib.sha256(raw).hexdigest())
            records.append(record);print(json.dumps(record),flush=True)
        return dict(status='PASS',context_token=digest(c),accepted_trade_date=c['accepted_trade_date'],current_joint=ref(ROOT,ROOT/'config/v4_current_native_joint_authority_v3.json'),actual_http_routes=len(records))
    try:result=promote(ROOT,candidate,predecessor_sha,readback)
    finally:server.shutdown();server.server_close();thread.join(timeout=3)
    assert protected=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in preserved}
    receipt=dict(contract_id='V4_REAL_CURRENT_NATIVE_JOINT_PUBLICATION_R1',acceptance='PASS_CURRENT_STAGING_COORDINATED_CAS_AND_READBACK',result=result,candidate=admission['candidate'],policy=admission['policy'],predecessor_sha256=predecessor_sha,records=records,protected_unchanged=protected,production_cutover=False,PIT_ELIGIBLE=False,AS_RECORDED=False,numerical_producers_reexecuted=False,server_stopped=True)
    atomic_json(DOC,output,receipt);print(json.dumps({'acceptance':receipt['acceptance'],'result':result}),flush=True)

if __name__=='__main__':main()
