from concurrent.futures import ThreadPoolExecutor
from workbench_service.operational_control_status import control_status


def test_namespace_switch_rollback_and_concurrent_isolation():
    legacy = dict(context=dict(accepted_trade_date='2026-09-30', last_accepted_trade_date='2026-09-30',
                               data_head_digest='old', source_revision='old-code', stage='V4-15', namespace='V4_CURRENT_ACCEPTED'),
                  context_token='legacy-token', production_permission={'STOCK_CORE': False})
    operational = dict(accepted_trade_date='2026-10-08', context_token='new-token',
                       membership_observed_at='2026-10-09T01:00:00Z', authorization_mode='DIRECT_HUMAN_USER')
    def read(i):
        result = control_status(legacy, operational if i % 2 else None, 'new-digest')
        assert result['legacy_strict_pit_context']['data_head_digest'] == 'old'
        assert result['production_permission'] == {'STOCK_CORE': False}
        if i % 2:
            assert result['last_accepted_trade_date'] == '2026-10-08'
            assert result['data_head_digest'] == 'new-digest'
            assert result['operational_context']['capability_permissions']['trading_execution'] is False
        else:
            assert result['operational_context'] is None
            assert result['last_accepted_trade_date'] == '2026-09-30'
        result['legacy_strict_pit_context']['capability_permissions']['STOCK_CORE'] = True
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(read, range(200)))
    assert legacy['production_permission']['STOCK_CORE'] is False
