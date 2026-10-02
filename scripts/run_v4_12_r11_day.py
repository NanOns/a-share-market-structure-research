"""Fresh-process R11 engineering runner; synthetic fixture never grants source authority."""
import argparse,json,sys
from pathlib import Path
from decimal import Decimal
from scripts.v4_11_promotion_contract_r1 import ROOT
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore,exact_json,digest
from workbench_analysis.v4_12_structure_engine import StructureEngine
from workbench_analysis.v4_12_input_binder import InputBinder
from workbench_analysis.v4_12_frozen_snapshot import SnapshotMaterializer
from workbench_analysis.v4_12_ast_runtime import ASTEngine

CUTOFF='2026-10-02T06:00:00+00:00'

class SyntheticBinder(InputBinder):
    """Explicit synthetic scenario adapter outside runtime namespace, no accepted claim."""
    def __init__(self,c,date,fixture):
        super().__init__(c,date,CUTOFF);self.fixture=fixture
        self.data={'component_artifacts':{'RAW_DAILY':{'path':'SYNTHETIC_RAW'},'ADJUSTED_DAILY':{'path':'SYNTHETIC_ADJUSTED'}}}
    def source(self,ref):return {'SYNTHETIC':dict(qfq_mul='1',qfq_add='0')}
    def bind(self,sid,prior_snapshot=None,extra_namespaces=None):
        self.validate_namespaces(extra_namespaces);prior=self.prior(prior_snapshot,sid);self.bound_prior=prior
        values={**self.contracts.config['machine_vectors']['defaults'],**self.fixture['values']}
        facts={n:self.record(r,values.get(n),'KNOWN' if values.get(n) is not None else 'UNKNOWN',None if values.get(n) is not None else 'SYNTHETIC_MISSING',date=self.date) for n,r in self.fields.items() if r['field_role']!='D1_OUTPUT'}
        if prior:
            for n,r in self.fields.items():
                if r['field_role']=='FROZEN_PRIOR_D1':
                    item=prior[0]['facts'][n];facts[n]=self.record(r,item['value'],item['quality'],item['reason'],prior[1],self.previous)
            anchor=prior[0]['anchor'];counter=prior[0]['counter_state']
            lo,hi=anchor['anchor_raw_lower'],anchor['anchor_raw_upper']
            updates=dict(lo=lo,hi=hi,post_creation_market_sessions=sum(anchor['available_date']<d<=self.date for d in self.calendar),post_creation_evaluable_sessions=counter['post_creation_evaluable_sessions']+int(values['evaluable'] is True),prior_adjacent_evaluable=prior[0]['facts']['prior_adjacent_evaluable']['value'] is True)
            for n,v in updates.items():facts[n]=self.record(self.fields[n],v,'KNOWN',date=self.date)
        else:
            for n in ['post_creation_market_sessions','post_creation_evaluable_sessions']:facts[n]=self.record(self.fields[n],0,'KNOWN',date=self.date)
        # This is a declared local machine dependency, no independent rule implementation.
        support=ASTEngine(self.contracts.config,facts).target('support')
        facts['support_today']=self.record(self.fields['support_today'],support.value,support.quality,list(support.reasons))
        return facts

def run(args):
    c=FrozenContracts(ROOT);engine=StructureEngine(c,args.date,CUTOFF,args.revision)
    if args.fixture:
        fixture=json.loads((ROOT/args.fixture).read_bytes());engine.binder=SyntheticBinder(c,args.date,fixture);ids=['SYNTHETIC']
    else:ids=sorted(r['security_id'] for r in exact_json(ROOT,engine.binder.data['component_artifacts']['IDENTITY_UNIVERSE'])['rows'])
    prior=dict(frozen_manifest=json.loads((ROOT/args.prior).read_bytes())) if args.prior else None
    results=[engine.evaluate(sid,prior) for sid in ids]
    store=CandidateStore(ROOT,args.directory)
    refs=[store.jsonl('runtime_observations.jsonl.gz',[r['observation'] for r in results],True),store.jsonl('runtime_bindings.jsonl.gz',[r['bindings'] for r in results],True),store.jsonl('anchors.jsonl',[a for r in results for a in r['anchors']]),store.jsonl('events.jsonl',[a for r in results for a in r['events']]),store.jsonl('transitions.jsonl',[a for r in results for a in r['transitions']])]
    if 'state_observations' in results[0]:refs.append(store.jsonl('state_observations.jsonl.gz',[a for r in results for a in r['state_observations']],True))
    manifest=store.json('runtime_manifest.json',dict(contract_id='V4_12_R11_RUNTIME_CANDIDATE_MANIFEST',trade_date=args.date,revision=args.revision,available_at=CUTOFF,entry=c.entry_ref,contract_digest=c.digest,artifacts=refs,prior=prior,scope='SYNTHETIC_ENGINEERING_ONLY' if args.fixture else 'REAL_ACCEPTED_SOURCE_CANDIDATE',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False))
    snapshot=SnapshotMaterializer(c,store).seal(results,manifest,CUTOFF)
    store.json('snapshot_ref.json',snapshot)
    print(json.dumps(dict(date=args.date,revision=args.revision,count=len(ids),snapshot=snapshot)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--revision',default='r1');p.add_argument('--directory',required=True);p.add_argument('--fixture');p.add_argument('--prior');run(p.parse_args())
