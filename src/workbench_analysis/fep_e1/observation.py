"""FEP_OBSERVATION_V1: logical event identity, independent of UI/revision."""
from .contracts import digest, instant


def build(scope, *, entity_id, trade_date, signal_key, episode_key, slot_deadline,
          core_signal_contract_id):
    if scope['status'] != 'ENGINEERING_ENABLED' or scope['scope_id'] != 'FEP_STOCK_ENTRY_CORE':
        raise ValueError('FEP_SCOPE_NOT_ENABLED')
    if not all((entity_id, trade_date, signal_key, core_signal_contract_id)):
        raise ValueError('FEP_OBSERVATION_IDENTITY_REQUIRED')
    instant(slot_deadline)
    row = dict(scope_id=scope['scope_id'], entity_id=entity_id, trade_date=trade_date,
               signal_key=signal_key, episode_key=episode_key, slot_deadline=slot_deadline,
               core_signal_contract_id=core_signal_contract_id)
    row['observation_id'] = digest([row[k] for k in ('scope_id', 'entity_id', 'trade_date', 'signal_key')])
    return row
