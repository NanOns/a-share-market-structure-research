"""Independent precise projections and immutable pre-call invocation verifier."""
import json
from datetime import datetime
from scripts.v4_14_independent_edge_oracle_r18r1 import EdgeOracle
from scripts.v4_14_independent_oracle import read,exact,checksum,require

def resolve(value,path):
    for part in path.split('/')[1:]:value=value[int(part)] if isinstance(value,list) else value[part]
    return value

class ConsumptionOracle(EdgeOracle):
    def __init__(self,root):
        super().__init__(root)
        self.mapping=json.loads((self.root/'config/v4_14_precall_consumption_mapping_r18r1r1_v1.json').read_bytes())
        require(self.mapping['frozen_dag']==self.contracts[2],'CONSUMPTION_FROZEN_DAG_AUTHORITY')
        self.mappings={m['edge_id']:m for m in self.mapping['mappings']}
        require(set(self.mappings)==set(self.expected_edges),'CONSUMPTION_MAPPING_EDGE_SET')
        for key,e in self.expected_edges.items():
            for name,value in e.items():require(self.mappings[key][name]==value,'CONSUMPTION_MAPPING_IDENTITY')
        for r in self.mapping['owner_interfaces']:exact(root,r)
    def resolve(self,artifact_root,output,r):
        require(r['scope'] in ['CURRENT_OUTPUT','PREVIOUS_PUBLICATION'],'CONSUMPTION_REF_SCOPE')
        value=output if r['scope']=='CURRENT_OUTPUT' else read(artifact_root,r['publication'])
        return resolve(value,r['pointer'])
    def edges(self,artifact_root,m):
        out=m['output'];rows=out['edge_receipts'];nodes=out['node_records'];ids=[r['edge_id'] for r in rows]
        require(len(ids)==30 and len(set(ids))==30 and set(ids)==set(self.expected_edges),'CONSUMPTION_MISSING_OR_UNEXPECTED_EDGE')
        exact(self.root,out['consumption_mapping_ref']);require(read(self.root,out['consumption_mapping_ref'])==self.mapping,'CONSUMPTION_STALE_MAPPING')
        order=['F0','A','B0','B1','B2','C','D0','D1','D2','EVENT_DIFF','MEMBERSHIP','D3_CONTEXT','D3','GATE_B_OBSERVATION']
        authority=m['envelope']['authority_bindings'];owners=authority['owners'];owner_refs=dict(F0=authority['data'],A=owners['v4_07'],B0=owners['v4_08'],B1=owners['v4_08'],B2=owners['v4_08'],C=owners['v4_09'],D0=owners['v4_11'],D1=owners['v4_12'],D2=owners['v4_10'],EVENT_DIFF=owners['v4_11'],MEMBERSHIP=authority['membership'],D3_CONTEXT=owners['v4_13'],D3=owners['v4_13'],GATE_B_OBSERVATION=self.contracts[0])
        for i,node in enumerate(order):
            record=nodes[node];inv=record['invocation'];require(inv==read(artifact_root,record['invocation_ref']),'CONSUMPTION_NOT_PERSISTED_PRECALL')
            require(inv['phase']=='PRECALL_FROZEN' and inv['node_id']==node and checksum(inv['invocation_input'])==inv['invocation_input_digest'],'CONSUMPTION_INVOCATION_CHANGED')
            require(inv['owner_authority']==owner_refs[node] and read(self.root,inv['mapping_ref'])==self.mapping,'CONSUMPTION_INVOCATION_OWNER_AUTHORITY')
            require(inv['execution_context']==dict(target_trade_date=m['target_trade_date'],target_revision=m['target_revision'],previous_market_session=m['previous_market_session'],cutoff=m['envelope']['cutoff'],calendar_binding=self.calendar_ref,contract_package_digest=m['contract_package_digest']),'CONSUMPTION_INVOCATION_CONTEXT')
            require((inv['prepared_sequence'],record['call_started_sequence'],record['output_sequence'])==(3*i+1,3*i+2,3*i+3),'CONSUMPTION_POSTHOC_ENVELOPE')
            expected_incoming={key for key,e in self.expected_edges.items() if e['consumer']==node}
            bindings=inv['edge_bindings'];require({b['edge_id'] for b in bindings}==expected_incoming and len(bindings)==len(expected_incoming),'CONSUMPTION_INVOCATION_BINDINGS')
        for r in rows:
            key=r['edge_id'];definition=self.mappings[key];node=nodes[r['consumer']];inv=node['invocation'];binding=next(b for b in inv['edge_bindings'] if b['edge_id']==key)
            for name,value in self.expected_edges[key].items():require(r[name]==value,'CONSUMPTION_WRONG_EDGE_IDENTITY:'+name)
            prior=r['time_role']=='T_MINUS_1';missing=prior and m['previous_state_publication'] is None
            date=m['previous_market_session'] if prior else m['target_trade_date'];require(r['source_trade_date']==date and r['target_trade_date']==m['target_trade_date'] and r['previous_market_session']==self.previous(m['target_trade_date']),'CONSUMPTION_EDGE_DATE')
            if r['available_at'] is None:require(missing,'CONSUMPTION_AVAILABILITY_MISSING')
            else:require(datetime.fromisoformat(r['available_at'])<=datetime.fromisoformat(m['envelope']['cutoff']),'CONSUMPTION_AFTER_CUTOFF')
            expected_pointer='/missing_sources/'+key if missing else ('/output' if prior else '')+'/node_records/'+r['producer']+'/output'+definition['producer_projection']
            expected_ref=dict(scope='PREVIOUS_PUBLICATION' if prior and not missing else 'CURRENT_OUTPUT',publication=m['previous_state_publication'] if prior and not missing else None,pointer=expected_pointer)
            require(r['producer_payload_ref']==binding['producer_payload_ref']==r['input_ref']==expected_ref,'CONSUMPTION_WHOLE_NODE_OR_WRONG_PROJECTION')
            source=self.resolve(artifact_root,out,expected_ref);arg_path='/capabilities/'+key if missing else definition['consumer_argument_path']
            require(binding['consumer_argument_path']==r['consumer_argument_path']==arg_path,'CONSUMPTION_ARGUMENT_UNBOUND')
            argument=resolve(inv['invocation_input'],arg_path)
            require(r['producer_payload_digest']==binding['producer_payload_digest']==r['input_digest']==checksum(source),'CONSUMPTION_PRODUCER_DIGEST')
            require(r['consumer_argument_digest']==binding['consumer_argument_digest']==r['consumer_input_digest']==checksum(argument),'CONSUMPTION_ARGUMENT_CHANGED')
            require(r['invocation_ref']==node['invocation_ref'] and r['invocation_input_digest']==inv['invocation_input_digest'],'CONSUMPTION_RECEIPT_INVOCATION')
            require(r['consumer_input_ref']==dict(scope='CURRENT_OUTPUT',publication=None,pointer='/node_records/'+r['consumer']+'/invocation/invocation_input'+arg_path),'CONSUMPTION_POSTHOC_MIRROR')
            degraded=definition['binding_mode']=='ACCEPTED_CAPABILITY_GATE' or missing
            require(r['status']==binding['status']==('DEGRADED_ACCEPTED_CAPABILITY' if degraded else 'EXECUTED'),'CONSUMPTION_FALSE_EXECUTED')
            require(r['binding_mode']==binding['binding_mode']==definition['binding_mode'],'CONSUMPTION_BINDING_MODE')
            if degraded:
                require(argument['value'] is None and argument['quality']==r['quality']=='UNKNOWN' and argument['reason']==r['reason']==binding['reason'] and bool(r['reason']),'CONSUMPTION_DEGRADED_KNOWN')
                expected_reason='NO_EXACT_PREVIOUS_ENGINEERING_PUBLICATION' if missing else 'ACCEPTED_OWNER_INTERFACE_OR_NATIVE_HISTORY_CAPABILITY_UNAVAILABLE'
                if not missing and r['producer']=='D1' and r['consumer']=='D2':expected_reason=read(self.root,owners['v4_11'])['capabilities']['V4_12_STRUCTURE_SUPPORT']
                require(r['reason']==expected_reason,'CONSUMPTION_DEGRADED_REASON_AUTHORITY')
                require(argument['upstream_ref']==expected_ref and argument['upstream_digest']==checksum(source) and argument['owner_head_ref']==r['owner_head_ref'],'CONSUMPTION_DEGRADED_AUTHORITY')
            else:require(source==argument and r['quality']=='KNOWN','CONSUMPTION_NOT_EXACT_ARGUMENT')
            require(r['output_digest']==checksum(nodes[r['consumer']]['output']),'CONSUMPTION_OUTPUT_DIGEST')
            require((r['precall_prepared_sequence'],r['call_started_sequence'],r['output_sequence'])==(inv['prepared_sequence'],node['call_started_sequence'],node['output_sequence']),'CONSUMPTION_RECEIPT_SEQUENCE')
        complete=out['edge_completeness']
        for name in ['missing_edges','unexpected_edges','false_executed_edges','unbound_consumer_arguments','post_hoc_only_edges']:require(complete[name]==[],'CONSUMPTION_INCOMPLETE')
        require(set(complete['expected_active_edges'])==set(self.expected_edges),'CONSUMPTION_EMITTED_EXPECTATIONS')
        for status,name in [('EXECUTED','executed_edges'),('DEGRADED_ACCEPTED_CAPABILITY','degraded_edges'),('NOT_APPLICABLE_BY_FROZEN_CONTRACT','not_applicable_edges')]:require(set(complete[name])=={r['edge_id'] for r in rows if r['status']==status},'CONSUMPTION_PARTITION')
        # Independently inspect field mappings against frozen literals and actual
        # accepted reducer schemas, not a runtime-owned expected-result helper.
        f0=nodes['F0']['output'];fixture=read(self.root,self.mapping['fixture_package']);cbook=read(self.root,fixture['prewatch']['source']);facts=next(v['facts'] for v in cbook['vectors'] if v['id']==fixture['prewatch']['vector_id'])
        seedbook=read(self.root,fixture['seed']['source']);expected_seed={k:dict(value=True if v=='TRUE' else False if v=='FALSE' else v,reason=None) for k,v in seedbook['base_input'].items()};choice=m['envelope']['owner_inputs'];expected_seed['severe_extension']['value']=choice.get('severe_extension',False)
        if choice.get('unknown'):expected_seed['price_identity_READY'].update(value=None,reason='EXPLICIT_SYNTHETIC_UNKNOWN')
        require(f0['base_seed_primitives']==expected_seed and f0['d0_facts']==fixture['confirmation']['values'],'CONSUMPTION_UNFROZEN_PRIMITIVES')
        require(f0['stock_core']=={k:v for k,v in facts.items() if k!='base_seed_state'},'CONSUMPTION_UNFROZEN_STOCK_CORE')
        book=read(self.root,fixture['structure']['source']);sv=next(v for v in book['vectors'] if v['vector_id']==m['envelope']['owner_inputs'].get('structure_vector','S01'))
        structural={**book['defaults'],**sv['inputs']};structural['prior_separated_sessions']=read(artifact_root,m['previous_state_publication'])['output']['structure_ledger']['separated_sessions'] if m['previous_state_publication'] else 0
        require(f0['core_facts']==structural and nodes['D1']['invocation']['invocation_input']['core_facts']==structural,'CONSUMPTION_D1_NOT_FROZEN_CORE_FACTS')
        d2args=nodes['D2']['invocation']['invocation_input'];provenance=out['d2']['inputs'][0]['input_provenance']
        for field in ['CONFIRMED','PREWATCH']:require(provenance[field]['value']==d2args['values'][field],'CONSUMPTION_D2_SCHEMA_PROJECTION')
        eventargs=nodes['EVENT_DIFF']['invocation']['invocation_input'];row=eventargs['confirmation_facts']
        require(provenance['CONFIRMED']['value']==row['confirmation_status'] and provenance['scenario']['value']==(row['primary_scenario'] or 'UNKNOWN') and eventargs['d2_publication']==out['d2'],'CONSUMPTION_D0_EVENT_VALIDATION_PATH')
        for node in ['B0','B1']:require(nodes[node]['output']['output_state']=='UNKNOWN','CONSUMPTION_NATIVE_CAPABILITY_OVERCLAIM')
        require(nodes['B2']['output']['confirmed_raw']=='UNKNOWN' and nodes['B2']['output']['warm_raw']=='UNKNOWN','CONSUMPTION_B2_OVERCLAIM')
        return True
    def canonical(self,artifact_root,gate):
        require(gate['candidate_namespace']=='reports/v4_14_replay_r18/full_dag_r5','CONSUMPTION_NONCANONICAL_ATTEMPT')
        require(gate['attempt_disposition']['full_dag_r5']=='CURRENT_R18R1R1_CANDIDATE','CONSUMPTION_CANONICAL_AUTHORITY')
        for k in ['missing_edges','unexpected_edges','false_executed_edges','unbound_consumer_arguments','post_hoc_only_edges']:require(gate[k]==[],'CONSUMPTION_CANONICAL_INCOMPLETE')
        self.gate(artifact_root,gate['persisted_e2e']);return True
