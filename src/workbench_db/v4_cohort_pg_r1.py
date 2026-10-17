"""Exact PG cohort Owner transport; admission remains in the original read gate."""
import json
from pathlib import Path
from .v4_native import connection, workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore, CONTRACT, digest

COHORT_KIND = 'validation_cohort'

def prepare_owner(root, *, accepted_head, owner_binding, trade_date, folder='data/v4/cohort_pg'):
    """Validate the existing grant/source before writing an isolated PG candidate.

    Returns a descriptor, never changes a Head or creates a replacement grant.
    """
    from workbench_analysis.validation_cohort_read_contract_r3 import read_authorized_statistics
    from workbench_analysis.r43_owner_replay import checked
    source_owner = _load_source_owner(root, owner_binding)
    read_authorized_statistics(root, accepted_head=accepted_head, owner_binding=owner_binding,
                               trade_date=trade_date, owner_reader=lambda binding: source_owner)
    owner = source_owner
    store = ForwardFactStore(root, folder)
    key = trade_date + ':' + digest(json.dumps(owner, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
    return store.append(COHORT_KIND, key, owner)

def _load_source_owner(root, binding):
    """One-time producer ingress; runtime consumers must use ``load_owner``."""
    from workbench_analysis.r43_owner_replay import checked
    path=checked(root,binding)
    document=json.loads(path.read_bytes())
    if document.get('contract_id')!='VALIDATION_COHORT_READ_R3_V2':
        raise ValueError('COHORT_SOURCE_OWNER_CONTRACT_MISMATCH')
    return document

def load_owner(root, binding):
    """Read a Head-bound PG Owner only; source JSON is never a runtime fallback."""
    from workbench_analysis.r43_owner_replay import checked_pg as checked
    root = Path(root).resolve()
    path = checked(root, binding)
    document = json.loads(path.read_bytes())
    if document.get('contract_id') != CONTRACT:
        raise ValueError('COHORT_PG_DESCRIPTOR_REQUIRED_NO_FILE_FALLBACK')
    folder = path.parent.parent
    expected_schema = workspace_schema(folder, 'forward')
    if document.get('engine') != 'postgresql' or document.get('schema') != expected_schema or document.get('kind') != COHORT_KIND:
        raise ValueError('COHORT_PG_DESCRIPTOR_IDENTITY_MISMATCH')
    with connection(expected_schema, read_only=True) as pg:
        if ForwardFactStore._database_identity(pg) != document.get('database_identity'):
            raise ValueError('COHORT_PG_DATABASE_IDENTITY_MISMATCH')
        row = pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s', (COHORT_KIND, document['fact_key'])).fetchone()
    if row is None or row[1] != document['payload_sha256'] or digest(row[0].encode()) != row[1]:
        raise ValueError('COHORT_PG_PAYLOAD_DIGEST_MISMATCH')
    owner = json.loads(row[0])
    if owner.get('contract_id') != 'VALIDATION_COHORT_READ_R3_V2':
        raise ValueError('COHORT_PG_OWNER_CONTRACT_MISMATCH')
    return owner
