"""Fresh single execution of the complete current V4 test scope."""
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.v4_production_cutover_evidence import ROOT,REPORT,binding,write


def prepare_disposable():
    """Clone only the relocated, verified test template; never production."""
    import hashlib
    import json
    import psycopg
    from psycopg import sql
    manifest=REPORT/'TEST_CLUSTER_RELOCATION.json'
    clusters=json.loads(manifest.read_bytes())
    cluster=clusters['fresh'];expected=(Path(cluster['root'])/'data').resolve()
    if not expected.is_relative_to(Path('G:/codex_tmp/test_temp').resolve()):
        raise ValueError('OWNED_DISPOSABLE_CLUSTER_REQUIRED')
    dsn=cluster['admin_dsn'];template='fep_e1_template'
    files=sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql'))
    checksums={hashlib.sha256(p.read_text(encoding='utf8').encode()).hexdigest() for p in files}
    with psycopg.connect(dsn.replace('dbname=postgres','dbname='+template)) as pg:
        actual_checksums={str(r[0]).strip() for r in pg.execute('select checksum_sha256 from v4_meta.schema_migrations').fetchall()}
        if actual_checksums!=checksums:raise ValueError('EXACT_MIGRATION_TEMPLATE_REQUIRED')
        if pg.execute('select count(*) from v4.sector_membership_facts').fetchone()[0]:raise ValueError('EMPTY_V4_TEMPLATE_REQUIRED')
    name='fep_v4_cutover_'+uuid.uuid4().hex[:12]
    with psycopg.connect(dsn,autocommit=True) as pg:
        actual=Path(pg.execute('show data_directory').fetchone()[0]).resolve()
        if actual!=expected:raise ValueError('DISPOSABLE_CLUSTER_IDENTITY_MISMATCH')
        pg.execute(sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(sql.Identifier(name),sql.Identifier(template)))
    result=dsn.replace('dbname=postgres','dbname='+name)
    # Preserve the already accepted verification-only upstream namespace aliases
    # on this new clone. Each alias requires the identical actually executed SQL.
    from scripts.apply_v4_phase0_schema import VERSIONS
    aliases=[]
    with psycopg.connect(result) as pg:
        for filename,version in VERSIONS.items():
            path=ROOT/'src/workbench_db/migrations/v4_postgres'/filename
            sha=hashlib.sha256(path.read_text(encoding='utf8').encode()).hexdigest()
            canonical='FEP_E5_CANONICAL_'+path.stem.upper()
            row=pg.execute('select checksum_sha256 from v4_meta.schema_migrations where version=%s',(canonical,)).fetchone()
            if not row or row[0].strip()!=sha:raise ValueError('ACTUALLY_EXECUTED_UPSTREAM_SQL_REQUIRED')
            pg.execute("insert into v4_meta.schema_migrations values (%s,%s,clock_timestamp(),'ISOLATED_VERIFIED_CANONICAL_ALIAS_V1') on conflict do nothing",(version,sha))
            if pg.execute('select checksum_sha256 from v4_meta.schema_migrations where version=%s',(version,)).fetchone()[0].strip()!=sha:raise ValueError('UPSTREAM_NAMESPACE_ALIAS_CHECKSUM_CONFLICT')
            aliases.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha,actually_executed_as=canonical,legacy_contract_alias=version,SQL_reexecuted=False))
    write(REPORT/'V4_SQL_DISPOSABLE_FIXTURE.json',dict(dsn=result,verified_data_directory=str(actual),migrations=[binding(p.relative_to(ROOT).as_posix()) for p in files],verified_upstream_aliases=aliases,accepted_alias_contract=binding('scripts/forward_remainder_pg.py'),production=False))
    return result


