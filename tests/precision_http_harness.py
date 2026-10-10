"""Loopback SYNTHETIC two-Head QA, real BFF/routes/UI, never production CAS."""
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref
from workbench_service.core_product_bff_r1 import CoreProductBFFR1

D0, D1 = '2026-10-09', '2026-10-12'


class Harness:
    def __init__(self, root, repo):
        self.root, self.repo = Path(root).resolve(), Path(repo).resolve()
        if self.root.drive.upper()!='G:' or not self.root.is_relative_to(Path('G:/codex_tmp').resolve()):
            raise ValueError('SYNTHETIC_G_TEMP_ROOT_REQUIRED')
        self.requests=[]
        b=publish(root,'inputs/base.json',dict(synthetic=True))
        owner={k:b for k in ('lifecycle','core','sector','prewatch','rotation','forward')}
        common=dict(synthetic_only=True,production=False,membership_snapshot=b,source_registry={},
            membership_observed_at=D0+'T16:00:00+08:00', observed_at=D0+'T16:00:00+08:00')
        old=dict(common,accepted_trade_date=D0,data_cutoff_date=D0,dates=[D0],published_sessions=[D0],owners={D0:owner})
        old_binding=publish(root,'inputs/d0_head.json',old)
        publish(root,f"data/v4/predecessors/{old_binding['sha256']}.json",old)
        new_members=publish(root,'inputs/new_members.json',dict(synthetic=True,changed_members=True))
        self.new=dict(common,accepted_trade_date=D1,data_cutoff_date=D1,dates=[D0,D1],published_sessions=[D0,D1],
                      owners={D0:owner,D1:dict(owner)},membership_snapshot=new_members,predecessor=old_binding)
        sector=publish(root,'inputs/sector_candidate.json',dict(T0=D0,production=False,sources={k:owner[k] for k in ('lifecycle','core','sector','prewatch')},
            membership=b,model=b,dependencies=[b],evidence_class='RECONSTRUCTED_RESEARCH_ONLY',
            rows=[dict(sector_id='INDUSTRY:T0706',T0=D0,production=False,formal_consumer_enabled=False,
                       inputs={},CONFIRMED='TRUE',WARM='UNKNOWN',member_count=3,quoted_count=3)]))
        state=publish(root,'inputs/state_candidate.json',dict(T0=D0,production=False,source=b,membership=b,model=b,config=b,
            implementation=b,universe_count=3,signal_count=12,research_eligible_count=1,evidence_class='RECONSTRUCTED_RESEARCH_ONLY'))
        atomic_json(root,self.root/'data/v4/producer_candidate_index_v2.json',dict(contract_id='PRODUCER_CANDIDATE_INDEX_V2',
            sessions={D0:dict(head=old_binding,sector=sector,full_state=state,production=False)}))
        self.original=old
        self.activate(old)
        self.old_token=self.api.token

    def activate(self, head):
        atomic_json(self.root,self.root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',head)
        token=ref(self.root,self.root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')['sha256']
        api=SimpleNamespace(root=self.root,candidate=head,token=token,cache={},snapshot={'memberships':head['membership_snapshot']})
        api.context=lambda:dict(trade_date=head['accepted_trade_date'],production_accepted=False,synthetic_only=True,
            contract_id='SYNTHETIC_TWO_HEAD_QA',PIT_ELIGIBLE=False,AS_RECORDED=False,read_source_label='隔离 synthetic 固定案例')
        harness=self
        class BFF(CoreProductBFFR1):
            def counts(self,day):return dict(stocks=3,sectors=3,focus=0)
            def project(self,domain,day):
                if domain not in ('stocks','sectors'):return []
                return [dict(entity_id=('SEC-SYNTHETIC'+str(i) if domain=='stocks' else 'INDUSTRY:T070'+str(i)),
                    display_name='隔离证券'+str(i) if domain=='stocks' else '隔离板块'+str(i),
                    symbol='SH.60000'+str(i) if domain=='stocks' else 'INDUSTRY:T070'+str(i),
                    fields=dict(close=dict(value=10+i+(100 if day==D1 else 0),quality='KNOWN'),
                        member_count=dict(value=3,quality='KNOWN'),sector_type=dict(value='INDUSTRY',quality='KNOWN')))
                    for i in range(6,9)]
            def source(self,domain,day):
                if domain=='forward':return {'episodes':[],'events':[]}
                if domain in ('rotation','events'):return []
                if domain=='sector':return [dict(sector_id='INDUSTRY:T0706',member_ids=['SEC-SYNTHETIC6'])]
                return []
        self.api=api
        self.bff=BFF(api,SimpleNamespace(status=lambda:dict(preview_only=True)))

    def handler(self):
        harness=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send(self,code,data,mime='application/json; charset=utf-8'):
                raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
                self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)))
                self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
            def do_POST(self):
                if self.path!='/__qa__/advance':return self.send(405,dict(reason='READ_ONLY_QA'))
                harness.activate(harness.new)
                return self.send(200,dict(synthetic_only=True,token=harness.api.token))
            def do_GET(self):
                parsed=urlparse(self.path);path=parsed.path
                if path.startswith('/v4/assets/'):
                    name=path.rsplit('/',1)[-1]
                    if name in ('app.js','api.js','components.js','stock.js','replay.js','labels.js'):
                        return self.send(200,(harness.repo/'src/workbench_service/static/core-product-r1'/name).read_bytes(),'application/javascript')
                    if name=='style.css':
                        return self.send(200,(harness.repo/'src/workbench_service/static/research/style.css').read_bytes(),'text/css')
                    return self.send(404,{})
                if path.startswith('/api/v4/'):
                    q=parse_qs(parsed.query,keep_blank_values=True)
                    try:
                        if any(len(v)!=1 for v in q.values()):raise ValueError('DUPLICATE_PARAMETER')
                        code,data=harness.bff.get(path,{k:v[0] for k,v in q.items()})
                    except (ValueError,KeyError,OSError,TypeError) as e:
                        code,data=(409 if str(e)=='CONTEXT_TOKEN_MISMATCH' else 400),dict(reason=str(e))
                    harness.requests.append(dict(path=path,query=q,status=code,token=harness.api.token,
                        candidate_status=data.get('candidate_research',{}).get('candidate_status')))
                    return self.send(code,data)
                if path=='/__qa__/requests':return self.send(200,harness.requests)
                shell=(harness.repo/'src/workbench_service/static/research/index.html').read_text('utf-8')
                shell=shell.replace('真实生产快照','隔离 synthetic 双 Head 案例').replace('<body>',
                    '<body><div style="background:#ffe6a0;padding:8px;position:relative;z-index:10">隔离工程测试；D1 为固定模拟日期，不是实际首获。'
                    '<button onclick="fetch(\'/__qa__/advance\',{method:\'POST\'}).then(()=>location.reload())">切换到 D1（隔离测试）</button></div>')
                return self.send(200,shell.encode(),'text/html; charset=utf-8')
        return Handler


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--port',type=int,default=28767)
    args=parser.parse_args()
    if args.port in (28765,28766):raise ValueError('EXISTING_SERVICE_PORT_PROTECTED')
    h=Harness(args.root,Path(__file__).resolve().parents[1])
    with ThreadingHTTPServer(('127.0.0.1',args.port),h.handler()) as server:
        print('SYNTHETIC_QA_READY',flush=True);server.serve_forever()
