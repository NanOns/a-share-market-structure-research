"""Two disclosed detached regression scopes, no bypass flags or deselection."""
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts import validate_r17r1_clean_detached as checkout

ROOT=Path(__file__).resolve().parents[1]
BASE='f4ad7d632e53734798c064f011e2b53ecd99bc27'

def atomic(path, value, raw=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    data=value if raw else (json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
    tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(data);os.replace(tmp,path)

def suite(directory, command, output):
    before=checkout.call(['git','status','--porcelain'],cwd=directory)
    result=subprocess.run(command,cwd=directory,capture_output=True,text=True,encoding='utf8',errors='replace')
    atomic(output/'runner.log',(result.stdout+result.stderr).encode(),raw=True)
    after=checkout.call(['git','status','--porcelain'],cwd=directory)
    assert before==after==b'', 'DETACHED_SOURCE_CHANGED'
    assert result.returncode==0, str(output/'runner.log')
    return dict(command=command,exit_code=result.returncode,git_status_before=before.decode(),git_status_after=after.decode())

def restore_representation(directory, manifest):
    restored=[]
    for path,ref in manifest.items():
        target=directory/path;raw=target.read_bytes()
        if hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref['bytes']:continue
        canonical=raw.replace(b'\r\n',b'\n')
        variants=[canonical,canonical.replace(b'\n',b'\r\n')]
        value=next((v for v in variants if len(v)==ref['bytes'] and hashlib.sha256(v).hexdigest()==ref['sha256']),None)
        assert value is not None, 'NO_EXACT_REPRESENTATION:'+path
        atomic(target,value,raw=True);restored.append(path)
    if restored:
        checkout.call(['git','add','-f','--',*restored],cwd=directory)
        assert subprocess.run(['git','diff','--cached','--quiet','--exit-code'],cwd=directory).returncode==0
    assert not checkout.call(['git','status','--porcelain'],cwd=directory).strip()
    return restored

def run(source, output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    # Retained sources/tests/oracles must be literally identical Git objects.
    changed=checkout.call(['git','diff',BASE,source,'--name-only','--','src','tests','config','scripts','reports/v4_14_replay_r18'],text=True,encoding='utf8').splitlines()
    allowed=lambda p:p=='tests/test_r19_promotion_contracts.py' or p.startswith(('config/v4_15_','scripts/r19','scripts/validate_r19')) or p=='config/v4_14_accepted_entry_contract_v1.json'
    assert all(allowed(p) for p in changed), changed
    manifest=json.loads((ROOT/'reports/r19a/PROTECTED_WORKTREE_BYTES.json').read_bytes())
    checkout.CHECKOUT=ROOT.parent/'r19-audited-baseline-clean'
    base_lfs=checkout.prepare(BASE);base_dir=checkout.CHECKOUT
    base_repr=restore_representation(base_dir,manifest)
    baseline_out=output/'audited_baseline';baseline_out.mkdir(exist_ok=True)
    existing_gate=baseline_out/'regression_gate.json'
    if existing_gate.exists():
        previous=json.loads(existing_gate.read_bytes())
        assert previous['source_sha']==BASE and previous['exit_code']==0 and previous['git_status_before']==previous['git_status_after']==''
        assert checkout.call(['git','rev-parse','HEAD'],cwd=base_dir,text=True).strip()==BASE
        assert not checkout.call(['git','status','--porcelain'],cwd=base_dir).strip()
        baseline=dict(command=previous['command'],exit_code=0,git_status_before='',git_status_after='',reused_unchanged_baseline_evidence=True)
    else:
        baseline=suite(base_dir,[sys.executable,'-m','scripts.validate_r18_rollback_regression',str(baseline_out)],baseline_out)
    bg=json.loads((baseline_out/'regression_gate.json').read_bytes())
    assert bg['pass_count']==1168 and not bg['failures'] and not bg['errors'] and not bg['skipped'] and bg['deselected_count']==0
    checkout.CHECKOUT=ROOT.parent/'r19-candidate-clean'
    candidate_lfs=checkout.prepare(source);candidate_dir=checkout.CHECKOUT
    candidate_manifest=dict(manifest)
    def collect(value):
        if isinstance(value,list):
            for item in value:collect(item)
        elif isinstance(value,dict):
            if {'path','sha256','bytes'}<=set(value):
                binding={k:value[k] for k in ['path','sha256','bytes']}
                assert value['path'] not in candidate_manifest or candidate_manifest[value['path']]==binding
                candidate_manifest[value['path']]=binding
            else:
                for item in value.values():collect(item)
    package=json.loads((candidate_dir/'config/v4_15_contract_package_v1.json').read_bytes())
    collect(package)
    for item in package['contracts']:collect(json.loads((candidate_dir/item['path']).read_bytes()))
    candidate_repr=restore_representation(candidate_dir,candidate_manifest)
    candidate_out=output/'candidate';candidate_out.mkdir(exist_ok=True)
    xml=candidate_out/'regression.xml'
    candidate=suite(candidate_dir,[sys.executable,'-m','pytest','tests/test_r19_promotion_contracts.py','-q','--junitxml='+str(xml)],candidate_out)
    cases=list(ET.parse(xml).iter('testcase'));failed=[c.attrib for c in cases if c.find('failure') is not None];errors=[c.attrib for c in cases if c.find('error') is not None];skipped=[c.attrib for c in cases if c.find('skipped') is not None]
    log=(candidate_out/'runner.log').read_text();require_no_deselection=not re.search(r'\b[1-9]\d* deselected\b',log)
    assert cases and not failed and not errors and not skipped and require_no_deselection
    cg=dict(**candidate,source_sha=source,passed=len(cases),failed=failed,errors=errors,skipped=skipped,deselected=0)
    atomic(candidate_out/'regression_gate.json',cg)
    receipt=dict(status='PASS',execution_baseline=BASE,tested_candidate_source=source,contexts={'audited_baseline':dict(**baseline,source_sha=BASE,passed=1168,failed=0,errors=0,skipped=0,deselected=0,scope='ALL_RETAINED_OWNER_REPLAY_ROLLBACK_TESTS_ON_EXACT_AUDITED_PREPROMOTION_STATE',verified_lfs_objects=base_lfs,exact_byte_representation_restored=base_repr),'candidate':dict(**candidate,source_sha=source,passed=len(cases),failed=0,errors=0,skipped=0,deselected=0,scope='CURRENT_PROMOTION_AND_R19B_C_D_CONTRACT_ORACLES',verified_lfs_objects=candidate_lfs,exact_byte_representation_restored=candidate_repr)},total_passed=1168+len(cases),no_broad_deselection=True,no_assume_unchanged_or_skip_worktree=True,retained_source_blobs_unchanged=True,current_pointer_legacy_runtime_compatibility='NOT_CLAIMED_SEPARATE_OPEN_AUDIT_R19_AUDIT_02',formal_migration=False,V4_15_RUNTIME='NOT_IMPLEMENTED',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    atomic(output/'CLEAN_DETACHED_REGRESSION.json',receipt)
    print(json.dumps(receipt))

if __name__=='__main__':run(*sys.argv[1:])
