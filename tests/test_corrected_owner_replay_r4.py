from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import pytest

from tdx.gbbq_reader import GbbqRecord
from workbench_analysis.corrected_owner_replay import transform_window, independent_affine, midrank
from v4.factors.core import rps_midrank


def event(day, category=1, cash=1, bonus=0):
    return GbbqRecord('SH.600000','600000',day,category,cash,0,bonus,0,'TEST',0,1)


def raw(day, close=1000):
    return (day,close,close+100,close-100,close,10000.0,1000,0)


def test_unsupported_event_only_blocks_crossing_bars():
    classes={'6':{'formal_disposition':'PRICE_AFFECTING_UNSUPPORTED'}}
    rows=transform_window([raw(20260921),raw(20260923),raw(20260928)],
                          [event(20260922,6)],classes,'2026-09-28')
    assert rows[0]['qfq_ohlc'] is None
    assert rows[1]['qfq_ohlc']==[10,11,9,10]
    assert rows[2]['qfq_ohlc']==[10,11,9,10]


def test_future_events_and_suspension_gap_do_not_leak():
    es=[event(20260922,cash=2,bonus=1),event(20261015,cash=500)]
    rows=transform_window([raw(20260921),raw(20260928)],es,
        {'1':{'formal_disposition':'PRICE_AFFECTING_SUPPORTED'}},'2026-09-28')
    assert rows[0]['qfq_ohlc'][0]==independent_affine(10,20260921,es,20260928)
    assert rows[-1]['qfq_ohlc'][0]==10


def test_sorted_midrank_preserves_frozen_tie_formula():
    values={'a':1.0,'b':1.0,'c':2.0,'d':None,'e':-2.0}
    assert midrank(values,set(values))==rps_midrank(values,list(values))[0]


def test_descendant_reader_preserves_exact_head_and_producer_identities():
    from workbench_analysis.v4_13_descendant_contracts import DescendantContracts
    c=DescendantContracts(Path(__file__).resolve().parents[1])
    assert c.authority['production'] is False
    assert c.digest==c.authority['contract_digest']
    assert c.resolutions
