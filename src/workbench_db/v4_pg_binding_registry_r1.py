"""Append-only PG index for immutable versioned Owner locators."""
from pathlib import Path
import json

from .v4_forward_pg_r1 import ForwardFactStore, canonical, digest
from .v4_native import connection, workspace_schema

FOLDER = 'data/v4/operational_authority_registry_pg_r1'
KIND = 'owner_binding_registry'
CONTRACT = 'V4_OPERATIONAL_OWNER_BINDING_REGISTRY_R1'


def _key(owner_kind, token, day):
    return digest(canonical(dict(contract_id=CONTRACT, owner_kind=owner_kind,
        token=token, T0=day)))


def put(root, owner_kind, token, day, binding):
    """Persist one exact owner locator and read it back before returning."""
    store = ForwardFactStore(Path(root).resolve(), FOLDER)
    key = _key(owner_kind, token, day)
    payload = dict(contract_id=CONTRACT, owner_kind=owner_kind,
        token=token, T0=day, binding=binding)
    descriptor = store.append(KIND, key, payload)
    if store.read(descriptor) != payload:
        raise ValueError('OPERATIONAL_OWNER_BINDING_REGISTRY_READBACK_MISMATCH')
    return descriptor


def get(root, owner_kind, token, day):
    """Resolve a locator from the shared PG fact store; no file fallback."""
    root = Path(root).resolve()
    folder = root / FOLDER
    schema = workspace_schema(folder, 'forward')
    workspace_namespace=ForwardFactStore.namespace_for(folder)
    fact_key = _key(owner_kind, token, day)
    with connection(schema, read_only=True) as pg:
        row = pg.execute(
            'SELECT payload,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s',
            (workspace_namespace,KIND, fact_key),
        ).fetchone()
    if row is None:
        raise ValueError('OPERATIONAL_OWNER_BINDING_REGISTRY_NOT_FOUND')
    raw = row[0].encode('utf-8')
    if digest(raw) != row[1]:
        raise ValueError('OPERATIONAL_OWNER_BINDING_REGISTRY_DIGEST_MISMATCH')
    payload = json.loads(raw)
    if (not isinstance(payload, dict) or payload.get('contract_id') != CONTRACT
            or (payload.get('owner_kind'), payload.get('token'), payload.get('T0'))
            != (owner_kind, token, day) or not isinstance(payload.get('binding'), dict)):
        raise ValueError('OPERATIONAL_OWNER_BINDING_REGISTRY_CONTEXT_INVALID')
    return payload['binding']
