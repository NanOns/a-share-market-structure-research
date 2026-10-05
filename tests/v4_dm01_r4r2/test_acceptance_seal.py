"""Real repository seal readback; no runtime grant or source capture."""
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from workbench_analysis import dm01_runtime_r4 as r
from scripts.build_r25_bridge_r4r2 import produce_bridge
from scripts.validate_r25_preflight import selection

ROOT = Path(__file__).resolve().parents[2]


def test_real_external_envelope_and_extension_bytes():
    head = r.accepted_envelope(ROOT)
    assert head['contract_id'] == 'DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1'
    assert head['r4r2_external_verdict'] == 'PASS_DM01_R4R2_R25_BRIDGE_INTEGRATION'
    authority = r.path(ROOT, head['independent_external_authority']).read_text(encoding='utf8')
    for key in ('runtime_contract', 'promotion_policy', 'calendar_head',
                'successor_daily_contract', 'runtime_dependencies_v4',
                'packet_preflight_v2', 'bridge_oracle', 'bridge_producer',
                'runtime_consumer', 'runtime_writer'):
        binding = head[key]
        assert r.ref(ROOT, ROOT / binding['path']) == binding
        assert binding['sha256'] in authority
    assert subprocess.check_output(
        ['git', 'rev-parse', head['tested_tag'] + '^{}'], cwd=ROOT,
        text=True).strip() == head['tested_source']


def test_sealed_future_wait_has_no_source_or_publication():
    data = (ROOT / r.HEAD).read_bytes()
    output = ROOT / 'reports/r25/target_session_bridge/acceptance_seal_wait_not_created.json'
    assert not output.exists()
    result = produce_bridge(ROOT, parent=None, child=None, candidate=None,
                            source=None, receipts=None, observation=None,
                            target='2026-10-08', observed_at=datetime.now(timezone.utc).isoformat(),
                            output=output.relative_to(ROOT).as_posix())
    assert result == dict(status='WAIT_MARKET_CLOSE', bridge_created=False,
                         r25_grant=False, source_requests=0)
    assert not output.exists() and (ROOT / r.HEAD).read_bytes() == data
    assert selection(ROOT)['status'] == 'WAIT_ACCEPTED_DAILY_INPUT'


def test_acceptance_does_not_grant_shadow_or_move_heads():
    previous = json.loads((ROOT / 'reports/dm01_r4r2/PROTECTED_STATE.json').read_bytes())
    for binding in previous['protected']['bindings']:
        assert r.ref(ROOT, ROOT / binding['path']) == binding
    assert not (ROOT / 'data/v4/V4_16_ACCEPTED_HEAD.json').exists()
    activation = json.loads((ROOT / 'config/v4_16_runtime_activation_authority_v3.json').read_bytes())
    assert activation['runtime_authorized'] is False
    assert activation['real_shadow_authorized'] is False
    assert r.accepted_envelope(ROOT)['permissions'] == r.PERMISSIONS
