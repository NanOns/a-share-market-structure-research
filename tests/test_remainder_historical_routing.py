import json,hashlib,subprocess
from pathlib import Path
import pytest
from scripts.full_chain_repair_io import ROOT,binding
from workbench_analysis.historical_binding_routing_remainder import HistoricalExactReader,CurrentExactReader,REGISTRY

@pytest.mark.parametrize('number',range(20))
def test_all_historical_occurrences_exact(number):
    r=HistoricalExactReader(ROOT);b=r.registry['occurrences'][number]['binding'];raw,receipt=r.read(b)
    assert hashlib.sha256(raw).hexdigest()==b['sha256'] and receipt['grants_current_permission'] is False

@pytest.mark.parametrize('kind',['sha','bytes','path','windows','blob'])
def test_wrong_identities_and_windows_alias(kind,monkeypatch):
    r=HistoricalExactReader(ROOT);b=dict(r.registry['occurrences'][0]['binding'])
    if kind=='sha':b['sha256']='0'*64
    elif kind=='bytes':b['byte_count']+=1
    elif kind=='path':b['path']='unknown.json'
    elif kind=='windows':b['path']=b['path'].replace('/','\\');assert r.read(b)[0];return
    elif kind=='blob':
        original=subprocess.check_output
        def changed(args,**kw):return b'wrong blob' if args[1:3]==['cat-file','blob'] else original(args,**kw)
        monkeypatch.setattr(subprocess,'check_output',changed)
    with pytest.raises(ValueError):r.read(b)

def test_current_never_reads_historical_stage():
    current=CurrentExactReader(ROOT);assert current.read(binding('data/v4/V4_STAGE_ACCEPTED_HEAD.json'))
    historical=HistoricalExactReader(ROOT).registry['occurrences'][0]['binding']
    with pytest.raises(ValueError,match='CURRENT_BYTES_REQUIRED'):current.read(historical)

def test_old_v13_reader_remains_pinned():
    from workbench_analysis.v4_13_accepted_contract_package import current_contracts
    with pytest.raises(ValueError,match='UNAUTHORIZED_V4_13_STAGE'):current_contracts(ROOT)
