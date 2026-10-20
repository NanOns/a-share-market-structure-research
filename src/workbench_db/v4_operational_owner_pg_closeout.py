"""Head-bound operational owner facts; archive JSON is migration evidence only."""
import json
import re
from pathlib import Path
from pathlib import PurePosixPath
from .v4_native import connection
from .v4_forward_pg_r1 import ForwardFactStore,CONTRACT,digest,canonical,resolve_migrated_legacy_fact

OWNER='V4_OPERATIONAL_OWNER_NATIVE_PG_CLOSEOUT_R1'
FOLDER='data/v4/operational_owner_pg_closeout_r1'


def read_schema(root,binding,descriptor,workspace_root=None):
    """Resolve the PG namespace from the Head-bound inline locator.

    The descriptor is covered by the immutable Head binding and checked by
    ``descriptor_metadata`` before this function is called. Resolving its
    schema from a workspace path or an origin/Head JSON file would make a
    legitimate workspace move change the database identity and would put
    file reads back on the runtime consumer path.
    """
    if (not isinstance(binding,dict) or not isinstance(descriptor,dict)
            or binding.get('pg_descriptor')!=descriptor):
        raise ValueError('PG_OPERATIONAL_OWNER_INLINE_DESCRIPTOR_REQUIRED_NO_FILE_FALLBACK')
    schema=descriptor.get('schema')
    if not isinstance(schema,str) or (schema!='v4' and not re.fullmatch(r'v4_(?:forward|r8_forward)_[a-f0-9]{16}',schema)):
        raise ValueError('INVALID_V4_PG_SCHEMA')
    return schema

def prepare(root,head_token,day,domain,source_binding,rows):
    from .v4_historical_source_ingress_pg_r1 import read_bound
    source=read_bound(root,source_binding['path'],source_binding['sha256'])
    if len(source['raw'])!=source_binding.get('bytes'):
        raise ValueError('PG_OPERATIONAL_OWNER_SOURCE_SIZE_MISMATCH')
    payload=dict(contract_id=OWNER,head_token=head_token,T0=day,domain=domain,
                 source_binding=source_binding,rows=rows,PIT_ELIGIBLE=False,AS_RECORDED=False)
    binding=ForwardFactStore(root,FOLDER).append(domain,head_token+'_'+day+'_'+domain,payload,migration_timeout_seconds=120)
    return inline_descriptor(root,binding)

def inline_descriptor(root,binding):
    """Bind the PG-returned descriptor inline without opening a local file."""
    descriptor=binding.get('pg_descriptor') if isinstance(binding,dict) else None
    if not isinstance(descriptor,dict):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_INLINE_REQUIRED_NO_FILE_FALLBACK')
    raw=canonical(descriptor)
    if digest(raw)!=binding.get('sha256') or len(raw)!=binding.get('bytes'):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_CANONICAL_REQUIRED')
    if (descriptor.get('contract_id'),descriptor.get('engine'))!=(CONTRACT,'postgresql'):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_REQUIRED')
    if descriptor.get('payload_sha256') is None or descriptor.get('database_identity') is None:
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_IDENTITY_REQUIRED')
    return dict(binding)

def append_authority_manifest(root,authority):
    """Store business authority in PG and return its Head-embeddable locator."""
    manifest_key=digest(canonical(authority))
    binding=ForwardFactStore(root,FOLDER).append('authority_manifest',manifest_key,authority)
    return inline_descriptor(root,binding)

def descriptor_metadata(root,binding):
    """Validate a publisher-supplied PG locator without opening business files."""
    descriptor=binding.get('pg_descriptor') if isinstance(binding,dict) else None
    if not isinstance(descriptor,dict):
        raise ValueError('PG_OPERATIONAL_OWNER_INLINE_DESCRIPTOR_REQUIRED_NO_FILE_FALLBACK')
    raw=canonical(descriptor)
    if digest(raw)!=binding.get('sha256') or len(raw)!=binding.get('bytes'):
        raise ValueError('PG_OPERATIONAL_OWNER_INLINE_DESCRIPTOR_DIGEST_MISMATCH')
    kind=descriptor.get('kind');fact_key=descriptor.get('fact_key')
    if not isinstance(kind,str) or not isinstance(fact_key,str):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_IDENTITY_REQUIRED')
    expected=(Path(FOLDER)/kind/(digest(fact_key.encode())+'.pg.json')).as_posix()
    if binding.get('path')!=expected:
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_PATH_MISMATCH')
    return descriptor

def validate_source_binding(source_binding):
    """Validate the stored source identity without reading the source artifact."""
    if not isinstance(source_binding,dict) or set(source_binding)!={'path','sha256','bytes'}:
        raise ValueError('PG_OPERATIONAL_OWNER_SOURCE_BINDING_REQUIRED')
    path=source_binding.get('path');sha=source_binding.get('sha256');size=source_binding.get('bytes')
    if (not isinstance(path,str) or not path or PurePosixPath(path).is_absolute()
            or '..' in PurePosixPath(path).parts or not isinstance(sha,str) or len(sha)!=64
            or any(c not in '0123456789abcdef' for c in sha) or type(size) is not int or size<0):
        raise ValueError('PG_OPERATIONAL_OWNER_SOURCE_BINDING_REQUIRED')
    return source_binding

