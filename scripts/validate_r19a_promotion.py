"""Independent promotion oracle: expected authorities reconstructed from Git/audit."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'f4ad7d632e53734798c064f011e2b53ecd99bc27'
TESTED = '04b310c2b011dbeb99dd1c2430165201917dd328'
STAGE = 'data/v4/V4_STAGE_ACCEPTED_HEAD.json'
HEAD = 'data/v4/V4_14_ACCEPTED_HEAD.json'
EXPECTED = {
    'external_audit': 'docs/evidence/r19/V4_R18R1R1R1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md',
    'rollback_complete_seal': 'reports/r18r1r1r1b/V4_14_RUNTIME_CANDIDATE_ROLLBACK_COMPLETE_SEAL.json',
    'runtime_seal': 'reports/r18r1r1c/V4_14_RUNTIME_CANDIDATE_R18R1R1_SEAL.json',
    'canonical_full_dag_r5': 'reports/r18r1r1b/final_full_dag_gate.json',
    'consumption_oracle': 'reports/r18r1r1c/independent_consumption_oracle_gate.json',
    'rollback_receipt': 'reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json',
    'rollback_oracle': 'reports/r18r1r1r1b/independent_rollback_oracle_gate.json',
    'contract_package': 'config/v4_14_replay_gate_b_contract_v1_1.json',
    'amended_predecessor': 'data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json',
    'data_head': 'data/v4/V4_DATA_ACCEPTED_HEAD.json',
    'parent_stage': 'reports/r19a/PARENT_STAGE_HEAD.json',
    'calendar': 'data/v4/source_evidence/dm01_a01_r3/chain_inputs_r1/calendar_union_2e0938120e3b371aa9c84422c06b4c14de0f8894cc8f3caa9dd9c61299239e74.json',
    'membership': 'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json',
}
CAP = dict(ENGINEERING_SYNTHETIC_REPLAY='FULL_PASS', FULL_D0_D1_D2_REPLAY='ENGINEERING_ACCEPTED', EDGE_CONSUMPTION_TRUTH='PASS', CROSS_PROCESS_PREVIOUS_SESSION='PASS', SAME_DAY_REVISION_ISOLATION='PASS', DETERMINISTIC_REPLAY='PASS', ROLLBACK_RECEIPT='PASS', REAL_ACCEPTED_SOURCE_REPLAY='PASS_CAPABILITY_SCOPED', HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED', REAL_SIGNAL_CAPABILITY='DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY')

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def git_bytes(path):
    raw = subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)
    if raw.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        lines=raw.decode().splitlines(); digest=lines[1].split('sha256:')[1]; size=int(lines[2].split()[1])
        data=(ROOT/path).read_bytes()
        require(len(data)==size and hashlib.sha256(data).hexdigest()==digest, 'BASELINE_LFS_OBJECT_'+path)
        return data
    return raw

def binding(path, raw):
    return dict(path=path, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def validate(head=None, stage=None):
    h = json.loads((ROOT / HEAD).read_bytes()) if head is None else head
    s = json.loads((ROOT / STAGE).read_bytes()) if stage is None else stage
    require(h['audited_head'] == BASE and h['tested_source'] == TESTED, 'EXACT_AUDITED_TESTED_HEAD')
    require(h['stage']=='V4-14' and h['status']=='ALGORITHM_STATE_REPLAY_DEGRADED_PASS' and h['external_acceptance']=='EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED', 'CAPABILITY_SCOPED_STATUS')
    require(h['ALGORITHM_STATE_REPLAY_PASS']=='DEGRADED_PASS_CAPABILITY_SCOPED' and h['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' and h['capabilities']==CAP, 'HISTORICAL_PIT_OVERCLAIM')
    require(h['external_audit_decision']=='PASS_FINAL_V4_14_RUNTIME_CAPABILITY_SCOPED' and h['REAL_ACCEPTED_SOURCE_REPLAY']=='PASS_CAPABILITY_SCOPED' and h['accepted_trade_date']=='2026-09-30', 'ACCEPTANCE_SCOPE')
    require(set(h['bindings'])==set(EXPECTED), 'EVIDENCE_COMPLETENESS')
    audit = (ROOT / EXPECTED['external_audit']).read_bytes()
    require(hashlib.sha256(audit).hexdigest()=='ba077c931b9e8c303588d1551d500c910749a40f902d87a750a9af54384747fc' and len(audit)==5931,'EXACT_EXTERNAL_AUDIT_BYTES')
    for token in [BASE, TESTED, '7035c130027ecaef2f5443cea05c64f328081b01abf839ec98ed34828a43bc5c', 'PASS_FINAL_V4_14_RUNTIME_CAPABILITY_SCOPED', 'HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED']:
        require(token.encode() in audit, 'EXTERNAL_AUDIT_AUTHORITY')
    for name,path in EXPECTED.items():
        raw = (ROOT / path).read_bytes()
        expected = audit if name=='external_audit' else git_bytes(STAGE if name=='parent_stage' else path)
        require(raw==expected and h['bindings'][name]==binding(path, expected), 'EXACT_BINDING_'+name)
    seal = json.loads(git_bytes(EXPECTED['rollback_complete_seal']))
    require(seal['tested_source_sha']==TESTED and seal['rollback_receipt']==h['bindings']['rollback_receipt'], 'ROLLBACK_COMPLETE_SEAL')
    require(seal['canonical_r5_gate']==h['bindings']['canonical_full_dag_r5'] and seal['independent_rollback_oracle']==h['bindings']['rollback_oracle'], 'CANONICAL_R5_ROLLBACK_ORACLE')
    entry_path='config/v4_14_accepted_entry_contract_v1.json'
    entry_raw=(ROOT/entry_path).read_bytes(); entry=json.loads(entry_raw)
    require(h['entry_contract']==binding(entry_path,entry_raw) and entry['bindings']==h['bindings'] and entry['capabilities']==CAP and entry['audited_head']==BASE and entry['tested_source']==TESTED and entry['accepted_head_namespace']==HEAD, 'ENTRY_CONTRACT')
    for item in [h,entry]:
        require(all(item.get(k) is False for k in ['production','shadow','focus','V4_15_runtime']), 'PERMISSION_NOT_GRANTED')
    parent=json.loads(git_bytes(STAGE))
    expected_stage=dict(parent)
    expected_stage.update(accepted_stage_range='V4_00_TO_V4_14_ACCEPTED', v4_14_binding=binding(HEAD,(ROOT/HEAD).read_bytes()), v4_14_status='ALGORITHM_STATE_REPLAY_DEGRADED_PASS', v4_14_external_acceptance='PASS_FINAL_V4_14_RUNTIME_CAPABILITY_SCOPED', v4_14_capabilities=CAP, v4_15_entry='CONTRACT_FREEZE_AUTHORIZED_RUNTIME_NOT_AUTHORIZED')
    require(s==expected_stage, 'EXACT_STAGE_PARENT_AND_PERMISSION')
    tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'data/v4'],cwd=ROOT,text=True).splitlines()
    protected=['AGENTS.md']+[p for p in tracked if 'ACCEPTED_HEAD' in p and p!=STAGE]
    for p in protected:
        actual=(ROOT/p).read_bytes(); base=git_bytes(p)
        require(actual==base or actual.replace(b'\r\n',b'\n')==base, 'PROTECTED_GIT_CONTENT_'+p)
        manifest=json.loads((ROOT/'reports/r19a/PROTECTED_WORKTREE_BYTES.json').read_bytes())
        require(binding(p,actual)==manifest[p], 'PROTECTED_UNCHANGED_'+p)
    require(not (ROOT/'data/v4/V4_15_ACCEPTED_HEAD.json').exists(), 'NO_V4_15_ACCEPTED_HEAD')
    return dict(R19A_V4_14_PROMOTION='PASS_LOCAL', V4_14_ACCEPTED_HEAD='CREATED', ALGORITHM_STATE_REPLAY_PASS='DEGRADED_PASS_CAPABILITY_SCOPED', V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_14_ACCEPTED', V4_DATA_ACCEPTED_HEAD='2026-09-30', Production=False, Shadow=False, Focus=False, V4_15_RUNTIME='NOT_AUTHORIZED', NEXT='R19B_R19C_V4_15_CONTRACT_FREEZE', protected_count=len(protected))

if __name__=='__main__':
    from scripts.r19_io import atomic
    result=validate()
    atomic('reports/r19a/PROMOTION_GATE.json', result)
    print(json.dumps(result))
