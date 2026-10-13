"""Exact frozen trigger observations; incomplete episode history stays censored."""
from pathlib import Path
from collections import Counter
from .r43_owner_replay import OUT,load,checked,gzrows,gzwrite,ref
from .market_source_acquisition import write
from .v4_12_ast_runtime import ASTEngine
from .v4_12_structure_io import FrozenContracts,digest

def materialize_breakout_observations(root):
    root=Path(root).resolve();out=root/OUT;c=FrozenContracts(root)
    replay=load(out/'PROFILE_STRUCTURE_REPLAY.json');receipts=[]
    contract=out/'RECONSTRUCTED_EPISODE_OBSERVATION_CONTRACT_V1.json'
    write(contract,dict(contract_id='RECONSTRUCTED_EPISODE_OBSERVATION_V1',task='R4.3 W5',trigger='Exact frozen definition.breakout_trigger',semantics='Known true/false qualifies only price trigger observation, never absence of previous episode. TRUE observations have immutable reconstructed observation IDs; prehistory left-censored.',formal_basic_breakout_override=False,AS_RECORDED=False,PIT_ELIGIBLE=False,acceptance='IN_PROGRESS',next_stage='FIELD_LOCAL_SOURCE_REVIEW'))
    for item in replay['owners']:
        day=item['owner']['trade_date'];manifest=load(checked(root,item['structure_manifest']))
        binding=next(r for r in manifest['artifacts'] if r['path'].endswith('runtime_security.jsonl.gz'));records=[]
        for row in gzrows(checked(root,binding)):
            observed=ASTEngine(c.config,row['breakout_input_bindings']).field('breakout_trigger').record()
            sid=row['identity']['security_id'];payload=dict(security_id=sid,trade_date=day,producer_contract_id='RECONSTRUCTED_EPISODE_OBSERVATION_V1',breakout_trigger=observed,basic_breakout_state=row['basic_breakout_state'],prior_episode_set_quality=row['breakout_episode_set_quality'],prior_episode_absence_proven=row['breakout_episode_set_quality']=='KNOWN',episode_boundary='LEFT_CENSORED_PRIOR_HISTORY' if row['breakout_episode_set_quality']!='KNOWN' else 'BOUND_EPISODE_SET',source_refs=[binding,ref(root,contract)],AS_RECORDED=False,PIT_ELIGIBLE=False,knowledge_lineage='RECONSTRUCTED_CORRECTED')
            payload['reconstructed_trigger_observation_id']=digest(payload) if observed['value'] is True else None
            records.append(payload)
        artifact=gzwrite(root,out/'owners'/day/'breakout_trigger_observations.jsonl.gz',records)
        receipts.append(dict(trade_date=day,rows=len(records),artifact=artifact,trigger_counts=dict(Counter(str(r['breakout_trigger']['value']) for r in records)),formal_breakout_counts=dict(Counter(r['basic_breakout_state'] for r in records)),left_censored_count=sum(not r['prior_episode_absence_proven'] for r in records)))
    write(out/'BREAKOUT_OBSERVATION_REPLAY.json',dict(contract=ref(root,contract),owners=receipts,acceptance='EXACT_FROZEN_TRIGGER_OBSERVATIONS_COMPUTED_PRIOR_ABSENCE_NOT_INVENTED',formal_state_overrides=0))
    return receipts
