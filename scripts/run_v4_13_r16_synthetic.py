"""Synthetic contract witness only; never an accepted data producer or replay source."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from test_v4_13_r16a_runtime import fixture_binder
from workbench_analysis.v4_13_io import FrozenContracts,atomic,canonical,digest,file_ref
from workbench_analysis.v4_13_loo_runtime import LOOContextRuntime
from workbench_analysis.v4_13_profile_runtime import ProfileRuntime
from workbench_analysis.v4_13_publication import publish,readback


def run(revision):
    contracts=FrozenContracts(ROOT);binder=fixture_binder(contracts)
    concepts=['A','Z'] if revision=='r1' else ['A','B','Z']
    for name in concepts:
        members=[dict(r,sector_id=name,sector_type='THEME') for r in binder.memberships if r['sector_type']=='INDUSTRY']
        binder.memberships.extend(members);binder.groups[name]=members
        for r in members:binder.by_security[r['security_id']].append(r)
    binder.snapshot['snapshot_id']=digest(sorted((r['sector_id'],r['security_id']) for r in binder.memberships))
    binder.snapshot['source_revision_id']='SYNTHETIC_MEMBERSHIP_REVISION_'+revision
    for r in binder.memberships:r['snapshot_id']=binder.snapshot['snapshot_id']
    fixture=atomic(ROOT,f'reports/v4_13_runtime_r16/synthetic_closed/2026-09-30/{revision}/independent_input.json',canonical(dict(scope='SYNTHETIC_NOT_ACCEPTED_FACTS',memberships=binder.memberships,core=binder.stock,native=binder.current,seed=binder.seed)),append_only=True)
    binder.refs=[fixture];binder.membership_head['facts']=fixture
    binder.structure={};binder.structure_ref=None;binder.prior_session_ref={'trade_date':'2026-09-29','context_publication':None,'reason':'SYNTHETIC_NO_PRIOR_CONTEXT'}
    if revision!='r1':
        old='reports/v4_13_runtime_r16/synthetic_closed/2026-09-30/r1/manifest.json'
        previous=readback(ROOT,file_ref(ROOT,old))
        assert previous['profile_advanced'][0]['fields']['supporting_concepts']['value']==['A','Z']
    context=LOOContextRuntime(contracts).compute(binder,'target',revision)
    profile=ProfileRuntime(contracts).compute(binder,'target',revision,context)
    expected=dict(primary_industry='I',supporting_concepts=concepts,relative_sector_state='LEADING_ACCELERATING',algorithmic_support_quality='UNKNOWN',loo_member_ids=['a','b','c','d','e'],sector_rs1=1,seed_width=0,prior_session='2026-09-29')
    oracle_ref=atomic(ROOT,f'reports/v4_13_runtime_r16/synthetic_closed/2026-09-30/{revision}/independent_expected.json',canonical(expected),append_only=True)
    meta=dict(source_refs=[fixture],diagnostics={'scope':'SYNTHETIC_HAND_WRITTEN_ORACLE_NOT_ACCEPTED_FACTS'},contract_refs=contracts.refs,contract_digest=contracts.digest,prior_session_ref=binder.prior_session_ref,membership_digest=digest(binder.memberships),loo_history_digest=binder.history_digest,structure_source_digest=None,available_at=binder.cutoff,scope='SYNTHETIC_OWNER_PARITY_WITNESS_NOT_REAL_AUTHORITY',independent_expected_ref=oracle_ref)
    ref=publish(ROOT,'synthetic_closed','2026-09-30',revision,[profile],context['contexts'],meta)
    print(json.dumps(ref,sort_keys=True))


if __name__=='__main__':run(sys.argv[1])
