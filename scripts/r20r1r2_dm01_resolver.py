"""Resolve accepted native daily components through production batch chains."""
import json
from pathlib import Path
from scripts.r20r1r2_io import ROOT,ref,exact,require,digest

HEAD='data/v4/V4_DATA_ACCEPTED_HEAD.json'
REGISTRY='config/v4_15_maturity_t0_lineage_r20r1r1_v2.json'

def dates(calendar):return [x['trade_date'] if isinstance(x,dict) else x for x in calendar['session_dates']]
def artifact(receipt):return dict(path=receipt['artifact_path'],sha256=receipt['artifact_sha256'],bytes=receipt['artifact_bytes'])

def component(receipt,date,parent,components,root):
    require(receipt['component_id']=='ADJUSTED_DAILY' and receipt['contract_id']=='DM01_ADJUSTED_DAILY_INCREMENT_R3_3','NATIVE_COMPONENT_RECEIPT')
    require(receipt['trade_date']==receipt['target_trade_date']==date and receipt['parent_data_head_digest']==parent['sha256'],'RECEIPT_DATE_PARENT')
    require(receipt['parent_component_bindings']==components,'PARENT_COMPONENT_MISMATCH')
    path=(Path(receipt['artifact_path']).parent/'receipt.json').as_posix();binding=ref(path,root)
    require(exact(binding,root)==receipt,'EXACT_ACCEPTED_RECEIPT_REQUIRED')
    a=artifact(receipt);payload=exact(a,root)
    require(payload['contract_id']=='DM01_ADJUSTED_DAILY_ARTIFACT_R3_3' and payload['trade_date']==date,'NATIVE_ARTIFACT_DATE')
    require(receipt['status'] in ['FULL_PASS','DEGRADED_PASS'] and len(payload['rows'])==receipt['row_count'] and digest(payload['rows'])==receipt['logical_digest'],'EXACT_COMPONENT_CONTENT')
    return dict(trade_date=date,artifact=a,receipt=binding)

