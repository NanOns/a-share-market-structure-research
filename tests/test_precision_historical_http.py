"""Socket HTTP with real production BFF, synthetic accepted-chain sources."""
import json
import threading
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer
import pytest
from precision_http_harness import Harness,D0,D1


@pytest.fixture
def http(tmp_path):
    h=Harness(tmp_path,Path(__file__).resolve().parents[1])
    server=ThreadingHTTPServer(('127.0.0.1',0),h.handler())
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def request(path,**q):
        try:
            with urlopen('http://127.0.0.1:'+str(server.server_port)+path+'?'+urlencode(q)) as r:
                return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    yield h,request
    server.shutdown();server.server_close();thread.join()


def test_http_current_token_historical_stock_sector_cohort_and_pagination(http):
    h,get=http
    code,before=get('/api/v4/candidates/sectors/INDUSTRY:T0706',trade_date=D0,context_token=h.old_token)
    assert code==200 and before['candidate_research']['candidate_status']=='AVAILABLE'
    h.activate(h.new)
    code,after=get('/api/v4/candidates/sectors/INDUSTRY:T0706',trade_date=D0,context_token=h.api.token)
    assert code==200 and after['candidate_research']['source']==before['candidate_research']['source']
    assert after['candidate_research']['item']==before['candidate_research']['item']
    code,cohort=get('/api/v4/candidates/cohort',trade_date=D0,context_token=h.api.token)
    assert code==200 and cohort['candidate_research']['research_eligible_count']==1
    assert cohort['candidate_research']['observed_count'] is None
    code,old=get('/api/v4/stocks',trade_date=D0,context_token=h.api.token,limit=1,offset=1)
    code,new=get('/api/v4/stocks',trade_date=D1,context_token=h.api.token,limit=1,offset=1)
    assert old['context']['trade_date']==D0 and old['offset']==1
    assert old['items'][0]['fields']['close']['value']+100==new['items'][0]['fields']['close']['value']
    code,bad=get('/api/v4/candidates/cohort',trade_date=D0,context_token=h.old_token)
    assert code==409 and bad['reason']=='CONTEXT_TOKEN_MISMATCH'


@pytest.mark.parametrize('case',['UNACCEPTED_HEAD','MUTATED_ARCHIVE','WRONG_SESSION','FUTURE_DATE'])
def test_http_historical_negative_cases(http,case):
    h,get=http;h.activate(h.new)
    index_path=h.root/'data/v4/producer_candidate_index_v2.json'
    index=json.loads(index_path.read_bytes())
    if case=='UNACCEPTED_HEAD':index['sessions'][D0]['head']=dict(index['sessions'][D0]['head'],sha256='f'*64)
    elif case=='MUTATED_ARCHIVE':
        (h.root/f"data/v4/predecessors/{h.new['predecessor']['sha256']}.json").write_bytes(b'{}')
    elif case=='WRONG_SESSION':
        # The current release grants D1, but the D0 bound candidate does not.
        index['sessions'][D1]=index['sessions'][D0]
    index_path.write_text(json.dumps(index))
    day=D1 if case=='WRONG_SESSION' else '2026-10-13' if case=='FUTURE_DATE' else D0
    code,data=get('/api/v4/candidates/cohort',trade_date=day,context_token=h.api.token)
    if case=='FUTURE_DATE':
        assert code==400 and data['reason']=='TARGET_DATE_NOT_GRANTED'
    else:
        assert code==200 and data['candidate_research']['candidate_status']=='UNAVAILABLE'
        assert data['candidate_research']['reason']==case


def test_versioned_dependency_archive_restores_original_bytes_only(tmp_path):
    from workbench_analysis.producer_dependency_archive_v1 import freeze_dependencies
    from workbench_service.candidate_research_read_v2 import checked_dependency
    from workbench_analysis.r43_owner_replay import ref
    root=tmp_path
    source=root/'src/original.py';source.parent.mkdir();source.write_bytes(b'original implementation\n')
    binding=ref(root,source)
    frozen=freeze_dependencies(root,[binding])
    assert frozen[0]['sha256']==binding['sha256']
    archive=root/frozen[0]['path']
    assert archive.read_bytes()==b'original implementation\n'
    # Exercise missing-archive degradation separately from automatic freezing.
    archive.unlink()
    source.write_bytes(b'new implementation\n')
    with pytest.raises(ValueError,match='HISTORICAL_COMPUTATION_BYTES_NOT_CAPTURED'):
        checked_dependency(root,binding)
    archive=root/'docs/evidence/producer_dependency_archive_v1'/ (binding['sha256']+'.bin')
    archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(b'original implementation\n')
    assert checked_dependency(root,binding).read_bytes()==b'original implementation\n'
    archive.write_bytes(b'mutated')
    with pytest.raises(ValueError,match='HISTORICAL_COMPUTATION_BYTES_NOT_CAPTURED'):
        checked_dependency(root,binding)
    # Dataset bindings are never redirected to code archives.
    original=root/'inputs/owner';original.parent.mkdir();original.write_bytes(b'owner')
    binding=ref(root,original);original.write_bytes(b'changed')
    (archive.parent/(binding['sha256']+'.bin')).write_bytes(b'owner')
    with pytest.raises(ValueError):
        checked_dependency(root,binding)
