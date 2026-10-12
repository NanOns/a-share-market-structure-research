"""Versioned, explicitly isolated native PG projection and Joint Head publication.

This contract grants no production permission or historical PIT qualification.
It uses the normal producer, content validator, CAS, rollback and HTTP consumer.
"""
import copy
import json
from pathlib import Path
import psycopg
from workbench_db.v4_native import configured_dsn
from .current_v4_context import canonical, digest, SourceInvalid
from .joint_release import AUTHORITY, activate, validate
from .production_v4 import build_snapshot, ProductionV4ResearchReader
from .v4_daily_refresh import atomic_bytes

CONTRACT='V4_ENGINEERING_NATIVE_PG_PUBLICATION_R3'
ADMISSION='config/v4_engineering_pg_publication_r3.json'

def attest(root):
    root=Path(root).resolve()
    allowed=Path('G:/codex_tmp').resolve()
    if not root.is_relative_to(allowed) or root==allowed:
        raise SourceInvalid('ENGINEERING_DISPOSABLE_G_ROOT_REQUIRED')
    record=json.loads((root/ADMISSION).read_bytes())
    if record.get('contract_id')!=CONTRACT or record.get('scope')!='ENGINEERING_ONLY' or record.get('production_permission') is not False:
        raise SourceInvalid('ENGINEERING_ADMISSION_REQUIRED')
    if Path(record['workspace_root']).resolve()!=root:
        raise SourceInvalid('ENGINEERING_WORKSPACE_IDENTITY_MISMATCH')
    with psycopg.connect(configured_dsn(),connect_timeout=5) as pg:
        pg.execute('SET TRANSACTION READ ONLY')
        identity=pg.execute("SELECT current_database(),(pg_control_system()).system_identifier,current_setting('data_directory')").fetchone()
    directory=Path(identity[2]).resolve()
    if not directory.is_relative_to(allowed) or directory!=Path(record['pg_data_directory']).resolve() or str(identity[1])!=str(record['pg_system_identifier']) or identity[0]!=record['pg_database']:
        raise SourceInvalid('ENGINEERING_PG_IDENTITY_MISMATCH')
    return record

def publish(root, *, health):
    """health must call normal HTTP routes; no alternate reader is injected."""
    root=Path(root).resolve();admission=attest(root)
    before=(root/AUTHORITY).read_bytes();previous=json.loads(before)
    if previous.get('trading') is not False:
        raise SourceInvalid('ENGINEERING_TRADING_AUTHORITY_FORBIDDEN')
    staged=build_snapshot(root,publish=False)
    reader=ProductionV4ResearchReader(root,snapshot_authority=staged['pointer'])
    candidate=copy.deepcopy(previous)
    candidate.update(contract_id='V4_JOINT_RELEASE_V2_PG_CONTENT',snapshot=staged['pointer'],trade_date=reader.manifest['context']['accepted_trade_date'])
    # The builder consumes current versioned authorities, which may differ
    # from the historical Joint Head. Bind every required Owner to the exact
    # staged source, never copy stale owners or discard validation requirements.
    features=reader.manifest['domain_features'];sources=reader.manifest['sources']
    owners=copy.deepcopy(previous['daily_owner_authorities'])
    for name in ('market','sector','stocks','market_center','forward'):
        owners[name]['trade_date']=candidate['trade_date']
        owners[name]['input_data_head']=dict(path='data/v4/V4_DATA_ACCEPTED_HEAD.json',sha256=reader.manifest['context']['data_head_digest'])
    for name,keys in {'sector':('native','factors','profiles'),'stocks':('series','factors','profiles')}.items():
        for key in keys:owners[name][key]=copy.deepcopy(features[name][key])
    for name,key,source in (('market','market','market_operational'),('market_center','publication','market_center'),('forward','publication','forward_operational')):
        owners[name][key]=copy.deepcopy(sources[source])
    candidate['daily_owner_authorities']=owners
    # Avoid introducing production scope flags: the candidate preserves the
    # exact existing bounded owner and UI contracts and adds explicit provenance.
    candidate['engineering_execution']=dict(contract_id=CONTRACT,scope='ENGINEERING_ONLY',production_permission=False,admission_sha256=digest(canonical(admission)))
    validate(root,candidate)
    receipt=activate(root,candidate,digest(before),health)
    result=dict(contract_id=CONTRACT,status='ENGINEERING_PUBLISHED',staged=staged,publication=receipt,production_permission=False,previous_authority_sha256=digest(before),new_authority_sha256=digest((root/AUTHORITY).read_bytes()))
    atomic_bytes(root/'runtime/engineering_pg_publication_r3/RESULT.json',canonical(result)+b'\n')
    return result
