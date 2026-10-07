import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from workbench_service.current_v4_context import CurrentAcceptedV4Reader, SourceInvalid, digest, canonical
from workbench_service.v4_daily_refresh import AUTHORITY, atomic_bytes, publish_accepted_view, refresh_status

ROOT=Path(__file__).resolve().parents[1]


def disposable(tmp_path):
    runtime=json.loads((ROOT/AUTHORITY).read_bytes())
    contract=json.loads((ROOT/runtime['read_authority']['path']).read_bytes())
    refs=[*contract['anchors'].values(),*contract['owner_heads'].values(),*contract['sources'].values()]
    refs.extend(ref for rows in contract['row_bindings'].values() for ref in rows)
    paths={ref['path'] for ref in refs}|{AUTHORITY,runtime['read_authority']['path']}
    for path in paths:
        target=tmp_path/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,target)
    # Candidate path is explicit; no mutable production source is used in tests.
    shutil.copyfile(tmp_path/runtime['read_authority']['path'],tmp_path/'candidate.json')
    return tmp_path


def test_no_new_trading_day_preserves_current():
    status=refresh_status(ROOT,now=datetime(2026,10,7,18,tzinfo=ZoneInfo('Asia/Shanghai')))
    assert status['status']=='WAIT_NEXT_ACCEPTED_INPUT'
    assert status['source_requests']==0 and status['data_preserved']
    assert status['context']['context']['accepted_trade_date']=='2026-09-30'


def test_atomic_publish_and_cas(tmp_path):
    root=disposable(tmp_path);before=digest((root/AUTHORITY).read_bytes())
    receipt=publish_accepted_view(root,'candidate.json',before)
    assert receipt['status']=='PUBLISHED_CURRENT_ACCEPTED'
    assert CurrentAcceptedV4Reader(root).load_context()['context']['accepted_trade_date']=='2026-09-30'
    with pytest.raises(SourceInvalid,match='CAS_CONFLICT'):publish_accepted_view(root,'candidate.json','0'*64)


def test_failure_retains_last_accepted_pointer(tmp_path):
    root=disposable(tmp_path);before=(root/AUTHORITY).read_bytes()
    c=json.loads((root/'candidate.json').read_bytes());c['sources']['membership']['sha256']='0'*64
    atomic_bytes(root/'candidate.json',canonical(c))
    with pytest.raises(SourceInvalid):publish_accepted_view(root,'candidate.json',digest(before))
    assert (root/AUTHORITY).read_bytes()==before


def test_standard_candidate_path_is_validated_instead_of_old_runtime(tmp_path):
    root=disposable(tmp_path);before=(root/AUTHORITY).read_bytes()
    candidate='config/v4_current_accepted_read_contract_v1.json'
    c=json.loads((root/'candidate.json').read_bytes());c['sources']['membership']['sha256']='0'*64
    atomic_bytes(root/candidate,canonical(c))
    with pytest.raises(SourceInvalid):publish_accepted_view(root,candidate,digest(before))
    assert (root/AUTHORITY).read_bytes()==before


def test_publish_readback_failure_restores_previous_pointer(tmp_path,monkeypatch):
    root=disposable(tmp_path);before=(root/AUTHORITY).read_bytes()
    original=CurrentAcceptedV4Reader.load_context
    def fail_readback(self):
        if self.follow_runtime:raise SourceInvalid('READBACK_FAULT_INJECTION')
        return original(self)
    monkeypatch.setattr(CurrentAcceptedV4Reader,'load_context',fail_readback)
    with pytest.raises(SourceInvalid,match='READBACK_FAULT_INJECTION'):
        publish_accepted_view(root,'candidate.json',digest(before))
    assert (root/AUTHORITY).read_bytes()==before


def test_concurrent_candidate_replacement_cannot_mix_module_gates(tmp_path,monkeypatch):
    root=disposable(tmp_path);raw=(root/'candidate.json').read_bytes()
    original=CurrentAcceptedV4Reader.read
    def replace_after_summary(self,module,query=None):
        result=original(self,module,query)
        if module=='summary':atomic_bytes(root/'candidate.json',b'invalid-next-candidate')
        return result
    monkeypatch.setattr(CurrentAcceptedV4Reader,'read',replace_after_summary)
    receipt=publish_accepted_view(root,'candidate.json',digest((root/AUTHORITY).read_bytes()))
    assert receipt['status']=='PUBLISHED_CURRENT_ACCEPTED'
    assert json.loads((root/AUTHORITY).read_bytes())['read_authority']['sha256']==digest(raw)


def test_disposable_rollback_exact_and_no_v3(tmp_path):
    root=disposable(tmp_path);before=(root/AUTHORITY).read_bytes()
    publish_accepted_view(root,'candidate.json',digest(before))
    after=(root/AUTHORITY).read_bytes();post=CurrentAcceptedV4Reader(root).load_context()
    atomic_bytes(root/AUTHORITY,before)
    assert (root/AUTHORITY).read_bytes()==before
    atomic_bytes(root/AUTHORITY,after)
    assert CurrentAcceptedV4Reader(root).load_context()==post
    assert post['source_mode']=='V4_ACCEPTED_RESEARCH_READONLY'


def test_next_accepted_input_simulation_no_production_access(tmp_path):
    # Rebind a complete isolated synthetic owner graph, using the actual reader,
    # module gates and publisher. This never establishes real future acceptance.
    root=disposable(tmp_path);date='2026-10-08'
    original_token=CurrentAcceptedV4Reader(root).load_context()['context_token']
    contract=json.loads((root/'candidate.json').read_bytes())
    refs=[*contract['anchors'].values(),*contract['owner_heads'].values(),*contract['sources'].values()]
    refs.extend(ref for rows in contract['row_bindings'].values() for ref in rows)
    known={ref['path']:ref for ref in refs};built={};visiting=set()
    aliases={ref.get('authority_source_path',ref['path']):ref['path'] for ref in refs}
    def transform(value):
        if isinstance(value,list):return [transform(x) for x in value]
        if isinstance(value,dict):
            path=aliases.get(value.get('path'),value.get('path'))
            if path in known and value.get('sha256')==known[path]['sha256']:
                return {**value,**build(path)}
            return {k:transform(v) for k,v in value.items()}
        return date if value=='2026-09-30' else value
    def build(path):
        if path in built:return built[path]
        if path.endswith('.gz'):return known[path]
        assert path not in visiting,'Synthetic graph must be acyclic'
        visiting.add(path)
        raw=(root/path).read_bytes()
        if '.jsonl' in path:
            raw=b'\n'.join(canonical(transform(json.loads(line))) for line in raw.splitlines() if line)+b'\n'
        else:raw=canonical(transform(json.loads(raw)))+b'\n'
        atomic_bytes(root/path,raw)
        built[path]=dict(path=path,bytes=len(raw),sha256=digest(raw))
        visiting.remove(path)
        return built[path]
    contract=transform(contract)
    atomic_bytes(root/'candidate.json',canonical(contract))
    before=digest((root/AUTHORITY).read_bytes())
    receipt=publish_accepted_view(root,'candidate.json',before,now=datetime(2026,10,9,tzinfo=ZoneInfo('Asia/Shanghai')))
    assert json.loads((root/AUTHORITY).read_bytes())['last_accepted_trade_date']==date
    assert receipt['status']=='PUBLISHED_CURRENT_ACCEPTED'
    assert receipt['context']['context']['accepted_trade_date']==date
    assert receipt['context']['context_token']!=original_token
