import json
import shutil
from pathlib import Path

import pytest

from workbench_service.current_v4_context import CurrentAcceptedV4Reader, resolve_source_mode

ROOT=Path(__file__).resolve().parents[1]


def clone_authority(tmp_path):
    contract=json.loads((ROOT/'config/v4_current_accepted_read_contract_v1.json').read_bytes())
    paths=['config/v4_current_accepted_read_contract_v1.json']+[r['path'] for r in [*contract['anchors'].values(),*contract['owner_heads'].values()]]
    for name in paths:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
    return tmp_path,contract


def test_current_reader_uses_exact_accepted_heads():
    result=CurrentAcceptedV4Reader(ROOT).load_context()
    assert result['status']=='READY_CURRENT_ACCEPTED'
    assert result['context']['accepted_trade_date']=='2026-09-30'
    assert result['context']['stage']=='V4-15'
    assert all(value is False for value in result['production_permission'].values())


def test_current_reader_no_latest_discovery(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('source discovery')
    monkeypatch.setattr(Path,'glob',forbidden);monkeypatch.setattr(Path,'rglob',forbidden)
    assert CurrentAcceptedV4Reader(ROOT).read('health')[0]==200


def test_current_reader_wait_next_input_keeps_data():
    reader=CurrentAcceptedV4Reader(ROOT,today='2026-10-08')
    for module in ['summary','radar','entity','sector','cohort','settlement','health']:
        code,payload=reader.read(module)
        assert code==200
        assert payload['context']['freshness_state']=='WAIT_NEXT_ACCEPTED_INPUT'
        assert payload['items']


def test_current_reader_missing_future_date_not_unknown():
    reader=CurrentAcceptedV4Reader(ROOT,today='2099-01-01')
    assert reader.load_context()['status']=='READY_CURRENT_ACCEPTED'
    assert reader.read('entity')[1]['items'][0]['fields']['close']['quality']=='KNOWN'


def test_current_reader_digest_mismatch_blocks_scope(tmp_path):
    folder,contract=clone_authority(tmp_path)
    p=folder/contract['anchors']['data_head']['path'];p.write_bytes(p.read_bytes()+b' ')
    code,payload=CurrentAcceptedV4Reader(folder).read('context')
    assert code==409 and payload['code']=='SOURCE_INVALID'


def test_current_reader_valid_empty_is_not_unknown(monkeypatch):
    reader=CurrentAcceptedV4Reader(ROOT)
    original=reader._rows
    monkeypatch.setattr(reader,'_rows',lambda contract,key: [] if key=='ledger' else original(contract,key))
    code,payload=reader.read('radar')
    assert code==200 and payload['module_status']=='EMPTY_VALID'
    assert payload['metadata']['reason']=='NO_ELIGIBLE_OBJECTS'


def test_current_reader_never_falls_back_to_v3(tmp_path):
    (tmp_path/'data').mkdir()
    assert CurrentAcceptedV4Reader(tmp_path).read('context')[0]==409


def test_production_reader_missing_authority_fails_closed(tmp_path):
    folder,_=clone_authority(tmp_path)
    code,payload=CurrentAcceptedV4Reader(folder,require_runtime=True).read('context')
    assert code==409 and payload['reason']=='RUNTIME_AUTHORITY_MISSING'


def test_shadow_reader_behavior_unchanged():
    from workbench_service.shadow_context import ShadowContextReader
    assert ShadowContextReader(ROOT).handle('/api/v4/shadow/context',{})[1]['status']=='NO_REAL_SHADOW_DATA'


def test_v4_20_v2_display_does_not_grant_capability():
    assert resolve_source_mode(False,True)=='V4_ACCEPTED_RESEARCH_READONLY'
    assert resolve_source_mode(True,True)=='PRODUCTION_V4_PROVISIONAL'
    assert resolve_source_mode(False,False)=='NO_PERMISSION'
    assert not CurrentAcceptedV4Reader(ROOT).load_context()['focus_write']


def test_context_filter_and_deep_link_stability():
    reader=CurrentAcceptedV4Reader(ROOT)
    token=reader.load_context()['context_token']
    payload=reader.read('entity',{'q':'688349','context_token':token})[1]
    assert payload['context_token']==token and payload['total']==1
    assert reader.read('entity',{'context_token':'stale'})[0]==409
    assert reader.load_context()['context_token']==token


def test_module_bad_digest_does_not_block_other_module(tmp_path):
    folder,contract=clone_authority(tmp_path)
    bad=folder/contract['sources']['membership']['path'];bad.parent.mkdir(parents=True,exist_ok=True);bad.write_bytes(b'invalid')
    reader=CurrentAcceptedV4Reader(folder)
    assert reader.read('sector')[0]==409
    assert reader.read('context')[0]==200
