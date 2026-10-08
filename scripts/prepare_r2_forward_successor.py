"""Stage Forward owner upgrade without changing the live authority."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader,build_snapshot
from workbench_service.joint_release import AUTHORITY,validate,checked_path
from workbench_service.current_v4_context import digest,SourceInvalid
OUT=ROOT/'docs/evidence/r2_forward_continuation_20261008'

def main():
    final='--final' in sys.argv
    name='FINAL_CANDIDATE.json' if final else 'CANDIDATE.json'
    if (OUT/name).exists():raise SourceInvalid('FORWARD_SUCCESSOR_FROZEN')
    before=(ROOT/AUTHORITY).read_bytes();candidate=json.loads(before);reader=ProductionV4ResearchReader(ROOT)
    owner=json.loads((ROOT/'data/v4/r2_daily_candidates/forward_v2_20261008/v4_forward_operational_authority_v1.json').read_bytes())
    publication=json.loads(checked_path(ROOT,owner['publication']).read_bytes())
    old=reader.manifest['domain_features']['forward']
    assert publication['enrollments']==old['enrollments']
    assert len(publication['enrollments'])==117 and len(publication['plans'])==585
    assert publication['settlement_gate']['due_count']==0 and publication['settlement_gate']['actual_price_reads']==0
    assert all(o['outcome_status']=='PENDING' and o['R_N'] is None for o in publication['outcomes'])
    assert len(publication['t0_freezes'])==117
    write(OUT/'REAL_COHORT_ORACLE.json',dict(result='PASS',actual_enrollments=117,actual_plans=585,t0_freezes=117,
        enrollment_source_unchanged=True,actual_due=0,actual_price_reads=0,real_maturity_proven=False,
        legacy_outcomes_preserved=publication['legacy_outcomes']==old['outcomes'],source=owner['publication']))
    owners=copy.deepcopy(candidate['daily_owner_authorities']);owners['forward']=owner
    snapshot=build_snapshot(ROOT,publish=False,focus_override=dict(trade_date=candidate['trade_date'],input_data_head=owner['input_data_head'],
        publication=reader.manifest['sources']['focus_operational'],journal=reader.manifest['sources']['focus_journal']),authority_overrides=owners)
    candidate.update(snapshot=snapshot['pointer'],daily_owner_authorities=owners)
    if final:
        source=ROOT/'src/workbench_service/static/research'
        build=digest(__import__('workbench_service.current_v4_context',fromlist=['canonical']).canonical(
            {p.name:digest(p.read_bytes()) for p in sorted(source.iterdir()) if p.is_file()}))
        assets={}
        for p in sorted(source.iterdir()):
            if not p.is_file():continue
            target=ROOT/'data/v4/ui_releases'/build/p.name
            if not target.exists():write(target,p.read_bytes())
            assert target.read_bytes()==p.read_bytes();assets[p.name]=ref(target)
        candidate.update(ui_build_id=build,ui_assets=assets)
    validate(ROOT,candidate)
    assert (ROOT/AUTHORITY).read_bytes()==before
    write(OUT/name,candidate);write(OUT/('FINAL_SNAPSHOT.json' if final else 'SNAPSHOT.json'),snapshot)
    if not (OUT/'PREDECESSOR.json').exists():write(OUT/'PREDECESSOR.json',dict(authority=json.loads(before),sha256=digest(before)))
    print(json.dumps(dict(result='FORWARD_CANDIDATE_STAGED',context_token='research-v4-'+candidate['snapshot']['manifest']['sha256'])))

if __name__=='__main__':main()
