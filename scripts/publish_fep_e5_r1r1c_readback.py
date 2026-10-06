"""Read-only GitHub publication verification after the authorized Git push."""
import json, subprocess, sys
from scripts import run_fep_e5_r1r1c as r

REPO='NanOns/a-share-market-structure-research'
BRANCH='codex/v4-system-reform'

def api(path):
    return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/{path}'],cwd=r.ROOT))

def record(sha):
    assert r.b.git('rev-parse','HEAD').decode().strip()==sha
    remote=r.b.git('ls-remote','origin','refs/heads/'+BRANCH).decode().split()[0]
    assert remote==sha
    commit=api('commits/'+sha);assert commit['sha']==sha
    paths=r.b.git('diff','--name-only','-z',r.BASE,sha).decode().split('\0')
    # Large historical artifact inventories truncate the recursive GitHub API.
    # Read only exact nonrecursive directory trees, caching shared ancestors.
    cache={sha:api('git/trees/'+sha)}
    def entry_at(path):
        tree_sha=sha
        for part in path.split('/'):
            if tree_sha not in cache:cache[tree_sha]=api('git/trees/'+tree_sha)
            tree=cache[tree_sha];assert not tree.get('truncated')
            entry=next(x for x in tree['tree'] if x['path']==part)
            tree_sha=entry['sha']
        assert entry['type']=='blob'
        return entry
    files=[]
    for path in filter(None,paths):
        local=r.b.git('rev-parse',sha+':'+path).decode().strip()
        size=int(r.b.git('cat-file','-s',local).decode())
        entry=entry_at(path)
        assert entry['sha']==local and entry['size']==size
        files.append(dict(path=path,git_blob=local,bytes=size,status='PASS',url=f'https://github.com/{REPO}/blob/{sha}/{path}'))
    checks=api('commits/'+sha+'/check-runs');status=api('commits/'+sha+'/status');workflows=api('actions/workflows')
    r.emit('REMOTE_PUBLICATION_READBACK',dict(status='REMOTE_CANDIDATE_VISIBLE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',
        baseline=r.BASE,code_sha=sha,local_HEAD=sha,remote_branch_HEAD=remote,github_commit_SHA=commit['sha'],
        github_parent_SHAs=[x['sha'] for x in commit['parents']],branch=BRANCH,files=files,
        all_changed_files_remote_blob_and_size_verified=True,changed_files=len(files),tree_read_strategy='EXACT_NONRECURSIVE_DIRECTORY_TREES',
        commit_url=commit['html_url'],external_acceptance=False,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1C'))
    r.emit('REMOTE_CI_READBACK',dict(commit=sha,check_runs=checks,commit_status=status,workflows=workflows,
        CI_pass_claim=False,reason='Report configured GitHub checks exactly; absence of workflows/checks is not CI PASS.'))
    print('Verified remote commit and',len(files),'changed blobs; external_acceptance=false')

if __name__=='__main__':record(sys.argv[1])
