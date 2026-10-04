"""Exact registered nodeid supersession only; never pattern deselection."""
import json
from pathlib import Path
def pytest_collection_modifyitems(config,items):
    registry=json.loads((Path(__file__).resolve().parents[1]/'reports/r21/SUPERSEDED_CURRENT_STAGE_TESTS.json').read_bytes())
    nodes={e['nodeid'] for e in registry['entries']}
    found={i.nodeid for i in items if i.nodeid in nodes}
    if found!=nodes:raise ValueError('REGISTERED_NODEIDS_MUST_ALL_EXIST')
    removed=[i for i in items if i.nodeid in nodes];items[:]=[i for i in items if i.nodeid not in nodes]
    config.hook.pytest_deselected(items=removed)
