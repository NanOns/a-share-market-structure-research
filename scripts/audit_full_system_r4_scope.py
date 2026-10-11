"""R4 frozen inventory. Static candidates are never asserted to be live calls."""
import ast
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'
BASE = 'fbd23a6ba08d0948fe7ad421d1765fe363648522'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(8*1024*1024): h.update(data)
    return h.hexdigest()

def write(name, data):
    # Git HEAD alone does not identify executed uncommitted implementation.
    paths=set((ROOT/'src').rglob('*.py'))|set((ROOT/'scripts').glob('*.py'))|set((ROOT/'tests').glob('*.py'))
    paths.update(p for p in (ROOT/'conftest.py',ROOT/'run_workbench_service.py',ROOT/'run_desktop.py') if p.exists())
    bindings={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}
    tree_sha=hashlib.sha256(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    binding_name='R4_SOURCE_TREE_'+tree_sha+'.json'
    git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=subprocess.run(['git','diff','--quiet','--','src','scripts','tests','conftest.py','run_workbench_service.py','run_desktop.py'],cwd=ROOT).returncode!=0
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','src','scripts','tests'],cwd=ROOT,text=True).strip()
    if not (OUT/binding_name).exists():
        OUT.mkdir(parents=True,exist_ok=True)
        bound=dict(contract_id='R4_EXECUTION_SOURCE_TREE_R1',git_head=git_head,tree_sha256=tree_sha,bindings=bindings,meaning='Python source bytes at evidence emission; not proof of an earlier execution')
        temp=OUT/(binding_name+'.tmp');temp.write_text(json.dumps(bound,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(temp,OUT/binding_name)
    envelope = dict(contract_id='R4-MASTER-R1', base_head=BASE,
        source_SHA=None if dirty or untracked else git_head,source_git_head=git_head,
        source_revision_state='UNCOMMITTED_BYTES_BOUND' if dirty or untracked else 'COMMITTED',
        execution_source_binding=dict(path=binding_name,sha256=sha(OUT/binding_name),tree_sha256=tree_sha),
        run_utc=datetime.now(timezone.utc).isoformat(), scope='V4_ONLY_POSTGRESQL_ONLY',
        denominator=None, negative_vectors=[], previous_status='AUDIT_INCOMPLETE',
        current_status='IN_PROGRESS', evidence_links=[], owner='Codex / root',
        limitations=['Static import closure is a candidate superset, not runtime reachability proof'],
        next_conditions=['Dynamic entry validation and per-test contract review'], **{})
    envelope.update(data)
    path=OUT/name; path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(envelope,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    os.replace(tmp,path)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sources=list((ROOT/'src').rglob('*.py'))+list((ROOT/'scripts').glob('*.py'))+[ROOT/'run_workbench_service.py',ROOT/'run_desktop.py']
    modules={}; trees={}
    for p in sources:
        rel=p.relative_to(ROOT).as_posix()
        module=(rel[4:] if rel.startswith('src/') else rel)[:-3].replace('/','.')
        if module.endswith('.__init__'): module=module[:-9]
        modules[module]=rel
        try: trees[module]=ast.parse(p.read_text('utf-8-sig'))
        except (SyntaxError,UnicodeError): continue
    edges=[]; databases=[]
    for mod,tree in trees.items():
        package=mod if modules[mod].endswith('/__init__.py') else mod.rpartition('.')[0]
        for node in ast.walk(tree):
            imports=[]
            if isinstance(node,ast.Import): imports=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                prefix='.'.join(package.split('.')[:len(package.split('.'))-node.level+1]) if node.level else ''
                target='.'.join(x for x in (prefix,node.module) if x)
                imports=[target]+[target+'.'+a.name for a in node.names]
            elif isinstance(node,ast.Call) and isinstance(node.func,(ast.Name,ast.Attribute)):
                call=ast.unparse(node.func)
                if call.endswith(('import_module','__import__')) and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str): imports=[node.args[0].value]
                if call.endswith(('connect','create_engine','Popen','run')):
                    databases.append(dict(module=modules[mod],line=node.lineno,callee=call,expression=ast.unparse(node)[:450],source_sha=sha(ROOT/modules[mod]),status='SOURCE_CONFIRMED_REACHABILITY_OPEN',current_pid_loaded='NOT_VERIFIABLE'))
            for target in imports:
                if target in modules: edges.append(dict(caller=mod,callee=target,line=node.lineno,kind='EXPLICIT_LEGACY_V3_BRANCH' if mod=='run_workbench_service' and target=='workbench_service.app' else 'STATIC_IMPORT_CANDIDATE'))
    starts=['run_workbench_service','run_desktop','workbench_desktop.engine','workbench_service.core_product_server_r1','workbench_service.v4_server','workbench_service.continuous_daily_release']
    reached=set(starts); changed=True
    while changed:
        changed=False
        for e in edges:
            if e['kind']!='EXPLICIT_LEGACY_V3_BRANCH' and e['caller'] in reached and e['callee'] not in reached: reached.add(e['callee']);changed=True
    # CLI legacy branch is preserved separately; syntactic reachability is not admission.
    write('V4_RUNTIME_CALL_GRAPH_R4.json',dict(entries=starts,edges=edges,candidate_modules=sorted(reached),legacy_branch='run_workbench_service --legacy-v3 -> workbench_service.app; excluded only at this explicit entry',current_status='STATIC_CANDIDATES_FROZEN_DYNAMIC_OPEN'))
    write('V4_DB_CALL_GRAPH_R4.json',dict(connections=databases,current_status='SOURCE_INVENTORY_DYNAMIC_OPEN'))
    with (OUT/'DB_INVENTORY_R4.csv').open('w',encoding='utf8',newline='') as f:
        fields=['ID','module','line','entry','callee','expression','current_pid_loaded','database_engine','operation','read_write','authority','risk','migration_batch','source_sha','reproduction','status']
        writer=csv.DictWriter(f,fields);writer.writeheader()
        for i,row in enumerate(databases,1):
            item={k:row.get(k,'NOT_VERIFIABLE') for k in fields};item.update(ID=f'DB-INTENT-{i:04}',entry='STATIC_CANDIDATE',authority='R4-MASTER-R1',risk='REVIEW_REQUIRED',reproduction=f"{row['module']}:{row['line']}")
            writer.writerow(item)
    old=json.loads((ROOT/'config/v4_audit_regression_scope_r3.json').read_bytes())
    write('R4_V4_TEST_SCOPE_V2.json',dict(included_test_modules=old['included_test_modules'],excluded_test_modules=old.get('excluded_test_modules',[]),denominator=dict(r3_modules=245,r3_cases=4568,r3_pass=3810,r3_fail=237,r3_error=209,r3_skip=312,r4_legal_cases=None),current_status='BASELINE_PRESERVED_REVIEW_OPEN',scope_change=[]))
    r3=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
    import xml.etree.ElementTree as ET
    with gzip.open(r3/'b3_v4_final_junit.xml.gz','rb') as f: tree=ET.parse(f)
    with (OUT/'TEST_NODE_DISPOSITION_R4.csv').open('w',encoding='utf8',newline='') as f:
        fields=['nodeid','source_SHA','contract','previous_result','current_result','first_failure','business_semantics','owner','fix_commit','retest','exemption']
        w=csv.DictWriter(f,fields);w.writeheader()
        for c in tree.findall('.//testcase'):
            fault=c.find('failure'); fault=c.find('error') if fault is None else fault
            status='FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS'
            w.writerow(dict(nodeid=c.get('classname','')+'::'+c.get('name',''),source_SHA=BASE,contract='V4_APPLICABILITY_REVIEW_REQUIRED',previous_result=status,current_result='NOT_RUN',first_failure=(fault.get('message','') if fault is not None else ''),business_semantics='SEMANTIC_REPLAY_REQUIRED' if status=='PASS' else 'ROOT_CAUSE_REVIEW_REQUIRED',owner='Codex / root',fix_commit='',retest='',exemption='NONE'))
    paths=set((ROOT/'data/v4').glob('*HEAD*.json'))
    paths.update(ROOT/r['path'] for r in json.loads((r3/'B3_FINAL_PROTECTED_READBACK_R3.json').read_bytes())['records'])
    paths.update((ROOT/'runtime/dynamic_daily').glob('jobs.sqlite3*'))
    visited=set()
    for config in ['config/core_product_read_authority_r1.json','config/v4_research_snapshot_authority_v1.json','config/v4_production_runtime_authority_v1.json']:
        p=ROOT/config
        if p.exists():
            paths.add(p)
            def follow(value):
                if isinstance(value,dict):
                    if value.get('path') and value.get('sha256'):
                        q=ROOT/value['path'];paths.add(q)
                        if q in visited:return
                        visited.add(q)
                        if q.is_file() and q.suffix=='.json':
                            try: follow(json.loads(q.read_bytes()))
                            except (ValueError,RecursionError): pass
                    else:
                        for child in value.values(): follow(child)
                elif isinstance(value,list):
                    for child in value: follow(child)
            follow(json.loads(p.read_bytes()))
    if not (OUT/'R4_PROTECTED_BEFORE.json').exists():
        write('R4_PROTECTED_BEFORE.json',dict(records=[dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths) if p.is_file()],current_status='READ_ONLY_BASELINE',limitations=['TDX full directory hashing and production database identity not yet captured; online WAL can change naturally']))
    authorities=['AGENTS.md','docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md','docs/design/FEP_R2_MODULE_DESIGN_20260930.md','config/v4_audit_regression_scope_r3.json']
    write('R4_SCOPE_AUTHORITY.json',dict(bindings=[dict(path=p,sha256=sha(ROOT/p)) for p in authorities],external_audit=dict(file_id='1_1huGRGIcE5briW38cZBLxBvdOtbD1nt',sha256=sha(OUT/'INPUT_R3_EXTERNAL_AUDIT.md')),precedence='User V4-only and PostgreSQL-only override conflicting historical specs; historical artifacts preserved',current_status='AUTHORITY_FROZEN'))
    write('OWNER_REGISTRY_R4.json',dict(batches={f'R4-{i:02}':dict(owner='Codex / root',status='IN_PROGRESS' if i in (0,1,6) else 'NOT_STARTED') for i in range(11)},external_acceptance_owner='Independent reviewer, signature pending',current_status='OWNER_ASSIGNED'))
    print(json.dumps(dict(sources=len(modules),edges=len(edges),connection_candidates=len(databases),junit_nodes=len(tree.findall('.//testcase')),output=str(OUT))))

if __name__=='__main__': main()
