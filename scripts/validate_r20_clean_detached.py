"""Disclosed historical and current detached regression, with registered bytes only."""
import hashlib,json,subprocess,sys,re
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts import validate_r17r1_clean_detached as checkout
from scripts.r20_io import atomic
ROOT=Path(__file__).resolve().parents[1]
HISTORICAL='f4ad7d632e53734798c064f011e2b53ecd99bc27'

def ident(raw):return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

def historical_representations(directory,registry):
    """Legacy literal consumers get only specifically audited text variants."""
    restored=[]
    for e in registry['entries']:
        p=directory/e['path']
        if e['mode']!='AUDITED_CRLF_LF_EQUIVALENT_TEXT' or not p.exists():continue
        if e['source_kind']!='TEXT' or e['lfs_object_identity']:raise ValueError('NO_BINARY_NORMALIZATION')
        oid=checkout.call(['git','rev-parse','HEAD:'+e['path']],cwd=directory,text=True).strip()
        if oid!=e['git_blob_oid']:continue # Different historical source version is never normalized.
        raw=p.read_bytes()
        if ident(raw) not in e['admitted_representations']:raise ValueError('UNREGISTERED_WORKTREE_REPRESENTATION')
        blob=checkout.call(['git','cat-file','blob',oid],cwd=directory)
        if ident(blob)!=e['git_blob_binding']:raise ValueError('REGISTERED_GIT_BLOB_MISMATCH')
        lf=blob.replace(b'\r\n',b'\n');variants=[blob,lf,lf.replace(b'\n',b'\r\n')]
        # Preserve audited local representation when legacy exact callers expect it.
        desired=e['worktree_binding']
        if desired not in e['accepted_bindings']:continue
        value=next((v for v in variants if ident(v)==desired),None)
        if value is None:raise ValueError('AUDITED_REPRESENTATION_MISSING')
        if value!=raw:
            atomic(p,value,raw=True);restored.append(e['path'])
    if restored:checkout.call(['git','add','-f','--',*restored],cwd=directory)
    assert subprocess.run(['git','diff','--cached','--quiet','--exit-code'],cwd=directory).returncode==0
    assert not checkout.call(['git','status','--porcelain'],cwd=directory).strip()
    return restored

def suite(directory,cmd,out):
    before=checkout.call(['git','status','--porcelain'],cwd=directory)
    result=subprocess.run(cmd,cwd=directory,capture_output=True,text=True,encoding='utf8',errors='replace')
    atomic(out/'runner.log',(result.stdout+result.stderr).encode(),raw=True)
    after=checkout.call(['git','status','--porcelain'],cwd=directory)
    assert before==after==b'','DETACHED_SOURCE_CHANGED'
    assert result.returncode==0,str(out/'runner.log')
    return {'command':cmd,'exit_code':0,'git_status_before':'','git_status_after':''}

def run(source,output):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    registry=json.loads((ROOT/'data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json').read_bytes())
    # Accepted business implementations must remain identical Git objects.
    changed=checkout.call(['git','diff','2020234020e09020aca13fd84cdabde6fbb81f50',source,'--name-only','--','src'],text=True,encoding='utf8').splitlines()
    allowed={'src/workbench_analysis/v4_14_authority.py','src/workbench_analysis/v4_current_stage_authority.py','src/workbench_analysis/v4_portable_exact.py','src/workbench_analysis/v4_15_persistence.py','src/workbench_analysis/v4_15_radar_cohort.py','src/workbench_analysis/v4_15_settlement.py'}
    assert set(changed)<=allowed,changed
    checkout.CHECKOUT=ROOT.parent/'r20-historical-clean'
    hydrated=checkout.prepare(HISTORICAL);historical=checkout.CHECKOUT
    representations=historical_representations(historical,registry)
    ho=out/'historical';ho.mkdir(exist_ok=True)
    h=suite(historical,[sys.executable,'-m','scripts.validate_r18_rollback_regression',str(ho)],ho)
    hg=json.loads((ho/'regression_gate.json').read_bytes())
    assert hg['pass_count']==1168 and not hg['failures'] and not hg['errors'] and not hg['skipped'] and hg['deselected_count']==0
    h.update(source_sha=HISTORICAL,passed=1168,scope='ALL_RETAINED_OWNER_R17_R18_REPLAY_ROLLBACK_IN_EXACT_PREPROMOTION_CONTEXT',verified_lfs_objects=hydrated,registered_representations=representations)
    checkout.CHECKOUT=ROOT.parent/'r20-r19-contracts-clean'
    r19_source='2020234020e09020aca13fd84cdabde6fbb81f50'
    r19_lfs=checkout.prepare(r19_source);r19_directory=checkout.CHECKOUT
    r19_representations=historical_representations(r19_directory,registry)
    ro=out/'r19_contracts';ro.mkdir(exist_ok=True);r19_xml=ro/'tests.xml'
    r19=suite(r19_directory,[sys.executable,'-m','pytest','tests/test_r19_promotion_contracts.py','-q','--junitxml='+str(r19_xml)],ro)
    r19_cases=list(ET.parse(r19_xml).iter('testcase'))
    assert len(r19_cases)==62 and not any(c.find(k) is not None for c in r19_cases for k in ('failure','error','skipped'))
    assert not re.search(r'\b[1-9]\d* deselected\b',(ro/'runner.log').read_text())
    r19.update(source_sha=r19_source,passed=62,scope='ALL_R19_PROMOTION_AND_FROZEN_CONTRACT_TESTS_IN_EXACT_EXTERNALLY_AUDITED_R19_CONTEXT',verified_lfs_objects=r19_lfs,registered_representations=r19_representations)
    checkout.CHECKOUT=ROOT.parent/'r20-candidate-clean'
    lfs=checkout.prepare(source);candidate=checkout.CHECKOUT
    co=out/'candidate';co.mkdir(exist_ok=True);xml=co/'tests.xml'
    # Explicit complete R20 current suites: no tests deselected.
    tests=sorted(str(p.relative_to(candidate)).replace('\\','/') for p in (candidate/'tests').glob('test_r20*.py'))
    assert any('r20e' in p for p in tests) and len(tests)>=5
    c=suite(candidate,[sys.executable,'-m','pytest',*tests,'-q','--junitxml='+str(xml)],co)
    cases=list(ET.parse(xml).iter('testcase'))
    assert cases and not any(c.find(k) is not None for c in cases for k in ('failure','error','skipped'))
    assert not re.search(r'\b[1-9]\d* deselected\b',(co/'runner.log').read_text())
    c.update(source_sha=source,passed=len(cases),scope='ALL_R20_CURRENT_AUTHORITY_PORTABILITY_RADAR_COHORT_SETTLEMENT_E2E_ORACLE_TESTS',verified_lfs_objects=lfs,source_representation='UNMODIFIED_CHECKOUT_EXPLICIT_PORTABLE_READER')
    receipt=dict(status='PASS_LOCAL',tested_source=source,contexts={'historical':h,'r19_contracts':r19,'current':c},total_passed=1168+62+len(cases),failures=0,errors=0,skipped=0,deselected=0,no_broad_deselection=True,accepted_business_algorithms_unchanged=True)
    atomic(out/'CLEAN_DETACHED_REGRESSION.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':run(*sys.argv[1:])
