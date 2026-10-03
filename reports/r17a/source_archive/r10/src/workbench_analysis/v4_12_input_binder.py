"""Registry-driven accepted-source binder; blocked capabilities never acquire values."""
from datetime import datetime
from decimal import Decimal,InvalidOperation
from .v4_12_structure_io import exact_json,file_ref,digest

def check_availability(available_at,cutoff):
    if datetime.fromisoformat(available_at)>datetime.fromisoformat(cutoff):raise ValueError('FUTURE_SOURCE')

class InputBinder:
    def __init__(self,contracts,trade_date,cutoff):
        self.contracts=contracts;self.root=contracts.root;self.date=trade_date;self.cutoff=datetime.fromisoformat(cutoff)
        self.fields={r['field']:r for r in contracts.config['field_registry']['fields']};self.publications={};self.source_refs={}
        for row in self.fields.values():
            if row['field_role']=='UPSTREAM_ACCEPTED':
                head=file_ref(self.root,row['accepted_head_path'])
                if head['sha256']!=row['accepted_head_sha256']:raise ValueError('ACCEPTED_OWNER_DIGEST_MISMATCH')
        data_ref=contracts.config['time_counter_contract']['definitions']['data_authority']
        self.data=exact_json(self.root,data_ref)
        if trade_date>self.data['accepted_trade_date']:raise ValueError('FUTURE_DATE')
        calendar_ref=contracts.config['time_counter_contract']['definitions']['calendar_authority']
        self.calendar=exact_json(self.root,calendar_ref)['session_dates'];self.source_refs[calendar_ref['path']]=calendar_ref
        self.previous=max((d for d in self.calendar if d<trade_date),default=None)
        self.derivations=contracts.config['source_derivations_r2']
    def source(self,ref):
        if ref['path'] not in self.publications:
            payload=exact_json(self.root,ref);self.publications[ref['path']]={r['security_id']:r for r in payload.get('rows',[])}
            self.source_refs[ref['path']]=ref
        return self.publications[ref['path']]
    def validate_namespaces(self,extra):
        if extra:raise ValueError('FORBIDDEN_RUNTIME_INPUT_NAMESPACE:'+','.join(sorted(extra)))
    def check_input_claim(self,name,claim):
        """Reject an untrusted envelope before binding any values from it."""
        if name not in self.fields:raise ValueError('FALSE_ACCEPTED_OWNER_CLAIM')
        row=self.fields[name]
        if row['field_role']=='D1_OUTPUT':raise ValueError('D1_OUTPUT_CANNOT_BE_INPUT')
        if claim.get('producer_contract_id')!=row['producer_contract_id']:raise ValueError('EXACT_PRODUCER_REQUIRED')
        if row['field_role']=='D1_LOCAL_DERIVATION':raise ValueError('LOCAL_FIELD_CANNOT_BE_F0')
        if row['field_role']=='BLOCKED_CAPABILITY' and claim.get('quality')=='KNOWN':raise ValueError('UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE')
        if claim.get('source_namespace')!=row['source_namespace'] or claim.get('time_role')!=row['time_role']:raise ValueError('SOURCE_NAMESPACE_OR_TIME_ROLE_MISMATCH')
        if claim.get('quality')=='KNOWN':
            pub=row['target_publications'].get(self.date)
            if row['field_role']=='UPSTREAM_ACCEPTED' and (not pub or claim.get('source_digest')!=pub['artifact']['sha256']):raise ValueError('SOURCE_DIGEST_NOT_ACCEPTED')
            if row['field_role']=='FROZEN_PRIOR_D1' and claim.get('trade_date')!=self.previous:raise ValueError('SAME_DAY_OR_FOREIGN_PRIOR_D1')
        return True
    def record(self,row,value=None,quality='UNKNOWN',reason=None,pub=None,date=None):
        return dict(logical_field=row['field'],value=value,quality=quality,reason=reason,source_namespace=row['source_namespace'],
            producer_contract_id=row['producer_contract_id'],source_publication_id=pub['sha256'] if pub else None,
            source_digest=pub['sha256'] if pub else None,trade_date=date or (self.previous if row['time_role']=='T_MINUS_1' else self.date),time_role=row['time_role'])
    def prior(self,snapshot,security_id):
        if snapshot is None:return None
        ref=snapshot['artifact'];payload=exact_json(self.root,ref)
        if payload['trade_date']!=self.previous or payload['security_id']!=security_id:raise ValueError('SAME_DAY_OR_FOREIGN_PRIOR_D1')
        if payload['contract_digest']!=self.contracts.digest or payload['namespace']!='Frozen D1[t-1]':raise ValueError('PRIOR_D1_AUTHORITY_MISMATCH')
        if datetime.fromisoformat(payload['available_at'])>self.cutoff:raise ValueError('FUTURE_PRIOR_D1')
        if 'candidate_manifest' not in snapshot:raise ValueError('PRIOR_D1_CANDIDATE_MANIFEST_REQUIRED')
        manifest=exact_json(self.root,snapshot['candidate_manifest'])
        if manifest.get('entry')!=self.contracts.entry_ref or manifest.get('status')!='ENGINEERING_CANDIDATE_NOT_ACCEPTED' or ref not in manifest.get('artifacts',[]):
            raise ValueError('PRIOR_D1_CANDIDATE_MANIFEST_MISMATCH')
        if payload.get('knowledge_lineage')!='RECONSTRUCTED_CORRECTED' or payload.get('AS_RECORDED') is not False:raise ValueError('PRIOR_D1_LINEAGE_NOT_AUTHORIZED')
        return payload,ref
    def bind(self,security_id,prior_snapshot=None,extra_namespaces=None):
        self.validate_namespaces(extra_namespaces)
        prior=self.prior(prior_snapshot,security_id);self.bound_prior=prior;facts={}
        for name,row in self.fields.items():
            role=row['field_role']
            if role=='D1_OUTPUT':continue
            if role=='BLOCKED_CAPABILITY':facts[name]=self.record(row,reason=row['blocked_reason']);continue
            if role=='FROZEN_PRIOR_D1':
                prior_fact=prior[0].get('facts',{}).get(name) if prior else None
                if prior_fact and prior_fact['quality']=='KNOWN':facts[name]=self.record(row,prior_fact['value'],'KNOWN',pub=prior[1],date=self.previous)
                else:facts[name]=self.record(row,reason='NO_ACCEPTED_PRIOR_D1_PUBLICATION' if not prior else prior_fact.get('reason') if prior_fact else 'MISSING_FROZEN_PRIOR_D1_FIELD')
                continue
            if role=='D1_LOCAL_DERIVATION':facts[name]=self.record(row,reason='LOCAL_REQUIRED_SOURCE_UNAVAILABLE');continue
            if role!='UPSTREAM_ACCEPTED':raise ValueError('UNREGISTERED_FIELD_ROLE')
            pub=row['target_publications'].get(self.date)
            if not pub or not row['target_publication_available']:facts[name]=self.record(row,reason='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE');continue
            check_availability(pub['available_at'],self.cutoff.isoformat())
            expected_date=self.previous if row['time_role']=='T_MINUS_1' else self.date
            if pub['trade_date']!=expected_date:raise ValueError('SOURCE_TIME_ROLE_MISMATCH')
            ref=pub['artifact'];source=self.source(ref).get(security_id)
            if source is None:facts[name]=self.record(row,reason='MISSING_ACCEPTED_SOURCE_ROW',pub=ref,date=expected_date);continue
            field=row['accepted_source_field']
            if 'fields' in source:
                item=source['fields'].get(field,{})
                value=item.get('value');quality='KNOWN' if item.get('quality_state')=='OBSERVED' and value is not None else 'UNKNOWN'
                reason=None if quality=='KNOWN' else item.get('unknown_reason') or 'MISSING_ACCEPTED_FIELD'
            else:
                value=source.get(field);quality='KNOWN' if source.get(pub['quality_field'])=='READY' and value is not None else 'UNKNOWN'
                reason=None if quality=='KNOWN' else source.get('reason') or 'ACCEPTED_ADJUSTMENT_NOT_READY'
            if row['data_type'] in ['number','integer'] and quality=='KNOWN':
                try:
                    numeric=Decimal(str(value))
                    if not numeric.is_finite():raise InvalidOperation()
                    value=str(numeric)
                except (InvalidOperation,ValueError):quality='UNKNOWN';value=None;reason='INVALID_ACCEPTED_NUMERIC_FIELD'
            facts[name]=self.record(row,value if quality=='KNOWN' else None,quality,reason,ref,expected_date)
        self.local(facts,security_id,prior)
        return facts
    def local(self,facts,security_id,prior):
        # Only declared local coordinate views may use a frozen Anchor of identical basis identity.
        def assign(name,value,reason=None):
            if name in self.fields:facts[name]=self.record(self.fields[name],value,'KNOWN' if value is not None else 'UNKNOWN',reason)
        anchor=prior[0].get('anchor') if prior else None
        identity=(facts['price_basis']['value'],facts['adjustment_source_revision']['value'])
        if anchor:
            from .v4_12_anchor_runtime import coordinate_view
            view=coordinate_view(anchor,*identity,self.date,'binding')
            assign('lo',view['lower'],view['reason']);assign('hi',view['upper'],view['reason'])
        if facts['C']['quality']=='KNOWN':assign('observation_close_view',facts['C']['value'])
        if not anchor:
            for name in ['lo','hi','base_view','event_close_view','start_price_view','endpoint_price_view','recovery_line_view','prior_event_peak_view']:
                assign(name,None,'NO_ACCEPTED_PRIOR_D1_PUBLICATION')
        if all(facts[n]['quality']=='KNOWN' for n in ['C','lo','hi']):
            c,lo,hi=(Decimal(facts[n]['value']) for n in ['C','lo','hi']);assign('distance_zone',str(max(lo-c,c-hi,Decimal(0))))
        # The exact frozen dependency ledger determines evaluability. No factor calculation.
        definition=self.derivations['dependency_ledger']['evaluable']
        publication=definition['publications'].get(self.date)
        actual=self.source(publication).get(security_id) if publication else None
        required=definition['other_required_fields']
        unavailable=[facts[n]['reason'] for n in required if facts[n]['quality']!='KNOWN']
        if not actual:assign('evaluable',None,'MISSING_ACCEPTED_TRADING_STATUS')
        elif actual['status_conflict']:assign('evaluable',None,'ACCEPTED_STATUS_CONFLICT')
        elif not actual['actual_bar_present']:assign('evaluable',False,'MISSING_OR_SUSPENDED_ACTUAL_BAR')
        elif unavailable:assign('evaluable',None,';'.join(sorted(set(x for x in unavailable if x))))
        else:assign('evaluable',True)
        # No prior event/publication is known to be absent merely because bootstrapping.
        for name in ['post_creation_market_sessions','post_creation_evaluable_sessions','pivot_left_count','pivot_right_count']:
            if not anchor:assign(name,None,'NO_ACCEPTED_PRIOR_D1_PUBLICATION')
        if anchor:
            available=anchor['available_date']
            assign('post_creation_market_sessions',sum(available<day<=self.date for day in set(self.calendar)))
            baseline=prior[0].get('counter_state',{})
            count=baseline.get('post_creation_evaluable_sessions')
            if count is None:assign('post_creation_evaluable_sessions',None,'MISSING_FROZEN_EVALUABLE_HISTORY')
            else:assign('post_creation_evaluable_sessions',count+int(facts['evaluable']['value'] is True and self.date>available))
            for name in ['pivot_left_count','pivot_right_count']:assign(name,None,'UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE:PIVOT_HISTORY')
