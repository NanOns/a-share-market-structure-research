"""Read-only Structure projection and component-wise D3 profile enrichment."""
from copy import deepcopy
from .v4_13_io import envelope,digest


def fold_quality(qualities, table):
    if not qualities:raise ValueError('QUALITY_COMPONENTS_REQUIRED')
    result=qualities[0]
    for quality in qualities[1:]:result=table[result+'|'+quality]
    return result


def component(value=None, quality='UNKNOWN', reasons=(), refs=()):
    return dict(value=deepcopy(value),quality=quality,reasons=list(reasons),source_refs=deepcopy(list(refs)))


def sector_snapshot(selection, context, contracts, refs=()):
    schema=contracts.config['sector_context_state_schema'];table=contracts.config['quality_map']['component_pair_table']
    if selection['quality']=='NOT_APPLICABLE':return envelope(None,'NOT_APPLICABLE',None)
    names=list(schema['components'])
    if context is None:
        items={n:component(reasons=['UNKNOWN_SELECTED_LOO_CONTEXT'],refs=refs) for n in names}
        items['loo_confirmed_raw']=component(quality='NOT_IMPLEMENTED',reasons=['NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE'],refs=refs)
        items['loo_warm_raw']=component(quality='NOT_IMPLEMENTED',reasons=['AUD_AMOUNT_A_06_OPEN'],refs=refs)
        sector_id=None;sector_type=None;basis='PIT_OBSERVED' if selection.get('membership_basis')=='PIT_OBSERVED' else 'UNKNOWN'
    else:
        b0=context['b0'];b2=context['b2'];native=context['native_fields'];rotation=context['rotation'];rs=context['relative_sector_state']
        q=lambda s:'KNOWN' if s in ['TRUE','FALSE'] else 'UNKNOWN'
        val=lambda s:True if s=='TRUE' else False if s=='FALSE' else None
        items=dict(loo_b0_raw=component(val(b0['output_state']),q(b0['output_state']),b0['reason_codes'],refs),loo_confirmed_raw=component(quality='NOT_IMPLEMENTED',reasons=[b2['confirmed_reason']],refs=refs),loo_warm_raw=component(quality='NOT_IMPLEMENTED',reasons=[b2['warm_reason']],refs=refs),emergence=component(reasons=['UNKNOWN_ACCEPTED_EMERGENCE_CAPABILITY'],refs=refs),adjusted_seed_width=component(native['base_seed_width_adjusted']['value'],'KNOWN' if native['base_seed_width_adjusted']['quality']=='ACCEPTED' else 'UNKNOWN',[native['base_seed_width_adjusted']['reason_code']] if native['base_seed_width_adjusted']['reason_code'] else [],refs),rotation_core_state=component(None if rotation['output_state']=='UNKNOWN' else rotation['output_state'],'UNKNOWN' if rotation['output_state']=='UNKNOWN' else 'KNOWN',rotation.get('reason_codes',[]),refs),relative_sector_state=component(rs['value'],rs['quality'],[rs['reason']] if rs['reason'] else [],refs))
        sector_id=context['sector_id'];sector_type=context['sector_type'];basis=context['membership_basis']
    quality=fold_quality([items[n]['quality'] for n in names],table)
    obj=dict(selected_sector_id=sector_id,sector_type=sector_type,**items,membership_basis=basis,context_quality=quality,reasons=sorted({r for v in items.values() for r in v['reasons']}),source_refs=deepcopy(list(refs)))
    if set(obj)!=set(schema['required']):raise ValueError('STRUCTURED_CONTEXT_SCHEMA_MISMATCH')
    return envelope(obj,quality,None,refs)


def copy_structure(row, contracts, source_ref=None):
    config=contracts.config['projection'];out={};active=row.get('active_selection',{}).get('active_anchor_id') if row else None
    selected=next((state for state in row.get('anchor_states',[]) if state.get('anchor_id')==active),None) if row and active else None
    # Lookup by already-published active id; never select or calculate an Anchor.
    sources=dict(row or {},selected_anchor_state=selected)
    for name in config['fields']:
        if row is None:out[name]=envelope();continue
        value=sources
        for part in config['source_field_paths'][name].split('.'):
            value=value.get(part) if isinstance(value,dict) else None
        original=value if isinstance(value,dict) and 'quality' in value and 'value' in value else None
        if original:
            out[name]=deepcopy(original);out[name].setdefault('source_identity',[source_ref]);out[name].setdefault('reason',None)
        else:
            # Copy published quality/reason; do not classify known-null selection as NA.
            unknown=value is None or value=='UNKNOWN'
            quality='UNKNOWN' if unknown else 'KNOWN'
            reason=row.get('active_projection',{}).get('reason') if quality=='UNKNOWN' else None
            if name=='active_anchor_id':
                quality=row.get('active_selection',{}).get('quality','UNKNOWN')
                reason=row.get('active_selection',{}).get('reason')
            elif name=='basic_breakout_state':
                quality=row.get('breakout_projection_quality',row.get('active_projection',{}).get('breakout_projection_quality',quality))
                reason=row.get('breakout_projection_reason',row.get('active_projection',{}).get('breakout_projection_reason',reason))
            out[name]=envelope(deepcopy(value),quality,reason,[source_ref])
        out[name]['producer_identity']=dict(contract_id=config['source_publication_contract'],source_field=config['source_field_paths'][name])
    return out


