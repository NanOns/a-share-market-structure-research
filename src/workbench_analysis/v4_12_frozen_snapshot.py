"""Immutable engineering Frozen D1 bundles. No source reconstruction or business rules."""
import gzip
import hashlib
import json
from .v4_12_structure_io import canonical,digest,exact_json
from .v4_12_input_binder import check_availability

CONTRACT_PATH='config/v4_12_frozen_snapshot_contract_v1.json'

def exact_bytes(root,ref):
    path=(root/ref['path']).resolve()
    if not path.is_relative_to(root):raise ValueError('SOURCE_ESCAPE')
    raw=path.read_bytes()
    if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('EXACT_DIGEST_MISMATCH')
    return raw

class FrozenSnapshotLoader:
    def __init__(self,contracts,manifest_ref,cutoff):
        self.c=contracts;self.ref=manifest_ref;self.manifest=exact_json(contracts.root,manifest_ref);m=self.manifest
        if m.get('contract_id')!='V4_12_FROZEN_D1_CANDIDATE_MANIFEST_V1' or m.get('status')!='ENGINEERING_CANDIDATE_NOT_ACCEPTED':raise ValueError('PRIOR_D1_CANDIDATE_MANIFEST_MISMATCH')
        if m['entry']!=contracts.entry_ref or m['contract_digest']!=contracts.digest:raise ValueError('PRIOR_D1_AUTHORITY_MISMATCH')
        check_availability(m['available_at'],cutoff)
        if m['knowledge_lineage']!='RECONSTRUCTED_CORRECTED' or m['AS_RECORDED'] is not False or m['formal_accepted'] is not False:raise ValueError('PRIOR_D1_LINEAGE_NOT_AUTHORIZED')
        from .v4_12_structure_io import file_ref
        if m['snapshot_contract']!=file_ref(contracts.root,CONTRACT_PATH):raise ValueError('SNAPSHOT_CONTRACT_MISMATCH')
        source=exact_json(contracts.root,m['source_runtime_manifest'])
        if source.get('contract_id')!='V4_12_R11_RUNTIME_CANDIDATE_MANIFEST' or source.get('entry')!=contracts.entry_ref or source.get('contract_digest')!=contracts.digest:raise ValueError('UNSEALED_RUNTIME_SOURCE')
        if source.get('trade_date')!=m['trade_date'] or source.get('revision')!=m['revision'] or source.get('knowledge_lineage')!=m['knowledge_lineage'] or source.get('AS_RECORDED') is not False or source.get('formal_accepted') is not False:raise ValueError('SOURCE_MANIFEST_LINEAGE_MISMATCH')
        self.contract=exact_json(contracts.root,m['snapshot_contract'])
        self.index=exact_json(contracts.root,m['security_index'])['rows']
        raw=gzip.decompress(exact_bytes(contracts.root,m['snapshot_bundle']))
        self.rows={}
        for line in raw.splitlines():
            row=json.loads(line);sid=row['security_id']
            if sid in self.rows:raise ValueError('DUPLICATE_SNAPSHOT_SECURITY')
            self.rows[sid]=row
        if set(self.index)!=set(self.rows) or len(self.rows)!=m['row_count'] or digest(sorted(self.rows))!=m['security_ids_digest']:raise ValueError('SNAPSHOT_INDEX_MISMATCH')
    def read(self,security_id,previous):
        if security_id not in self.rows:raise ValueError('MISSING_FROZEN_SECURITY_ROW')
        r=self.rows[security_id];m=self.manifest
        if r['trade_date']!=previous or m['trade_date']!=previous or r['security_id']!=security_id:raise ValueError('SAME_DAY_OR_FOREIGN_PRIOR_D1')
        if digest(r)!=self.index[security_id]['row_digest']:raise ValueError('SNAPSHOT_ROW_DIGEST_MISMATCH')
        for name in ['revision','available_at','knowledge_lineage','AS_RECORDED','formal_accepted','contract_digest']:
            if r[name]!=m[name]:raise ValueError('SNAPSHOT_MANIFEST_ROW_MISMATCH:'+name)
        if r['namespace']!='Frozen D1[t]' or r['entry_digest']!=self.c.entry_ref['sha256'] or r['source_candidate_manifest_digest']!=m['source_runtime_manifest']['sha256']:raise ValueError('PRIOR_D1_AUTHORITY_MISMATCH')
        if r['counter_state_digest']!=digest(r['counter_state']):raise ValueError('COUNTER_STATE_DIGEST_MISMATCH')
        if any(name not in r for name in self.contract['required_fields']):raise ValueError('INCOMPLETE_FROZEN_SNAPSHOT')
        if r['counter_contract_id']!=self.c.config['time_counter_contract']['contract_id']:raise ValueError('COUNTER_CONTRACT_MISMATCH')
        if (r['anchor'] is None)!=(r['event'] is None):raise ValueError('ANCHOR_EVENT_BINDING_MISMATCH')
        if r['anchor'] and (r['event']['anchor_id']!=r['anchor']['anchor_id'] or r['event']['event_id']!=r['anchor']['source_event_id']):raise ValueError('ANCHOR_EVENT_BINDING_MISMATCH')
        return r,dict(**m['snapshot_bundle'],security_id=security_id,row_digest=self.index[security_id]['row_digest'],candidate_manifest=self.ref)

