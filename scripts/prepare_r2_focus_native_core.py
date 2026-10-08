"""Replay actual frozen days into a new native-Core namespace, preserving old log."""
import collections,gzip,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.joint_release import checked_path
from workbench_service.current_v4_context import canonical,digest
from focus_tracker.v4_native_core_journal import append
from focus_tracker.v4_native_core_adapter import CONTRACT,CAPABILITY
OUT=ROOT/'docs/evidence/r2_focus_native_core_continuation_20261008'

def main():
    r=ProductionV4ResearchReader(ROOT);day=r.context['trade_date'];authority=r.manifest['domain_features']['stocks'];old_ref=r.manifest['sources']['focus_journal'];old_bytes=checked_path(ROOT,old_ref).read_bytes()
    states=r.manifest['sources']['states'];prior=json.loads(gzip.decompress(checked_path(ROOT,states).read_bytes()))['prior_binding']
    source_by_digest={b['sha256']:b for b in (states,prior)}
    with sqlite3.connect(checked_path(ROOT,old_ref)) as db:
        days=list(db.execute('SELECT day,source_digest FROM days ORDER BY day'));inputs={d:json.loads(p) for d,p in db.execute('SELECT day,payload FROM day_inputs')};old=json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0])
    implementation={}
    for name in ('v4_path_adapter','v4_native_core_adapter','v4_native_core_journal','v4_native_core_daily_driver','v4_successor','path_state_v2','states','outcomes','price_path'):
        source=ROOT/'src/focus_tracker'/(name+'.py');raw=source.read_bytes();target=ROOT/'data/v4/r2_focus_native_core/implementations'/digest(raw)/source.name
        if not target.exists():write(target,raw)
        assert target.read_bytes()==raw;implementation[name]=ref(target)
    namespace=digest(canonical(dict(days=days,implementation=implementation,core=authority)))
    temp=Path('E:/codex_tmp/r2_native_core')/(namespace+'.sqlite')
    if temp.exists():raise RuntimeError('NATIVE_CORE_REPLAY_ALREADY_EXISTS_PRESERVED')
    head=None;receipts=[]
    for date,source_digest in days:
        current=inputs[date];current['implementation']=implementation
        current['native_core']={date:dict(contract_id=CAPABILITY,trade_date=date,price_basis=authority['price_basis'],factors=authority['factors'],profiles=authority['profiles'],series=authority['series'])} if date==day else {}
        result=append(temp,ROOT,source_by_digest[source_digest],head,path_inputs=current);head=result['head'];receipts.append(result)
    with sqlite3.connect(temp) as db:actual=json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0])
    assert len(actual['episodes'])==len(old['episodes']) and len(actual['events'])==len(old['events'])
    counts=collections.Counter();changes=[];comparisons=0
    for previous,new in zip(old['episodes'],actual['episodes']):
        for key in ('episode_id','parent_episode_id','anchors','start_date','end_date','outcomes'):assert previous.get(key)==new.get(key),(key,new['episode_id'])
        assert len(previous['observations'])==len(new['observations'])
        for a,b in zip(previous['observations'],new['observations']):
            for key in ('trade_date','event','membership','source_publication'):assert a.get(key)==b.get(key)
            for key in ('metrics','close','quality','target_state','suspended_dates','missing_dates','anchor_actual_bar'):assert a['price_path'].get(key)==b['price_path'].get(key)
            comparisons+=1;counts[b['path_resolution']]+=1
            native=b['native_core_evidence'];counts['native_'+native['status']]+=1
            if a['predicate_evidence']!=b['predicate_evidence']:changes.append(dict(episode_id=new['episode_id'],entity_id=new['entity_id'],trade_date=b['trade_date'],before=a['predicate_evidence'],after=b['predicate_evidence'],resolution=b['path_resolution'],native=native))
    assert checked_path(ROOT,old_ref).read_bytes()==old_bytes
    folder=ROOT/'data/v4/r2_focus_native_core'/head;folder.mkdir(parents=True,exist_ok=True);journal=folder/'journal.sqlite';write(journal,temp.read_bytes())
    publication=dict(actual,contract_id=CONTRACT,trade_date=day,earliest_valid_date=days[0][0],namespace='V4_NATIVE_CORE_CORRECTED_JOURNAL_V1',sources=dict(previous=r.manifest['sources']['focus_operational'],native_core=authority,implementation=implementation),knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,permissions=dict(read=True,automatic_event_write=False,manual_pin=False),legacy_history=dict(status='UNRECONCILED_PG_UNAVAILABLE',preserved=True),write_block_reason='NATIVE_CORE_CANDIDATE_REQUIRES_JOINT_QA')
    published=folder/'focus.json';write(published,publication)
    write(OUT/'REPLAY_ORACLE.json',dict(result='PASS',observation_comparisons=comparisons,episodes=len(actual['episodes']),changed_observations=len(changes),counts=dict(counts),changes=changes,original_journal=old_ref,old_journal_preserved=True,receipts=receipts,strict_pit=False))
    write(OUT/'FOCUS_CANDIDATE.json',dict(head=head,journal=ref(journal),publication=ref(published),trade_date=day))
    print(json.dumps(dict(result='STAGED',observations=comparisons,changes=len(changes),counts=dict(counts))))
if __name__=='__main__':main()
