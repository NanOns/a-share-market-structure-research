"""Preserve historical outcomes and freeze an additive V4 execution denominator.

Collection is not execution or legal acceptance. No historical node is removed.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')
BASE = Path('G:/codex_tmp/V4_R4_R3_FINAL_DELIVERY/evidence/junit/baseline')
PREFIX = 'docs/audits/r4_r3_scope_20261011/'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def gitbytes(path):
    frozen = OUT / 'historical' / Path(path).name
    if frozen.exists():
        return frozen.read_bytes()
    return subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT)

def emit(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    temp = p.with_suffix(p.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temp, p)

def canonical(node):
    module, name = node.split('::', 1)
    return module.replace('.', '/') + '.py::' + name

def build():
    old = json.loads(gitbytes(PREFIX + 'V4_TEST_LEGAL_SCOPE_FINAL.json'))
    new = json.loads((BASE / 'V4_TEST_LEGAL_SCOPE_FINAL.json').read_bytes())
    historical = list(csv.DictReader((BASE / 'TEST_NODE_DISPOSITION_FINAL.csv').open(encoding='utf-8-sig')))
    assert len(historical) == len({r['nodeid'] for r in historical}) == 4568
    assert len(new['baseline_execution_modules']) == 245
    xml = gzip.decompress(gitbytes(PREFIX + 'V4_BASELINE_FULL_GUARDED_20261011T214750.xml.gz'))
    cases = ET.fromstring(xml).findall('.//testcase')
    diagnostics = {}
    for c in cases:
        status = 'FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS'
        diagnostics[canonical(c.get('classname') + '::' + c.get('name'))] = (status, ''.join(c.itertext()))
    counts = {s: sum(v[0] == s for v in diagnostics.values()) for s in ('PASS', 'FAIL', 'ERROR', 'SKIP')}
    assert counts == dict(PASS=4487, FAIL=201, ERROR=98, SKIP=3)
    assert len(cases) == len(diagnostics) == 4789
    nominations = json.loads((BASE / 'V4_MODULE_LEGAL_SCOPE_REVIEW.json').read_bytes())['modules']
    modules = set(new['baseline_execution_modules']) | set(new['additional_candidate_modules'])
    # Additive conservative set: every nominated module remains. No V3-name exclusion.
    modules.update(m['path'] for m in nominations if m['nominated_for_review'])
    modules.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'tests').rglob('test_*.py')
                   if '/v4_' in p.relative_to(ROOT).as_posix() or p.name.startswith('test_v4_'))
    bindings = {p: sha((ROOT / p).read_bytes()) for p in sorted(modules)}
    additions = []
    old_bindings=json.loads(gitbytes(PREFIX+'SOURCE_BINDINGS.json'))['source_files']
    for p in sorted(set(new['additional_candidate_modules']) - set(old['additional_candidate_modules'])):
        origin = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', p], cwd=ROOT, text=True).strip()
        additions.append(dict(path=p, old_sha256=old_bindings.get(p), old_state='ABSENT_FROM_148_STATIC_NOMINATION',
                              new_sha256=bindings[p], last_change_commit=origin,
                              admission='ADMITTED_CONSERVATIVELY_NO_EXCLUSION',
                              semantic_acceptance='REQUIRES_EXECUTION_AND_OWNER_EVIDENCE'))
    emit('MODULE_148_TO_155_RECONCILIATION.json', dict(old_count=148, new_count=155, delta=additions,
         reason='Seven explicitly added native PG/exact/owner/transport modules; static candidate modules are not pytest nodes',
         old_artifact_sha256=sha(gitbytes(PREFIX+'V4_TEST_LEGAL_SCOPE_FINAL.json')),
         new_artifact_sha256=sha((BASE/'V4_TEST_LEGAL_SCOPE_FINAL.json').read_bytes())))
    baseline = {r['canonical_nodeid']: r for r in historical}
    nodes = sorted(set(baseline) | set(diagnostics))
    rows = []
    for node in nodes:
        h = baseline.get(node, {})
        status, fault = diagnostics.get(node, ('NOT_EXECUTED_IN_4789', ''))
        module = node.split('::')[0]
        rows.append(dict(nodeid=node, original_nodeid=h.get('nodeid',''), baseline_result=h.get('previous_result','NEW'),
                         diagnostic_4789_result=status, diagnostic_failure=fault,
                         current_validity='ADMITTED_NO_EXCLUSION', owner=module,
                         condition='CURRENT_CONTRACT_AND_ISOLATED_PG', source_sha256=bindings.get(module,''),
                         final_result='NOT_RUN', added=node not in baseline, exclusion_evidence='NONE'))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'V4_NODE_DISPOSITION.csv').open('w', encoding='utf8', newline='') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
    emit('HISTORICAL_4789_RECOUNT.json',dict(counts=counts, unique_nodes=len(diagnostics), preserved_baseline_nodes=len(baseline),
         baseline_in_diagnostic=len(set(baseline)&set(diagnostics)),
         diagnostic_new_nodes=len(set(diagnostics)-set(baseline)),
         absent_baseline_nodes=sorted(set(baseline)-set(diagnostics)), raw_xml_sha256=sha(xml)))
    emit('V4_LEGAL_TEST_DENOMINATOR.json',dict(contract='V4_FULL_CLOSEOUT_ADDITIVE_DENOMINATOR_R1',
         status='COLLECTION_AND_FINAL_EXECUTION_REQUIRED', preserved_original_nodes=4568, preserved_original_modules=245,
         exclusions=[], modules=sorted(modules), module_bindings=bindings, historical_node_union=nodes,
         legal_node_count=None, final_source_freeze_required=True,
         scope_rule='Conservative union of every original, nominated and current V4 module; no filename exclusions'))
    emit('HISTORICAL_FAILURE_NODES.json',dict(nodes=[n for n,(s,_) in diagnostics.items() if s in ('FAIL','ERROR','SKIP')]))
    return sorted(modules)

def collect(modules):
    stamp=str(time.time_ns())
    for name in ('COLLECTION.log','COLLECTION_EXECUTION.json','COLLECTION_INTENTS.jsonl','COLLECTION_INTENTS_COLLECTED_NODES.json'):
        p=OUT/name
        if p.exists():
            (OUT/(stamp+'_'+name)).write_bytes(p.read_bytes())
    env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',
             PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT),'G:/codex_tmp/r4_r3_python_deps']),
             R4_NATIVE_ISOLATION='1',V4_NATIVE_PG_DSN='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres',
             R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data',
             R4_CONNECTION_LEDGER=str(OUT/'COLLECTION_INTENTS.jsonl'))
    cmd=[sys.executable,'-B','-m','pytest','--collect-only','-q',*modules,'--continue-on-collection-errors',
         '-o','cache_dir=G:/codex_tmp/v4_full_closeout_20261012/pytest_cache',
         '--basetemp=G:/codex_tmp/test_temp/v4_closeout_collection']
    with (OUT/'COLLECTION.log').open('w',encoding='utf8') as f:
        result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    p=OUT/'COLLECTION_INTENTS_COLLECTED_NODES.json'
    collected=json.loads(p.read_bytes())['nodes'] if p.exists() else []
    csvpath=OUT/'V4_NODE_DISPOSITION.csv'
    rows=list(csv.DictReader(csvpath.open(encoding='utf8')))
    known={r['nodeid'] for r in rows}
    for node in collected:
        if node not in known:
            module=node.split('::')[0]
            rows.append(dict(nodeid=node,original_nodeid='',baseline_result='NEW',diagnostic_4789_result='NEW',
                             diagnostic_failure='',current_validity='ADMITTED_NO_EXCLUSION',owner=module,
                             condition='CURRENT_CONTRACT_AND_ISOLATED_PG',source_sha256=sha((ROOT/module).read_bytes()),
                             final_result='NOT_RUN',added=True,exclusion_evidence='NONE'))
    with csvpath.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
    d=json.loads((OUT/'V4_LEGAL_TEST_DENOMINATOR.json').read_bytes())
    d.update(collected_nodes=collected,legal_node_count=len(collected) if result.returncode==0 else None,
             partial_collected_node_count=len(collected),collection_exit_code=result.returncode,
             status='COLLECTED_FINAL_EXECUTION_REQUIRED' if result.returncode==0 else 'COLLECTION_ERRORS_REPAIR_REQUIRED')
    emit('V4_LEGAL_TEST_DENOMINATOR.json',d)
    emit('COLLECTION_EXECUTION.json',dict(command=cmd,exit_code=result.returncode,node_count=len(collected)))
    return result.returncode

def remaining(label,full=False,failed_from=None):
    if not label.isalnum():
        raise ValueError('EXPLICIT_LABEL_REQUIRED')
    nodes=json.loads((OUT/'V4_LEGAL_TEST_DENOMINATOR.json').read_bytes())['collected_nodes'] if full else json.loads((OUT/'REMAINING_FAILURE_NODEIDS.json').read_bytes())
    if failed_from:
        legal=json.loads((OUT/'V4_LEGAL_TEST_DENOMINATOR.json').read_bytes())['collected_nodes']
        def junit_identity(node):
            parts=node.split('::');return parts[0].removesuffix('.py').replace('/','.')+('.'+'.'.join(parts[1:-1]) if len(parts)>2 else '')+'::'+parts[-1]
        wanted={c.get('classname')+'::'+c.get('name') for c in ET.parse(failed_from).findall('.//testcase') if any(c.find(tag) is not None for tag in ('failure','error','skipped'))}
        nodes=[n for n in legal if junit_identity(n) in wanted]
        if {junit_identity(n) for n in nodes}!=wanted:raise ValueError('FAILED_NODE_IDENTITY_MAPPING_INCOMPLETE')
    prefix=OUT/label
    if prefix.with_suffix('.xml').exists():
        raise ValueError('PRESERVE_PRIOR_EXECUTION')
    env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',
             PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT),'G:/codex_tmp/r4_r3_python_deps']),
             R4_NATIVE_ISOLATION='1',V4_NATIVE_PG_DSN='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres',
             R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data',R4_CONNECTION_LEDGER=str(prefix)+'_INTENTS.jsonl',
             R4_R3_EXTRA_PG_FIXTURES=str(ROOT/PREFIX/'R3_EXTRA_PG_FIXTURES_R3.json'),FEP_E5_CANONICAL_TEST_ENABLE='1',
             FEP_AUTHORITY_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_authority_isolated',
             FEP_SIGNAL_BASELINE32_FRESH_TEST_DSN='host=127.0.0.1 port=55794 user=r4_isolated_admin dbname=fep_signal_baseline32_actual_fresh',
             FEP_SIGNAL_BASELINE32_UPGRADE_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_signal_baseline32_upgrade')
    if full:
        env.update(FEP_E1_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_e1_upgrade',
                   FEP_E5_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_e1_upgrade',
                   V4_10_DISPOSABLE_TEST_DSN='host=127.0.0.1 port=55795 user=r4_isolated_admin dbname=v4_v41011_clean_20261013_r1',
                   WORKBENCH_PG_DSN='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres',
                   FEP_TEST_RECEIPT_ROOT='G:/codex_tmp/v4_full_closeout_20261012/denominator/'+label+'_FEP_E1_RECEIPTS')
    if failed_from:
        response=prefix.with_suffix('.args');response.write_text('\n'.join(nodes)+'\n',encoding='utf8');targets=['@'+str(response)]
    else:targets=sorted({node.split('::')[0] for node in nodes}) if full else nodes
    cmd=[sys.executable,'-B','-m','pytest','-q',*targets,'--basetemp=G:/codex_tmp/test_temp/'+label,
         '-o','cache_dir=G:/codex_tmp/v4_full_closeout_20261012/pytest_cache','--junitxml='+str(prefix.with_suffix('.xml'))]
    with prefix.with_suffix('.log').open('w',encoding='utf8') as f:
        result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    emit(label+'_EXECUTION.json',dict(command=cmd,exit_code=result.returncode,expected_nodes=len(nodes),
         scope='EXACT_FULL_RUN_FAILURE_ERROR_SKIP_SET_NO_OMISSIONS' if failed_from else 'FULL_ADDITIVE_LEGAL_NODE_UNION_NO_EXCLUSIONS' if full else 'ONLY_ORIGINAL_FAILURE_ERROR_SKIP_NODES_EXCLUDING_THREE_REPAIRED_MODULES'))
    return result.returncode

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--collect',action='store_true');p.add_argument('--remaining');p.add_argument('--full');p.add_argument('--failed-from',type=Path);a=p.parse_args()
    if a.full:
        raise SystemExit(remaining(a.full,full=True,failed_from=a.failed_from))
    if a.remaining:
        raise SystemExit(remaining(a.remaining))
    m=build();raise SystemExit(collect(m) if a.collect else 0)
