import json
from datetime import timedelta
import pytest
from psycopg.types.json import Jsonb
from .conftest import *


def test_E1_01_wrong_observation_scope(base):
    rejected(base, lambda: observation(base, name='wrong',scope='ABSENT'))


def test_E1_02_wrong_target_scope_horizon(base):
    s=label(base)
    rejected(base, lambda: base.execute("insert into fep.label_revisions values ('o','OTHER','ABS:T5',1,2,%s,.2,null,'OBSERVED',true,%s,null)",(s['upstream_key'],s['target_digest'])))


def test_E1_03_snapshot_observation_mismatch(base):
    observation(base,'other')
    s=label(base,obs='other');dataset(base,expected=[dict(observation_id='other',target_id='ABS:T5')]);fold(base);selection(base,s)
    rejected(base,lambda:row(base,s),match='foreign key')


def test_E1_04_snapshot_feature_contract_mismatch(base):
    rejected(base,lambda:base.execute("insert into fep.snapshots values ('wrong','o',1,'WINDOW',%s,%s,%s)",
        (digest('f'),digest('q'),T)),match='SNAPSHOT_FEATURE_CONTRACT_MISMATCH')


def test_E1_05_label_digest_revision_mismatch(base):
    s=label(base);dataset(base);fold(base)
    s['target_digest']=digest('wrong')
    rejected(base,lambda:selection(base,s),match='foreign key')


def test_E1_06_row_different_fold_selection(base):
    s=label(base);dataset(base);fold(base,'A');fold(base,'B');selection(base,s,'A')
    rejected(base,lambda:row(base,s,'B'),match='no rows')


@pytest.mark.parametrize('case,fact,mature,available,cutoff,reason',[
 ('E1_07',12,5,12,10,'NOT_VISIBLE'),('E1_08',2,15,6,10,'NOT_TRAINABLE'),
 ('E1_09',2,5,12,10,'NOT_VISIBLE'),('E1_10',2,5,20,10,'NOT_VISIBLE')])
def test_three_time_blocks(base,case,fact,mature,available,cutoff,reason):
    s=label(base,fact=fact,mature=mature,available=available);dataset(base);fold(base,cutoff=cutoff)
    rejected(base,lambda:selection(base,s),match=reason)


def test_E1_11_later_fold_new_revision(base):
    r1=label(base,available=10);r2=label(base,revision=2,available=20)
    dataset(base);fold(base,'A',cutoff=10);fold(base,'B',cutoff=20)
    selection(base,r1,'A');selection(base,r2,'B');row(base,r1,'A');row(base,r2,'B')
    assert base.execute('select fold_id,label_revision from fep.dataset_rows order by fold_id').fetchall()==[('A',1),('B',2)]


def test_E1_12_reconstruction_not_pit(base):
    rejected(base,lambda:base.execute("insert into fep.observation_revisions values ('o',2,'PUB',%s,%s,%s,'NONE','PIT_OBSERVED','REPLAY',1,%s)",
        (T-timedelta(days=1),Jsonb(dict(publication='PUB')),digest('new'),T)),match='RECONSTRUCTION_NOT_PIT')


def test_E1_13_pending_denominator(base):
    dataset(base);fold(base)
    base.execute("insert into fep.dataset_fold_label_selection values ('ds','A','FIT','o','ABS:T5',null,null,'PENDING_DUE','PENDING')")
    base.execute('set constraints all immediate')
    assert base.execute('select count(*) from fep.dataset_eligibility_ledger').fetchone()[0]==1
    assert base.execute('select count(*) from fep.dataset_rows').fetchone()[0]==0


def test_E1_14_missing_denominator_block(base):
    rejected(base,lambda:(base.execute("insert into fep.datasets values ('bad',%s,'FEATURE','POLICY',%s,%s,%s,%s)",
        (SCOPE,T,Jsonb(dict(expected_targets=[dict(observation_id='o',target_id='ABS:T5')])),digest('bad'),T)),
        base.execute('set constraints all immediate')),match='DENOMINATOR_INCOMPLETE')


def test_E1_15_no_global_revision(pg):
    names={r[0] for r in pg.execute("select column_name from information_schema.columns where table_schema='fep' and table_name='dataset_eligibility_ledger'")}
    assert 'selected_label_revision' not in names


@pytest.mark.parametrize('case,entity,day,episode,obs',[
 ('E1_16','SEC-A','2026-09-01','local-1','o'),
 ('E1_17','SEC-B','2026-09-01','local-2','o2'),
 ('E1_18','SEC-A','2026-09-02','local-1','o2')])
