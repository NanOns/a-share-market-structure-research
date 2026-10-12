import json
import pytest
from focus_tracker.v4_daily_driver import advance
from workbench_service.current_v4_context import SourceInvalid,canonical,digest


def test_daily_noop_checks_exact_owner_inputs_and_head_before_work(tmp_path,monkeypatch):
    inputs={'implementation':{'kernel':{'sha256':'same'}},'owner':'dated'}
    from workbench_db.v4_journal_pg_r1 import JournalConnection
    from focus_tracker.v4_journal import CONTRACT
    path=tmp_path/'journal.pg.json'
    db=JournalConnection(path,tmp_path,CONTRACT)
    try:
        db.execute('INSERT INTO metadata VALUES(?,?)',('head','head'))
        db.execute('INSERT INTO days VALUES(?,?,?)',('2026-09-30','states','[]'))
        db.execute('INSERT INTO day_inputs VALUES(?,?)',('2026-09-30',canonical(inputs).decode()))
        db.commit()
    finally:db.close()
    binding=dict(path=path.name,sha256=digest(path.read_bytes()))
    manifest=dict(context={'accepted_trade_date':'2026-09-30'},sources={'states':{'sha256':'states'}})
    monkeypatch.setattr('focus_tracker.v4_daily_driver.path_inputs',lambda *args:inputs)
    monkeypatch.setattr('focus_tracker.v4_daily_driver.append',lambda *args,**kwargs:pytest.fail('NOOP must not append'))
    work=tmp_path/'no_work'
    result=advance(tmp_path,manifest,previous_journal=binding,previous_publication={'sha256':'publication'},expected_head='head',work_root=work)
    assert result['status']=='NOOP' and result['source_requests']==0
    assert not work.exists()
    with pytest.raises(SourceInvalid,match='CAS_CONFLICT'):
        advance(tmp_path,manifest,previous_journal=binding,expected_head='wrong',work_root=work)
    inputs['owner']='revision'
    with pytest.raises(SourceInvalid,match='SAME_DAY_REVISION'):
        advance(tmp_path,manifest,previous_journal=binding,expected_head='head',work_root=work)
    assert not work.exists()
