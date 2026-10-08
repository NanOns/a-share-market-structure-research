import csv,io,json
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import pytest
from workbench_service.current_v4_context import digest,SourceInvalid
from workbench_service.csv_export import stock_csv
from workbench_service.pit_observation import freeze

def test_csv_preserves_quotes_unicode_and_page_identity():
    rows=[dict(entity_id=str(i),display_name='中文,"名称"',symbol=str(i),trade_date='2026-09-30',fields={'close':{'value':1}}) for i in range(401)]
    def query(domain,q,summary):
        page=rows[q['offset']:q['offset']+q['limit']]
        return dict(items=page,total=len(rows),has_next=q['offset']+len(page)<len(rows))
    raw,count=stock_csv(SimpleNamespace(query=query),{})
    data=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    assert count==401 and len(data)==402 and data[1][1]=='中文,"名称"'
    assert len({x[0] for x in data[1:]})==401

def test_first_observed_freeze_never_backdates_pit_and_rejects_future(tmp_path):
    source=tmp_path/'source.json';source.write_text('{}');binding=dict(path='source.json',sha256=digest(source.read_bytes()))
    r=SimpleNamespace(root=tmp_path,context={'trade_date':'2026-09-30'},manifest={'sources':{'membership':binding}})
    first=freeze(r);assert first['strict_t0_pit_ready'] is False and first['AS_RECORDED'] is False
    assert freeze(r)==first
    with pytest.raises(SourceInvalid,match='FUTURE'):freeze(r,(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    with pytest.raises(SourceInvalid,match='BACKDATED'):freeze(r,(datetime.now(timezone.utc)-timedelta(days=30)).isoformat())


def test_existing_first_observed_freeze_verifies_archived_bytes(tmp_path):
    source=tmp_path/'source.json';source.write_text('{}')
    binding=dict(path=source.name,sha256=digest(source.read_bytes()))
    r=SimpleNamespace(root=tmp_path,context={'trade_date':'2026-09-30'},manifest={'sources':{'membership':binding}})
    first=freeze(r);archive=tmp_path/first['sources']['membership']['path']
    archive.write_text('{"tampered":true}')
    with pytest.raises(SourceInvalid,match='DIGEST_MISMATCH'):freeze(r)
