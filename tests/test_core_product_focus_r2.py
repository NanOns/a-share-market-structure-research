"""Explicit synthetic boundary cases; no production data acceptance claims."""
from focus_tracker.core_product_focus_r2 import project
import pytest


def row(day, validity='VALID', pre='TRUE', confirmed='FALSE'):
    return dict(entity_id='FIXTURE-A', trade_date=day, validity=validity,
                raw_qualification={'PREWATCH': pre, 'CONFIRMED': confirmed}, publication_id='FIXTURE:'+day)


def test_invalidation_blocks_reentry_until_a_later_valid_session():
    days={'2026-09-28':[row('2026-09-28')],
          '2026-09-29':[row('2026-09-29','INVALIDATED',confirmed='TRUE')],
          '2026-09-30':[row('2026-09-30','INVALIDATED',confirmed='TRUE')],
          '2026-10-08':[row('2026-10-08')]}
    result=project(days)
    assert [e['event'] for e in result['events']]==['NEW','INVALIDATED','REENTERED']
    assert result['episodes'][0]['end_date']=='2026-09-29'
    assert result['episodes'][1]['parent_episode_id']==result['episodes'][0]['episode_id']
    assert project(days)==result
    assert len({e['idempotency_key'] for e in result['events']})==3
    assert days['2026-09-29'][0]['validity']=='INVALIDATED'


def test_initial_invalidated_positive_signal_does_not_enroll():
    assert project({'2026-09-28':[row('2026-09-28','INVALIDATED',confirmed='TRUE')]})['episodes']==[]


def test_duplicate_same_day_entity_is_rejected():
    with pytest.raises(ValueError,match='FOCUS_DUPLICATE_ENTITY'):
        project({'2026-09-28':[row('2026-09-28'),row('2026-09-28')]})
