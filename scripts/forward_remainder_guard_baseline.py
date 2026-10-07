"""Exact pre-033 contrast fixture; migration 033 executes inside each rollback test."""
import json
import psycopg
from psycopg import sql
from scripts.full_chain_repair_io import ROOT,write,binding
from scripts import run_fep_e5_r1r1b as b
from workbench_analysis.fep_e5 import canonical_ledger as c
P='reports/forward_r2_remainder_consolidated_20261007/'
def run():
    clusters=json.loads((ROOT/(P+'IA06_CLUSTER_BOOTSTRAP.json')).read_bytes())
    folder=ROOT/P/'signal_guard_pre033';folder.mkdir(exist_ok=True)
    write((folder/'HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json').relative_to(ROOT).as_posix(),(ROOT/'reports/fep_e5_r1r1c/HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json').read_bytes(),raw=True)
    dsns={};receipts={}
    paths=[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql')) if int(p.name[:3])>=28 and int(p.name[:3])<=32]
    for kind,cluster in clusters.items():
        name='fep_guard_pre033_v2_'+kind
        with psycopg.connect(cluster['admin_dsn'],autocommit=True) as pg:
            assert str(pg.execute('show data_directory').fetchone()[0]).replace('\\','/').lower()==str(cluster['root']+'/data').replace('\\','/').lower()
            pg.execute(sql.SQL('create database {} template fep_e1_core_template').format(sql.Identifier(name)))
        dsns[kind]=cluster['admin_dsn'].replace('dbname=postgres','dbname='+name)
        with psycopg.connect(dsns[kind],autocommit=True) as pg:receipts[kind]=c.apply(pg,ROOT,paths)
    b.REPORT=folder;b.frozen=lambda:None;b.DSNS=dsns;b.project()
    write(P+'IA06_SIGNAL_GUARD_BASELINE_PROOF.json',dict(profile='EXACT_PRE_033_SCHEMA_WITH_FROZEN_CANONICAL_INPUTS',migrations=receipts,current_schema_not_downgraded=True,DSNS=dsns,test_purpose='baseline contrast; actual 033 executed per test inside rollback transaction',source=binding('tests/test_full_chain_fep_db.py')))
if __name__=='__main__':run()
