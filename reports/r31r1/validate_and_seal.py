"""Atomic R31R1 evidence, clean regression and exact source sealing."""
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from reports.r31.audit_oracle import validate_contract,final_verdict
TAG='codex/r31r1-v4-22-audit-contract-repair-tested-source-20261005'
C=json.loads((ROOT/'config/v4_22_independent_audit_contract_v1.json').read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,v):
    p=ROOT/name; p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.stage')
    raw=v if isinstance(v,bytes) else (v if isinstance(v,str) else json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()
    with t.open('wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    os.replace(t,p)
def regression(directory,label):
    directory=Path(directory).resolve(); previous=json.loads((ROOT/'reports/r31/CLEAN_REGRESSION.json').read_bytes())
    scope=previous['scope']+['tests/test_v4_22_r31r1_repair.py']
    temp=Path('F:/codex_tmp')/('r31r1-'+label); xml=temp.with_suffix('.xml'); temp.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src'+os.pathsep+'.',PYTHONIOENCODING='utf-8',TEMP=str(temp.parent),TMP=str(temp.parent),TMPDIR=str(temp.parent),WORKBENCH_API_BACKEND='duckdb',WORKBENCH_PG_DSN='dbname=r31r1_mock host=127.0.0.1 port=1 connect_timeout=1')
    before=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    r=subprocess.run([sys.executable,'-m','pytest',*scope,'-q','-p','no:cacheprovider','--basetemp='+str(temp),'--junitxml='+str(xml)],cwd=directory,env=env,capture_output=True)
    after=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    raw=xml.read_bytes(); tree=ET.fromstring(raw); cases=tree.findall('.//testcase')
    failures=[t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None]
    errors=len(tree.findall('.//error')); skipped=len(tree.findall('.//skipped'))
    result=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),scope=scope,tests=len(cases),passed=len(cases)-len(failures)-errors-skipped,failures=failures,errors=errors,skipped=skipped,deselected=0,exit_code=r.returncode,worktree_before_clean=before==b'',worktree_after_clean=after==b'',status='PASS_SCOPED_NO_NEW_FAILURES' if set(failures)==set(previous['failures']) and errors==skipped==0 and len(cases)>previous['tests'] else 'FAIL',historical_debt='R26-A01_SEPARATE_OPEN_NONBLOCKING_DEBT')
    write('reports/r31r1/'+label+'-tests.xml',raw); write('reports/r31r1/'+label+'-output.txt',r.stdout+r.stderr); write('reports/r31r1/'+label+'-summary.json',result)
    print(json.dumps(result),flush=True); assert result['status'].startswith('PASS')
    if label=='clean': assert before==after==b''
def evidence():
    assert validate_contract(C,ROOT)==[]
    from tests.test_v4_22_r31r1_repair import test_final,test_parent,test_authority
    matrices={}
    for family,fn,count in [('FINAL',test_final,6),('REFINT',test_parent,8),('AUTH',test_authority,6)]:
        rows=[]
        for i in range(1,count+1): fn(i); rows.append(dict(vector=f'R31R1-{family}-{i:02}',acceptance='PASS_LOCAL_DESIGN_VECTOR_ONLY'))
        matrices[family]=rows
    for name,family in [('FINAL_VERDICT_OPEN_ITEM_GATE','FINAL'),('OPEN_ITEM_CLOSURE_BINDING_GATE','FINAL'),('SESSION_PARENT_LINKAGE_GATE','REFINT'),('SESSION_PARENT_NEGATIVE_MATRIX','REFINT'),('ITEM_AUTHORITY_VALIDATION_GATE','AUTH'),('ITEM_AUTHORITY_NEGATIVE_MATRIX','AUTH'),('OPEN10_REFERENTIAL_INTEGRITY_RECHECK','REFINT')]:
        write('reports/r31r1/'+name+'.json',dict(status='PASS_LOCAL_REPAIRED',vectors=matrices[family],simulation_only=True,real_rows_written=0,open_items_closed=False,external_acceptance=False))
    baseline=json.loads((ROOT/'reports/r31r1/PROTECTED_BASELINE.json').read_bytes())
    changed={kind:[p for p,d in entries.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=d] for kind,entries in baseline.items() if isinstance(entries,dict)}
    absent={p:not (ROOT/p).exists() for p in C['protected_state']['accepted_head_absence']}
    assert not any(changed.values()) and all(absent.values())
    write('reports/r31r1/PROTECTED_BYTES.json',dict(status='PASS',changed=changed,accepted_head_absence=absent,current_state=C['current_state'],tdx_writes=False,real_rows_written=0))
