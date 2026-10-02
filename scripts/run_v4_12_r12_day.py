"""Fresh-process Snapshot V2 replay; synthetic inputs isolated outside runtime."""
import argparse,json,sys
from pathlib import Path
from decimal import Decimal
from scripts.v4_11_promotion_contract_r1 import ROOT
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore,exact_json
from workbench_analysis.v4_12_multi_anchor_engine import MultiAnchorEngine
from workbench_analysis.v4_12_frozen_snapshot_v2 import InputBinderV2,SnapshotMaterializerV2
from workbench_analysis.v4_12_anchor_runtime import coordinate_view
CUTOFF='2026-10-02T06:00:00+00:00'
class SyntheticBinderV2(InputBinderV2):
    def __init__(self,c,date,fixture):
        super().__init__(c,date,CUTOFF);self.fixture=fixture;self.calls=0
        self.data={'component_artifacts':{'RAW_DAILY':{'path':'SYNTHETIC_RAW'},'ADJUSTED_DAILY':{'path':'SYNTHETIC_ADJUSTED'}}}
    def source(self,ref):return {'SYNTHETIC':dict(qfq_mul='1',qfq_add='0')}
    def bind(self,sid,prior_snapshot=None,extra_namespaces=None):
        if prior_snapshot is not None:raise ValueError('COMMON_F0_CANNOT_SELECT_ANCHOR')
        self.calls+=1;self.bound_prior=None;values={**self.contracts.config['machine_vectors']['defaults'],**self.fixture['values']}
        facts={n:self.record(r,values.get(n),'KNOWN' if values.get(n) is not None else 'UNKNOWN',None if values.get(n) is not None else 'SYNTHETIC_MISSING',date=self.date) for n,r in self.fields.items() if r['field_role']!='D1_OUTPUT'}
        for n in ['post_creation_market_sessions','post_creation_evaluable_sessions']:facts[n]=self.record(self.fields[n],0,'KNOWN',date=self.date)
        return facts
    def local(self,facts,sid,prior):
        state=prior[0];anchor=state['anchor'];view=coordinate_view(anchor,facts['price_basis']['value'],facts['adjustment_source_revision']['value'],self.date,'overlay')
        def assign(n,v,reason=None):facts[n]=self.record(self.fields[n],v,'KNOWN' if v is not None else 'UNKNOWN',reason,date=self.date)
        assign('lo',view['lower'],view['reason']);assign('hi',view['upper'],view['reason'])
        assign('post_creation_market_sessions',sum(anchor['available_date']<d<=self.date for d in self.calendar))
        count=state['counter_state']['post_creation_evaluable_sessions'];assign('post_creation_evaluable_sessions',count+int(facts['evaluable']['value'] is True) if count is not None else None)
        if view['quality']!='KNOWN':assign('evaluable',None,view['reason'])
        if all(facts[n]['quality']=='KNOWN' for n in ['C','lo','hi']):
            c,lo,hi=(Decimal(str(facts[n]['value'])) for n in ['C','lo','hi']);assign('distance_zone',str(max(lo-c,c-hi,Decimal(0))))

def run(args):
    c=FrozenContracts(ROOT);engine=MultiAnchorEngine(c,args.date,CUTOFF,args.revision)
    if args.fixture:
        engine.binder=SyntheticBinderV2(c,args.date,json.loads((ROOT/args.fixture).read_bytes()));ids=['SYNTHETIC']
    else:ids=sorted(r['security_id'] for r in exact_json(ROOT,engine.binder.data['component_artifacts']['IDENTITY_UNIVERSE'])['rows'])
    prior=dict(frozen_manifest_v2=json.loads((ROOT/args.prior).read_bytes())) if args.prior else None
    results=[engine.evaluate(sid,prior) for sid in ids]
    if args.fixture:assert engine.binder.calls==len(ids)
    store=CandidateStore(ROOT,args.directory);refs=[]
    for name,rows,compressed in [('runtime_security.jsonl.gz',results,True),('state_observations.jsonl.gz',[o for r in results for o in r['observations']],True),('transitions.jsonl',[o for r in results for o in r['transitions']],False),('anchors.jsonl',[o for r in results for o in r['anchors']],False),('events.jsonl',[o for r in results for o in r['events']],False)]:refs.append(store.jsonl(name,rows,compressed))
    source=store.json('runtime_manifest.json',dict(contract_id='V4_12_R12_RUNTIME_CANDIDATE_MANIFEST',status='ENGINEERING_CANDIDATE_NOT_ACCEPTED',trade_date=args.date,revision=args.revision,available_at=CUTOFF,entry=c.entry_ref,contract_digest=c.digest,snapshot_contract=engine.state_ref,artifacts=refs,prior=prior,
        scope='SYNTHETIC_ENGINEERING_ONLY' if args.fixture else 'REAL_ACCEPTED_SOURCE_CANDIDATE',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,raw_fallback_count=0,provider_replacement_count=0,V4_11_candidate_substitution_count=0,common_F0_bind_count=len(ids)))
    snapshot=SnapshotMaterializerV2(c,store).seal(results,source,CUTOFF);store.json('snapshot_ref.json',snapshot)
    print(json.dumps(dict(date=args.date,revision=args.revision,securities=len(ids),anchors=sum(len(r['anchor_states']) for r in results),transitions=sum(len(r['transitions']) for r in results))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--revision',default='r1');p.add_argument('--directory',required=True);p.add_argument('--fixture');p.add_argument('--prior');run(p.parse_args())
