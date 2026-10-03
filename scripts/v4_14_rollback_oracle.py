"""Expected bytes come from the audited Git baseline, never rollback code."""
import subprocess,json,hashlib
from pathlib import Path
BASE='f7b3402e4fbd5c98f4e76e3a56042a84960e120a'
PREFIX='reports/r18r1r1r1a/sandbox'
PROTECTED=['AGENTS.md','data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_12_ACCEPTED_HEAD.json','data/v4/V4_13_ACCEPTED_HEAD.json','data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json']
CANDIDATE='reports/r18r1r1c/V4_14_RUNTIME_CANDIDATE_R18R1R1_SEAL.json'
GATE='reports/r18r1r1b/final_full_dag_gate.json'
EXTRA=[CANDIDATE,GATE,'reports/r18r1r1c/independent_consumption_oracle_gate.json','reports/r18r1r1c/real_scoped_recheck.json','config/v4_14_precall_consumption_mapping_r18r1r1_v1.json']
def require(ok,reason):
    if not ok:raise ValueError(reason)
class RollbackOracle:
    def __init__(self,root):
        self.root=Path(root).resolve()
        names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'reports/v4_14_replay_r18/full_dag_r5'],cwd=self.root,text=True).splitlines()
        self.keep_names=names+EXTRA;paths=list(dict.fromkeys(PROTECTED+self.keep_names+['config/v4_capability_cutover_policy_v1.json']))
        raw=subprocess.check_output(['git','cat-file','--batch'],cwd=self.root,input=''.join(BASE+':'+p+'\n' for p in paths).encode());self.expected={};self.blobs={};offset=0
        for path in paths:
            end=raw.index(b'\n',offset);header=raw[offset:end].split();require(header[1]==b'blob','ORACLE_BASELINE_BLOB');size=int(header[2]);value=raw[end+1:end+1+size];offset=end+size+2
            self.blobs[path]=value;self.expected[path]=dict(path=path,sha256=hashlib.sha256(value).hexdigest(),bytes=size)
        self.parent=self.expected[PROTECTED[-1]];self.parent_bytes=self.blobs[PROTECTED[-1]];self.candidate=self.expected[CANDIDATE]
        self.policy=json.loads(self.blobs['config/v4_capability_cutover_policy_v1.json']);self.oldseal=json.loads(self.blobs[CANDIDATE])
        require(json.loads(self.parent_bytes)['accepted_stage_range']=='V4_00_TO_V4_13_ACCEPTED','ORACLE_PREDECESSOR_STAGE')
    def read(self,binding,sandbox=False):
        path=binding['path'];p=self.root/path
        require(not Path(path).is_absolute() and '..' not in Path(path).parts and p.resolve().is_relative_to(self.root),'ORACLE_PATH_ESCAPE')
        require(not any((self.root/Path(*Path(path).parts[:i])).is_symlink() for i in range(1,len(Path(path).parts)+1)),'ORACLE_SYMLINK_ESCAPE')
        if sandbox:require(path.startswith(PREFIX+'/'),'ORACLE_SANDBOX_PATH_ESCAPE')
        require(p.is_file(),'ORACLE_ARTIFACT_MISSING');raw=p.read_bytes()
        require(len(raw)==binding['bytes'] and hashlib.sha256(raw).hexdigest()==binding['sha256'],'ORACLE_EXACT_BYTES');return raw
    def fields(self,receipt):
        require(set(self.policy['failure_receipt_required_fields'])<=set(receipt),'ORACLE_FAILURE_RECEIPT_FIELDS')
        require(receipt['contract_id']==self.policy['contract_id'] and receipt['stage_id']=='V4-14' and bool(receipt['reason_codes']) and bool(receipt['recovery_owner']),'ORACLE_FAILURE_RECEIPT_VALUES')
        require(receipt['previous_accepted_head']==self.parent,'ORACLE_EXACT_PREDECESSOR')
    def validate(self,r):
        self.fields(r);require(r['execution_baseline']==BASE and r['sandbox_root']==PREFIX,'ORACLE_SCOPE')
        require(r['candidate_seal']==self.candidate and r['canonical_r5_gate']==self.expected[GATE],'ORACLE_CANDIDATE_AUTHORITY')
        require(r['v4_14_contract_package']==self.oldseal['authority_bindings']['contract_package'],'ORACLE_CONTRACT_PACKAGE')
        require(r['rollback_result']=='PASS' and r['idempotent'] is True and r['V4_14_ACCEPTED_HEAD']=='NOT_CREATED' and r['ALGORITHM_STATE_REPLAY_PASS']=='NOT_GRANTED_PENDING_EXTERNAL_AUDIT','ORACLE_NO_PARTIAL_ACCEPTANCE')
        for key in ['production','shadow','focus','V4_15','Stage_advance','Data_advance']:require(r[key] is False,'ORACLE_PERMISSION')
        require(not (self.root/'data/v4/V4_14_ACCEPTED_HEAD.json').exists(),'ORACLE_REAL_V4_14_HEAD')
        expected_heads=[self.expected[p] for p in PROTECTED]
        require(r['protected_heads_before']==r['protected_heads_after']==expected_heads,'ORACLE_REAL_PROTECTED_MUTATION')
        for binding in expected_heads:self.read(binding)
        expected_keep=[self.expected[p] for p in self.keep_names]
        # The implementation sorts its filesystem list; Git's tree order is also
        # lexicographic for these file paths. Compare mapping sets independently.
        require({b['path']:b for b in r['candidate_artifacts_preserved']}=={b['path']:b for b in expected_keep} and len(r['candidate_artifacts_preserved'])==len(expected_keep),'ORACLE_CANDIDATE_DELETION')
        for binding in expected_keep:self.read(binding)
        require(self.read(r['previous_accepted_head_archive'],True)==self.parent_bytes,'ORACLE_WRONG_PARENT_ARCHIVE')
        scenarios=r['scenarios'];require([s['scenario_id'] for s in scenarios]==['RB'+str(i).zfill(2) for i in range(1,9)],'ORACLE_SCENARIO_COVERAGE')
        for number,s in enumerate(scenarios[:6],1):
            sid=s['scenario_id'];path=PREFIX+'/'+sid
            require(s['sandbox_path']==path and s['head_path']==path+'/head.json','ORACLE_SANDBOX_PATH_ESCAPE')
            for name in ['before','after_fault','first_rollback_snapshot','second_rollback_snapshot','parent_archive']:
                require(s[name]['path'].startswith(path+'/'),'ORACLE_WRONG_SCENARIO_PATH')
            require(self.read(s['before'],True)==self.read(s['parent_archive'],True)==self.parent_bytes,'ORACLE_WRONG_PREDECESSOR_BYTES')
            require(self.read(s['first_rollback_snapshot'],True)==self.read(s['second_rollback_snapshot'],True)==self.parent_bytes,'ORACLE_ROLLBACK_BYTES_OR_IDEMPOTENCY')
            require(self.read(s['first_rollback']['head'],True)==self.read(s['second_rollback']['head'],True)==self.parent_bytes and s['second_rollback']['status']=='IDEMPOTENT','ORACLE_SECOND_ROLLBACK_CHANGED')
            self.fields(s['failure_receipt']);fault=self.read(s['after_fault'],True)
            if number in [1,3,4]:require(s['activation'] is None and fault==self.parent_bytes,'ORACLE_REJECTED_ACTIVATION_CHANGED_HEAD')
            else:
                activated=self.read(s['activation'],True);pointer=json.loads(activated)
                require(pointer==dict(status='SANDBOX_CANDIDATE_UNACCEPTED',previous_accepted_head=self.parent,candidate_seal=self.candidate,production=False,shadow=False,focus=False,V4_15=False,ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT'),'ORACLE_ACTIVATION_PERMISSION_OR_PARENT')
                require(fault==activated and s['cas_expected']==self.parent and s['first_rollback']['status']=='RESTORED','ORACLE_ACTIVATION_CAS')
            reason=s['failure_receipt']['reason_codes']
            require(reason==[({1:'INJECTED_FAILURE_BEFORE_ACTIVATION',2:'INJECTED_FAILURE_AFTER_ACTIVATION',3:'STALE_PREDECESSOR_CAS',4:'ACCEPTED_SOURCE_DIGEST_MISMATCH',5:'ACCEPTED_SOURCE_DIGEST_MISMATCH',6:'INJECTED_FAILURE_AFTER_ACTIVATION'})[number]],'ORACLE_FAULT_REASON')
            if number==3:require(s['cas_expected']['sha256']!=self.parent['sha256'],'ORACLE_STALE_CAS_NOT_INJECTED')
            elif number not in [2,5,6]:require(s['cas_expected']==self.parent,'ORACLE_WRONG_CAS_PARENT')
            if number in [4,5]:require(self.read(s['fault_evidence'],True)!=(self.blobs[CANDIDATE] if number==4 else self.parent_bytes),'ORACLE_MUTATION_NOT_INJECTED')
        require(scenarios[6]['candidate_artifacts']==r['candidate_artifacts_preserved'] and scenarios[7]['protected_before']==scenarios[7]['protected_after']==expected_heads,'ORACLE_RETENTION_SCENARIOS')
        return True
