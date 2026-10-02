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


def sector_snapshot(selection, context, contracts, refs=(),component_refs=None):
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
    if component_refs is not None:
        for name in names:items[name]['source_refs']=deepcopy(component_refs[name])
    quality=fold_quality([items[n]['quality'] for n in names],table)
    obj=dict(selected_sector_id=sector_id,sector_type=sector_type,**items,membership_basis=basis,context_quality=quality,reasons=sorted({r for v in items.values() for r in v['reasons']}),source_refs=deepcopy(list(refs)))
    if set(obj)!=set(schema['required']):raise ValueError('STRUCTURED_CONTEXT_SCHEMA_MISMATCH')
    return envelope(obj,quality,None,refs)


def copy_structure(row, contracts, source_ref=None):
    config=contracts.config['projection'];out={};active=row.get('active_selection',{}).get('active_anchor_id') if row else None
    if source_ref and 'producer_contract_id' in source_ref and source_ref['producer_contract_id']!=config['source_publication_contract']:raise ValueError('STRUCTURE_PRODUCER_IDENTITY_MISMATCH')
    selected=next((state for state in row.get('anchor_states',[]) if state.get('anchor_id')==active),None) if row and active else None
    # Lookup by already-published active id; never select or calculate an Anchor.
    sources=dict(row or {},selected_anchor_state=selected)
    missing=object()
    def lookup(path):
        value=sources
        if path is None:return missing
        for part in path.split('.'):
            if not isinstance(value,dict) or part not in value:return missing
            value=value[part]
        return value
    for name,spec in config['projection_mapping'].items():
        value=lookup(spec['value_source']);quality=lookup(spec['quality_source']);reason=lookup(spec['reason_source'])
        original=value if isinstance(value,dict) and 'value' in value and 'quality' in value else None
        if original and spec['value_mode']=='ENVELOPE_VALUE_OR_EXACT_OBJECT':value=original['value']
        if quality is missing or reason is missing:
            quality=spec['missing_metadata_quality'];reason=spec['missing_metadata_reason']
        if row is None:quality='UNKNOWN';reason='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'
        out[name]=envelope(None if value is missing else deepcopy(value),quality,deepcopy(reason),[source_ref] if source_ref else [])
        # Published producer/source metadata remains intact; derived lookup provenance is separate.
        if original:
            for key in ['producer_identity','source_identity','producer_contract_id']:
                if key in original:out[name][key]=deepcopy(original[key])
        out[name]['projection_provenance']=dict(publication_contract_id=config['source_publication_contract'],
            value_source=spec['value_source'],quality_source=spec['quality_source'],reason_source=spec['reason_source'],
            selected_anchor_id=active,row_identity=deepcopy(row.get('identity')) if row else None,source_ref=deepcopy(source_ref))
        out[name].setdefault('producer_identity',deepcopy(out[name]['projection_provenance']))
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
        component_refs=binder.component_sources(security_id,selection,context_result['loo_identity']) if hasattr(binder,'component_sources') else None
        refs=list({(r['path'],r['producer_contract_id']):r for rs in component_refs.values() for r in rs}.values()) if component_refs else deepcopy(binder.refs)
        snapshot=sector_snapshot(selection,selected,self.contracts,refs,component_refs)
        fields=dict(**relationships,sector_context_state=snapshot,sector_context_quality=envelope(snapshot['quality'],'KNOWN',None,refs))
        structure_ref=binder.structure_source() if hasattr(binder,'structure_source') else binder.structure_ref
        copied=copy_structure(binder.structure.get(security_id),self.contracts,structure_ref);fields.update(copied)
        rotation=component()
        if selected:
            r=selected['rotation'];rotation=envelope(None if r['output_state']=='UNKNOWN' else r['output_state'],'UNKNOWN' if r['output_state']=='UNKNOWN' else 'KNOWN',r.get('reason_codes'),component_refs['rotation_core_state'] if component_refs else [self.contracts.owner_refs['V4_08']])
        else:rotation=envelope(refs=component_refs['rotation_core_state'] if component_refs else [self.contracts.owner_refs['V4_08']])
        sq=fold_quality([f['quality'] for f in copied.values()],self.contracts.config['quality_map']['component_pair_table'])
        structure=envelope({k:deepcopy(v) for k,v in copied.items()},sq,None,[structure_ref] if structure_ref else [])
        enrichment=dual_enrichment(rotation,structure,self.contracts);fields['rotation_structure_enrichment']=envelope(enrichment,enrichment['combined_quality'],None,[self.contracts.owner_refs['V4_08'],self.contracts.owner_refs['V4_12']])
        registry={r['field']:r for r in self.contracts.config['field_registry']['fields']}
        for name,field in fields.items():
            spec=registry[name]
            if not field.get('source_identity'):
                field['source_identity']=[r['binding'] for r in spec['source_bindings']] if 'source_bindings' in spec else [spec['source_binding']]
            field.setdefault('producer_contract_id',spec['producer_contract_id'])
            field.update(membership_basis=basis,loo_basis=context_result['loo_identity'])
        expected={r['field'] for r in self.contracts.config['field_registry']['fields']}
        if set(fields)!=expected:raise ValueError('ADVANCED_PROFILE_FIELDS_INCOMPLETE')
        after=digest(dict(stock=binder.stock.get(security_id),seed=binder.seed.get(security_id)))
        if before!=after:raise ValueError('CONTEXT_RAW_QUALIFICATION_MUTATION')
        return dict(security_id=security_id,trade_date=binder.date,revision=revision,cutoff=binder.cutoff,fields=fields,contract_digest=self.contracts.digest,membership_digest=binder.snapshot['snapshot_id'],membership_source_revision=binder.snapshot['source_revision_id'],loo_identity=context_result['loo_identity'],source_refs=binder.refs,loo_history_digest=binder.history_digest,structure_source_digest=binder.structure_ref['sha256'] if binder.structure_ref else None,prior_session_ref=binder.prior_session_ref,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,raw_qualification_before=before,raw_qualification_after=after)
