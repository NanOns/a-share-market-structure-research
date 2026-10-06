"""Real PostgreSQL negative inserts on frozen isolated canonical fixtures only."""
import copy
import json
import psycopg
from psycopg.types.json import Jsonb
import pytest
from scripts.full_chain_repair_io import ROOT

@pytest.fixture(params=[('fresh',55492),('upgrade',55493)])
def pg(request):
    kind,port=request.param
    pg=psycopg.connect(f'host=127.0.0.1 port={port} user=fep_e5_admin dbname=fep_e5b_{kind} connect_timeout=3')
    try:yield pg
    finally:pg.rollback();pg.close()

def insert(pg,row):
    pg.execute('INSERT INTO fep.observations SELECT * FROM jsonb_populate_record(NULL::fep.observations,%s)',(Jsonb(row),))

def example(pg):
    row=pg.execute("SELECT to_jsonb(o) FROM fep.observations o WHERE scope_id='FEP_STOCK_ENTRY_CORE' LIMIT 1").fetchone()[0]
    row.update(observation_id='REPAIR_DB_NEGATIVE',entity_id='REPAIR_DB_NEGATIVE',signal_key='FIRST_PREWATCH:REPAIR_DB_NEGATIVE')
    return row

def install(pg):pg.execute((ROOT/'src/workbench_db/migrations/v4_postgres/033_fep_signal_contract_integrity_v1.sql').read_text(encoding='utf8'))

def test_baseline_unknown_signal_accepted(pg):
    row=example(pg);row['core_signal_contract_id']='NONEXISTENT_CONTRACT'
    insert(pg,row)
    assert pg.execute("SELECT core_signal_contract_id FROM fep.observations WHERE observation_id='REPAIR_DB_NEGATIVE'").fetchone()[0]=='NONEXISTENT_CONTRACT'

@pytest.mark.parametrize('case',['unknown','target','reconstruction','scope','predicate','signal','family'])
def test_signal_db_reject(pg,case):
    install(pg);row=example(pg)
    if case=='unknown':row['core_signal_contract_id']='NONEXISTENT_CONTRACT'
    if case=='target':row['core_signal_contract_id']='FEP_E1_TARGETS_V1'
    if case=='reconstruction':row['core_signal_contract_id']='FEP_E5_HISTORICAL_RECONSTRUCTION_AUTHORITY_V1'
    if case=='scope':
        scope=pg.execute("SELECT to_jsonb(s) FROM fep.scopes s WHERE scope_id='FEP_STOCK_ENTRY_CORE'").fetchone()[0]
        scope.update(scope_id='REPAIR_OTHER_SCOPE',digest='b'*64)
        pg.execute('INSERT INTO fep.scopes SELECT * FROM jsonb_populate_record(NULL::fep.scopes,%s)',(Jsonb(scope),))
        row['scope_id']='REPAIR_OTHER_SCOPE'
    if case=='signal':row['signal_key']='DAILY_LANDMARK:REPAIR'
    if case in ('predicate','family'):
        body=pg.execute("SELECT body FROM fep.contracts WHERE contract_id='FEP_E2_ENTRY_EVENT_STRATA_V1_1'").fetchone()[0]
        if case=='predicate':body['predicate_digest']='0'*64
        # New existing contract cannot substitute for frozen FIRST_PREWATCH authority.
        pg.execute('INSERT INTO fep.contracts VALUES(%s,%s,%s,%s,%s,clock_timestamp())',('WRONG_EVENT_CONTRACT','TARGET' if case=='family' else 'WRONG_EVENT_CONTRACT','repair1',Jsonb(body),'a'*64))
        with pytest.raises(psycopg.Error):
            with pg.transaction():pg.execute("INSERT INTO fep.signal_contract_registry VALUES('WRONG_EVENT_CONTRACT','FEP_STOCK_ENTRY_CORE','FIRST_PREWATCH','FEP_E2_ENTRY_EVENT_STRATA_V1_1',%s,%s)",('a'*64,body['predicate_digest']))
        row['core_signal_contract_id']='WRONG_EVENT_CONTRACT'
    with pytest.raises(psycopg.Error,match='FEP_OBSERVATION_SIGNAL_AUTHORITY_MISMATCH|foreign key'):
        with pg.transaction():insert(pg,row)

def test_signal_registry_positive_and_immutable(pg):
    before=pg.execute('SELECT count(*) FROM fep.observations').fetchone()[0]
    install(pg);insert(pg,example(pg))
    assert pg.execute('SELECT count(*) FROM fep.observations').fetchone()[0]==before+1
    for op in ('UPDATE fep.signal_contract_registry SET signal_family=\'BAD\'','DELETE FROM fep.signal_contract_registry'):
        with pytest.raises(psycopg.Error,match='IMMUTABLE_SIGNAL_REGISTRY'):
            with pg.transaction():pg.execute(op)

def test_signal_registry_role_and_search_path(pg):
    install(pg)
    assert pg.execute("SELECT has_table_privilege('fep_application','fep.signal_contract_registry','SELECT'),has_table_privilege('fep_application','fep.signal_contract_registry','INSERT'),has_table_privilege('fep_application','fep.deployment_heads','UPDATE')").fetchone()==(True,False,False)
    for function in ('signal_registry_guard','observation_signal_guard','signal_registry_immutable'):
        owner,settings=pg.execute('SELECT pg_get_userbyid(proowner),proconfig FROM pg_proc WHERE oid=%s::regprocedure',('fep.'+function+'()',)).fetchone()
        assert owner=='fep_schema_owner' and 'search_path=pg_catalog, fep' in settings
