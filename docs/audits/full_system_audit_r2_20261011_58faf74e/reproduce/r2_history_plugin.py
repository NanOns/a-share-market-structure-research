import pytest
from pathlib import Path
@pytest.fixture(autouse=True)
def r2_history(request,monkeypatch,pinned_v9_v10_publication_history_profile):
 if request.node.path.name in ('test_promotion.py','test_accepted_head_r1.py') and '/v4_10/' in request.node.path.as_posix():
  from scripts import promote_v4_09_accepted_head as v9,validate_v4_10_promotion_r1 as v10
  root=Path('G:/codex_tmp/full_system_audit_r2_58faf74e/history_bridge_profile')
  monkeypatch.setattr(v9,'ROOT',root);monkeypatch.setattr(v10,'ROOT',root)

 if request.node.name.startswith('test_b0_validator_rejects_self_consistent_wrong_producer_or_contract'):
  from scripts import promote_v4_08_accepted_head as v8
  monkeypatch.setattr(v8,'ROOT',Path('G:/codex_tmp/full_system_audit_r2_58faf74e/b0_historical_profile'))

 if request.node.name=='test_real_warmup_historical_block_no_head_move_and_exact_observation_readback':
  monkeypatch.setattr(request.module,'ROOT',Path('G:/codex_tmp/full_system_audit_r2_58faf74e/amount_sources'))
