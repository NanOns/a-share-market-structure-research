"""Default V4 dispatch must use the existing daily policy and date contract."""
import hashlib
import json
from pathlib import Path
import pytest

SOURCE = Path('G:/codex_tmp/r4_r3_pg_publication_v2')


def test_actual_daily_reader_preserves_authority_and_date():
    from workbench_analysis.operational_successor_v1 import accepted_api
    from workbench_service.operational_successor_bff_v1 import OperationalSuccessorBFFV1
    api = accepted_api(SOURCE)
    context = api.context()
    assert context['accepted_trade_date'] == '2026-10-09'
    assert context['read_scope'] == 'USER_AUTHORIZED_OPERATIONAL_DAILY'
    assert context['independent_external_acceptance'] is False
    assert context['PIT_ELIGIBLE'] is False
    response = OperationalSuccessorBFFV1(api, None).envelope('2026-10-09')
    assert response['context']['accepted_trade_date'] == context['accepted_trade_date']
    assert response['context']['data_cutoff_date'] == '2026-10-09'
    assert response['context_token'] == context['context_token']


def test_daily_policy_unready_is_rejected_before_consumer(tmp_path):
    from workbench_analysis.operational_successor_v1 import accepted_api
    candidate = json.loads((SOURCE / 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    policy = json.loads((SOURCE / candidate['release_policy']['path']).read_bytes())
    policy['publication_ready'] = False
    raw = json.dumps(policy).encode()
    path = tmp_path / candidate['release_policy']['path']
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    candidate['release_policy'] = dict(path=candidate['release_policy']['path'], sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    head = tmp_path / 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head.parent.mkdir(parents=True)
    head.write_text(json.dumps(candidate), encoding='utf8')
    with pytest.raises(ValueError, match='DAILY_ALGORITHM_ADMISSION_NOT_READY'):
        accepted_api(tmp_path)


def test_daily_policy_digest_mismatch_is_rejected(tmp_path):
    from workbench_analysis.operational_successor_v1 import accepted_api
    candidate = json.loads((SOURCE / 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    path = tmp_path / candidate['release_policy']['path']
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{}')
    head = tmp_path / 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head.parent.mkdir(parents=True)
    head.write_text(json.dumps(candidate), encoding='utf8')
    with pytest.raises(ValueError, match='CORRECTED_INPUT_DIGEST_MISMATCH'):
        accepted_api(tmp_path)
