"""Head-bound operational owner facts; archive JSON is migration evidence only."""
import json
from pathlib import Path
from pathlib import PurePosixPath
from .v4_native import connection,workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore,CONTRACT,digest,canonical

OWNER='V4_OPERATIONAL_OWNER_NATIVE_PG_CLOSEOUT_R1'
FOLDER='data/v4/operational_owner_pg_closeout_r1'


def read_schema(root,binding,descriptor,workspace_root=None):
    """Resolve an exact read-only predecessor origin for a G-drive candidate."""
    root=Path(root).resolve()
    expected=workspace_schema(Path(workspace_root or root)/FOLDER,'forward')
    if descriptor.get('schema')==expected or workspace_root is not None:return expected
    config=root/'config/r8_owner_read_origin_r1.json'
    if not config.is_file():return expected
    from workbench_analysis.r43_owner_replay import checked
    origin=json.loads(config.read_bytes())
    if (root.drive.upper()!='G:' or 'codex_tmp' not in root.parts
            or origin.get('contract_id')!='R8_ISOLATED_OWNER_READ_ORIGIN_R1'
            or origin.get('scope')!='READ_ONLY_ACCEPTED_PREDECESSOR'
            or Path(origin.get('candidate_root','')).resolve()!=root):
        raise ValueError('ISOLATED_OWNER_READ_ORIGIN_INVALID')
    source=Path(origin['source_workspace_root']).resolve()
    if source.drive.upper()!='G:' or source==root:raise ValueError('ISOLATED_OWNER_SOURCE_ROOT_INVALID')
    head=json.loads(checked(root,origin['source_head']).read_bytes())
    if head.get('contract_id')!='V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1':
        raise ValueError('ISOLATED_OWNER_SOURCE_HEAD_REQUIRED')
    authority=json.loads(checked(root,head['native_pg_owner_authority']).read_bytes())
    if (authority.get('contract_id')!='V4_HEAD_EMBEDDED_NATIVE_PG_OWNER_AUTHORITY_V2'
            or authority.get('source_owners')!=head.get('owners')):
        raise ValueError('ISOLATED_OWNER_SOURCE_AUTHORITY_MISMATCH')
    allowed=[entry['descriptor'] for domains in authority['owners'].values() for entry in domains.values()]
    source_schema=workspace_schema(source/FOLDER,'forward')
    if binding not in allowed or descriptor.get('schema')!=source_schema:
        raise ValueError('ISOLATED_OWNER_DESCRIPTOR_NOT_IN_ACCEPTED_PREDECESSOR')
    return source_schema

def prepare(root,head_token,day,domain,source_binding,rows):
    from workbench_analysis.r43_owner_replay import checked
    checked(root,source_binding)
    payload=dict(contract_id=OWNER,head_token=head_token,T0=day,domain=domain,
                 source_binding=source_binding,rows=rows,PIT_ELIGIBLE=False,AS_RECORDED=False)
    binding=ForwardFactStore(root,FOLDER).append(domain,head_token+'_'+day+'_'+domain,payload,migration_timeout_seconds=120)
    return inline_descriptor(root,binding)

def inline_descriptor(root,binding):
    """Attach the immutable PG locator during publication, for file-free readers."""
    from workbench_analysis.r43_owner_replay import checked
    path=checked(root,binding)
    raw=path.read_bytes()
    descriptor=json.loads(raw)
    if canonical(descriptor)!=raw:
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_CANONICAL_REQUIRED')
    if (descriptor.get('contract_id'),descriptor.get('engine'))!=(CONTRACT,'postgresql'):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_REQUIRED')
    if descriptor.get('payload_sha256') is None or descriptor.get('database_identity') is None:
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_IDENTITY_REQUIRED')
    return dict(binding,pg_descriptor=descriptor)

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
    if (descriptor.get('contract_id'),descriptor.get('engine'),descriptor.get('schema'),descriptor.get('kind'))!=(CONTRACT,'postgresql',schema,domain):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    validate_source_binding(source_binding)
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=descriptor.get('database_identity'):
            raise ValueError('PG_OPERATIONAL_OWNER_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s',
                       (domain,descriptor['fact_key'])).fetchone()
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
    if (descriptor.get('contract_id'),descriptor.get('engine'),descriptor.get('schema'),descriptor.get('kind'))!=(CONTRACT,'postgresql',schema,'authority_manifest'):
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_DESCRIPTOR_REQUIRED_NO_FILE_FALLBACK')
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=descriptor.get('database_identity'):
            raise ValueError('PG_OPERATIONAL_OWNER_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s',
                       ('authority_manifest',descriptor['fact_key'])).fetchone()
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
    from workbench_analysis.r43_owner_replay import checked
    if not isinstance(authority_binding,dict):
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_MIGRATION_BINDING_REQUIRED')
    if authority_binding.get('path')!='config/v4_operational_owner_pg_closeout_r1.json':
        raise ValueError('PG_OPERATIONAL_OWNER_AUTHORITY_MIGRATION_SOURCE_INVALID')
    authority=json.loads(checked(root,authority_binding).read_bytes())
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
    if (descriptor.get('contract_id'),descriptor.get('engine'),descriptor.get('schema'),descriptor.get('kind'))!=(CONTRACT,'postgresql',schema,domain):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    validate_source_binding(source_binding)
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=descriptor.get('database_identity'):
            raise ValueError('PG_OPERATIONAL_OWNER_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute("SELECT payload_sha256,encode(sha256(convert_to(payload,'UTF8')),'hex') FROM forward_facts WHERE kind=%s AND fact_key=%s",
                       (domain,descriptor['fact_key'])).fetchone()
    if row is None or row!=(descriptor['payload_sha256'],descriptor['payload_sha256']):
        raise ValueError('PG_OPERATIONAL_OWNER_PAYLOAD_DIGEST_MISMATCH')
