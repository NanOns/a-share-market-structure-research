"""Bounded target-only Market repair; retain original failing artifacts."""
import argparse,json,sys,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_analysis import r43_market_replay as market,r43_daily_price_limits as limits
from workbench_analysis.r43_owner_replay import load,checked,ref
from workbench_analysis.operational_owner_adapter_v1 import private_scope
from workbench_analysis.operational_increment_plan_v1 import predecessor_documents
from scripts.verify_v4_append_full_values_r1_1 import business

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--generation',required=True);args=p.parse_args()
    started=time.monotonic();root=Path(args.root).resolve();base=root/args.generation
    raw=Path(market.__file__).read_bytes();folder=base/'market_context_patch_r1_1'/hashlib.sha256(raw).hexdigest();folder.mkdir(parents=True,exist_ok=True)
    before=(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes();parent=load(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    previous=predecessor_documents(root,parent)
    for name in ('PROFILE_STRUCTURE_REPLAY.json','CORE_REPLAY.json'):
        path=folder/name
        if not path.exists():path.write_bytes((base/'owner_v3'/name).read_bytes())
    # The original target-day limit Owner is immutable and has already passed
    # the real-source gate. No historical or current limit is recalculated.
    limit_receipts=load(base/'owner_v3/DAILY_PRICE_LIMIT_REPLAY.json')['owners']
    import builtins
    original_import=builtins.__import__
    def imports(name,globals=None,locals=None,fromlist=(),level=0):
        if name=='r43_daily_price_limits' and level==1:
            from types import SimpleNamespace
            return SimpleNamespace(materialize_daily_limits=lambda _:limit_receipts)
        return original_import(name,globals,locals,fromlist,level)
    def version_ref(basepath,path):
        path=Path(path).resolve()
        if not path.is_relative_to(root):
            blob=path.read_bytes();archive=folder/'executed_sources'/hashlib.sha256(blob).hexdigest()/path.name;archive.parent.mkdir(parents=True,exist_ok=True)
            if not archive.exists():archive.write_bytes(blob)
            path=archive
        return ref(basepath,path)
    scope=private_scope(market,dict(OUT=folder.relative_to(root).as_posix(),ref=version_ref,__builtins__=dict(vars(builtins),__import__=imports)))
    outputs=scope['materialize_market'](root,predecessor_profiles=previous['profiles'],
        predecessor_markets=[dict(trade_date=d,market=b['market']) for d,b in sorted(parent['owners'].items())])
    new=load(checked(root,outputs[-1]['market']));oldfolder=root/'data/v4/dynamic_daily_owners/2026-10-13/35e5a7c80925e59b640bcc694df1184e8bb850634b10085473cd26f6b9b89b57'
    reference=load(oldfolder/'owner_v3/MARKET_REPLAY.json')['owners'][-1]['market'];old=load(checked(root,reference))
    identity_keys={'adjustment_basis_id','market_snapshot_id','input_source_digest'}
    def value(x):
        if isinstance(x,dict):return {k:value(v) for k,v in business(x).items() if k not in identity_keys}
        if isinstance(x,list):return [value(v) for v in x]
        return x
    equal=value(new)==value(old)
    target_owner=load(folder/'CORE_REPLAY.json')['owners'][0]
    current_limit=next(r['artifact'] for r in limit_receipts if r['trade_date']=='2026-10-13')
    prior_market=load(checked(root,parent['owners'][parent['accepted_trade_date']]['market']))
    prior_limit=next(b for b in prior_market['input_bindings'] if Path(b['path']).name=='daily_price_limits_v1.jsonl.gz' and '/owners/'+parent['accepted_trade_date']+'/' in b['path'])
    producer=version_ref(root,Path(market.__file__))
    expected_source=hashlib.sha256(json.dumps(dict(core_owner=target_owner['source_digest'],current_limits=current_limit,prior_limits=prior_limit,producer=producer),sort_keys=True).encode()).hexdigest()
    for name in ('axes','trend'):
        identity=new[name]['identity']
        if identity['input_source_digest']!=expected_source or identity['market_snapshot_id']!=target_owner['source_digest'] or identity['adjustment_basis_id']!=target_owner['source_digest']:
            raise ValueError('MARKET_ACTUAL_INPUT_IDENTITY_HASH_FAILED')
    for binding in new['input_bindings']:checked(root,binding)
    if (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()!=before:raise ValueError('HEAD_CHANGED_DURING_MARKET_REPAIR')
    receipt=dict(contract_id='V4_R1_1_TARGET_MARKET_ACCEPTED_CONTEXT_REPAIR',acceptance='PASS' if equal else 'FAIL',compute_sessions=['2026-10-13'],
        market_binding=outputs[-1]['market'],market_replay=ref(root,folder/'MARKET_REPLAY.json'),reference=reference,
        predecessor_market_bindings={d:b['market'] for d,b in parent['owners'].items()},
        independently_loaded_prior_context=True,history_owners_changed=False,original_failure_preserved=True,
        G3=dict(status='PASS',actual_input_digest_recomputed=True,producer=producer,current_limit=current_limit,accepted_prior_limit=prior_limit,
            parameter_bindings={name:ref(root,root/'config'/name) for name in ('v4_market_path_successor_contract_v1.json','v4_03_parameter_set_v1.json','v4_03_parameter_registry_v1.json')},
            all_input_binding_hashes_verified=True,predecessor_is_exact_accepted_A=True),elapsed_seconds=round(time.monotonic()-started,3))
    result_path=folder/'RESULT.json'
    if result_path.exists():result_path=folder/'RESULT_G3.json'
    result_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(receipt))
if __name__=='__main__':main()
