from pathlib import Path
import pytest,psycopg
from psycopg.types.json import Jsonb
from src.v4.confirmation_persistence import *
from scripts.v4_11_candidate_inputs_r1 import projection,positive_values
from scripts.v4_11_engineering_vectors_r1 import from_confirmation,event_vector
from src.v4.confirmation_d2_bridge import engineering_d2_publication

def test_retry_consumer_and_append_only(pg):
    x=projection(positive_values());r=publish(pg,x)
    assert publish(pg,x)==r
    assert pg.execute('SELECT count(*) FROM v4.confirmation_candidate_facts_r1').fetchone()[0]==1
    with pytest.raises(ConfirmationError,match='CONSUMER_IDENTITY_MISMATCH'):publish(pg,x,consumer_contract_id='OTHER')
    for table in ('confirmation_candidate_facts_r1','confirmation_candidate_publications_r1'):
        with pytest.raises(psycopg.Error,match='V4_11_CANDIDATE_APPEND_ONLY'):
            with pg.transaction():pg.execute('DELETE FROM v4.'+table)
    with pytest.raises(psycopg.Error):
        with pg.transaction():pg.execute('UPDATE v4.confirmation_candidate_publications_r1 SET accepted=true')

def test_event_publish_and_readback(pg):
    x=projection(positive_values());facts=detect_confirmation(x);old,new,frozen,events=event_vector('PREWATCH')
    d2=engineering_d2_publication([from_confirmation(facts['rows'][0],prior=old['rows'][0])])
    r=publish(pg,x,d2_publication=d2,prior_session_head=frozen)
    assert publish(pg,x,d2_publication=d2,prior_session_head=frozen)==r
    payload=pg.execute('SELECT payload FROM v4.confirmation_candidate_events_r1 WHERE publication_id=%s',(r['event_publication_id'],)).fetchone()[0]
    assert payload['primary_event']=='NEW_CONFIRMED' and payload['prior_session_state_head_digest']==frozen['head_digest']
    with pytest.raises(ConfirmationError,match='D0_D2_FACT_PUBLICATION_MISMATCH'):publish(pg,x,d2_publication=new,prior_session_head=frozen)

def test_atomic_failure(pg):
    x=projection(positive_values())
    pg.execute("CREATE FUNCTION pg_temp.reject_fact() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'INJECTED_FAIL'; END $$")
    pg.execute('CREATE TRIGGER fail_fact BEFORE INSERT ON v4.confirmation_candidate_facts_r1 FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_fact()')
    with pytest.raises(psycopg.Error,match='INJECTED_FAIL'):
        publish(pg,x)
    assert pg.execute('SELECT count(*) FROM v4.confirmation_candidate_publications_r1').fetchone()[0]==0

def test_migration_rollback(pg):
    root=Path(__file__).resolve().parents[2]
    with pg.transaction():
        pg.execute((root/'src/workbench_db/migrations/v4_postgres_rollbacks/026_confirmation_events_candidate_r1.sql').read_text())
        assert pg.execute("SELECT to_regclass('v4.confirmation_candidate_facts_r1')").fetchone()[0] is None
        pg.execute((root/'src/workbench_db/migrations/v4_postgres/026_confirmation_events_candidate_r1.sql').read_text())
        publish(pg,projection(positive_values()))

def test_direct_ordinary_writer_and_consumer_bypass_rejected(pg):
    x=projection(positive_values());facts=detect_confirmation(x)
    with pytest.raises(psycopg.Error,match='V4_11_CONTROLLED_PUBLISHER_ROLE_REQUIRED'):
        with pg.transaction():pg.execute('INSERT INTO v4.confirmation_candidate_publications_r1(publication_id,consumer_contract_id,producer_contract_id,parameter_set_id,payload,payload_digest) VALUES(%s,%s,%s,%s,%s,%s)',
            (facts['publication_id'],CONSUMER,'CONFIRMATION_DETECTOR_V1','V4_11_CONFIRMATION_PARAMETER_SET_V1',Jsonb(facts),digest(facts)))
    publish(pg,x)
    with pytest.raises(psycopg.Error):
        with pg.transaction():
            pg.execute('SET LOCAL ROLE v4_11_candidate_publisher_r1')
            pg.execute('INSERT INTO v4.confirmation_candidate_facts_r1 VALUES(%s,%s,%s,%s)',(facts['publication_id'],'OTHER','OTHER',Jsonb(facts['rows'][0])))

def test_incomplete_publication_cannot_commit(pg):
    x=projection(positive_values());facts=detect_confirmation(x)
    with pytest.raises(psycopg.Error,match='V4_11_PUBLICATION_INCOMPLETE'):
        with pg.transaction():
            pg.execute('SET LOCAL ROLE v4_11_candidate_publisher_r1')
            pg.execute('INSERT INTO v4.confirmation_candidate_publications_r1(publication_id,consumer_contract_id,producer_contract_id,parameter_set_id,payload,payload_digest) VALUES(%s,%s,%s,%s,%s,%s)',
                (facts['publication_id'],CONSUMER,'CONFIRMATION_DETECTOR_V1','V4_11_CONFIRMATION_PARAMETER_SET_V1',Jsonb(facts),digest(facts)))
            pg.execute('SET CONSTRAINTS v4.confirmation_candidate_fact_complete IMMEDIATE')
