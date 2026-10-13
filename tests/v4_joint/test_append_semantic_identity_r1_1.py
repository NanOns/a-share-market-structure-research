from collections import Counter
import pytest
from scripts.verify_v4_append_semantic_identity_r1_1 import normalize,canonical_event_map,verify_bindings

def test_ids_are_semantically_resolved_without_hiding_prices_or_quality():
    a={'episode_id':'A','close':10.,'quality':'KNOWN','input_digest':'x'}
    b={'episode_id':'B','close':10.,'quality':'KNOWN','input_digest':'y'}
    assert normalize(a,{'A':['S','2026-10-09']},Counter())==normalize(b,{'B':['S','2026-10-09']},Counter())
    for key,value in [('close',10.01),('quality','UNKNOWN'),('close',None)]:
        changed=dict(b,**{key:value})
        assert normalize(a,{'A':['S','2026-10-09']},Counter())!=normalize(changed,{'B':['S','2026-10-09']},Counter())

def test_ambiguous_episode_semantics_fail_closed():
    row={'episode_id':'A','entity_id':'S','start_date':'2026-10-09'}
    with pytest.raises(ValueError,match='AMBIGUOUS'):canonical_event_map({'episodes':[row,dict(row,episode_id='B')]})

def test_future_reference_fails_closed(tmp_path):
    with pytest.raises(ValueError,match='FUTURE_DATE'):verify_bindings(tmp_path,{'trade_date':'2026-10-14'},'2026-10-13')
