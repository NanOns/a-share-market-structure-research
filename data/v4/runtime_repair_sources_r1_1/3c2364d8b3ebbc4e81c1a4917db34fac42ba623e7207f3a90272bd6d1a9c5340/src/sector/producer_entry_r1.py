"""SHA-bound SECTOR Producer entry, isolated from formal Owner admission.

The entry consumes original per-field receipts, never derives CONFIRMED/WARM
from Native labels. Missing publishers remain missing, independently by field.
"""
from pathlib import Path
import gzip
import hashlib
import json
from datetime import datetime, timezone

from .d2_admission_candidate_r4 import FIELDS, extract, instant

CONTRACT = 'SECTOR_PRODUCER_SOURCE_ENTRY_R1'


def read_bound(root, binding):
    root = Path(root).resolve()
    path = (root / binding['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('SOURCE_PATH_OUTSIDE_PROJECT_OR_MISSING')
    raw = path.read_bytes()
    if (hashlib.sha256(raw).hexdigest() != binding['sha256'] or
            len(raw) != binding['bytes']):
        raise ValueError('SOURCE_BYTES_BINDING_MISMATCH')
    if path.suffix == '.gz':
        raw = gzip.decompress(raw)
    return raw


def prepare_entry(root, native, *, source_binding, cutoff, publishers=None,
                  prior=None, prior_binding=None, sessions=None):
    """Read six independently bound Owner receipts for an isolated candidate.

    Publisher bindings prove bytes, not approval. Production/reducer activation
    requires an independently admitted frozen contract; this entry cannot do it.
    """
    raw = read_bound(root, source_binding)
    if instant(cutoff) > datetime.now(timezone.utc):
        raise ValueError('FUTURE_CUTOFF_REJECTED')
    originals = [json.loads(line) for line in raw.splitlines() if line.strip()]
    matches = [row for row in originals if row.get('sector_id') == native['sector_id']
               and row.get('trade_date') == native['trade_date']]
    if len(matches) != 1 or matches[0] != native:
        raise ValueError('NATIVE_OWNER_ROW_MISMATCH')
    if prior is not None:
        if prior_binding is None or json.loads(read_bound(root, prior_binding)) != prior:
            raise ValueError('EXACT_PRIOR_OWNER_BINDING_REQUIRED')
        if not prior.get('first_available') or instant(prior['first_available']) > instant(cutoff):
            raise ValueError('PRIOR_FIRST_AVAILABLE_REQUIRED_AT_CUTOFF')
    upstream, verdicts = {}, {}
    for field in FIELDS:
        binding = (publishers or {}).get(field)
        if binding is None:
            verdicts[field] = 'SOURCE_NOT_PRESENT'
            continue
        receipt = json.loads(read_bound(root, binding))
        required = {'entity_type', 'entity_id', 'field', 'member_ids',
                    'member_set_asof', 'AS_RECORDED', 'first_available'}
        if required - receipt.keys():
            raise ValueError('PRODUCER_ENTITY_AND_MEMBERSHIP_LINEAGE_REQUIRED')
        if (receipt['entity_type'] != 'SECTOR' or
                receipt['entity_id'] != native['sector_id'] or receipt['field'] != field):
            raise ValueError('PRODUCER_ENTITY_FIELD_MISMATCH')
        if receipt['AS_RECORDED'] is not True:
            verdicts[field] = 'NON_AS_RECORDED_RECEIPT'
            continue
        reference = prior if field in ('frozen_invalidation',
                                       'episode_invalidation_contract_id') else native
        if reference is None:
            verdicts[field] = 'EXACT_PRIOR_EPISODE_SOURCE_MISSING'
            continue
        members = receipt['member_ids']
        if (len(members) != len(set(members)) or
                sorted(members) != sorted(reference['member_ids']) or
                receipt['member_set_asof'] != reference['member_set_asof']):
            verdicts[field] = 'MEMBERSHIP_VERSION_OR_DENOMINATOR_MISMATCH'
            continue
        if instant(receipt['first_available']) > instant(cutoff):
            verdicts[field] = 'FIRST_AVAILABLE_AFTER_CUTOFF'
            continue
        if field == 'scenario' and receipt.get('value') not in (
                'BASE_BUILD', 'BREADTH_BUILD', 'RECOVERY_BUILD', 'BROADENING',
                'REACCELERATING', 'SUSTAINED', 'NONE'):
            verdicts[field] = 'SCENARIO_OUTSIDE_FROZEN_DOMAIN'
            continue
        if field == 'episode_invalidation_contract_id' and (
                receipt.get('episode_id') != prior.get('episode_id') or
                receipt.get('value') != prior.get('invalidation_contract_id') or
                receipt.get('invalidation_contract_sha256') !=
                prior.get('invalidation_contract_sha256')):
            verdicts[field] = 'CREATION_FROZEN_CONTRACT_MISMATCH'
            continue
        upstream[field] = dict(receipt, source_sha256=binding['sha256'])
        verdicts[field] = 'SOURCE_BYTES_VERIFIED_CANDIDATE_ONLY'
    result = extract(native, source_binding=source_binding, cutoff=cutoff,
                     upstream=upstream, prior=prior, sessions=sessions)
    for field, reason in verdicts.items():
        if field not in upstream:
            result['upstream'][field]['reason'] = reason
    result.update(entry_contract_id=CONTRACT, publisher_bindings=publishers or {},
                  prior_owner_binding=prior_binding,
                  source_verdicts=verdicts, production_authorized=False)
    return result
