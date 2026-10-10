"""A third synthetic Head preserves first frozen candidate identity and clocks."""
import json
from copy import deepcopy
from test_candidate_historical_read_precision import two_heads
from test_producer_continuation_r2 import display_fixture
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref
from workbench_service.candidate_research_read_v2 import read_candidates


def test_three_head_history_never_rewrites_old_identity(two_heads):
    root, day, old, original, second, second_binding, index = two_heads
    original_bytes = (root/original['path']).read_bytes()
    archived_second = publish(root, 'data/v4/predecessors/' + second_binding['sha256'] + '.json', second)
    third = deepcopy(second)
    third.update(accepted_trade_date='2026-10-13', dates=second['dates']+['2026-10-13'], predecessor=archived_second)
    atomic_json(root, root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json', third)
    current = ref(root, root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    result = read_candidates(root, head=third, token=current['sha256'], day=day)
    assert result['candidate_status'] == 'RESEARCH_CANDIDATE_FROZEN'
    assert result['source_cutoff_date'] == day and result['historical_first_available'] is None
    assert result['observed_count'] is None and result['formal_consumer_enabled'] is False
    assert (root/'data/v4/predecessors'/ (original['sha256']+'.json')).read_bytes() == original_bytes
