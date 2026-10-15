from workbench_analysis import forward_r7_pipeline as pipeline
import pytest


@pytest.mark.parametrize('mixed',[False,True])
def test_accepted_head_hook_publishes_hash_bound_rows_and_advances_due_sources(tmp_path,monkeypatch,mixed):
    day='2026-10-14';head=dict(accepted_trade_date=day,published_sessions=['2026-10-13',day])
    refs={name:dict(path=name,sha256=name[0]*64) for name in ('raw','core','sector','lifecycle')}
    refs['freeze']=dict(path='freeze',sha256='f'*64)
    head['source_registry']={day:dict(freeze=refs['freeze'])}
    seen={}
    class Store:
        def verify_existing_storage(self):pass
        def register_definitions(self,*args):pass
        def publish_day(self,**kwargs):
            seen['publish']=kwargs;seen.setdefault('publications',[]).append(kwargs)
            return dict(status='PUBLISHED')
        def pending_due_dates(self,**kwargs):return [day]
        def legacy_no_quote_due_dates(self):return [day]
        def review_legacy_no_quote(self,**kwargs):seen['review']=kwargs;return dict(appended=0)
        def advance_due_settlements(self,**kwargs):seen['advance']=kwargs;return dict(appended=0)
        def record_failure(self,**kwargs):raise AssertionError(kwargs)
    monkeypatch.setattr(pipeline,'ForwardR7Store',lambda *args,**kwargs:Store())
    monkeypatch.setattr(pipeline,'load_definitions',lambda root:({},'definitions'))
    monkeypatch.setattr(pipeline,'_head',lambda root:head)
    monkeypatch.setattr(pipeline,'_bindings',lambda *args:refs)
    def document(root,binding):
        if binding['path']=='freeze':return dict(target_session=day,observed_at='2026-10-15T11:31:00+00:00',
            first_available_at='2026-10-15T11:31:00+00:00',source_ready_at='2026-10-15T11:31:00+00:00')
        if binding['path']=='raw':return [dict(security_id='sid',close=10)]
        if binding['path']=='lifecycle':return dict(rows=[])
        return []
    monkeypatch.setattr(pipeline,'_document',document)
    monkeypatch.setattr(pipeline,'official_sessions',lambda root:['2026-10-13',day,'2026-10-15','2026-10-16'])
    rows=[dict(entity_type='STOCK',entity_id='sid')]
    if mixed:
        rows.append(dict(entity_type='SECTOR',entity_id='unproved-members'))
        monkeypatch.setattr(pipeline,'classify_after_close_capture',lambda **kwargs:dict(lane='LIVE_OOS'))
    monkeypatch.setattr(pipeline,'build_daily_universe',lambda **kwargs:rows)
    monkeypatch.setattr(pipeline,'build_schedules',lambda *args,**kwargs:[])
    result=pipeline.capture_after_accepted_head(tmp_path,head,head_accepted_at='2026-10-15T12:00:00+00:00')
    assert result['status']=='PUBLISHED'
    digest=seen['publish']['rows'][0]['source_digest']
    assert len(digest)==64
    assert seen['review']['source_digests_by_date'][day]==digest
    assert seen['advance']['source_digests_by_date'][day]==digest
    if mixed:
        groups={p['lane']:p for p in seen['publications']}
        assert set(groups)=={'LIVE_OOS','LATE_OBSERVED_NOT_PIT'}
        assert groups['LIVE_OOS']['rows'][0]['entity_type']=='STOCK'
        sector=groups['LATE_OBSERVED_NOT_PIT']['rows'][0]
        assert sector['entity_type']=='SECTOR' and sector['PIT_ELIGIBLE'] is False
        assert sector['lane']==sector['evidence_lane']=='LATE_OBSERVED_NOT_PIT'
        assert len({p['run_id'] for p in seen['publications']})==2
