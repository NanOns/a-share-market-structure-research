"""Read-only remote Git proof; never relies on a tested-source bundle."""
import json,subprocess
from scripts.r20_io import ROOT,read

def verify():
    seal=read('reports/r20e/V4_15_RUNTIME_CANDIDATE_R20_SEAL.json');source=seal['tested_source'];g=seal['tested_source_governance']
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    subprocess.run(['git','merge-base','--is-ancestor',source,head],cwd=ROOT,check=True)
    changed=subprocess.check_output(['git','diff','--name-only',source,head],cwd=ROOT).decode().splitlines()
    if any(not p.startswith(('reports/r20','docs/audits/V4_R20')) for p in changed):raise ValueError('FINAL_SEAL_MUST_BE_EVIDENCE_ONLY')
    raw=subprocess.check_output(['git','ls-remote',g['remote_url'],g['immutable_tag_ref'],g['immutable_tag_ref']+'^{}',g['final_branch_ref']],cwd=ROOT).decode()
    refs={line.split()[1]:line.split()[0] for line in raw.splitlines()}
    if refs.get(g['immutable_tag_ref']+'^{}',refs.get(g['immutable_tag_ref']))!=source:raise ValueError('TESTED_SOURCE_NOT_EXACT_REMOTE_TAG')
    if refs.get(g['final_branch_ref'])!=head:raise ValueError('FINAL_HEAD_NOT_REMOTE_BRANCH')
    return dict(REMOTE_TESTED_SOURCE_ADDRESSABILITY='PASS_LOCAL',tested_source=source,immutable_remote_tag=g['immutable_tag_ref'],remote_branch=g['final_branch_ref'],remote_final_head=head,tested_source_in_final_ancestry=True,final_commit_evidence_only=True,bundle_only=False,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
if __name__=='__main__':print(json.dumps(verify(),indent=2))