def accepted_heads(root,selected=None):
    registry=json.loads((Path(root)/REGISTRY).read_bytes());anchor=registry['T0_data_archive'];heads=[];b=ref(HEAD,root);seen=set()
    while True:
        require(b['sha256'] not in seen,'DATA_HEAD_CYCLE');seen.add(b['sha256']);h=exact(b,root)
        require(h['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2','PRODUCTION_DATA_HEAD_REQUIRED')
        contract=exact(h['contract'],root);require(contract['contract_id']==h['contract_id'] and h['version']=='2.0.0' and set(h)==set(contract['required_fields']),'EXACT_PRODUCTION_HEAD_SCHEMA')
        heads.append((b,h))
        if (b['sha256'],b['bytes'])==(anchor['sha256'],anchor['bytes']):break
        parent=h['parent_archive'];require(h['parent_head_sha256']==parent['sha256'],'PARENT_DATA_HEAD_DIGEST')
        require(exact(parent,root)['accepted_trade_date']<h['accepted_trade_date'],'STRICT_BATCH_ADVANCE');b=parent
    heads.reverse()
    if selected is None:return heads
    exact(selected,root);matches=[i for i,(b,h) in enumerate(heads) if (b['sha256'],b['bytes'])==(selected['sha256'],selected['bytes'])]
    if not matches:
        # Existing acceptance-record evidence, rather than a second component registry,
        # admits an immutable prior accepted revision superseded at the same cutoff.
        admitted=[]
        for hb,h in heads[1:]:
            record=exact(h['external_acceptance_record'],root)
            admitted.extend((binding,h['accepted_trade_date']) for binding in record['evidence_bindings'] if isinstance(binding,dict) and binding.get('sha256')==selected['sha256'] and binding.get('bytes')==selected['bytes'])
        require(len(admitted)==1,'EXACT_ACCEPTED_DATA_SNAPSHOT')
        prior=exact(selected,root);require(prior['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2' and prior['accepted_trade_date']==admitted[0][1],'EXACT_SUPERSEDED_SAME_CUTOFF_HEAD')
        branch=[];b=selected;seen=set()
        while True:
            require(b['sha256'] not in seen,'ARCHIVED_HEAD_CYCLE');seen.add(b['sha256']);h=exact(b,root);require(h['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2' and h['version']=='2.0.0' and set(h)==set(exact(h['contract'],root)['required_fields']),'EXACT_ARCHIVED_HEAD_SCHEMA');branch.append((b,h))
            if (b['sha256'],b['bytes'])==(anchor['sha256'],anchor['bytes']):break
            require(h['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2' and h['parent_head_sha256']==h['parent_archive']['sha256'],'ARCHIVED_HEAD_PARENT')
            require(exact(h['parent_archive'],root)['accepted_trade_date']<h['accepted_trade_date'],'ARCHIVED_BATCH_ADVANCE');b=h['parent_archive']
        return list(reversed(branch))
    require(len(matches)==1,'ONE_ACCEPTED_DATA_SNAPSHOT')
    heads=heads[:matches[0]+1];heads[-1]=(selected,heads[-1][1]);return heads

def resolve_accepted_adjusted_daily_path(frozen_t0,due_date,current_data_head=None,root=ROOT):
    root=Path(root);heads=accepted_heads(root,current_data_head)
    base_ref,base=heads[0];require(base['accepted_trade_date']==frozen_t0,'EXACT_T0_DATE')
    calendar=exact(heads[-1][1]['calendar'],root);ss=dates(calendar);past=dates(exact(base['calendar'],root))
    require(ss==sorted(set(ss)) and ss[:len(past)]==past,'EXACT_CALENDAR_PREFIX')
    require(due_date in ss and frozen_t0<=due_date<=heads[-1][1]['accepted_trade_date'],'DUE_INSIDE_ACCEPTED_CUTOFF')
    t0_artifact=base['component_artifacts']['ADJUSTED_DAILY'];t0_receipt=base['component_permissions']['ADJUSTED_DAILY']['receipt'];r0=exact(t0_receipt,root);a0=exact(t0_artifact,root)
    require(artifact(r0)==t0_artifact and a0['trade_date']==frozen_t0 and a0['contract_id']=='DM01_ADJUSTED_DAILY_ARTIFACT_R3_3','EXACT_T0_NATIVE_COMPONENT')
    lineage=[];previous_head=base_ref;previous_components=base['component_artifacts'];previous_date=frozen_t0
    for hb,h in heads[1:]:
        require('FORWARD_EVALUATION_INPUTS' not in h['component_artifacts'],'FIXTURE_ONLY_HEAD_SHAPE_REJECTED')
        chain=exact(h['accepted_chain'],root);record=exact(h['external_acceptance_record'],root)
        require(chain['contract_id']=='DM01_ACCEPTED_CONTINUOUS_CHAIN_V1' and chain['anchor']['archive']==h['parent_archive'] and chain['anchor']['archive']==previous_head,'EXACT_ACCEPTED_BATCH_ANCHOR')
        require(chain['accepted_through']==record['accepted_through']==h['accepted_trade_date'] and chain['external_acceptance_record']==h['external_acceptance_record'],'EXACT_ACCEPTED_CHAIN_CUTOFF')
        require(record['external_acceptance']==h['external_acceptance']=='EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN','ACCEPTED_CHAIN_AUTHORITY')
        require(record['candidate_bindings']==[n['candidate'] for n in chain['nodes']],'WRONG_ACCEPTED_CHAIN_MEMBERSHIP')
        require(record['accepted_scope']['sessions']==[n['trade_date'] for n in chain['nodes']] and record['external_authority']==chain['external_authority'] and record['audited_head']==chain['external_authority']['audited_head'],'EXACT_ACCEPTANCE_SCOPE_AUTHORITY')
        exact(chain['external_authority']['document'],root)
        require(chain['nodes'] and h['final_candidate']==chain['nodes'][-1]['candidate'],'FINAL_CANDIDATE_MEMBERSHIP')
        require(not any(h['permissions'].values()) and not any(chain[k] for k in ['production','shadow','focus']),'NO_PERMISSION_UPGRADE')
        if root.resolve()==ROOT.resolve():
            require(record.get('fixture_scope') is None and chain.get('fixture_scope') is None,'FIXTURES_CANNOT_GRANT_REAL_AUTHORITY')
            require(chain['external_authority']['authority_kind']=='INDEPENDENT_EXTERNAL_ACCEPTANCE','FORMAL_EXTERNAL_ACCEPTANCE_REQUIRED')
        context=exact(chain['source_context'],root);require(context['calendar']['binding']==h['calendar'] and exact(chain['builder_contract'],root)['execution_context']==chain['source_context'],'ACCEPTED_CONTEXT_CALENDAR')
        parent=previous_head;components=previous_components
        for node in chain['nodes']:
            day=node['trade_date'];require(next((d for d in ss if d>previous_date),None)==day,'ACCEPTED_SESSION_GAP')
            require(node['parent']==parent,'CHAIN_PARENT_MISMATCH');candidate=exact(node['candidate'],root)
            require(candidate['contract_id']=='DM01_ATOMIC_CONTINUOUS_CANDIDATE_R3_3' and candidate['target_trade_date']==day and candidate['parent_data_head_digest']==parent['sha256'] and node['components']==candidate['components'],'EXACT_CANDIDATE_MEMBERSHIP')
            parent_context=exact(candidate['parent_context_binding'],root);manifest=exact(parent_context['component_manifest_binding'],root)
            require(parent_context['binding']==parent and parent_context['components']==components and manifest['components']==components and manifest['parent_data_head_digest']==parent['sha256'],'EXACT_PARENT_COMPONENT_MANIFEST')
            resolved=component(node['components']['ADJUSTED_DAILY'],day,parent,components,root)
            require(node['components']['ADJUSTED_DAILY']['source_revision']==candidate['source_freeze_digest'],'COMPONENT_SOURCE_FREEZE_REVISION')
            resolved.update(source_data_head=hb,accepted_chain=h['accepted_chain'],candidate=node['candidate'],source_context=chain['source_context'])
            lineage.append(resolved);components={k:artifact(v) for k,v in node['components'].items()};parent=node['candidate'];previous_date=day
        require(components==h['component_artifacts'],'HEAD_FINAL_COMPONENTS_ONLY')
        require(h['canonical_data_revision']==candidate['logical_digest'] and h['source_revision']==candidate['source_freeze_digest'],'HEAD_FINAL_REVISION_BINDINGS')
        final=candidate['components']['ADJUSTED_DAILY'];permission=h['component_permissions']['ADJUSTED_DAILY']
        require(permission['artifact']==artifact(final) and exact(permission['receipt'],root)==final,'FINAL_PERMISSION_RECEIPT')
        previous_head=hb;previous_components=components
    needed=ss[ss.index(frozen_t0)+1:ss.index(due_date)+1]
    path=[x for x in lineage if x['trade_date'] in needed]
    require([x['trade_date'] for x in path]==needed,'ONE_ACCEPTED_COMPONENT_PER_SESSION')
    return dict(contract_id='V4_15_ACCEPTED_DM01_PATH_RESOLUTION_V1',source_data_head=heads[-1][0],calendar=heads[-1][1]['calendar'],T0=frozen_t0,due_date=due_date,T0_adjusted_daily=t0_artifact,T0_component_receipt=t0_receipt,path=path)
