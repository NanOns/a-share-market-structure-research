"""Explicit D2-to-Focus vocabulary bridge; frozen historical kernels stay unchanged."""
from copy import deepcopy

CONTRACT = 'D2_FOCUS_VALIDITY_BRIDGE_R2'


def normalized_days(days):
    result = deepcopy(days)
    for day, records in result.items():
        if len({r['entity_id'] for r in records}) != len(records):
            raise ValueError('FOCUS_DUPLICATE_ENTITY')
        for row in records:
            if row['trade_date'] != day:
                raise ValueError('FOCUS_DATE_MIX')
            if row.get('validity') == 'INVALIDATED':
                row['source_d2_validity'] = 'INVALIDATED'
                row['validity'] = 'INVALID'
                # An invalidated D2 observation cannot start or re-enter Focus.
                row['raw_qualification'] = dict(row['raw_qualification'], PREWATCH='FALSE', CONFIRMED='FALSE')
    return result


def project(days):
    from .v4_successor import project as frozen_project
    result = frozen_project(normalized_days(days))
    result['validity_bridge_contract_id'] = CONTRACT
    return result


def enriched_project(days, paths):
    from .v4_native_core_adapter import enriched_project as frozen_project
    result = frozen_project(normalized_days(days), paths)
    result['validity_bridge_contract_id'] = CONTRACT
    result['focus_write_authorized'] = False
    return result
