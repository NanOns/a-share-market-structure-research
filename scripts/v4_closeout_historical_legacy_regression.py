"""Run exact retained legacy-contract nodes under existing disposable guards.

These results never satisfy current V4 native consumer or release acceptance.
The native guard is kept unchanged in the separate current-runtime process.
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')
PREFIXES=('tests/upgrade_m','tests/upgrade_v3/')

def identity(node):
    parts=node.split('::')
    return parts[0].removesuffix('.py').replace('/','.')+('.'+'.'.join(parts[1:-1]) if len(parts)>2 else '')+'::'+parts[-1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--failed-from',type=Path,required=True);a=p.parse_args()
    if not a.label.isalnum():raise ValueError('EXPLICIT_NEW_LABEL_REQUIRED')
    prefix=OUT/a.label
    if prefix.with_suffix('.xml').exists() or prefix.with_suffix('.json').exists():raise ValueError('PRESERVE_PRIOR_EVIDENCE')
    cases=ET.parse(a.failed_from).findall('.//testcase')
    wanted={c.get('classname')+'::'+c.get('name') for c in cases if any(c.find(t) is not None for t in ('failure','error','skipped'))}
    legal=json.loads((OUT/'V4_LEGAL_TEST_DENOMINATOR.json').read_bytes())['collected_nodes']
    # Explicit historical publication/API contract families; no V4 module is dropped.
    nodes=[n for n in legal if identity(n) in wanted and
           (n.startswith(PREFIXES) or n.startswith('tests/test_forward_p1_isolation.py::'))]
    sources={n.split('::')[0] for n in nodes}
    modules=[dict(path=n,sha256=hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),
                  scope='RETAINED_HISTORICAL_CONTRACT_ONLY',current_v4_acceptance=False) for n in sorted(sources)]
    manifest=dict(contract_id='V4_RETAINED_LEGACY_REGRESSION_DISPOSABLE_R1',nodes=nodes,modules=modules,
                  exclusions=[],source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  input_failure_sha256=hashlib.sha256(a.failed_from.read_bytes()).hexdigest(),
                  current_v4_guard_unchanged=True,current_pg_only_or_production_acceptance=False,
                  reason='Direct original DuckDB API/publication fixtures are retained legacy contracts; current V4 entry has an independent fail-closed native guard')
    prefix.with_suffix('.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    prefix.with_suffix('.args').write_text('\n'.join(nodes)+'\n',encoding='utf8')
    env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1',
             PYTHONUTF8='1',PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT),'G:/codex_tmp/r4_r3_python_deps']))
    for key in ('R4_NATIVE_ISOLATION','V4_NATIVE_PG_DSN','V4_AUDIT_SCOPE_MANIFEST'):env.pop(key,None)
    cmd=[sys.executable,'-B','-m','pytest','-q','@'+str(prefix.with_suffix('.args')),
         '--basetemp=G:/codex_tmp/test_temp/'+a.label,'-o','cache_dir=G:/codex_tmp/v4_full_closeout_20261012/pytest_cache',
         '--junitxml='+str(prefix.with_suffix('.xml'))]
    with prefix.with_suffix('.log').open('w',encoding='utf8') as stream:
        result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
