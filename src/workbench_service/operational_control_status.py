"""V2 control plane: current read authority and legacy proof permissions are separate."""
from copy import deepcopy

CONTRACT = 'V4_CONTROL_STATUS_NAMESPACES_V2'


def control_status(legacy, operational=None, head_digest=None):
    old = deepcopy(legacy['context'])
    old['context_token'] = legacy['context_token']
    old['as_of'] = old['accepted_trade_date']
    old['capability_permissions'] = deepcopy(legacy['production_permission'])
    current = deepcopy(operational) if operational is not None else deepcopy(old)
    current['trade_date'] = current['accepted_trade_date']
    if operational is not None:
        current.update(last_accepted_trade_date=current['accepted_trade_date'],
                       data_head_digest=head_digest, source_revision=current['context_token'],
                       data_updated_at=current['membership_observed_at'],
                       stage='R43_SCOPED_OPERATIONAL', namespace='V4_OPERATIONAL_RESEARCH',
                       as_of=current['accepted_trade_date'],
                       capability_permissions=dict(research_read=True, historical_pit=False,
                                                   trading_execution=False, focus_write=False))
    current.update(strict_pit_legacy_trade_date=old['accepted_trade_date'],
                   legacy_strict_pit_date=old['accepted_trade_date'],
                   strict_pit_context_token=old['context_token'],
                   current_operational_trade_date=operational['accepted_trade_date'] if operational else None,
                   operational_accepted_trade_date=operational['accepted_trade_date'] if operational else None,
                   control_date_source=('USER_AUTHORIZED_OPERATIONAL_HEAD' if operational.get('authorization_mode') == 'DIRECT_HUMAN_USER'
                                        else 'INDEPENDENTLY_ACCEPTED_OPERATIONAL_HEAD') if operational else 'LEGACY_STRICT_PIT_HEAD')
    return dict(current, operational_context=deepcopy(current) if operational else None,
                legacy_strict_pit_context=old,
                production_permission=deepcopy(legacy['production_permission']),
                production_permission_scope='LEGACY_STRICT_PIT_PROOF_ONLY',
                field_migration=dict(contract=CONTRACT, top_level_metadata='CURRENT_READ_AUTHORITY',
                                     deprecated_fields=['production_permission'],
                                     replacement='legacy_strict_pit_context.capability_permissions; operational_context.capability_permissions'))
