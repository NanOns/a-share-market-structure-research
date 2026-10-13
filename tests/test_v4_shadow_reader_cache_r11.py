import json,threading,time
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from scripts.v4_r11_shadow_http import handler

def test_shadow_generation_singleflight_private_dates(monkeypatch,tmp_path):
    from workbench_analysis import operational_successor_v1 as reader
    from workbench_service import core_product_bff_r1 as bff
    builds=[]
    class Reader:
        def __init__(self,root,candidate):
            builds.append(candidate['accepted_trade_date']);time.sleep(.02)
            self.candidate=candidate;self.token=candidate['accepted_trade_date'];self.cache={};self.snapshot={}
    class BFF:
        def __init__(self,api,legacy):self.api=api
        def get(self,path,query):
            assert not self.api.cache;self.api.cache['request']=1
            return 200,dict(context_token=self.api.token,context={'trade_date':self.api.token})
    monkeypatch.setattr(reader,'OperationalSuccessorReaderV1',Reader)
    monkeypatch.setattr(bff,'CoreProductBFFR1',BFF)
    head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head.parent.mkdir(parents=True)
    head.write_text(json.dumps({'accepted_trade_date':'2026-10-12'}))
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(tmp_path,tmp_path));thread=threading.Thread(target=server.serve_forever);thread.start()
    def fetch(_):
        with urlopen(f'http://127.0.0.1:{server.server_port}/api/v4/context') as r:return json.loads(r.read())
    try:
        with ThreadPoolExecutor(max_workers=5) as pool:values=list(pool.map(fetch,range(5)))
        assert builds==['2026-10-12'] and all(v['context_token']=='2026-10-12' for v in values)
        head.write_text(json.dumps({'accepted_trade_date':'2026-10-13'}))
        assert fetch(0)['context_token']=='2026-10-13'
        assert builds==['2026-10-12','2026-10-13']
    finally:server.shutdown();thread.join();server.server_close()
