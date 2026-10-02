"""Synthetic candidate revision objects: immutable facts and append-only views."""
from copy import deepcopy
import json
import sys
import tempfile
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore,digest
from workbench_analysis.v4_12_anchor_runtime import create_anchor,coordinate_view,create_event

def verify():
    c=FrozenContracts(ROOT);store=CandidateStore(ROOT)
    fields=dict(price_basis='SYNTHETIC_RAW_COORDINATE',adjustment_source_revision='SYNTHETIC_CREATION_REVISION')
    anchor=create_anchor(c,'BULLISH_IMPULSE_BODY','SYNTHETIC','2026-09-24','2026-09-24T16:00:00+00:00',fields,'SYNTHETIC_EVENT','0'*64,
        (10,11),dict(scope='SYNTHETIC_ONLY'),dict(mul='1',add='0',scope='SYNTHETIC_ONLY'))
    original=deepcopy(anchor);event=create_event(c,anchor,'r1');event_before=digest(event);views=[];transitions=[]
    for revision in ['r1','r2','r3']:
        view=coordinate_view(anchor,fields['price_basis'],fields['adjustment_source_revision'],'2026-09-25',revision)
        views.append(view);transitions.append(dict(event_id=event['event_id'],anchor_id=anchor['anchor_id'],observation_trade_date='2026-09-25',revision=revision,
            prior_session_ref='SYNTHETIC_2026_09_24_BASELINE',same_day_revision_is_prior=False,own_frozen_invalid_if=event['frozen_invalidation_ast']))
    assert anchor==original and digest(event)==event_before
    # Active display selection cannot change the bound event's invalidation Anchor.
    other=deepcopy(anchor);other['anchor_id']='SYNTHETIC_OTHER_DISPLAY_ANCHOR';active_display=other['anchor_id']
    assert event['anchor_id']==anchor['anchor_id']!=active_display
    (ROOT/'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='candidate_conflict_probe_',dir=ROOT/'tmp') as directory:
        probe=CandidateStore(ROOT,Path(directory).relative_to(ROOT).as_posix())
        ref=probe.json('original.json',anchor);assert ref==probe.json('original.json',anchor)
        try:probe.json('original.json',other);conflict_rejected=False
        except ValueError as error:conflict_rejected=str(error).startswith('IMMUTABLE_REVISION_CONFLICT')
    assert conflict_rejected
    receipt=dict(status='PASS',scope='SYNTHETIC_ENGINEERING_ONLY_NOT_FORMAL_SOURCE',original_anchor=anchor,immutable_anchor_digest=digest(anchor),event=event,
        observation_views=views,transitions=transitions,append_only_revision_count=3,original_fact_unchanged=True,conflict_rejected=True,
        active_display_anchor_id=active_display,episode_bound_anchor_id=event['anchor_id'],episode_invalid_if_unchanged=True)
    receipt['frozen_anchor_schema_readback']='PASS'
    receipt['supersedes_initial_diagnostic']='V4_12_SYNTHETIC_CANDIDATE_LIFECYCLE.json; initial constructor diagnostic retained, not formal authority'
    store.json('V4_12_SYNTHETIC_CANDIDATE_LIFECYCLE_R1_SCHEMA_VALID.json',receipt)
    print(json.dumps(dict(status='PASS',append_only_revision_count=3,original_fact_unchanged=True)))

if __name__=='__main__':verify()
