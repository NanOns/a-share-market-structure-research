from pathlib import Path
from collections import defaultdict
from copy import deepcopy
from workbench_analysis.corrected_owner_replay import load,checked,gzrows,ref
from workbench_analysis.tdx_member_retro_r43 import EVIDENCE,validate_snapshot,digest
from workbench_analysis.market_source_acquisition import write
from sector.native_r5 import build_native


def main(root):
    out=root/EVIDENCE;s=load(out/'MEMBER_SNAPSHOT_S.json');rows=validate_snapshot(s,root)
    owner=load(out/'owner_v3/PROFILE_STRUCTURE_REPLAY.json')['owners'][0]['owner'];day=owner['trade_date']
    core={r['security_id']:r for r in gzrows(checked(root,owner['core']))};current={}
    for sid,r in core.items():
        fields={k:dict(value=v['value'],quality='ACCEPTED' if v.get('quality_state')=='OBSERVED' else 'UNKNOWN',max_source_date=day) for k,v in r['fields'].items()}
        current[sid]=dict(trade_date=day,fields=fields)
    members=[dict(r,snapshot_id=s['membership_snapshot_id'],target_trade_date=day) for r in rows
        if r['security_id'] in core and r['list_date'] and r['list_date']<=day and (not r['delist_date'] or r['delist_date']>day) and 'DERIVED_PARENT' not in r['source']]
    groups=defaultdict(set)
    for r in members:groups[r['sector_id']].add(r['security_id'])
    concepts=sorted(k for k,v in groups.items() if k.startswith('THEME:') and len(v)>20)
    a=concepts[0];b=next(x for x in concepts[1:] if groups[a]-groups[x]);sid=next(x for x in sorted(groups[a]-groups[b]) if current[x]['fields']['ret5']['value'] is not None)
    parameters=load(root/'config/v4_08_algorithm_parameter_set_r5.json');sources=dict(core=owner['core'],membership=ref(root,out/'MEMBER_SNAPSHOT_S.json'))
    def compute(ms,snapshot):
        return build_native(ms,current,target=day,snapshot_id=snapshot,publication_id='R43_ACTUAL_MEMBER_MOVE_QA',parameter_set=parameters,source_bindings=sources)
    before=compute(members,s['membership_snapshot_id']);repeat=compute(members,s['membership_snapshot_id'])
    assert digest(before)==digest(repeat)
    moved=deepcopy(members);row=next(x for x in moved if x['sector_id']==a and x['security_id']==sid);row['sector_id']=b
    new_id='QA_NEW_MEMBER_S:'+digest(moved)
    for row in moved:row['snapshot_id']=new_id
    after=compute(moved,new_id);beforeby={r['sector_id']:r for r in before};afterby={r['sector_id']:r for r in after}
    primitives=('sector_rs1','sector_rs5','sector_rs20','sector_member_count','breadth_ret1','breadth_ret5','breadth_ret20')
    changed=[];unchanged=[]
    for sector in beforeby:
        same=all(beforeby[sector]['fields'][k]['value']==afterby[sector]['fields'][k]['value'] for k in primitives)
        (unchanged if same else changed).append(sector)
        if sector not in (a,b):assert same
    assert a in changed and b in changed
    rank_changes=[sector for sector in beforeby if any(beforeby[sector]['fields']['sector_rs'+str(n)+'_pct']['value']!=afterby[sector]['fields']['sector_rs'+str(n)+'_pct']['value'] for n in (5,20,60))]
    assert checked(root,owner['core']).exists() and checked(root,owner['raw']).exists()
    write(out/'W4_MEMBERSHIP_MOVE_AND_DETERMINISM_QA.json',dict(trade_date=day,actual_snapshot=ref(root,out/'MEMBER_SNAPSHOT_S.json'),
        actual_core=owner['core'],actual_raw=owner['raw'],security_id=sid,moved_from=a,moved_to=b,
        affected_native_primitives=changed,unaffected_native_primitive_count=len(unchanged),cross_section_rank_changes=rank_changes,
        cross_section_rank_policy='Ranking is a global downstream dependency; unrelated group primitives stay fixed but cross-section percentile may change',
        two_same_input_native_digest=digest(before),deterministic=True,test_mutation_new_snapshot_id=new_id,
        acceptance='REAL_S_MEMBER_MOVE_AND_DETERMINISM_PASS',production_mutation=False))


if __name__=='__main__':main(Path(__file__).resolve().parents[1])
