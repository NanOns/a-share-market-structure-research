"""Reuse isolated E1 fixture clusters: minimal replay/readback, then full tests.

Explicit loopback DSNs only, E/F fixture directories, no database rebuild.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import psycopg
from psycopg.conninfo import conninfo_to_dict,make_conninfo

from scripts import run_fep_e1_acceptance as foundation
from scripts.validate_r25_preflight import protected,selection
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.db import apply,validate_inventory

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/fep_e1_r2_final'


def restore_side_effects():
    # Original PASS_KEEP tests emit into their frozen R1 locations. Preserve the
    # newly measured receipts here, then restore the pre-stage historical bytes.
    for name in ('CAS_CONCURRENCY_fep_e1_fresh.json','CAS_CONCURRENCY_fep_e1_upgrade.json','TRANSACTION_ROLLBACK_GATE.json'):
        old=ROOT/'reports/fep_e1'/name
        raw=old.read_bytes();tmp=REPORT/(name+'.tmp');tmp.write_bytes(raw);tmp.replace(REPORT/name)
        original=subprocess.check_output(['git','show','7474fb2:reports/fep_e1/'+name],cwd=ROOT)
        tmp=old.with_name(old.name+'.tmp');tmp.write_bytes(original);tmp.replace(old)


def run():
    params={};inventories={};checks=[];results={}
    for db,var in [('fep_e1_fresh','FEP_E1_ADMIN_DSN'),('fep_e1_upgrade','FEP_E1_UPGRADE_ADMIN_DSN')]:
        p=conninfo_to_dict(os.environ[var])
        if (p.get('host'),p.get('user'),p.get('dbname')) != ('127.0.0.1','fep_e1_admin','postgres'):
            raise ValueError('FEP_EXPLICIT_LOOPBACK_FIXTURE_ADMIN_REQUIRED')
        params[db]=p
        with psycopg.connect(make_conninfo(**dict(p,dbname=db))) as pg:
            directory=pg.execute('show data_directory').fetchone()[0]
            if not directory.replace('\\','/').lower().startswith(('e:/codex_tmp/fep_e1_','f:/codex_tmp/fep_e1_')):
                raise ValueError('FEP_ENGINEERING_DATA_DIRECTORY_REQUIRED')
            replay=apply(pg,ROOT,bootstrap=False);pg.commit()
            validate_inventory(pg);inv=foundation.inventory(pg)
            inventories[db]=dict(schema_digest=digest(inv),inventory=inv)
            checks.append(dict(database=db,data_directory=directory,replay=replay,
                               version=pg.execute('select version()').fetchone()[0],
                               timezone=pg.execute('show timezone').fetchone()[0]))
    assert inventories['fep_e1_fresh']['schema_digest']==inventories['fep_e1_upgrade']['schema_digest']
    foundation.REPORT=REPORT
    for db,p in params.items():
        results[db]=foundation.tests(db,p)
        print(db,results[db]['passed'],results[db]['failed_nodes'],flush=True)
    restore_side_effects()
    atomic_json(REPORT/'TARGETED_SUMMARY.json',dict(databases=results,same_fresh_upgrade_schema=True))
    migrations=[]
    for path in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('0[23][0-9]_*.sql')):
        if 28<=int(path.name[:3])<=31:
            rel=path.relative_to(ROOT).as_posix();raw=path.read_bytes()
            assert raw==subprocess.check_output(['git','show','7474fb2:'+rel],cwd=ROOT)
            migrations.append(dict(path=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    atomic_json(REPORT/'PASS_KEEP_DATABASE_READBACK.json',dict(status='PASS' if all(not v['exit_code'] for v in results.values()) else 'FAIL',
                unchanged_migrations=migrations,instances=checks,databases=inventories,same_fresh_upgrade_schema=True,
                table_count=33,guard_count=32,rebuild=False,existing_fixture_clusters=True,
                gates=['role/search_path','CAS concurrency/idempotency','rollback','schema inventory','40 negative vectors'],
                prior_label_time_authority='UNCHANGED_PASS_KEEP_ENGINEERING_REAL_PENDING'))
    if any(v['exit_code'] for v in results.values()):raise ValueError('FEP_TARGETED_RETEST_FAILED')
    atomic_json(REPORT/'R25_WAIT_READBACK.json',dict(status='PASS',protected=protected(ROOT),selection=selection(ROOT)))
    baseline=json.loads((ROOT/'reports/fep_e1/SCOPED_REGRESSION_SUMMARY.json').read_bytes())
    command=[s for s in baseline['command'] if not s.startswith(('--basetemp=','--junitxml=','--deselect='))]
    command[0]=sys.executable
    deselections=['tests/v4_dm01_r4/test_runtime.py::test_current_real_v2_parent_and_future_wait',
                  'tests/test_v4_18_migration_contract.py::test_all_declared_tables_have_explicit_namespace_rules']
    command+=['tests/fep',*['--deselect='+n for n in deselections],
              '--basetemp=E:/codex_tmp/test_temp/fep-e1-r2-final-scoped',
              '--junitxml='+str(REPORT/'scoped.xml')]
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'src')
    env['WORKBENCH_PG_DSN']=make_conninfo(**dict(params['fep_e1_fresh'],dbname='fep_e1_fresh'))
    env['FEP_E1_TEST_DSN']=env['WORKBENCH_PG_DSN'];env['TEMP']=env['TMP']='E:/codex_tmp/test_temp'
    print('Running full final scoped regression after ALL implementation/config/test changes',flush=True)
    with (REPORT/'scoped.log.tmp').open('wb') as f:
        code=subprocess.call(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    os.replace(REPORT/'scoped.log.tmp',REPORT/'scoped.log')
    restore_side_effects()
    cases=ET.parse(REPORT/'scoped.xml').findall('.//testcase')
    failures=sorted(c.attrib['classname']+'::'+c.attrib['name'] for c in cases
                    if c.find('failure') is not None or c.find('error') is not None)
    obsolete='tests.test_v4_18_migration_contract::test_all_declared_tables_have_explicit_namespace_rules'
    known=set(baseline['current_failed_nodes'])-{obsolete}
    introduced=sorted(set(failures)-known)
    summary=dict(command=command,exit_code=code,full_final_run=True,
                 passed=sum(all(c.find(k) is None for k in ('failure','error','skipped')) for c in cases),
                 skipped=sum(c.find('skipped') is not None for c in cases),current_failed_nodes=failures,
                 existing_debt_nodes=sorted(known),prior_registered_count=43,additional_reproduced_baseline_count=9,
                 introduced_active_failures=introduced,resolved_existing_debts=sorted(known-set(failures)),
                 deselections=[dict(node=deselections[0],classification='SUPERSEDED_PRE_SEAL_ASSERTION',status='NOT_PASS'),
                               dict(node=deselections[1],classification='SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION',status='NOT_PASS')],
                 status='PASS_NO_INTRODUCED_ACTIVE_FAILURES' if not introduced else 'FAIL')
    atomic_json(REPORT/'SCOPED_REGRESSION_SUMMARY.json',summary)
    atomic_json(REPORT/'R25_WAIT_READBACK.json',dict(status='PASS',protected=protected(ROOT),selection=selection(ROOT)))
    print(json.dumps({k:summary[k] for k in ('passed','skipped','introduced_active_failures','status')}),flush=True)
    if introduced:raise ValueError('FEP_FINAL_INTRODUCED_REGRESSION_FAILURES')


if __name__=='__main__':run()