class SnapshotMaterializer:
    def __init__(self,contracts,store):
        self.c=contracts;self.store=store
        self.contract=json.loads((contracts.root/CONTRACT_PATH).read_bytes())
    def row(self,result,source_manifest,available_at):
        obs=result['observation'];bindings=result['bindings']['fields'];derived=obs['derived'];prior=result.get('bound_prior')
        anchor=prior.get('anchor') if prior and prior.get('anchor') else result['anchors'][0] if result['anchors'] else None
        event=prior.get('event') if prior and prior.get('event') else result['events'][0] if result['events'] else None
        def fact(value=None,reason=None):return dict(value=value,quality='KNOWN' if value is not None and value!='UNKNOWN' else 'UNKNOWN',reason=reason or ([] if value is not None and value!='UNKNOWN' else ['MISSING_RUNTIME_PROJECTION']))
        def source(name):return derived.get(name,bindings.get(name,fact()))
        counters={n:source(n)['value'] for n in self.contract['counter_fields']}
        counters['test_count']=source('next_test_count')['value']
        from decimal import Decimal
        for n,v in counters.items():
            if v is not None:
                number=Decimal(str(v))
                if number!=number.to_integral_value() or number<0:raise ValueError('INVALID_RUNTIME_COUNTER')
                counters[n]=int(number)
        if anchor and anchor['available_date']==obs['trade_date']:
            # New Anchor has no post-creation observations yet; not a support test.
            counters={n:0 for n in self.contract['counter_fields']};counters['test_count']=0
        facts={}
        for spec in self.contract['fact_projections']:
            name=spec['field'];kind=spec['kind'];src=spec['source']
            if kind=='anchor':facts[name]=fact(anchor.get(src) if anchor else None,['NO_BOUND_ANCHOR'] if not anchor else None)
            elif kind=='counter':facts[name]=fact(counters.get(src),source('next_test_count' if src=='test_count' else src).get('reason'))
            elif kind=='runtime':
                if name in ['anchor_original_atr','anchor_original_price']:
                    facts[name]=prior['facts'][name] if prior and anchor else source(src) if anchor else fact(reason=['NO_BOUND_ANCHOR'])
                else:facts[name]=source(src)
            elif kind=='support':
                current=obs['outputs']['support']
                previous=prior.get('last_known_support_state') if prior else None
                if current['quality']!='KNOWN' and previous in [None,'UNKNOWN'] and prior:previous=prior.get('facts',{}).get('prior_support_state',{}).get('value')
                facts[name]=fact(current['value'] if current['quality']=='KNOWN' else previous,current['reason'] if previous is None else None)
            elif kind=='event':
                if not event:facts[name]=fact(reason=['NO_BOUND_EVENT'])
                elif name=='prior_valid_event':
                    invalid=source('hard_invalidated');facts[name]=fact(not invalid['value']) if invalid['quality']=='KNOWN' else fact(reason=invalid['reason'])
                else:facts[name]=fact(True)
            elif kind=='machine_flag':
                state=obs['outputs'][src]
                facts[name]=fact(state['value'] in spec['states']) if state['quality']=='KNOWN' else fact(reason=state['reason'])
        row=dict(snapshot_id=digest(dict(identity=obs['identity'],contract=self.c.digest)),security_id=obs['security_id'],trade_date=obs['trade_date'],revision=obs['revision'],available_at=available_at,
            namespace='Frozen D1[t]',contract_digest=self.c.digest,entry_digest=self.c.entry_ref['sha256'],input_digest=obs['input_digest'],observation_digest=digest(obs),source_candidate_manifest_digest=source_manifest['sha256'],
            facts=facts,anchor=anchor,event=event,counter_state=counters,counter_contract_id=self.c.config['time_counter_contract']['contract_id'],counter_state_digest=digest(counters),
            knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,last_known_support_state=obs['frozen_output_envelope']['last_known_support_state'],
            state_observations=obs['outputs'],invalidation_facts=obs['frozen_output_envelope']['invalidation_facts'])
        row['last_known_support_state']=facts['prior_support_state']['value']
        for machine in ['support','acceptance','breakout','pullback','recovery']:row[machine+'_state']=obs['outputs'][machine]['state']
        return row
    def seal(self,results,source_manifest,available_at):
        from .v4_12_structure_io import file_ref
        rows=[self.row(r,source_manifest,available_at) for r in results]
        if not rows or len({r['security_id'] for r in rows})!=len(rows):raise ValueError('INVALID_SNAPSHOT_SCOPE')
        dates={(r['trade_date'],r['revision']) for r in rows}
        if len(dates)!=1:raise ValueError('MIXED_SNAPSHOT_REVISION')
        bundle=self.store.jsonl('frozen_d1.jsonl.gz',rows,True)
        index=self.store.json('frozen_d1_index.json',dict(rows={r['security_id']:dict(row_digest=digest(r),snapshot_id=r['snapshot_id']) for r in rows}))
        m=dict(contract_id='V4_12_FROZEN_D1_CANDIDATE_MANIFEST_V1',status='ENGINEERING_CANDIDATE_NOT_ACCEPTED',trade_date=rows[0]['trade_date'],revision=rows[0]['revision'],available_at=available_at,
            entry=self.c.entry_ref,contract_digest=self.c.digest,snapshot_contract=file_ref(self.c.root,CONTRACT_PATH),snapshot_bundle=bundle,security_index=index,row_count=len(rows),security_ids_digest=digest(sorted(r['security_id'] for r in rows)),source_runtime_manifest=source_manifest,
            knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False)
        return self.store.json('frozen_d1_manifest.json',m)
