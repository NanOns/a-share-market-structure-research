"""R4.2.1 field boundary: TDX primary and CSRC auxiliary never share fields."""
from copy import deepcopy
from statistics import median

CONTRACT = 'V4_PRIMARY_SECTOR_TAXONOMY_V2'
PRIMARY = 'TDX_INDUSTRY_CONCEPT'
AUXILIARY = 'BAOSTOCK_CSRC_INDUSTRY'
PRIMARY_FIELDS = ('sector_rs1', 'sector_rs5', 'sector_rs20', 'breadth',
                  'ma20_width', 'base_seed_aggregate', 'b0', 'rotation_state',
                  'relative_sector_state', 'homepage_sector_rank', 'focus_mainline_sector')


def validate_primary_memberships(rows, day):
    for row in rows:
        kind = row.get('sector_type')
        if (kind not in ('INDUSTRY', 'THEME') or
                not row.get('sector_id', '').startswith(kind + ':') or
                row.get('taxonomy', PRIMARY) != PRIMARY):
            raise ValueError('PRIMARY_TAXONOMY_NAMESPACE_REJECTED')
        if (row.get('membership_asof_date') != day or
                row.get('membership_basis') != 'PIT_OBSERVED' or
                row.get('membership_quality') != 'PIT_OBSERVED_ACCEPTED' or
                not row.get('security_id') or not row.get('source_revision_id') or
                not row.get('source_file_digests') or
                not row.get('source_file', '').startswith('T0002/')):
            raise ValueError('NO_ACCEPTED_TDX_DATED_MEMBERSHIP')
        cutoff = row.get('cutoff')
        if not cutoff or any(not row.get(k) or row[k] > cutoff for k in
                             ('provider_available_at', 'system_available_at')):
            raise ValueError('TDX_MEMBERSHIP_AVAILABILITY_UNPROVEN')
    return rows


def primary_projection(day, memberships, producer, *, auxiliary=None):
    """Only validated TDX inputs reach the primary producer; auxiliary is ignored."""
    if not memberships:
        return {field: {'value': None, 'quality': 'UNKNOWN',
                        'reason': 'NO_ACCEPTED_TDX_DATED_MEMBERSHIP'}
                for field in PRIMARY_FIELDS}
    validate_primary_memberships(memberships, day)
    result = producer(deepcopy(memberships))
    def reject_auxiliary(value):
        if isinstance(value, dict):
            if value.get('taxonomy', PRIMARY) != PRIMARY:
                raise ValueError('PRIMARY_PRODUCER_TAXONOMY_REJECTED')
            for k, item in value.items():
                if k.startswith('csrc_'):
                    raise ValueError('AUXILIARY_FIELD_IN_PRIMARY_PRODUCER')
                reject_auxiliary(item)
        elif isinstance(value, list):
            for item in value:
                reject_auxiliary(item)
        elif isinstance(value, str) and value.startswith('BAO_CSRC:'):
            raise ValueError('PRIMARY_PRODUCER_NAMESPACE_REJECTED')
    reject_auxiliary(result)
    return {'contract_id': CONTRACT, 'taxonomy': PRIMARY, 'trade_date': day,
            'result': result}


def auxiliary_projection(value):
    """Recursively rename every auxiliary payload key, including nested kernels."""
    if isinstance(value, dict):
        return {('csrc_' + k if not k.startswith('csrc_') else k): auxiliary_projection(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [auxiliary_projection(v) for v in value]
    return value


def loo_medians(rows, returns, sid):
    sectors = sorted({r['sector_id'] for r in rows if r['security_id'] == sid})
    result = {}
    for sector in sectors:
        others = sorted({r['security_id'] for r in rows
                         if r['sector_id'] == sector and r['security_id'] != sid})
        values = [returns[s] for s in others if returns.get(s) is not None]
        result[sector] = {'non_target_count': len(others),
                          'observed_count': len(values),
                          'ret5_median': median(values) if values else None}
    return result
