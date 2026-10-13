"""Frozen-node execution profiles; historical contracts never admit current PG."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')

def identity(node):
    parts=node.split('::');return parts[0][:-3].replace('/','.')+('.'+'.'.join(parts[1:-1]) if len(parts)>2 else '')+'::'+parts[-1]
def historical_modules():
    result={}
    for name,key in [('v4_frozen_test_profiles_remainder_v1.json','profiles'),('v4_frozen_test_profiles_full_closeout_r1.json','profiles'),('v4_legacy_api_test_profiles_remainder_v1.json','modules'),('v4_legacy_identity_test_profiles_remainder_v1.json','modules')]:
        for row in json.loads((ROOT/'config'/name).read_bytes())[key]:
            if row.get('scope')!='SINGLE_FROZEN_AST_NODE':result[row['path']]=name
    result['tests/test_forward_p1_isolation.py']='Explicit original DuckDB runtime isolation contract'
    current=json.loads((ROOT/'config/v4_current_native_test_contracts_r4.json').read_bytes())
    assert current['grants_current_permission'] is False
    for row in current['modules']:
        assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['source_sha256']
        assert row['profile']=='CURRENT_NATIVE_PG_ONLY'
        result.pop(row['path'],None)
    return result
def environment(label,native):
    from tests.final_disposable_paths import configured_source_roots
    env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONPATH=os.pathsep.join([str(ROOT/'tests/final_child_guard'),str(ROOT/'src'),str(ROOT),'G:/codex_tmp/r4_r3_python_deps']))
    env.update(FINAL_SOURCE_GUARD_ROOTS=json.dumps([str(p) for p in configured_source_roots()]),FINAL_CHILD_AUDIT_ROOT='G:/codex_tmp/test_temp/'+label+'_child_source_guard')
    env.update(R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data',R4_CONNECTION_LEDGER=str(OUT/(label+'_INTENTS.jsonl')),R4_R3_EXTRA_PG_FIXTURES=str(ROOT/'docs/audits/r4_r3_scope_20261011/R3_EXTRA_PG_FIXTURES_R3.json'),FEP_E5_CANONICAL_TEST_ENABLE='1',FEP_AUTHORITY_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_authority_isolated',FEP_SIGNAL_BASELINE32_FRESH_TEST_DSN='host=127.0.0.1 port=55794 user=r4_isolated_admin dbname=fep_signal_baseline32_actual_fresh',FEP_SIGNAL_BASELINE32_UPGRADE_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_signal_baseline32_upgrade',FEP_E1_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_e1_upgrade',FEP_E5_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_e1_upgrade',V4_10_DISPOSABLE_TEST_DSN='host=127.0.0.1 port=55795 user=r4_isolated_admin dbname=v4_v41011_clean_20261013_r1',WORKBENCH_PG_DSN='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres',FEP_TEST_RECEIPT_ROOT=str(OUT/(label+'_FEP_E1_RECEIPTS')))
    env.pop('V4_AUDIT_SCOPE_MANIFEST',None)
    if native:env.update(R4_NATIVE_ISOLATION='1',V4_NATIVE_PG_DSN='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres')
    else:
        for key in ('R4_NATIVE_ISOLATION','V4_NATIVE_PG_DSN','R4_R3_EXTRA_PG_FIXTURES'):env.pop(key,None)
    return env
def execute(label,nodes,native):
    prefix=OUT/label
    if prefix.with_suffix('.xml').exists() or prefix.with_suffix('.manifest.json').exists():raise ValueError('PRESERVE_PRIOR_EXECUTION')
    sources={n.split('::')[0] for n in nodes}
    manifest=dict(contract_id='V4_FINAL_SOURCE_NODE_PROFILE_R3',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),nodes=nodes,node_count=len(nodes),sources={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(sources)},profile='CURRENT_NATIVE_PG_ONLY' if native else 'RETAINED_HISTORICAL_DISPOSABLE_CONTRACTS_NO_CURRENT_ADMISSION',exclusions=[])
    prefix.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    prefix.with_suffix('.args').write_text('\n'.join(nodes)+'\n',encoding='utf8')
    cmd=[sys.executable,'-B','-m','pytest','-q','@'+str(prefix.with_suffix('.args')),'--basetemp=G:/codex_tmp/test_temp/'+label,'-p','no:cacheprovider','--junitxml='+str(prefix.with_suffix('.xml'))]
    with prefix.with_suffix('.log').open('w',encoding='utf8') as stream:result=subprocess.run(cmd,cwd=ROOT,env=environment(label,native),stdout=stream,stderr=subprocess.STDOUT)
    print(json.dumps(dict(label=label,nodes=len(nodes),exit_code=result.returncode)),flush=True)
    return result.returncode
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--failed-from',type=Path);parser.add_argument('--profile',choices=['native','historical'],required=True);args=parser.parse_args()
    source=json.loads((OUT/'FULLFROZENR2_MANIFEST.json').read_bytes())['nodes']
    if args.failed_from:
        wanted={c.get('classname')+'::'+c.get('name') for c in ET.parse(args.failed_from).findall('.//testcase') if any(c.find(t) is not None for t in ('failure','error','skipped'))}
        source=[n for n in source if identity(n) in wanted]
        if {identity(n) for n in source}!=wanted:raise ValueError('INCOMPLETE_FAILURE_NODE_JOIN')
    historical=historical_modules()
    def is_historical(node):return node.split('::')[0] in historical or node.startswith(('tests/upgrade_m','tests/upgrade_v3/'))
    native=args.profile=='native';nodes=[n for n in source if is_historical(n)!=native]
    return execute(args.label,nodes,native)

def collect_final(label):
    """Preserve all 7209 prior nodes and add every new task test module."""
    prior=json.loads((OUT/'FULLFROZENR2_MANIFEST.json').read_bytes())
    modules={n.split('::')[0] for n in prior['nodes']}
    added=subprocess.check_output(['git','log','--since=2026-10-12','--diff-filter=A','--format=','--name-only','--','tests'],cwd=ROOT,text=True).splitlines()
    modules.update(n for n in added if Path(n).name.startswith('test_') and n.endswith('.py') and (ROOT/n).is_file())
    target=OUT/(label+'.modules.args');target.write_text('\n'.join(sorted(modules))+'\n',encoding='utf8')
    cmd=[sys.executable,'-B','-m','pytest','--collect-only','-q','@'+str(target),'-p','no:cacheprovider','--basetemp=G:/codex_tmp/test_temp/'+label]
    with (OUT/(label+'.log')).open('w',encoding='utf8') as stream:result=subprocess.run(cmd,cwd=ROOT,env=environment(label,True),stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:raise ValueError('FINAL_COLLECTION_FAILED')
    collected=json.loads((OUT/(label+'_INTENTS_COLLECTED_NODES.json')).read_bytes())['nodes']
    if len(set(collected))!=len(collected) or not set(prior['nodes'])<=set(collected):raise ValueError('FINAL_ORIGINAL_NODE_OMISSION')
    manifest=dict(contract_id='V4_FINAL_LEGAL_NODE_FREEZE_R3',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),nodes=collected,denominator=len(collected),original_5463_preserved=True,prior_7209_preserved=True,added_nodes=sorted(set(collected)-set(prior['nodes'])),modules=sorted(modules),source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(modules)},assertions_unchanged=True,exclusions=[],historical_unavailable_inputs_have_explicit_node_skips=True,final_execution='NOT_YET_EXECUTED')
    (OUT/(label+'.json')).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'denominator':len(collected),'added_nodes':len(manifest['added_nodes']),'prior_7209_preserved':True}),flush=True)
    return manifest

if __name__=='__main__':raise SystemExit(main())
