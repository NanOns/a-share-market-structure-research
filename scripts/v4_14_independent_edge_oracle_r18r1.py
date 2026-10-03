"""Expected edges come directly from the frozen contract, never from runtime."""
import json
from datetime import datetime
from pathlib import Path
from scripts.v4_14_independent_oracle import Oracle,read,exact,checksum,require

class EdgeOracle(Oracle):
    def __init__(self,root):
        super().__init__(root)
        pack=json.loads((self.root/'config/v4_14_temporal_non_edge_registry_v1_1.json').read_bytes());self.expected_edges={};self.expected_owner_edges=set();self.expected_replay_edges=set()
        for name in ['owner_edges','replay_required_edges']:
            for definition in pack[name]:
                p=pack['canonical_nodes'].get(definition['producer'],definition['producer']);c=pack['canonical_nodes'].get(definition['consumer'],definition['consumer']);key=checksum([p,c,definition['field'],definition['time_role']]);head=definition.get('source_owner_binding',definition.get('owner'));contract=definition.get('contract_binding',head)
                cid=definition['contract_id'] if 'contract_id' in definition else read(root,head).get('contract_id',head['path'])
                require(key not in self.expected_edges,'EDGE_ORACLE_DUPLICATE_FROZEN_EDGE')
                self.expected_edges[key]=dict(edge_id=key,producer=p,consumer=c,declared_producer=definition['producer'],declared_consumer=definition['consumer'],field=definition['field'],time_role=definition['time_role'],owner_head_ref=head,owner_contract_ref=contract,owner_contract_id=cid,group=name)
                (self.expected_owner_edges if name=='owner_edges' else self.expected_replay_edges).add(key)
        self.schema=json.loads((self.root/'config/v4_14_edge_receipt_schema_r18r1_v1.json').read_bytes())
    def resolve(self,artifact_root,output,r):
        if r['scope']=='CURRENT_OUTPUT':value=output
        else:
            require(r['scope']=='PREVIOUS_PUBLICATION','EDGE_ORACLE_REFERENCE_SCOPE');value=read(artifact_root,r['publication'])
        for part in r['pointer'].split('/')[1:]:
            require(isinstance(value,dict) and part in value,'EDGE_ORACLE_POINTER_MISSING');value=value[part]
        return value
    def edges(self,artifact_root,m):
        out=m['output'];rows=out['edge_receipts'];ids=[r['edge_id'] for r in rows]
        require(len(ids)==len(set(ids)),'EDGE_ORACLE_DUPLICATE_RECEIPT');require(set(ids)==set(self.expected_edges),'EDGE_ORACLE_MISSING_OR_UNEXPECTED_EDGE')
        nodes=out['node_records'];fixture=read(self.root,out['fixture_package_ref']);exact(self.root,out['edge_schema_ref'])
        require(out['fixture_package_ref']==self.schema['fixture_package'],'EDGE_ORACLE_UNBOUND_FIXTURE_PACKAGE')
        for r in rows:
            require(not (set(self.schema['required'])-set(r)),'EDGE_ORACLE_SCHEMA_FIELDS')
            expected=self.expected_edges[r['edge_id']]
            for field,value in expected.items():require(r[field]==value,'EDGE_ORACLE_WRONG_IDENTITY_OR_OWNER:'+field)
            exact(self.root,r['owner_head_ref']);exact(self.root,r['owner_contract_ref'])
            require(r['status'] in self.schema['statuses'],'EDGE_ORACLE_INVALID_STATUS')
            require(r['status']=='EXECUTED' or isinstance(r['reason'],str) and bool(r['reason']),'EDGE_ORACLE_REASON_REQUIRED')
            date=m['previous_market_session'] if r['time_role']=='T_MINUS_1' else m['target_trade_date']
            require(r['source_trade_date']==date and r['target_trade_date']==m['target_trade_date'] and r['previous_market_session']==self.previous(m['target_trade_date']),'EDGE_ORACLE_WRONG_SOURCE_DATE')
            if r['available_at'] is None:require(r['status']=='DEGRADED_ACCEPTED_CAPABILITY' and m['previous_state_publication'] is None and r['time_role']=='T_MINUS_1','EDGE_ORACLE_AVAILABILITY_MISSING')
            else:require(datetime.fromisoformat(r['available_at'].replace('Z','+00:00'))<=datetime.fromisoformat(m['envelope']['cutoff'].replace('Z','+00:00')),'EDGE_ORACLE_AFTER_CUTOFF')
            value=self.resolve(artifact_root,out,r['input_ref']);consumer=self.resolve(artifact_root,out,r['consumer_input_ref']);result=self.resolve(artifact_root,out,r['output_ref'])
            require(checksum(value)==r['input_digest']==r['consumer_input_digest']==checksum(consumer) and value==consumer,'EDGE_ORACLE_HARDCODED_DOWNSTREAM_SUBSTITUTE')
            require(checksum(result)==r['output_digest'],'EDGE_ORACLE_OUTPUT_DIGEST')
            if r['time_role']=='T_MINUS_1' and m['previous_state_publication']:
                require(r['input_ref']['scope']=='PREVIOUS_PUBLICATION' and r['input_ref']['publication']==m['previous_state_publication'],'EDGE_ORACLE_NOT_EXACT_PREVIOUS_PUBLICATION')
        completeness=out['edge_completeness'];groups={k:set(completeness[k]) for k in ['executed_edges','degraded_edges','not_applicable_edges']}
        require(set(completeness['expected_active_edges'])==set(self.expected_edges) and set.union(*groups.values())==set(self.expected_edges) and not completeness['missing_edges'] and not completeness['unexpected_edges'],'EDGE_ORACLE_COMPLETENESS_SUMMARY')
        for status,field in [('EXECUTED','executed_edges'),('DEGRADED_ACCEPTED_CAPABILITY','degraded_edges'),('NOT_APPLICABLE_BY_FROZEN_CONTRACT','not_applicable_edges')]:require(groups[field]=={r['edge_id'] for r in rows if r['status']==status},'EDGE_ORACLE_STATUS_PARTITION')
        # Verify actual owner call inputs, not just the generic receipt pointers.
        require(nodes['C']['input']['base_seed_state']==nodes['A']['output']['base_seed_state'],'EDGE_ORACLE_A_TO_C_LITERAL')
        cbook=read(self.root,fixture['prewatch']['source']);facts=next(v['facts'] for v in cbook['vectors'] if v['id']==fixture['prewatch']['vector_id'])
        require({k:v for k,v in nodes['C']['input'].items() if k!='base_seed_state'}=={k:v for k,v in facts.items() if k!='base_seed_state'},'EDGE_ORACLE_UNFROZEN_PREWATCH_FACTS')
        require(nodes['A']['input']['seed_facts']==nodes['F0']['output']['seed_facts'],'EDGE_ORACLE_F0_TO_A_SUBSTITUTE')
        for node in ['B1','B2']:require(nodes[node]['input']['b0']==nodes['B0']['output'],'EDGE_ORACLE_B0_CONSUMER_LITERAL')
        native=nodes['B0']['input']['native']['fields'];b0=nodes['B0']['output']
        require(isinstance(b0,dict) and b0.get('model_contract_id')=='V4_08_SECTOR_PREWATCH_B0_V2','EDGE_ORACLE_B0_LITERAL_NOT_OWNER_OUTPUT')
        if any(native.get(k,{}).get('value') is None for k in ['dq5','base_seed_width_adjusted','breadth_delta3','ma20_delta3']):require(b0['output_state']=='UNKNOWN' and b0['quality']=='UNKNOWN','EDGE_ORACLE_B0_CAPABILITY_UNKNOWN_COERCION')
        require(nodes['B2']['output']['confirmed_raw']=='UNKNOWN' and nodes['B2']['output']['warm_raw']=='UNKNOWN','EDGE_ORACLE_B2_CAPABILITY_OVERCLAIM')
        projection=nodes['D0']['input']['projection'];lineage=projection.get('replay_prewatch_lineage');require(isinstance(lineage,dict) and lineage['producer_output_digest']==checksum(nodes['C']['output']) and lineage['value']==nodes['C']['output']['raw_qualification'] and lineage['fixture_package_ref']==out['fixture_package_ref'],'EDGE_ORACLE_C_D0_UNBOUND_FIXTURE')
        from src.v4.state_identity import digest as owner_digest
        material={k:v for k,v in projection.items() if k not in ['publication_id','input_digest']};require(nodes['D0']['output']['input_publication_id']=='V4_11_INPUT:'+owner_digest(material),'EDGE_ORACLE_C_D0_NOT_IN_OWNER_INPUT_DIGEST')
        context_input=nodes['D3_CONTEXT']['input']
        for name,node in [('b0','B0'),('b1','B1'),('b2','B2'),('membership','MEMBERSHIP'),('core','F0'),('seed','A')]:require(context_input[name]==nodes[node]['output'],'EDGE_ORACLE_CONTEXT_PRODUCER_SUBSTITUTE')
        require(nodes['D3']['input']['context']==nodes['D3_CONTEXT']['output'] and nodes['D3']['input']['structure']==nodes['D1']['output'],'EDGE_ORACLE_PROFILE_PRODUCER_SUBSTITUTE')
        return True
    def manifest(self,artifact_root,m):
        super().manifest(artifact_root,m);return self.edges(artifact_root,m)
    def canonical(self,artifact_root,gate):
        require(gate['candidate_namespace']=='reports/v4_14_replay_r18/full_dag_r4','EDGE_ORACLE_NONCANONICAL_ATTEMPT')
        require(gate['attempt_disposition']['full_dag_r4']=='CURRENT_R18R1_CANDIDATE','EDGE_ORACLE_ATTEMPT_AUTHORITY')
        self.gate(artifact_root,gate['persisted_e2e'])
        return True