def read(root,binding,head_token,day,domain,source_binding,*,workspace_root=None):
    descriptor=descriptor_metadata(root,binding)
    schema=read_schema(root,binding,descriptor,workspace_root)
    if (descriptor.get('contract_id'),descriptor.get('engine'),descriptor.get('kind'))!=(CONTRACT,'postgresql',domain):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    namespace=descriptor.get('workspace_namespace')
    if schema!='v4':namespace=resolve_migrated_legacy_fact(schema,domain,descriptor['fact_key'],descriptor['payload_sha256'])
    elif namespace is None:raise ValueError('PG_OPERATIONAL_OWNER_NAMESPACE_REQUIRED')
    validate_source_binding(source_binding)
    with connection('v4',read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=descriptor.get('database_identity'):
            raise ValueError('PG_OPERATIONAL_OWNER_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s',
                       (namespace,domain,descriptor['fact_key'])).fetchone()
    if row is None or row[1]!=descriptor['payload_sha256'] or digest(row[0].encode())!=row[1]:
        raise ValueError('PG_OPERATIONAL_OWNER_PAYLOAD_DIGEST_MISMATCH')
    payload=json.loads(row[0])
    if (payload.get('contract_id'),payload.get('head_token'),payload.get('T0'),payload.get('domain'),payload.get('source_binding'))!=(OWNER,head_token,day,domain,source_binding):
        raise ValueError('PG_OPERATIONAL_OWNER_CONTEXT_MISMATCH')
    if payload.get('PIT_ELIGIBLE') is not False or payload.get('AS_RECORDED') is not False:
        raise ValueError('PG_OPERATIONAL_OWNER_PIT_ESCALATION')
    return payload['rows']

def read_authority_manifest(root,binding,*,workspace_root=None):
    """Read the authority value from PG; the inline descriptor is only a locator."""
    descriptor=descriptor_metadata(root,binding)
    schema=read_schema(root,binding,descriptor,workspace_root)
    if (descriptor.get('contract_id'),descriptor.get('engine'),descriptor.get('kind'))!=(CONTRACT,'postgresql','authority_manifest'):
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_DESCRIPTOR_REQUIRED_NO_FILE_FALLBACK')
    namespace=descriptor.get('workspace_namespace')
    if schema!='v4':namespace=resolve_migrated_legacy_fact(schema,'authority_manifest',descriptor['fact_key'],descriptor['payload_sha256'])
    elif namespace is None:raise ValueError('PG_OPERATIONAL_OWNER_NAMESPACE_REQUIRED')
    with connection('v4',read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=descriptor.get('database_identity'):
            raise ValueError('PG_OPERATIONAL_OWNER_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s',
                       (namespace,'authority_manifest',descriptor['fact_key'])).fetchone()
    if row is None or row[1]!=descriptor.get('payload_sha256') or digest(row[0].encode())!=row[1]:
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_PAYLOAD_DIGEST_MISMATCH')
    try:
        payload=json.loads(row[0])
    except (TypeError,ValueError) as exc:
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_PAYLOAD_INVALID') from exc
    if not isinstance(payload,dict):
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_PAYLOAD_INVALID')
    return payload

def load_authority(root,candidate,head_token,*,authority_binding=None):
    if not isinstance(authority_binding,dict):
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_MIGRATION_BINDING_REQUIRED')
    if authority_binding.get('path')!='config/v4_operational_owner_pg_closeout_r1.json':
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_MIGRATION_SOURCE_INVALID')
    # The binding identifies the one-time historical source ingress. Resolve
    # its bytes from the shared PG fact store; after ingress the workspace file
    # is never an authority or a runtime fallback.
    from .v4_historical_source_ingress_pg_r1 import read_bound
    source=read_bound(root,authority_binding['path'],authority_binding['sha256'])
    if len(source['raw'])!=authority_binding['bytes']:
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_SOURCE_SIZE_MISMATCH')
    authority=json.loads(source['raw'])
    if authority.get('contract_id')!=OWNER or authority.get('head_token')!=head_token:
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_HEAD_MISMATCH')
    if any(authority.get(name) is not False for name in ('historical_PIT_permission','PIT_ELIGIBLE','AS_RECORDED')):
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_PIT_ESCALATION')
    if authority.get('source_owners')!=candidate['owners']:
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_SOURCE_MISMATCH')
    if set(authority['owners'])!=set(candidate['owners']):
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_DATES_INCOMPLETE')
    for day,owners in candidate['owners'].items():
        if set(authority['owners'][day])!=set(owners):raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_DOMAINS_INCOMPLETE')
        for binding in authority['owners'][day].values():descriptor_metadata(root,binding)
    return authority

def attest_cached(root,binding,domain,source_binding,*,workspace_root=None):
    """Rehash live PG bytes before reusing a previously fully verified owner."""
    descriptor=descriptor_metadata(root,binding)
    schema=read_schema(root,binding,descriptor,workspace_root)
    if (descriptor.get('contract_id'),descriptor.get('engine'),descriptor.get('kind'))!=(CONTRACT,'postgresql',domain):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    namespace=descriptor.get('workspace_namespace')
    if schema!='v4':namespace=resolve_migrated_legacy_fact(schema,domain,descriptor['fact_key'],descriptor['payload_sha256'])
    elif namespace is None:raise ValueError('PG_OPERATIONAL_OWNER_NAMESPACE_REQUIRED')
    validate_source_binding(source_binding)
    with connection('v4',read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=descriptor.get('database_identity'):
            raise ValueError('PG_OPERATIONAL_OWNER_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute("SELECT payload_sha256,encode(sha256(convert_to(payload,'UTF8')),'hex') FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s",
                       (namespace,domain,descriptor['fact_key'])).fetchone()
    if row is None or row!=(descriptor['payload_sha256'],descriptor['payload_sha256']):
        raise ValueError('PG_OPERATIONAL_OWNER_PAYLOAD_DIGEST_MISMATCH')
