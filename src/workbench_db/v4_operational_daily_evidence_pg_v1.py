"""Head-bound PG evidence documents used to admit daily successor candidates."""
import json
from pathlib import Path

from .v4_forward_pg_r1 import canonical, digest
from .v4_operational_owner_pg_closeout import (
    prepare as append_owner_fact,
    read as read_owner_fact,
)
from workbench_analysis.r43_owner_replay import checked

KEY = 'native_daily_evidence'
CONTRACT = 'V4_OPERATIONAL_DAILY_EVIDENCE_PG_R1'
DOMAIN = 'daily_evidence'
DOCUMENTS = ('day_receipt', 'numeric_core_oracle', 'sector_oracle', 'source_freeze',
             'period_numeric_oracle')


def _fact_token(day, name, source_binding):
    return digest(canonical(dict(contract_id=CONTRACT, T0=day, document=name,
        source_binding=source_binding)))


def prepare(root, candidate):
    """Copy exact daily QA evidence into immutable PG facts for a successor Head."""
    root = Path(root).resolve()
    day = candidate['accepted_trade_date']
    if KEY in candidate:
        for name in DOCUMENTS:
            read(root, candidate, name)
        return dict(contract_id=CONTRACT, T0=day, documents=list(DOCUMENTS), reused=True,
            publication=False)
    receipt_binding = candidate['day_receipt']
    receipt = json.loads(checked(root, receipt_binding).read_bytes())
    if (receipt.get('target_session') != day or receipt.get('acceptance') != 'DERIVED_READY'
            or receipt.get('owners') != candidate.get('owners')):
        raise ValueError('DAILY_EVIDENCE_RECEIPT_IDENTITY_MISMATCH')
    sources = {
        'day_receipt': receipt_binding,
        'numeric_core_oracle': receipt['numeric_core_oracle'],
        'sector_oracle': receipt['sector_oracle'],
        'source_freeze': receipt['source_freeze'],
        'period_numeric_oracle': candidate['period_numeric_oracle'],
    }
    entries = {}
    for name in DOCUMENTS:
        source_binding = sources[name]
        value = receipt if name == 'day_receipt' else json.loads(checked(root, source_binding).read_bytes())
        fact_key = _fact_token(day, name, source_binding)
        descriptor = append_owner_fact(root, fact_key, day, DOMAIN, source_binding, [value])
        if read_owner_fact(root, descriptor, fact_key, day, DOMAIN, source_binding) != [value]:
            raise ValueError('DAILY_EVIDENCE_PG_PAYLOAD_DIFFERENCE:'+name)
        entries[name] = dict(source_binding=source_binding, descriptor=descriptor,
            fact_token=_fact_token(day, name, source_binding))
    candidate[KEY] = dict(contract_id=CONTRACT, T0=day, entries=entries)
    candidate['day_receipt'] = entries['day_receipt']['descriptor']
    candidate['period_numeric_oracle'] = entries['period_numeric_oracle']['descriptor']
    return dict(contract_id=CONTRACT, T0=day, documents=list(DOCUMENTS), publication=False)


def read(root, candidate, name, *, source_binding=None, workspace_root=None):
    """Read one exact QA document; PG mode never opens its source artifact."""
    authority = candidate.get(KEY)
    if (not isinstance(authority, dict) or authority.get('contract_id') != CONTRACT
            or authority.get('T0') != candidate.get('accepted_trade_date')):
        raise ValueError('DAILY_EVIDENCE_PG_AUTHORITY_REQUIRED_NO_FALLBACK')
    if name not in DOCUMENTS:
        raise ValueError('DAILY_EVIDENCE_DOCUMENT_NOT_REGISTERED')
    entry = authority.get('entries', {}).get(name)
    if not isinstance(entry, dict):
        raise ValueError('DAILY_EVIDENCE_PG_DOCUMENT_REQUIRED')
    binding = entry.get('source_binding')
    if source_binding is not None and source_binding != binding:
        raise ValueError('DAILY_EVIDENCE_SOURCE_BINDING_MISMATCH')
    if entry.get('fact_token') != _fact_token(authority['T0'], name, binding):
        raise ValueError('DAILY_EVIDENCE_FACT_TOKEN_MISMATCH')
    if name in ('day_receipt', 'period_numeric_oracle') and candidate.get(name) != entry.get('descriptor'):
        raise ValueError('DAILY_EVIDENCE_HEAD_DESCRIPTOR_MISMATCH')
    content = read_owner_fact(root, entry['descriptor'], entry['fact_token'], authority['T0'],
        DOMAIN, binding, workspace_root=workspace_root)
    if not isinstance(content, list) or len(content) != 1:
        raise ValueError('DAILY_EVIDENCE_PG_PAYLOAD_SHAPE_INVALID')
    return content[0]