def scope():
    selected=[]
    for folder in sorted((ROOT/'tests').iterdir()):
        if folder.is_dir() and (folder.name.startswith('v4_') or folder.name in ('fep','fep_e2','fep_e3','fep_e4','fep_e5')):
            selected.extend(p.relative_to(ROOT).as_posix() for p in sorted(folder.rglob('test_*.py')))
    prefixes=('test_v4_','test_forward_','test_full_chain_','test_remainder_')
    extra={'test_settlement_r1r1.py','test_r20d_settlement.py','test_a08_governance_propagation.py','test_pre16_governance.py','test_r6r1_governance_cleanup.py','test_r17a_historical_governance.py'}
    for p in sorted((ROOT/'tests').glob('test_*.py')):
        if p.name.startswith(prefixes) or p.name in extra or (p.name.startswith('test_r') and 'v4_' in p.read_text(encoding='utf8').lower()):selected.append(p.relative_to(ROOT).as_posix())
    selected=sorted(set(selected))
    assert 'tests/test_r17a_historical_governance.py' in selected
    write(REPORT/'V4_ONLY_EXECUTION_SCOPE.json',dict(files=selected,bindings=[binding(p) for p in selected],ignore=[],deselect=[],new_xfail=[],selector='V4 folders, integrated FEP/Forward, V4 root tests and historical governance explicit union'))
    return selected


def main():
    paths=scope();env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH']=os.pathsep.join([str(ROOT/'src'),str(ROOT),'E:/codex_tmp/fep_e3_deps'])
    env.update(REMAINDER_PG_ENABLE='1',FEP_E5_CANONICAL_TEST_ENABLE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    env['REMAINDER_TEST_TEMP_BASE']='G:/codex_tmp/test_temp'
    env['TEMP']=env['TMP']=env['REMAINDER_TEST_TEMP_BASE']
    env['REMAINDER_PG_CLUSTER_MANIFEST']=str(REPORT/'TEST_CLUSTER_RELOCATION.json')
    env['FEP_E1_TEST_DSN']='host=127.0.0.1 port=55641 user=fep_e1_admin dbname=fep_e1_upgrade connect_timeout=5'
    env['FEP_TEST_RECEIPT_ROOT']='reports/v4_production_cutover_20261007/fep_transaction_receipts'
    env['FEP_E5_TEST_DSN']=env['FEP_E1_TEST_DSN']
    env['V4_10_DISPOSABLE_TEST_DSN']=prepare_disposable();env['WORKBENCH_PG_DSN']=env['V4_10_DISPOSABLE_TEST_DSN']
    xml=REPORT/'full_regression.xml';log=REPORT/'full_regression.log'
    command=[sys.executable,'-B','-m','pytest','-q',*paths,'--basetemp=G:/codex_tmp/test_temp/v4_production_cutover_full_'+uuid.uuid4().hex[:12],'--junitxml='+str(xml)]
    start=time.time();write(REPORT/'FULL_REGRESSION_RUNNING.json',dict(command=command,start=start,scope_files=len(paths)))
    with log.open('w',encoding='utf8') as stream:result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    root=ET.parse(xml).getroot();cases=root.findall('.//testcase');suites=root.findall('.//testsuite')
    counts={key:sum(int(s.get(key,0)) for s in suites) for key in ['tests','errors','failures','skipped']}
    failures=[dict(test=c.get('classname')+'::'+c.get('name'),output=(c.find('failure') if c.find('failure') is not None else c.find('error')).text) for c in cases if c.find('failure') is not None or c.find('error') is not None]
    receipt=dict(exit_code=result.returncode,counts=counts,failures=failures,command=command,seconds=time.time()-start,scope=binding((REPORT/'V4_ONLY_EXECUTION_SCOPE.json').relative_to(ROOT).as_posix()),single_fresh_execution=True,junit=binding(xml.relative_to(ROOT).as_posix()),log=binding(log.relative_to(ROOT).as_posix()),ignore=[],deselect=[],new_xfail=[])
    write(REPORT/'V4_ONLY_FULL_REGRESSION_RECEIPT.json',receipt);print(counts,flush=True)
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