def test_phase_overlap(base,case,entity,day,episode,obs):
    if obs!='o':
        observation(base,obs,entity,day,episode)
        # A snapshot FK links the specific observation; revision publication check
        # is separately exercised. A second accepted publication is needed for day 2.
        pub='PUB'
        if day!='2026-09-01':
            add_publication(base,publication_id='PUB2',namespace_id='NS-E1',trade_date=date(2026,9,2),lineage_id='LINE2',gap='PREVIOUS_SESSION_HAS_NO_ACCEPTED_HEAD');pub='PUB2'
        snapshot(base,'snap2',obs,publication=pub)
    a=label(base);b=a if obs=='o' else label(base,obs)
    expected=[dict(observation_id=x,target_id='ABS:T5') for x in dict.fromkeys(['o',obs])]
    dataset(base,expected=expected);fold(base);fold(base,partition='TUNE');selection(base,a);selection(base,b,partition='TUNE');row(base,a)
    rejected(base,lambda:row(base,b,partition='TUNE',snapshot_id='snap' if obs=='o' else 'snap2'),match='PHASE_OVERLAP')


def test_E1_19_distinct_entity_local_episode(base):
    observation(base,'o2','SEC-B','2026-09-02','local-1')
    add_publication(base,publication_id='PUB2',namespace_id='NS-E1',trade_date=date(2026,9,2),lineage_id='LINE2',gap='PREVIOUS_SESSION_HAS_NO_ACCEPTED_HEAD')
    snapshot(base,'snap2','o2',publication='PUB2');a=label(base);b=label(base,'o2');dataset(base,expected=[dict(observation_id=x,target_id='ABS:T5') for x in ['o','o2']]);fold(base);fold(base,partition='TUNE');selection(base,a);selection(base,b,partition='TUNE');row(base,a);row(base,b,partition='TUNE',snapshot_id='snap2')
    assert base.execute('select count(*) from fep.dataset_rows').fetchone()[0]==2


def test_E1_20_immutable_update(base):
    rejected(base,lambda:base.execute("update fep.contracts set version='2' where contract_id='OBS'"),match='FEP_APPEND_ONLY')


def test_E1_21_immutable_delete(base):
    rejected(base,lambda:base.execute("delete from fep.contracts where contract_id='OBS'"),match='FEP_APPEND_ONLY')


def test_E1_22_inventory(pg):
    tables={r[0] for r in pg.execute("select tablename from pg_tables where schemaname='fep'")}
    guarded={r[0] for r in pg.execute("select c.relname from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='fep' and t.tgname='immutable'")}
    assert len(tables)==33 and len(guarded)==32 and tables-{'deployment_heads'}==guarded
    with pg.transaction():
        pg.execute('create table fep.unexpected_fact (id integer)')
        extra={r[0] for r in pg.execute("select tablename from pg_tables where schemaname='fep'")}-{'deployment_heads'}-guarded
        assert extra=={'unexpected_fact'}
        from workbench_analysis.fep_e1.db import validate_inventory
        rejected(pg,lambda:validate_inventory(pg),match='UNGUARDED_TABLE_INVENTORY')


def test_E1_34_no_recompute_and_exact_source(base):
    s=label(base)
    rejected(base,lambda:base.execute("insert into fep.label_revisions values ('o',%s,'ABS:T5',5,2,%s,.9,null,'OBSERVED',true,%s,1)",
        (SCOPE,s['upstream_key'],s['target_digest'])),match='LABEL_EXACT_SOURCE_MISMATCH')


def test_E1_35_missing_upstream(base):
    rejected(base,lambda:base.execute("insert into fep.label_source_bindings values ('missing','OBS','key','r',%s,'2026-09-08',%s,%s,%s,%s)",
        (digest('none'),T,T,T,T)),match='UPSTREAM_EXACT_AUTHORITY_REQUIRED')


def test_E1_37_duplicate_slot(base):
    sql="insert into fep.prediction_slots values (%s,'o',%s,'ABS:T5',5,'CORE',%s,%s,'NO_ACTIVE_MODEL')"
    base.execute(sql,('slot',SCOPE,T,T))
    rejected(base,lambda:base.execute(sql,('duplicate',SCOPE,T,T)),match='unique')


def test_E1_38_no_model_retained(base):
    base.execute("insert into fep.prediction_slots values ('slot','o',%s,'ABS:T5',5,'CORE',%s,%s,'NO_ACTIVE_MODEL')",(SCOPE,T,T))
    base.execute("insert into fep.slot_receipts values ('slot','receipt',%s,'MISSED',%s,%s)",(T,Jsonb(dict(reason='NO_ACTIVE_MODEL')),digest('no-model')))
    assert base.execute('select count(*) from fep.slot_receipts').fetchone()[0]==1
    assert base.execute('select count(*) from fep.models').fetchone()[0]==0
