"""Target-excluded recomputation, reusing frozen accepted V4-08/V4-04 owners."""
from copy import deepcopy
from sector.native_r5 import build_native, observed
from sector.rotation_r5 import evaluate_b0,advance_rotation,resolve_package
from sector.legacy_b2_r5 import build_b2_inputs,evaluate_b2
from v4.profile_core import relative
from .v4_13_io import digest,envelope,exact


def select_sector(candidates, complete=True):
    # READY is field-specific: uncertainty in any candidate cannot be ignored.
    if not complete or any(r['quality']!='READY' for r in candidates):return envelope(reason='UNKNOWN_REQUIRED_LOO_AUTHORITY_OR_HISTORY')
    if not candidates:return envelope(None,'NOT_APPLICABLE',None)
    order={'HIGH':0,'MEDIUM':1,'LOW':2}
    eligible=sorted(candidates,key=lambda r:(-int(r['confirmed_raw']),-int(r['warm_raw']),order[r['emergence']],-r['adjusted_seed_width'],r['sector_id']))
    return envelope(eligible[0]['sector_id'],'KNOWN',None)


def relative_sector(stock, current, target, native):
    if not native or not native['rank_eligible']:return envelope(reason='UNKNOWN_INSUFFICIENT_LOO_MEMBERS_OR_COVERAGE')
    inputs={f:stock.get(f) for f in ['rps5','rps20','rps20_delta3']}
    for n in (1,5):
        value=stock.get(f'stock_ret{n}');sector=native['fields'][f'sector_rs{n}']['value']
        inputs[f'rel_market_{n}']=value-sector if value is not None and sector is not None else None
    state=relative(inputs,stock.get('compression_state','UNKNOWN'),stock.get('ma_structure_state','UNKNOWN'))
    return envelope(None if state.value=='UNKNOWN' else state.value,'UNKNOWN' if state.value=='UNKNOWN' else 'KNOWN',state.unknown_reason,relative_substitutions=inputs,producer_contract_id=state.contract_id)