def seal(source):
    evidence(); clean=json.loads((ROOT/'reports/r31r1/clean-summary.json').read_bytes()); local=json.loads((ROOT/'reports/r31r1/local-summary.json').read_bytes())
    assert clean['source_commit']==source and clean['tests']==local['tests'] and clean['failures']==local['failures']
    assert subprocess.check_output(['git','rev-parse',TAG+'^{}'],text=True).strip()==source
    assert subprocess.check_output(['git','cat-file','-t',TAG],text=True).strip()=='tag'
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='codex/v4-system-reform'
    closure=['clean-tests.xml','clean-output.txt','clean-summary.json','CLEAN_REGRESSION.json','LOCAL_TEST_SUMMARY.json','TESTED_SOURCE_GOVERNANCE.json','R31R1_CANDIDATE_SEAL.json','CLEAN_CHECKOUT_PROOF.json']
    allow=['reports/r31r1/'+p for p in closure]+['docs/evidence/r31r1/R31R1_REPAIR_ACCEPTANCE.md']
    delta=subprocess.check_output(['git','diff','--name-only',source],text=True,encoding='utf8').splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z']).decode().split('\0')
    delta=sorted(set(delta+[p for p in untracked if p.startswith(('reports/r31r1/','docs/evidence/r31r1/'))]))
    assert set(delta)<=set(allow),delta
    write('reports/r31r1/CLEAN_CHECKOUT_PROOF.json',dict(source_commit=source,clean=clean['worktree_before_clean'] and clean['worktree_after_clean']))
    write('reports/r31r1/CLEAN_REGRESSION.json',clean); write('reports/r31r1/LOCAL_TEST_SUMMARY.json',local)
    write('reports/r31r1/TESTED_SOURCE_GOVERNANCE.json',dict(status='PASS',source_commit=source,annotated_tag=TAG,branch='codex/v4-system-reform',explicit_closure_allowlist=allow,post_test_delta=delta,post_test_semantic_drift=False))
    verdict=dict(R31R1_LOCAL_REPAIR='PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',R31_FINAL_VERDICT_OPEN_ITEM_ENFORCEMENT='PASS_LOCAL_REPAIRED',R31_OPEN10_SESSION_REFERENTIAL_INTEGRITY='PASS_LOCAL_REPAIRED',R31_ITEM_LEVEL_AUTHORITY_VALIDATION='PASS_LOCAL_REPAIRED',V4_22_CONTRACT_DESIGN='LOCAL_READY_FOR_EXTERNAL_AUDIT_AFTER_R31R1',V4_22_FINAL_AUDIT_ENTRY='BLOCKED_WAIT_REAL_GATES',V4_22_FINAL_PASS='NOT_GRANTED',V4_22_ACCEPTED_HEAD='NOT_CREATED',NEXT='STOP_WAIT_R31R1_INDEPENDENT_EXTERNAL_AUDIT',tested_source=source)
    write('reports/r31r1/R31R1_CANDIDATE_SEAL.json',verdict)
    write('docs/evidence/r31r1/R31R1_REPAIR_ACCEPTANCE.md',f'# R31R1 repair acceptance\n\nCONTRACT_DESIGN_ONLY. Tested source: `{source}`. Tag: `{TAG}`.\n\nThree narrow repairs passed local design vectors and exact clean regression: {clean["tests"]} tests, {clean["passed"]} passed; three inherited R26-A01 failures retained, zero new failures/errors/skips/deselections. Protected tracked and unrelated bytes unchanged. All current real open items remain open. No permissions or accepted head created.\n\nFinal formula requires independently bound explicit dispositions for OPEN-01..08 and OPEN-10; OPEN-09 remains nonblocking debt. Exact V4-21 required schemas are read from digest-bound authority; session parents bind publication/digest and event T0, with outcomes bound to processing publication rather than due date. Every item authority/evidence binding is checked against exact bytes and authorized domain membership.\n\n'+json.dumps(verdict,indent=2)+'\n')
if __name__=='__main__':
    if sys.argv[1]=='regression': regression(sys.argv[2],sys.argv[3])
    elif sys.argv[1]=='evidence': evidence()
    elif sys.argv[1]=='seal': seal(sys.argv[2])