def dual_enrichment(rotation, structure, contracts):
    table=contracts.config['quality_map']['component_pair_table']
    return dict(rotation_core_state=deepcopy(rotation['value']),rotation_quality=rotation['quality'],rotation_source_ref=deepcopy(rotation.get('source_identity',[])),structure_component=deepcopy(structure['value']),structure_quality=structure['quality'],structure_source_ref=deepcopy(structure.get('source_identity',[])),combined_quality=table[rotation['quality']+'|'+structure['quality']],reasons=[r for r in [rotation.get('reason'),structure.get('reason')] if r])


class ProfileRuntime:
    def __init__(self, contracts):self.contracts=contracts

    def compute(self, binder, security_id, revision, context_result):
        before=context_result['raw_qualification_digest'];relationships={k:deepcopy(context_result[k]) for k in ['primary_industry','supporting_concepts','algorithmic_support_sector','relative_sector_state']}
        basis='PIT_OBSERVED' if binder.membership_complete else 'UNKNOWN';selection=relationships['algorithmic_support_sector'];selection['membership_basis']=basis
        selected=next((r for r in context_result['contexts'] if r['sector_id']==selection['value']),None)
        refs=[]
        for r in binder.refs:
            if r:refs.append(dict(path=r['path'],sha256=r['sha256'],bytes=r.get('bytes',r.get('byte_count',r.get('actual_byte_count'))),producer_contract_id='LOO_CONTEXT_V1',trade_date=binder.date,available_at=binder.cutoff,source_revision='ARTIFACT_SHA256:'+r['sha256'],source_role='ACCEPTED_AUTHORITY_BINDING_NOT_TARGET_FACT_PUBLICATION',availability_role='ENGINEERING_REFERENCE_VERIFIED_BY_CUTOFF',sector_id=selection['value'],target_security_id=security_id,loo_identity=context_result['loo_identity']))
        snapshot=sector_snapshot(selection,selected,self.contracts,refs)
        fields=dict(**relationships,sector_context_state=snapshot,sector_context_quality=envelope(snapshot['quality'],'KNOWN',None,refs))
        copied=copy_structure(binder.structure.get(security_id),self.contracts,binder.structure_ref);fields.update(copied)
        rotation=component()
        if selected:
            r=selected['rotation'];rotation=envelope(None if r['output_state']=='UNKNOWN' else r['output_state'],'UNKNOWN' if r['output_state']=='UNKNOWN' else 'KNOWN',r.get('reason_codes'),[self.contracts.owner_refs['V4_08']])
        else:rotation=envelope(refs=[self.contracts.owner_refs['V4_08']])
        sq=fold_quality([f['quality'] for f in copied.values()],self.contracts.config['quality_map']['component_pair_table'])
        structure=envelope({k:deepcopy(v) for k,v in copied.items()},sq,None,[binder.structure_ref] if binder.structure_ref else [])
        enrichment=dual_enrichment(rotation,structure,self.contracts);fields['rotation_structure_enrichment']=envelope(enrichment,enrichment['combined_quality'],None,[self.contracts.owner_refs['V4_08'],self.contracts.owner_refs['V4_12']])
        registry={r['field']:r for r in self.contracts.config['field_registry']['fields']}
        for name,field in fields.items():
            spec=registry[name]
            if not field.get('source_identity'):
                field['source_identity']=[r['binding'] for r in spec['source_bindings']] if 'source_bindings' in spec else [spec['source_binding']]
            field.update(producer_contract_id=spec['producer_contract_id'],membership_basis=basis,loo_basis=context_result['loo_identity'])
        expected={r['field'] for r in self.contracts.config['field_registry']['fields']}
        if set(fields)!=expected:raise ValueError('ADVANCED_PROFILE_FIELDS_INCOMPLETE')
        after=digest(dict(stock=binder.stock.get(security_id),seed=binder.seed.get(security_id)))
        if before!=after:raise ValueError('CONTEXT_RAW_QUALIFICATION_MUTATION')
        return dict(security_id=security_id,trade_date=binder.date,revision=revision,cutoff=binder.cutoff,fields=fields,contract_digest=self.contracts.digest,membership_digest=binder.snapshot['snapshot_id'],membership_source_revision=binder.snapshot['source_revision_id'],loo_identity=context_result['loo_identity'],source_refs=binder.refs,loo_history_digest=binder.history_digest,structure_source_digest=binder.structure_ref['sha256'] if binder.structure_ref else None,prior_session_ref=binder.prior_session_ref,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,raw_qualification_before=before,raw_qualification_after=after)
