"""Prepare a pending V2 policy in the authorized formal staging workspace."""
import hashlib,json,os
from pathlib import Path
from workbench_analysis.operational_daily_exact_policy_v2 import CONTRACT,KERNEL,PATH,REQUIRED_SOURCES
from workbench_analysis.r43_owner_replay import ref

ROOT=Path(__file__).resolve().parents[1]
STAGING=Path('G:/codex work/v4-production-20261012')
DOC='docs/upgrade/V4_AUTO_EXACT_DAILY_CONTINUATION_R1_20261013.md'
PREDECESSOR='config/read_only_operational_daily_release_policy_v1_1.json'

def policy(root):
    old=json.loads((root/PREDECESSOR).read_bytes())
    sources={b['path'] for b in old['accepted_algorithm_bindings']}|REQUIRED_SOURCES
    sources.discard('src/adjustment/tdx_adjustment.py')
    bindings=[]
    for name in sorted(sources):
        raw=(ROOT/name).read_bytes()
        if name.startswith('src/'):
            digest=hashlib.sha256(raw).hexdigest()
            archive=Path('data/v4/closeout_exact_daily_sources_v2')/digest/name
            target=root/archive
            if target.exists() and target.read_bytes()!=raw:raise ValueError('PRESERVE_EXACT_RUNTIME_SOURCE_ARCHIVE')
            if not target.exists():atomic(target,raw)
            bindings.append(dict(ref(root,target),module_path=name))
        else:bindings.append(ref(root,root/name))
    # Preserve the original complete checkpoint denominator; do not bind only
    # top-level orchestration while leaving imported Profile math unversioned.
    checkpoint=json.loads((ROOT/'docs/audits/v4_full_closeout_20261012/continuation_20261013/PROFILE_COMPONENT_CHECKPOINT_SOURCE_R1.json').read_bytes())
    components=[]
    for item in checkpoint['unchanged_component_sources']:
        name=item['path'];raw=(ROOT/name).read_bytes();sha=hashlib.sha256(raw).hexdigest()
        target=root/'data/v4/exact_component_sources_v2'/sha/name
        if target.exists() and target.read_bytes()!=raw:raise ValueError('PRESERVE_COMPONENT_SOURCE_ARCHIVE')
        if not target.exists():atomic(target,raw)
        components.append(dict(ref(root,target),module_path=name))
    return dict(contract_id=CONTRACT,adjustment_contract=KERNEL,publication_ready=False,
        status='PENDING_REAL_NUMERIC_AND_CONSUMER_ACCEPTANCE',historical_PIT_permission=False,
        automated_trading_permission=False,probability_claims=False,external_acceptance='NOT_GRANTED',
        task_contract=ref(root,root/DOC),predecessor_policy=ref(root,root/PREDECESSOR),
        accepted_algorithm_bindings=bindings,component_source_binding_contract='V4_EXACT_COMPONENT_SOURCE_BINDINGS_R2',component_source_bindings=components)

def atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.exact.tmp');temp.write_bytes(raw);os.replace(temp,path)

def prepare():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='R1');args=parser.parse_args()
    if not args.label.isalnum():raise ValueError('VERSIONED_PENDING_POLICY_STAGE_REQUIRED')
    record=ROOT/'docs/audits/v4_full_closeout_20261012/continuation_20261013/EXACT_DAILY_PENDING_STAGING_R1.json'
    record=record.with_name('EXACT_DAILY_PENDING_STAGING_'+args.label+'.json')
    if record.exists():raise ValueError('PRESERVE_PRIOR_STAGING_RECEIPT')
    if (STAGING/PREDECESSOR).read_bytes()!=(ROOT/PREDECESSOR).read_bytes():raise ValueError('PRESERVE_FORMAL_PREDECESSOR_POLICY')
    names=('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')
    heads={n:(STAGING/'data/v4'/n).read_bytes() for n in names}
    pending=policy(ROOT);rows=[]
    for name in [b.get('module_path',b['path']) for b in pending['accepted_algorithm_bindings']]+[DOC]:
        raw=(ROOT/name).read_bytes();target=STAGING/name
        if name.startswith('src/'):
            rows.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),storage='SEPARATE_IMMUTABLE_EXECUTED_SOURCE_VERSION'))
            continue
        if target.exists() and target.read_bytes()!=raw:
            old=target.read_bytes();archive=STAGING/'runtime/exact_daily_source_predecessors'/hashlib.sha256(old).hexdigest()/name
            if archive.exists():assert archive.read_bytes()==old
            else:atomic(archive,old)
        atomic(target,raw)
        rows.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest()))
    # Restore original accepted source namespaces from preserved exact copies.
    # Current executable bytes remain in their own content-addressed archives.
    old=json.loads((STAGING/PREDECESSOR).read_bytes())
    for binding in old['accepted_algorithm_bindings']:
        target=STAGING/binding['path']
        if hashlib.sha256(target.read_bytes()).hexdigest()==binding['sha256']:continue
        alternatives=[STAGING/'runtime/exact_daily_source_predecessors'/binding['sha256']/binding['path'],
            STAGING/'data/v4/closeout_runtime_sources_r1/upstream'/binding['path']]
        original=next((p for p in alternatives if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==binding['sha256']),None)
        if original is None:raise ValueError('EXACT_UPSTREAM_SOURCE_RESTORATION_REQUIRED:'+binding['path'])
        changed=target.read_bytes();archive=STAGING/'runtime/exact_daily_source_predecessors'/hashlib.sha256(changed).hexdigest()/binding['path']
        if not archive.exists():atomic(archive,changed)
        atomic(target,original.read_bytes())
    for root in (ROOT,STAGING):atomic(root/PATH,json.dumps(policy(root),indent=2).encode())
    assert all((STAGING/'data/v4'/n).read_bytes()==raw for n,raw in heads.items())
    result=dict(contract_id='V4_EXACT_DAILY_PENDING_STAGING_R1',files=rows,publication_ready=False,
        historical_policy_preserved=True,heads_unchanged={n:hashlib.sha256(raw).hexdigest() for n,raw in heads.items()})
    atomic(record,json.dumps(result,indent=2).encode())
    print(json.dumps(dict(status='PENDING_CANDIDATE_PREPARED',files=len(rows),published=False)))

if __name__=='__main__':prepare()
