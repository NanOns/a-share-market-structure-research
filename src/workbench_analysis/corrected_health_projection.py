"""R4 producer metadata repair; frozen state-machine values remain unchanged."""
from copy import deepcopy
from pathlib import Path
from .corrected_owner_replay import load, checked, gzrows, gzwrite, ref, OUT
from .market_source_acquisition import write
from .v4_12_structure_io import FrozenContracts


def health_cell(state, mapping):
    support=state['state_observations']['support']
    known=support['quality']=='KNOWN' and support['state']!='UNKNOWN'
    return dict(value=mapping.get(support['state'],mapping['default']) if known else None,
                quality='KNOWN' if known else 'UNKNOWN',
                reason=[] if known else support.get('reason') or ['SUPPORT_STATE_UNKNOWN'])


def materialize_health(root):
    root=Path(root).resolve();out=root/OUT;replay=load(out/'PROFILE_STRUCTURE_REPLAY.json')
    c=FrozenContracts(root);mapping=c.config['output_schema']['structure_health_mapping'];receipts=[]
    contract=out/'HEALTH_PROJECTION_CONTRACT_V1.json'
    write(contract,dict(contract_id='V4_R4_STRUCTURE_HEALTH_METADATA_REPAIR_V1',mapping=mapping,
        source='Published active anchor support machine only',unknown_support='UNKNOWN',
        anchor_selection='COPY_PUBLISHED_ACTIVE_ID',business_threshold_changes=False,
        original_projection_preserved=True,production_admission=False))
    for owner in replay['owners']:
        day=owner['owner']['trade_date'];manifest=load(checked(root,owner['structure_manifest']))
        binding=next(a for a in manifest['artifacts'] if a['path'].endswith('runtime_security.jsonl.gz'))
        rows={r['identity']['security_id']:r for r in gzrows(checked(root,binding))}
        projected=gzrows(checked(root,owner['advanced_projection']))
        for p in projected:
            row=rows[p['security_id']];aid=row['active_selection'].get('active_anchor_id')
            state=next((s for s in row['anchor_states'] if s['anchor_id']==aid),None)
            cell=health_cell(state,mapping) if state else dict(value=None,quality='UNKNOWN',reason=['NO_PUBLISHED_ACTIVE_ANCHOR'])
            cell.update(producer_contract_id='V4_R4_STRUCTURE_HEALTH_METADATA_REPAIR_V1',
                 source_refs=[binding,ref(root,contract)],selected_anchor_id=aid)
            p['fields']['structure_health']=cell
        result=dict(trade_date=day,projection=gzwrite(root,out/'owners'/day/'advanced_structure_projection_v2.jsonl.gz',projected),
             known=sum(p['fields']['structure_health']['quality']=='KNOWN' for p in projected),total=len(projected),
             contract=ref(root,contract),original_projection=owner['advanced_projection'])
        receipts.append(result)
    write(out/'HEALTH_PROJECTION_REPLAY.json',dict(owners=receipts,acceptance='METADATA_REPAIRED_PENDING_QA'))
    return receipts
