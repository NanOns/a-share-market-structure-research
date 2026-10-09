"""Real saved-owner HTTP rehearsal; isolated candidate, no live Head mutation."""
from pathlib import Path
from copy import deepcopy
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
import json,sys,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref,checked
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_service.operational_successor_bff_v1 import OperationalSuccessorBFFV1
from workbench_service.research_bff import ResearchBFF
from workbench_service.v4_control_server_v2 import make_v4_handler
from workbench_service.operational_daily_server_v1 import successor_control
from workbench_service.current_v4_context import CurrentAcceptedV4Reader

def candidate_fixture():
    folder=ROOT/'docs/evidence/dynamic_daily_20261009/reader_rehearsal'
    owner=ROOT/'data/v4/dynamic_daily_owners/2026-10-08/6ab4f1a729f6b1f6eecd382a5312338f3c6ec87edef3f4ad83ebf80797ae79f1'
    c=json.loads((owner/'SUCCESSOR_CANDIDATE.json').read_bytes())
    parent=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    parent['dates']=parent['dates'][:-1];parent['accepted_trade_date']=parent['data_cutoff_date']=parent['dates'][-1]
    parent['owners']={d:parent['owners'][d] for d in parent['dates']}
    parent['evidence_kind']='SIMULATED_PREDECESSOR_WITH_REAL_IMMUTABLE_OWNERS'
    p=folder/'PREDECESSOR_FIXTURE.json';atomic_json(ROOT,p,parent)
    c['predecessor']=ref(ROOT,p)
    c['period_numeric_oracle']=ref(ROOT,owner/'PERIOD_NUMERIC_ORACLE.json')
    policy=ROOT/'config/read_only_operational_daily_release_policy_v1_1.json'
    c['release_policy']=ref(ROOT,policy);c['accepted_algorithm_bindings']=json.loads(policy.read_bytes())['accepted_algorithm_bindings']
    registry=json.loads((ROOT/c['registry']['path']).read_bytes())
    registry['rehearsal_original_registry']=c['registry']
    registry['rehearsal_io_rebinding_only']=True
    registry['bindings']=[ref(ROOT,ROOT/b['path']) if b['path'].endswith(('operational_owner_adapter_v1.py','operational_daily_owner_v1.py')) else b for b in registry['bindings']]
    registry_path=folder/'REGISTRY_FIXTURE.json';atomic_json(ROOT,registry_path,registry);c['registry']=ref(ROOT,registry_path)
    atomic_json(ROOT,folder/'CANDIDATE_FIXTURE.json',c)
    return c

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=28766);args=parser.parse_args()
    candidate=candidate_fixture();api=OperationalSuccessorReaderV1(ROOT,candidate)
    base=make_v4_handler(ROOT)
    _,legacy=CurrentAcceptedV4Reader(ROOT,require_runtime=True).read('context')
    class Handler(base):
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path.startswith('/api/v4/') or parsed.path=='/api/operations/status':
                if parsed.path=='/api/operations/status':
                    return self.send(200,dict(successor_control(api,legacy),evidence_kind='REAL_OWNER_READER_REHEARSAL_NO_CAS'))
                from copy import copy
                params={k:v[0] for k,v in parse_qs(parsed.query).items()}
                code,payload=OperationalSuccessorBFFV1(copy(api),ResearchBFF(ROOT)).get(parsed.path,params)
                return self.send(code,payload)
            return super().do_GET()
    print(json.dumps(dict(port=args.port,token=api.token,scope='REAL_SAVED_OWNER_HTTP_REHEARSAL_NO_LIVE_HEAD_MUTATION')),flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
