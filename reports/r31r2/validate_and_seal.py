"""Atomic R31R2 evidence, clean regression and exact source sealing."""
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from reports.r31.audit_oracle import validate_contract,final_verdict
TAG='codex/r31r2-v4-22-audit-contract-failclosed-tested-source-20261005'
C=json.loads((ROOT/'config/v4_22_independent_audit_contract_v1.json').read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,v):
    p=ROOT/name; p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.stage')
    raw=v if isinstance(v,bytes) else (v if isinstance(v,str) else json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()
    with t.open('wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    os.replace(t,p)
def regression(directory,label):
    directory=Path(directory).resolve(); previous=json.loads((ROOT/'reports/r31r1/CLEAN_REGRESSION.json').read_bytes())
    scope=previous['scope']+['tests/test_v4_22_r31r2_repair.py']
    temp=Path('F:/codex_tmp/test_temp')/('r31r2-'+label); xml=temp.with_suffix('.xml'); temp.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src'+os.pathsep+'.',PYTHONIOENCODING='utf-8',TEMP=str(temp.parent),TMP=str(temp.parent),TMPDIR=str(temp.parent),WORKBENCH_API_BACKEND='duckdb',WORKBENCH_PG_DSN='dbname=r31r2_mock host=127.0.0.1 port=1 connect_timeout=1')
    assert directory != temp and not directory.is_relative_to(temp) and not temp.is_relative_to(directory)
    before=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    r=subprocess.run([sys.executable,'-m','pytest',*scope,'-q','-p','no:cacheprovider','--basetemp='+str(temp),'--junitxml='+str(xml)],cwd=directory,env=env,capture_output=True)
    after=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    raw=xml.read_bytes(); tree=ET.fromstring(raw); cases=tree.findall('.//testcase')
    failures=[t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None]
    errors=len(tree.findall('.//error')); skipped=len(tree.findall('.//skipped'))
    result=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),scope=scope,tests=len(cases),passed=len(cases)-len(failures)-errors-skipped,failures=failures,errors=errors,skipped=skipped,deselected=0,exit_code=r.returncode,worktree_before_clean=before==b'',worktree_after_clean=after==b'',status='PASS_SCOPED_NO_NEW_FAILURES' if set(failures)==set(previous['failures']) and errors==skipped==0 and len(cases)>previous['tests'] else 'FAIL',historical_debt='R26-A01_SEPARATE_OPEN_NONBLOCKING_DEBT')
    write('reports/r31r2/'+label+'-tests.xml',raw); write('reports/r31r2/'+label+'-output.txt',r.stdout+r.stderr); write('reports/r31r2/'+label+'-summary.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='scope'}),flush=True); assert result['status'].startswith('PASS')
    if label=='clean': assert before==after==b''
def evidence():
    assert validate_contract(C,ROOT)==[]
    import tempfile
    from tests.test_v4_22_r31r2_repair import closure_vector,ledger_vector,test_build
    matrices={}
    with tempfile.TemporaryDirectory(prefix='r31r2-vectors-',dir='F:/codex_tmp/test_temp') as folder:
        base=Path(folder)
        closures=[]
        for i in range(1,14):
            directory=base/str(i); directory.mkdir(); closures.append(closure_vector(i,directory))
        matrices['CLOSURE']=closures
        matrices['LEDGER']=[ledger_vector(i) for i in range(1,13)]
        builds=[]
        for i in range(1,5):
            directory=base/('build-'+str(i)); directory.mkdir(); test_build(i,directory); builds.append(dict(vector=f'R31R2-BUILD-{i:02}',status='PASS_LOCAL_DESIGN_ONLY'))
        matrices['BUILD']=builds
    from reports.r31r2.build_contract import build_bytes
    expected=build_bytes(ROOT); assert expected==(ROOT/'config/v4_22_independent_audit_contract_v1.json').read_bytes()
    for family,rows in matrices.items():
        write('reports/r31r2/'+family+'_REPAIR_GATE.json',dict(status='PASS_LOCAL_REPAIRED',vectors=rows,simulation_only=True,real_rows_written=0,current_real_closures=0,external_acceptance=False))
    write('reports/r31r2/REPRODUCIBILITY_GATE.json',dict(status='PASS_LOCAL_REPAIRED',canonical_sha256=hashlib.sha256(expected).hexdigest(),baseline=C['repair_provenance'],next_stage=C['next_stage'],vectors=builds))
    baseline=json.loads((ROOT/'reports/r31r2/PROTECTED_BASELINE.json').read_bytes())
    changed={kind:[p for p,d in entries.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=d] for kind,entries in baseline.items() if isinstance(entries,dict)}
    absent={p:not (ROOT/p).exists() for p in C['protected_state']['accepted_head_absence']}
    assert not any(changed.values()) and all(absent.values())
    write('reports/r31r2/PROTECTED_BYTES.json',dict(status='PASS',changed=changed,accepted_head_absence=absent,current_state=C['current_state'],tdx_writes=False,real_rows_written=0))
def seal(source):
    clean=json.loads((ROOT/'reports/r31r2/clean-summary.json').read_bytes()); local=json.loads((ROOT/'reports/r31r2/local-summary.json').read_bytes())
    assert clean['source_commit']==source and clean['tests']==local['tests'] and clean['failures']==local['failures']
    assert subprocess.check_output(['git','rev-parse',TAG+'^{}'],text=True).strip()==source
    assert subprocess.check_output(['git','cat-file','-t',TAG],text=True).strip()=='tag'
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='codex/v4-system-reform'
    closure=['clean-tests.xml','clean-output.txt','clean-summary.json','CLEAN_REGRESSION.json','LOCAL_TEST_SUMMARY.json','TESTED_SOURCE_GOVERNANCE.json','R31R2_CANDIDATE_SEAL.json','CLEAN_CHECKOUT_PROOF.json']
    allow=['reports/r31r2/'+p for p in closure]+['docs/evidence/r31r2/R31R2_REPAIR_ACCEPTANCE.md']
    delta=subprocess.check_output(['git','diff','--name-only',source],text=True,encoding='utf8').splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','-z']).decode().split('\0')
    delta=sorted(set(delta+[p for p in untracked if p.startswith(('reports/r31r2/','docs/evidence/r31r2/'))]))
    assert set(delta)<=set(allow),delta
    protected=json.loads((ROOT/'reports/r31r2/PROTECTED_BASELINE.json').read_bytes())
    assert all((ROOT/p).is_file() and sha(ROOT/p)==d for kind in ('tracked','unrelated') for p,d in protected[kind].items())
    write('reports/r31r2/CLEAN_CHECKOUT_PROOF.json',dict(source_commit=source,clean=clean['worktree_before_clean'] and clean['worktree_after_clean']))
    write('reports/r31r2/CLEAN_REGRESSION.json',clean); write('reports/r31r2/LOCAL_TEST_SUMMARY.json',local)
    write('reports/r31r2/TESTED_SOURCE_GOVERNANCE.json',dict(status='PASS',source_commit=source,annotated_tag=TAG,branch='codex/v4-system-reform',explicit_closure_allowlist=allow,post_test_delta=delta,post_test_semantic_drift=False))
    verdict=dict(R31R2_LOCAL_REPAIR='PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',R31_OPEN_ITEM_CLOSURE_EVIDENCE_VERIFICATION='PASS_LOCAL_REPAIRED',R31_CHILD_LEDGER_SCHEMA_FAIL_CLOSED='PASS_LOCAL_REPAIRED',R31_REPAIR_REPRODUCIBILITY_AND_STAGE_IDENTITY='PASS_LOCAL_REPAIRED',V4_22_CONTRACT_DESIGN='LOCAL_READY_FOR_EXTERNAL_AUDIT_AFTER_R31R2',V4_22_FINAL_AUDIT_ENTRY='BLOCKED_WAIT_REAL_GATES',V4_22_FINAL_PASS='NOT_GRANTED',V4_22_ACCEPTED_HEAD='NOT_CREATED',NEXT='STOP_WAIT_R31R2_INDEPENDENT_EXTERNAL_AUDIT',tested_source=source)
    write('reports/r31r2/R31R2_CANDIDATE_SEAL.json',verdict)
    write('docs/evidence/r31r2/R31R2_REPAIR_ACCEPTANCE.md',f'# R31R2 repair acceptance\n\nCONTRACT_DESIGN_ONLY. Tested source: `{source}`. Tag: `{TAG}`.\n\nThree narrow repairs passed local design vectors and exact clean regression: {clean["tests"]} tests, {clean["passed"]} passed; three inherited R26-A01 failures retained, zero new failures/errors/skips/deselections. Protected tracked and unrelated bytes unchanged. All current real open items remain open. No permissions or accepted head created.\n\nClosure evidence and expressly authorized closure authority are independently read by exact path, SHA and contract identity; canonical receipt digest alone is insufficient. Every supplied ledger row validates full required schema and exact lane/namespace/origin/publication rules before filtering diagnostic lanes. Historical builder refuses newer canonical contracts; the R31R2 builder deterministically reproduces version 1.0.2 from exact baseline Git bytes. OPEN-09 remains nonblocking; OPEN-01..08 and OPEN-10 still require exact disposition. User explicitly authorized the single obsolete R31R1 FINAL-05 assertion update; the new exact-readable simulation covers OPEN-09 nonblocking semantics without changing real records.\n\n'+json.dumps(verdict,indent=2)+'\n')
if __name__=='__main__':
    if sys.argv[1]=='regression': regression(sys.argv[2],sys.argv[3])
    elif sys.argv[1]=='evidence': evidence()
    elif sys.argv[1]=='seal': seal(sys.argv[2])
