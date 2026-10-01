"""Seal the clean-repair overlay, retaining R1 artifact and source archives."""
import subprocess
from scripts.stage_next_round_bundle_r2 import selected as original_selected
from scripts.next_round_bundle_r2 import ROOT,P,read,write,bind,verify_protected,atomic_bytes

EXTRA=['scripts/stage_next_round_bundle_r3.py','scripts/verify_next_round_bundle_clean_r3.py',
       'scripts/formalize_parallel_scoped_acceptance_r3.py',
       'docs/audits/NEXT_ROUND_R2_CLEAN_REPAIR_SUPPLEMENT_20261001.md',
       'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R12_FORMALIZATION_R2.json',
       'docs/audits/PARALLEL_SCOPED_ACCEPTANCE_CLEAN_REPRESENTATION_SUPPLEMENT_R3_20261001.md']

def main():
    verify_protected();paths=set(original_selected()+EXTRA)
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'data/v4/source_evidence/next_round_r2_clean_repair').rglob('*') if p.is_file())
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'tests/v4_parallel_scoped_formalization_r1').rglob('*.py'))
    textpaths=[p for p in paths if p.startswith(('src/','scripts/','tests/','config/')) and b'\r\n' in (ROOT/p).read_bytes()]
    attrs=(ROOT/'.gitattributes').read_bytes()
    missing=[p+' -text' for p in sorted(textpaths) if (p+' -text').encode() not in attrs]
    if missing:atomic_bytes('.gitattributes',attrs+b'\n'+('\n'.join(missing)+'\n').encode())
    path=P+'BATCH_CANDIDATE_ARTIFACT_MANIFEST_R2.json'
    refs=[bind(p) for p in sorted(paths) if p!=path]
    write(path,dict(contract_id='V4_NEXT_ROUND_R2_ARTIFACT_MANIFEST_R2',artifacts=refs,
        supersedes=bind(P+'BATCH_CANDIDATE_ARTIFACT_MANIFEST_R1.json'),manifest_self_excluded=True,
        current_scoped_formalization=bind(P+'scoped_acceptance/SCOPED_FORMALIZATION_CLOSURE_R3.json'),
        source_supersession=bind(P+'scoped_acceptance/CLEAN_REPAIR_ORIGINAL_SOURCE_ARCHIVES_R1.json'),
        scope='AUTHORIZED_R2_BATCH_AND_STRICT_CLEAN_REPRESENTATION_REPAIR_ONLY',external_acceptance=False))
    paths.add(path)
    for start in range(0,len(paths),60):subprocess.run(['git','add','-f','--',*sorted(paths)[start:start+60]],cwd=ROOT,check=True)
    staged=set(filter(None,subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode('utf8').split('\0')))
    if not staged.issubset(paths):raise ValueError('STAGING_OUTSIDE_CLEAN_REPAIR_SCOPE')
    verify_protected();print(dict(new_manifest=bind(path),staged=len(staged)))

if __name__=='__main__':main()
