"""Head-bound operational owner facts; archive JSON is migration evidence only."""
import json
from pathlib import Path
from .v4_native import connection,workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore,CONTRACT,digest

OWNER='V4_OPERATIONAL_OWNER_NATIVE_PG_CLOSEOUT_R1'
FOLDER='data/v4/operational_owner_pg_closeout_r1'

def prepare(root,head_token,day,domain,source_binding,rows):
    from workbench_analysis.r43_owner_replay import checked
    checked(root,source_binding)
    payload=dict(contract_id=OWNER,head_token=head_token,T0=day,domain=domain,
                 source_binding=source_binding,rows=rows,PIT_ELIGIBLE=False,AS_RECORDED=False)
    return ForwardFactStore(root,FOLDER).append(domain,head_token+'_'+day+'_'+domain,payload,migration_timeout_seconds=120)

def read(root,binding,head_token,day,domain,source_binding):
    from workbench_analysis.r43_owner_replay import checked
    path=checked(root,binding);descriptor=json.loads(path.read_bytes())
    schema=workspace_schema(Path(root)/FOLDER,'forward')
    if (descriptor.get('contract_id'),descriptor.get('engine'),descriptor.get('schema'),descriptor.get('kind'))!=(CONTRACT,'postgresql',schema,domain):
        raise ValueError('PG_OPERATIONAL_OWNER_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    checked(root,source_binding)
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

def load_authority(root,candidate,head_token):
    from workbench_analysis.r43_owner_replay import checked
    path=Path(root)/'config/v4_operational_owner_pg_closeout_r1.json'
    if not path.exists():return None
    authority=json.loads(path.read_bytes())
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
        for binding in authority['owners'][day].values():checked(root,binding)
    return authority
