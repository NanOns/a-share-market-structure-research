"""Replay immutable pre-promotion contracts through the declared exact anchor archive.

Only historical tests receive this adapter. New V2 readback uses the production
reader directly, and all other paths and hashes retain the original hash gate.
"""
from pathlib import Path
import json
import pytest
from workbench_analysis.dm01_accepted_chain_v1 import resolve_frozen_binding,HEAD_PATH,ANCHOR_SHA,HEAD_CONTRACT

@pytest.fixture(autouse=True)
def historical_anchor_readback(monkeypatch):
    root=Path(__file__).resolve().parents[2]
    if json.loads((root/HEAD_PATH).read_bytes()).get('contract_id')!=HEAD_CONTRACT:return
    from workbench_analysis import dm01_incremental_component_builders_r3 as r1
    from workbench_analysis import dm01_incremental_component_builders_r3_2 as r2
    from workbench_analysis import dm01_incremental_component_builders_r3_3 as r3
    for module in (r1,r2,r3):
        original=module.bound_path
        def archived(ref,_original=original):
            if ref.get('path')==HEAD_PATH and ref.get('sha256')==ANCHOR_SHA:
                return resolve_frozen_binding(root,ref)
            return _original(ref)
        monkeypatch.setattr(module,'bound_path',archived)
