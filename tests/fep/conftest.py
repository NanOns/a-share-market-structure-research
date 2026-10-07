"""Opt-in real PostgreSQL fixtures; every test rolls back its isolated state."""
import os
import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
import pytest
import psycopg
from psycopg.types.json import Jsonb
from tests.v4_phase0.test_postgres_schema import add_namespace, add_publication
from workbench_analysis.fep_e1.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
SCOPE = 'FEP_STOCK_ENTRY_CORE'
T = datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def pg():
    dsn = os.environ.get('FEP_E1_TEST_DSN')
    if not dsn:
        pytest.skip('FEP_E1_TEST_DSN required for real isolated PostgreSQL')
    p = psycopg.connect(dsn)
    name = p.execute('select current_database()').fetchone()[0]
    if name not in ('fep_e1_fresh', 'fep_e1_upgrade'):
        p.close()
        raise ValueError('FEP_ISOLATED_TEST_DATABASE_REQUIRED')
    try:
        yield p
    finally:
        p.rollback()
        p.close()


def contract(p, name, body=None):
    body = {} if body is None else body
    p.execute('insert into fep.contracts values (%s,%s,%s,%s,%s,now())',
              (name, name, '1', Jsonb(body), digest([name, body])))


def observation(p, name='o', entity='SEC-A', day='2026-09-01', episode='local-1', scope=SCOPE):
    # Current 033 typed authority for explicitly synthetic test signals.
    signal_contract='ENGINEERING_FIXTURE:'+scope
    if p.execute('select 1 from fep.scopes where scope_id=%s',(scope,)).fetchone():
        if not p.execute('select 1 from fep.contracts where contract_id=%s',(signal_contract,)).fetchone():
            body=dict(accepted_contract=dict(contract_id=signal_contract,observation_scope=scope,formal_signals=['ENGINEERING_FIXTURE']),predicate_digest=digest(['fixture',scope]))
            contract(p,signal_contract,body)
            p.execute('insert into fep.signal_contract_registry values (%s,%s,%s,%s,%s,%s)',(signal_contract,scope,'ENGINEERING_FIXTURE',signal_contract,digest([signal_contract,body]),body['predicate_digest']))
    p.execute('insert into fep.observations values (%s,%s,%s,%s,%s,%s,%s,%s)',
              (name, scope, entity, day, 'ENGINEERING_FIXTURE:'+name, episode, signal_contract, T))


def snapshot(p, name='snap', obs='o', feature='FEATURE', publication='PUB'):
    manifest = {k: 'NONE' for k in ('accepted_head','algorithm_contract','parameter_contract','calendar',
                'universe','adjustment_basis','membership','state_event_revision','enrichment_revision')}
    manifest.update(publication=publication, feature_contract=feature)
    p.execute('insert into fep.observation_revisions values (%s,1,%s,%s,%s,%s,\'NONE\',\'PIT_OBSERVED\',\'SHADOW\',null,%s)',
              (obs, publication, T-timedelta(days=1), Jsonb(manifest), digest(manifest), T))
    p.execute('insert into fep.snapshots values (%s,%s,1,%s,%s,%s,%s)',
              (name, obs, feature, digest([name,'f']), digest([name,'q']), T))


@pytest.fixture
def base(pg):
    for name in ('OBS','FEATURE','POLICY','WINDOW'):
        contract(pg, name)
    add_namespace(pg, 'NS-E1')
    add_publication(pg, publication_id='PUB', namespace_id='NS-E1',
                    trade_date=date(2026,9,1), lineage_id='LINE-E1')
    for scope in (SCOPE, 'OTHER'):
        pg.execute("insert into fep.scopes values (%s,'STOCK','ENTRY','FIRST_PREWATCH','CORE','NS-E1','OBS',%s)",
                  (scope,digest(scope)))
    pg.execute("insert into fep.targets values ('ABS:T5','OBS',%s,5,'ratio','NUMERIC','V4-15.R_N','{}','[\"OBSERVED\"]',true)",(SCOPE,))
    observation(pg)
    snapshot(pg)
    return pg


def label(p, obs='o', revision=1, fact=2, mature=5, available=6, training=True, quality='OBSERVED'):
    key=f'{obs}-r{revision}'; source = dict(upstream_key=key, upstream_revision=str(revision),
        source_digest=digest(['source',key]), observation_id=obs, target_id='ABS:T5',
        target_digest=digest(['target',key]), numeric_value=.2, class_value=None,
        quality=quality, training_allowed=training, label_event_end='2026-09-08',
        **{k:(T+timedelta(days=n)).isoformat() for k,n in zip(
           ('source_fact_available_at','label_training_mature_at','label_revision_available_at'),(fact,mature,available))})
    contract(p, 'AUTH-'+key, dict(evidence_class='ENGINEERING_FIXTURE',exact_upstream_rows=[source]))
    p.execute('insert into fep.label_source_bindings values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
              (key,'AUTH-'+key,key,str(revision),source['source_digest'],source['label_event_end'],
               source['source_fact_available_at'],source['label_training_mature_at'],source['label_revision_available_at'],T+timedelta(days=30)))
    p.execute('insert into fep.label_revisions values (%s,%s,\'ABS:T5\',5,%s,%s,.2,null,%s,%s,%s,%s)',
              (obs,SCOPE,revision,key,quality,training,source['target_digest'],revision-1 if revision>1 else None))
    return source


def dataset(p, name='ds', expected=None):
    expected = [dict(observation_id='o',target_id='ABS:T5')] if expected is None else expected
    manifest = dict(expected_targets=expected,evidence_class='ENGINEERING_FIXTURE')
    p.execute('insert into fep.datasets values (%s,%s,\'FEATURE\',\'POLICY\',%s,%s,%s,%s)',
              (name,SCOPE,T+timedelta(days=40),Jsonb(manifest),digest([name,manifest]),T+timedelta(days=40)))
    for e in expected:
        p.execute('insert into fep.dataset_eligibility_ledger values (%s,%s,%s,%s,5,\'EXPECTED\',null)',
                  (name,e['observation_id'],SCOPE,e['target_id']))


def fold(p, name='A', partition='FIT', cutoff=10, ds='ds'):
    p.execute('insert into fep.dataset_fold_cutoffs values (%s,%s,%s,%s,%s,\'POLICY\',%s)',
              (ds,name,partition,T+timedelta(days=cutoff),T+timedelta(days=cutoff),digest([name,partition])))


def selection(p, source, fold_id='A', partition='FIT', eligibility='ELIGIBLE', ds='ds'):
    p.execute('insert into fep.dataset_fold_label_selection values (%s,%s,%s,%s,\'ABS:T5\',%s,%s,\'EXACT_ASOF\',%s)',
              (ds,fold_id,partition,source['observation_id'],int(source['upstream_revision']),source['target_digest'],eligibility))


def row(p, source, fold_id='A', partition='FIT', snapshot_id='snap', ds='ds'):
    p.execute('insert into fep.dataset_rows values (%s,%s,\'FEATURE\',%s,%s,\'ABS:T5\',%s,%s,1,%s,%s,null)',
              (ds,SCOPE,source['observation_id'],snapshot_id,int(source['upstream_revision']),source['target_digest'],partition,fold_id))


def rejected(p, fn, match=None):
    transaction_id=p.execute('select txid_current()').fetchone()[0]
    with pytest.raises((psycopg.Error, ValueError), match=match) as exc:
        with p.transaction():
            fn()
    print(json.dumps(dict(expected_block=True,transaction_id=transaction_id,
                         sqlstate=getattr(exc.value,'sqlstate',None),exception=str(exc.value))))
