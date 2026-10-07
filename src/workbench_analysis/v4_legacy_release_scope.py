"""Historical V1 diagnostic binding alongside explicit current stage authority."""
import hashlib
import json
from pathlib import Path
from .v4_current_stage_authority import CurrentStageAuthority


def release_scope(root):
    root = Path(root).resolve()
    contract = json.loads((root / 'config/v4_legacy_release_scope_v1.json').read_bytes())
    if contract['role'] != 'HISTORICAL_V1_RELEASE_DIAGNOSTIC_ONLY':
        raise ValueError('LEGACY_RELEASE_SCOPE_REQUIRED')
    for key in ('historical_pointer', 'current_stage_contract'):
        reference = contract[key]
        raw = (root / reference['path']).read_bytes()
        if len(raw) != reference['bytes'] or hashlib.sha256(raw).hexdigest() != reference['sha256']:
            raise ValueError('LEGACY_RELEASE_SCOPE_BINDING_CHANGED:' + key)
    if any(contract.get(k) is not False for k in ('runtime_permission', 'production', 'shadow', 'focus', 'default_ui')):
        raise ValueError('LEGACY_RELEASE_SCOPE_PERMISSION_REJECTED')
    current = CurrentStageAuthority(root)
    return {'contract_id': contract['contract_id'], 'historical_role': contract['role'],
            'historical_pointer': contract['historical_pointer'],
            'current_head': current.current_head, 'current_stage_contract': contract['current_stage_contract'],
            'historical_replay_is_current_acceptance': False, 'runtime_permission': False}
