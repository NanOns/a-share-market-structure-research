"""V4_08_B2_SEMANTIC_MAPPING_R5_1, exact legacy validity or UNKNOWN.

phase2.prepare.valid_member needs identity, missing_state and activity facts.
PIT formal membership and finite ret1 alone do not reproduce those facts.
Only accepted exact valid_member observations can feed phase2.validity.
"""
from sector.phase2 import validity, VERSION
from sector.roles import sector_role
from workbench_service.semantic import resolve_semantics, UNKNOWN_TAG

CONTRACT_ID = 'V4_08_B2_SEMANTIC_MAPPING_R5_1'


def bind_semantic(memberships, current, target):
    result = {}
    for row in memberships:
        sid = row['sector_id']
        record = {k: row[k] for k in ('sector_id', 'sector_type', 'sector_name', 'semantic_bucket', 'sector_role') if k in row}
        previous = result.setdefault(sid, dict(record=record, members=set()))
        if previous['record'] != record:
            raise ValueError('SECTOR_METADATA_CONFLICT')
        previous['members'].add(row['security_id'])
    output = {}
    for sid, entry in result.items():
        record = entry['record']
        role = record.get('sector_role') or sector_role({'INDUSTRY':'industry','THEME':'concept','STYLE':'style'}.get(record['sector_type'], ''), record.get('sector_name', ''))
        valid = []
        for member in entry['members']:
            row = current.get(member, {})
            observation = row.get('legacy_valid_member', {})
            if row.get('trade_date') != target or observation.get('quality') != 'ACCEPTED' or observation.get('producer_contract') != VERSION or not isinstance(observation.get('value'), bool):
                valid = None
                break
            valid.append(observation['value'])
        # EXCLUDED_ROLE independently proves legacy sector_valid false;
        # otherwise absence of exact producer inputs must remain UNKNOWN.
        sector_valid = False if role == 'EXCLUDE_FROM_THEME_RANK' else validity(len(entry['members']), sum(valid), role)[0] if valid is not None else None
        output[sid] = dict(**record, sector_valid=sector_valid, mapping_contract_id=CONTRACT_ID,
                           validity_producer=VERSION, validity_reason='EXACT_VALID_MEMBER_RULE' if valid is not None else 'LEGACY_VALID_MEMBER_PROVENANCE_UNAVAILABLE')
    return output


def eligibility(record):
    if not record or not record.get('sector_name') or record.get('sector_valid') is None:
        return None
    resolved = resolve_semantics(record)
    # Legacy maps reviewed-unknown tags to exclusion. Preserve that exact
    # known result; missing accepted provenance is handled above as UNKNOWN.
    return resolved['normal_rank_eligible']
