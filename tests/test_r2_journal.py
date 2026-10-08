import json,sqlite3
import pytest
from focus_tracker.v4_journal import append
from workbench_service.current_v4_context import digest,SourceInvalid

def source(root,day,pre='TRUE'):
    p=root/(day+'.json');p.write_text(json.dumps({'rows':[dict(entity_id='A',trade_date=day,raw_qualification={'PREWATCH':pre,'CONFIRMED':'FALSE'},publication_id=day)]}))
    return dict(path=p.name,sha256=digest(p.read_bytes()))

def test_idempotent_monotonic_journal_and_rollback(tmp_path):
    p=tmp_path/'journal.sqlite';a=source(tmp_path,'2026-09-29');b=source(tmp_path,'2026-09-30','FALSE')
    first=append(p,tmp_path,a,None)
    assert append(p,tmp_path,a,first['head'])['status']=='NOOP'
    with pytest.raises(SourceInvalid,match='INJECTED'):append(p,tmp_path,b,first['head'],fail_after_append=True)
    with sqlite3.connect(p) as db:assert db.execute('SELECT count(*) FROM days').fetchone()[0]==1
    second=append(p,tmp_path,b,first['head']);assert second['events']==2
    with pytest.raises(SourceInvalid,match='CAS'):append(p,tmp_path,b,first['head'])
