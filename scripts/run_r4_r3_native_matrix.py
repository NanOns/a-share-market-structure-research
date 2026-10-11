"""Explicit G-only native fixture profile; retains every selected test node."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
label=sys.argv[1]
if not re.fullmatch('[A-Z][A-Z0-9_]{1,80}',label):raise ValueError('VERSIONED_MATRIX_LABEL_REQUIRED')
paths=sys.argv[2:]
if not paths or any(not (ROOT/p).resolve().is_relative_to(ROOT/'tests') or '/upgrade_v3/' in p.replace('\\','/') for p in paths):
    raise ValueError('EXPLICIT_CURRENT_V4_TEST_PATHS_REQUIRED')
if (OUT/(label+'.xml')).exists() or (OUT/(label+'_RAW.log')).exists():raise ValueError('RETAIN_EXISTING_RAW_MATRIX')
env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',
    PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT),'G:/codex_tmp/r4_r3_python_deps']),R4_NATIVE_ISOLATION='1',
    V4_NATIVE_PG_DSN='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres',
    R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data',R4_CONNECTION_LEDGER=str(OUT/(label+'_INTENTS.jsonl')))
env.pop('R4_ENGINEERING_HISTORICAL_GIT_ROOT',None)
extra=OUT/'R3_EXTRA_PG_FIXTURES_R3.json'
if extra.exists():
    env.update(R4_R3_EXTRA_PG_FIXTURES=str(extra),FEP_E5_CANONICAL_TEST_ENABLE='1',
        FEP_AUTHORITY_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_authority_isolated',
        FEP_SIGNAL_BASELINE32_FRESH_TEST_DSN='host=127.0.0.1 port=55794 user=r4_isolated_admin dbname=fep_signal_baseline32_actual_fresh',
        FEP_SIGNAL_BASELINE32_UPGRADE_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_signal_baseline32_upgrade')
command=[sys.executable,'-B','-m','pytest','-p','tests.v4_native_isolation_plugin_r4',*paths,'-q',
    '--basetemp=G:/codex_tmp/test_temp/'+label,'-o','cache_dir=G:/codex_tmp/pytest_cache_r4_r3_matrix',
    '--junitxml='+str(OUT/(label+'.xml'))]
start=time.time()
def source_bindings():
    files=sorted(p for directory in ('src','scripts','tests','config') for p in (ROOT/directory).rglob('*')
        if p.is_file() and p.suffix in ('.py','.json'))
    return {p.relative_to(ROOT).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in files}
before=source_bindings()
(OUT/(label+'_SOURCE_BINDINGS.json')).write_text(json.dumps(dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=before),indent=2)+'\n',encoding='utf8')
with (OUT/(label+'_RAW.log')).open('x',encoding='utf8') as stream:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
record=dict(command=command,exit_code=result.returncode,seconds=time.time()-start,
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    paths=paths,extra_fixture_manifest_sha256=hashlib.sha256(extra.read_bytes()).hexdigest() if extra.exists() else None,
    full_acceptance='OPEN_SEPARATE_FULL_DENOMINATOR_REQUIRED')
after=source_bindings()
record['changed_source_paths']=sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p))
record['source_bytes_stable']=before==after
(OUT/(label+'_EXECUTION.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps(record));sys.exit(result.returncode)