class LOOContextRuntime:
    def __init__(self, contracts):
        self.contracts=contracts;self.dep=contracts.dependencies
        self.params,self.registry=resolve_package(self.dep['rotation_contract'],self.dep['parameter_set'],exact(contracts.root,contracts.config['loo_context']['accepted_sector_dependencies']['parameter_set']),self.dep['field_registry'])

    def compute(self, binder, security_id, revision):
        relationships=binder.relationship(security_id);related={r['sector_id'] for r in binder.by_security.get(security_id,[])}
        # Exclusion precedes native, seed, cross-section, endpoint and rotation computation.
        scope=binder.memberships if binder.current else [r for sid in sorted(related) for r in binder.groups[sid]]
        members=[r for r in scope if r['security_id']!=security_id]
        current={s:r for s,r in binder.current.items() if s!=security_id}
        seed={s:v for s,v in binder.seed.items() if s!=security_id}
        lineage=digest(dict(excluded_target_id=security_id,membership_source=binder.membership_head['facts']['sha256'],non_target_related_members=sorted((r['sector_id'],r['security_id']) for r in members),history_digest=binder.history_digest))
        history={k:{s:r for s,r in v['current'].items() if s!=security_id} for k,v in binder.history.items()}
        prior_members={k:{sid:[s for s in ids if s!=security_id] for sid,ids in v['memberships'].items()} for k,v in binder.history.items()}
        prior_dates={k:v['trade_date'] for k,v in binder.history.items()}
        prior_native={}
        # Historical rank endpoints are rebuilt across each full endpoint universe.
        for k,v in binder.history.items():
            if v.get('accepted_owner_lineage') is not True:raise ValueError('UNACCEPTED_LOO_HISTORY')
            old_members=[r for r in v['membership_rows'] if r['security_id']!=security_id]
            result=build_native(old_members,history[k],target=v['trade_date'],snapshot_id=v['snapshot_id'],publication_id=lineage,parameter_set=self.dep['parameter_set'],source_bindings=v['source_refs'],seed={s:x for s,x in v.get('seed',{}).items() if s!=security_id},seed_capability=v.get('seed_capability',False))
            prior_native[k]={r['sector_id']:r for r in result}
        # With no accepted target primitive at all, every sector is provably rank-ineligible.
        # Skip unavailable cross-section arithmetic; do not reuse self-including results.
        active_members=members if current else [r for r in members if r['sector_id'] in related]
        native=build_native(active_members,current,target=binder.date,snapshot_id=binder.snapshot['snapshot_id'],publication_id=lineage,parameter_set=self.dep['parameter_set'],source_bindings={'accepted_input_digest':digest(binder.refs)},prior=history,prior_memberships=prior_members,prior_date=prior_dates,prior_sector_rows=prior_native,seed=seed,seed_capability=binder.seed_capability)
        b2inputs=build_b2_inputs(native,current,binder.date,self.dep['b2_contract']['source_parameters']) if 'source_parameters' in self.dep['b2_contract'] else None
        # Source parameters are exact bound dependencies, resolved in the caller package.
        if b2inputs is None:
            import json
            ast=self.dep['b2_contract'];source=json.loads(exact(self.contracts.root,dict(path=ast['source_parameter_path'],sha256=ast['source_parameter_sha256'])))
            b2inputs=build_b2_inputs(native,current,binder.date,source)
        output=[];candidates=[]
        for row in native:
            b0=evaluate_b0(row,self.dep['b0_contract'],self.params)
            ast=self.dep['b2_contract'];b2=evaluate_b2(b2inputs[row['sector_id']],ast,source_sha256=ast['source_sha256'],source_parameter_sha256=ast['source_parameter_sha256'],parameter_set_sha256=ast['parameter_set_sha256'])
            # A self-including prior rotation publication is never admitted.
            # Missing registered independent LOO episode lineage remains unavailable.
            rotation=advance_rotation(row,current,prior_publication=None,prior_members=prior_members.get(1,{}).get(row['sector_id']),prior_core=history.get(1,{}),calendar_sessions=binder.sessions,contract=self.dep['rotation_contract'],registry=self.dep['field_registry'],parameters=self.params,seed_truth=seed,seed_capability=binder.seed_capability)
            if row['sector_id'] not in related:continue
            rs=relative_sector(binder.stock.get(security_id,{}),binder.current.get(security_id,{}),binder.date,row)
            item=dict(security_id=security_id,trade_date=binder.date,revision=revision,cutoff=binder.cutoff,sector_id=row['sector_id'],sector_type=row['sector_type'],membership_snapshot_id=binder.snapshot['snapshot_id'],membership_source_revision=binder.snapshot['source_revision_id'],membership_basis='PIT_OBSERVED' if binder.membership_complete else 'UNKNOWN',loo_identity=lineage,excluded_target_id=security_id,member_ids=row['member_ids'],native_fields=row['fields'],common_member_quality=row['common_member_quality'],b0=b0,b2=b2,rotation=rotation,relative_sector_state=rs,quality='UNKNOWN',reason='ACCEPTED_OWNER_HISTORY_OR_CAPABILITY_UNAVAILABLE',source_refs=binder.refs)
            output.append(item)
            candidates.append(dict(sector_id=row['sector_id'],quality='UNKNOWN',confirmed_raw=None,warm_raw=None,emergence=None,adjusted_seed_width=row['fields']['base_seed_width_adjusted']['value']))
        zero_related=related-{r['sector_id'] for r in output}
        # Known empty non-target sector is NA; it does not fabricate an eligible candidate.
        support=select_sector(candidates,binder.membership_complete)
        if zero_related and candidates:support=envelope(reason='UNKNOWN_OR_EMPTY_NON_TARGET_CANDIDATE')
        primary=relationships['primary_industry'];primary_row=next((r for r in output if r['sector_id']==primary['value']),None)
        rs=primary_row['relative_sector_state'] if primary_row else envelope(None,'NOT_APPLICABLE' if primary['quality']=='NOT_APPLICABLE' else 'UNKNOWN','NO_PRIMARY_LOO_SECTOR')
        return dict(**relationships,algorithmic_support_sector=support,relative_sector_state=rs,contexts=output,loo_identity=lineage,full_rank_universe=[r['sector_id'] for r in native if r['rank_eligible']],zero_non_target_sectors=sorted(zero_related),raw_qualification_digest=digest(dict(stock=binder.stock.get(security_id),seed=binder.seed.get(security_id))))
