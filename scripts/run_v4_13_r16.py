"""Explicit real accepted-source run/readback. No provider or raw data producer."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import argparse,json
from collections import Counter
from workbench_analysis.v4_13_io import FrozenContracts,canonical,digest,file_ref,atomic
from workbench_analysis.v4_13_input_binder import AcceptedInputBinder
from workbench_analysis.v4_13_loo_runtime import LOOContextRuntime
from workbench_analysis.v4_13_profile_runtime import ProfileRuntime
from workbench_analysis.v4_13_publication import publish_stream,readback


def run(revision,cutoff,limit=None):
    contracts=FrozenContracts(ROOT);binder=AcceptedInputBinder(contracts,'2026-09-30',cutoff);binder.load_structure()
    engine=LOOContextRuntime(contracts);projector=ProfileRuntime(contracts);profiles=[];contexts=[]
    # Exact PIT Head formal industry scope; every accepted industry identity is included.
    identity_head=json.loads((ROOT/'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json').read_bytes())['identity_head']
    identity=json.loads(__import__('workbench_analysis.v4_13_io',fromlist=['exact']).exact(ROOT,identity_head))
    universe=sorted({r['security_id'] for r in binder.memberships if r['sector_type']=='INDUSTRY'})
    if len(universe)!=binder.membership_head['formal_rows_by_type']['INDUSTRY']:raise ValueError('PIT_UNIVERSE_SCOPE_INCOMPLETE')
    mapping=json.loads(__import__('workbench_analysis.v4_13_io',fromlist=['exact']).exact(ROOT,identity['identity_revision']))
    if not set(universe)<={r['security_id'] for r in mapping['records']}:raise ValueError('UNACCEPTED_SECURITY_IDENTITY')
    if limit is not None:universe=universe[:limit]
    counts=Counter()
    def records():
        for index,sid in enumerate(universe):
            result=engine.compute(binder,sid,revision);profile=projector.compute(binder,sid,revision,result)
            for name,field in profile['fields'].items():counts[name+':'+field['quality']]+=1
            compact=[]
            for original in result['contexts']:
                # Transport only: preserve owner values/qualities/parameters/predicates;
                # exact row source refs carry the shared publication provenance once.
                row=dict(original)
                row['native_fields']={n:{k:v for k,v in item.items() if k not in ['source_publications','input_digests']} for n,item in row['native_fields'].items()}
                row['rotation']={k:v for k,v in row['rotation'].items() if k not in ['fields','native_fields']}
                compact.append(row)
            yield profile,compact
            if (index+1)%500==0:print(f'PROCESSED={index+1}/{len(universe)}',flush=True)
        diagnostics['field_quality_counts']=dict(counts)
    diagnostics=dict(authority_counters=binder.counters,field_quality_counts=dict(counts),capabilities={'current_membership':'AVAILABLE_EXACT_PIT','target_core_native':'UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE','target_seed':'UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE','loo_history':'UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE','legacy_B2':'NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE','structure':'AUTHORIZED_PUBLICATION_AVAILABLE_CAPABILITY_SCOPED' if binder.structure_ref else 'UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'},universe_count=len(universe))
    source_versions=[]
    for p in sorted((ROOT/'src/workbench_analysis').glob('v4_13_*.py')):
        original=file_ref(ROOT,p.relative_to(ROOT).as_posix());archived='reports/v4_13_runtime_r16/source_versions/'+original['sha256']+'/'+p.name
        source_versions.append(dict(**atomic(ROOT,archived,p.read_bytes(),append_only=True),original_path=original['path']))
    metadata=dict(contract_refs=contracts.refs,contract_digest=contracts.digest,input_accepted_head_refs=list(contracts.owner_refs.values()),membership_snapshot_identity=binder.snapshot,membership_digest=digest(binder.memberships),loo_history_digest=binder.history_digest,structure_source_digest=binder.structure_ref['sha256'] if binder.structure_ref else None,prior_session_ref=binder.prior_session_ref,available_at=cutoff,source_refs=binder.refs,diagnostics=diagnostics,scope='REAL_ACCEPTED_SOURCE_SCOPED_ENGINEERING' if limit is None else 'SMOKE_LIMITED_NOT_REAL_ACCEPTANCE',runtime_source_refs=source_versions,transport_contract_id='V4_13_R16_CONTEXT_TRANSPORT_V1_SHARED_PROVENANCE_ONCE')
    reference=publish_stream(ROOT,'real' if limit is None else 'smoke','2026-09-30',revision,records(),metadata)
    result=readback(ROOT,reference,collect=False);assert result['profile_advanced']==len(universe)
    return dict(manifest=reference,diagnostics=diagnostics,readback='PASS')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--revision',default='r1');p.add_argument('--cutoff',default='2026-10-02T15:00:00+08:00');p.add_argument('--limit',type=int);p.add_argument('--readback-manifest')
    args=p.parse_args()
    if args.readback_manifest:
        result=readback(ROOT,file_ref(ROOT,args.readback_manifest),collect=False);print(json.dumps(dict(readback='PASS',profile_count=result['profile_advanced'],manifest=result['manifest']),sort_keys=True))
    else:print(json.dumps(run(args.revision,args.cutoff,args.limit),sort_keys=True))
