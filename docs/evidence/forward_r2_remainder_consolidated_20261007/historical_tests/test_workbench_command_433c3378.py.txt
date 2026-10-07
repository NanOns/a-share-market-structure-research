import json, threading, urllib.request
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock
import pytest
from workbench_db import WorkbenchRepository
from workbench_publish import PublicationRequest
from workbench_publish.orchestrator import ControlledProduction
import workbench_publish.orchestrator as orch
import workbench_service.app as app

def test_controlled_compute_uses_fixed_project_entry_and_timeout(tmp_path,monkeypatch):
 root=Path(__file__).resolve().parents[2];release=root/'reports/releases/20260907/452811b8e0c54c029560aae46c6d3081'
 completed=Mock(returncode=0,stdout=json.dumps({'release_path':str(release)})+'\n',stderr='')
 monkeypatch.setattr(orch.subprocess,'run',lambda command,**kw:(setattr(completed,'command',command) or setattr(completed,'kwargs',kw) or completed))
 monkeypatch.setattr(orch,'load_computed_results',lambda root,request,release:request)
 request=PublicationRequest(date(2026,9,7),'bundle-1','model','compute')
 assert ControlledProduction(root,321)(request)==request
 assert completed.command[1].endswith('run_bundle_compute.py') and completed.kwargs['timeout']==321

def test_workbench_post_returns_job_and_get_reads_status(tmp_path,monkeypatch):
 root=Path(__file__).resolve().parents[2];db=tmp_path/'api.duckdb'
 with WorkbenchRepository(root,db) as repo:
  bundle={'source_bundle_id':'bundle-1','target_trade_date':'2026-09-07'}
  repo.connection.execute("insert into source_bundles values (?,?)",['bundle-1',json.dumps(bundle)])
  repo.connection.execute("insert into jobs values ('job-test','key-test','QUEUED','{}')")
 fake_publisher=Mock();fake_publisher.status.return_value={'status':'QUEUED','progress':{'status':'QUEUED'},'updated_at_utc':None}
 fake_publisher.wait.return_value={'status':'SUCCESS','publication_id':'m4-test'}
 monkeypatch.setattr(app,'submit_one_click',lambda *args:(fake_publisher, 'job-test'))
 monkeypatch.setattr(app.subprocess,'run',lambda *args,**kwargs:Mock(returncode=0,stderr=''))
 server=ThreadingHTTPServer(('127.0.0.1',0),app.make_handler(root,db));threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  base=f'http://127.0.0.1:{server.server_port}';html=urllib.request.urlopen(base+'/').read().decode();token=html.split("const csrf='")[1].split("'")[0]
  req=urllib.request.Request(base+'/api/jobs',data=b'{}',method='POST',headers={'Content-Type':'application/json','X-CSRF-Token':token})
  submitted=json.loads(urllib.request.urlopen(req).read());status=json.loads(urllib.request.urlopen(base+'/api/jobs?job_id='+submitted['job_id']).read())
  assert submitted['job_id'].startswith('daily-') and status['status'] in ('QUEUED','RUNNING')
  with pytest.raises(urllib.error.HTTPError) as duplicate:
   urllib.request.urlopen(req)
  assert duplicate.value.code==409
  assert json.loads(duplicate.value.read())['code']=='DAILY_INPUT_ALREADY_RUNNING'
 finally:server.shutdown();server.server_close()

def test_read_api_remains_available_during_publisher_transaction(tmp_path):
 root=Path(__file__).resolve().parents[2];db=tmp_path/'api.duckdb'
 with WorkbenchRepository(root,db): pass
 writer=app.duckdb.connect(str(db))
 try:
  writer.execute('begin transaction')
  writer.execute("insert into jobs values ('job-writer','key-writer','RUNNING','{}')")
  assert app.Api(db).publications()['items']==[]
 finally:
  writer.execute('rollback');writer.close()
