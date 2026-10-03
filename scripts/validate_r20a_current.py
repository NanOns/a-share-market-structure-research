"""Independent current-pointer oracle; no reader/writer imports for expected state."""
import json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='2020234020e09020aca13fd84cdabde6fbb81f50'
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
def require(ok,reason):
    if not ok:raise ValueError(reason)
def read(p):return json.loads((ROOT/p).read_bytes())
def blob(p):return subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
def verify(binding):
    p=(ROOT/binding['path']).resolve();require(p.is_relative_to(ROOT.resolve()),'PATH_ESCAPE');raw=p.read_bytes()
    requested={'sha256':binding['sha256'],'bytes':binding.get('bytes',binding.get('byte_count'))}
    observed={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    if observed==requested:return raw
    # Independent explicit registry admission, never imports the resolver.
    registry=read('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json')
    e=next((e for e in registry['entries'] if e['path']==binding['path']),None)
    require(e is not None and e['mode']=='AUDITED_CRLF_LF_EQUIVALENT_TEXT' and e['source_kind']=='TEXT' and not e['lfs_object_identity'],'EXPLICIT_TEXT_REPRESENTATION_REQUIRED')
    require(requested in e['accepted_bindings'] and observed in e['admitted_representations'],'UNREGISTERED_REPRESENTATION')
    git_raw=subprocess.check_output(['git','cat-file','blob',e['git_blob_oid']],cwd=ROOT)
    require({'sha256':hashlib.sha256(git_raw).hexdigest(),'bytes':len(git_raw)}==e['git_blob_binding'],'GIT_BLOB_IDENTITY')
    canonical=git_raw.replace(b'\r\n',b'\n')
    variants=[git_raw,canonical,canonical.replace(b'\n',b'\r\n')]
    require(raw in variants,'CONTENT_MUTATION')
    usable=next((v for v in variants if {'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)}==requested),None)
    require(usable is not None,'ACCEPTED_BYTES_MISSING')
    return usable
def validate(stage=None,head=None):
    stage=read(STAGE) if stage is None else stage;head=read('data/v4/V4_14_ACCEPTED_HEAD.json') if head is None else head
    original=blob(STAGE);parent=json.loads(original);expected=dict(parent)
    expected.update(v4_14_entry='COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_REPLAY_GATE_B',v4_15_entry='CONTRACT_FREEZE_EXTERNALLY_ACCEPTED_RUNTIME_ENGINEERING_AUTHORIZED_AFTER_R20A')
    require(stage==expected,'CURRENT_METADATA_COHERENCE_EXACT')
    require((ROOT/'reports/r20a/PARENT_STAGE_HEAD.json').read_bytes()==original,'EXACT_PARENT_ARCHIVE')
    require((ROOT/'data/v4/V4_14_ACCEPTED_HEAD.json').read_bytes()==blob('data/v4/V4_14_ACCEPTED_HEAD.json') and head==json.loads(blob('data/v4/V4_14_ACCEPTED_HEAD.json')),'V4_14_ACCEPTED_HEAD_KEEP')
    require(head['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' and head['ALGORITHM_STATE_REPLAY_PASS']=='DEGRADED_PASS_CAPABILITY_SCOPED','NO_PIT_OVERCLAIM')
    verify(stage['v4_14_binding']);entry=json.loads(verify(head['entry_contract']));require(entry['bindings']==head['bindings'] and entry['capabilities']==head['capabilities'],'ACCEPTED_ENTRY')
    c=read('config/v4_current_stage_authority_v1.json')
    require(c['current_head']==stage['v4_14_binding'] and c['current_head']['path']=='data/v4/V4_14_ACCEPTED_HEAD.json','CURRENT_NOT_V4_13')
    require(c['immutable_owner_heads']=={k:parent[k+'_binding'] for k in ['v4_07','v4_08','v4_09','v4_10','v4_11','v4_12','v4_13','v4_14']},'IMMUTABLE_OWNERS')
    for binding in c['immutable_owner_heads'].values():verify(binding)
    require(verify(c['data_head'])==blob('data/v4/V4_DATA_ACCEPTED_HEAD.json'),'DATA_HEAD_KEEP')
    data=json.loads(verify(c['data_head']));require(data['accepted_trade_date']=='2026-09-30' and c['calendar']==data['calendar'] and c['identity']==data['identity'],'DATA_CALENDAR_IDENTITY')
    verify(c['calendar']);verify(c['membership']);verify(c['v4_15_contract_package'])
    audit=verify(c['external_audit']).decode();require(BASE in audit and 'PARTIAL_PASS_CURRENT_STAGE_RUNTIME_ENTRY_REPAIR_REQUIRED' in audit and 'EXTERNALLY_ACCEPTED_CONTRACT_SCOPE_RUNTIME_ENTRY_BLOCKED' in audit,'R19_AUDIT_AUTHORITY')
    for obj in [head,entry,c]:require(all(obj.get(k,False) is False for k in ['production','shadow','focus','V4_15_runtime','V4_15_accepted','V4_16']),'PERMISSIONS_FALSE')
    require(not (ROOT/'data/v4/V4_15_ACCEPTED_HEAD.json').exists(),'NO_V4_15_ACCEPTED')
    for p in ['scripts/validate_r17r1_active_closure.py','src/workbench_analysis/v4_13_accepted_contract_package.py','scripts/v4_14_rollback_oracle.py','scripts/v4_14_consumption_oracle_r18r1r1.py']:
        worktree_blob=subprocess.check_output(['git','hash-object','--path='+p,p],cwd=ROOT).strip()
        accepted_blob=subprocess.check_output(['git','rev-parse',BASE+':'+p],cwd=ROOT).strip()
        require(worktree_blob==accepted_blob,'HISTORICAL_GIT_BLOB_KEEP_'+p)
    return dict(R20A_CURRENT_STAGE_AUTHORITY='PASS_LOCAL',STAGE_HEAD_V4_14_ENTRY_COHERENCE='PASS',CURRENT_V4_14_READER='PASS',HISTORICAL_READER_ISOLATION='PASS',R19_AUDIT_02='CLOSED_LOCAL',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_14_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',V4_14_ACCEPTED_HEAD='KEEP',V4_15_ACCEPTED_HEAD='NOT_CREATED',Production=False,Shadow=False,Focus=False,R20C_R20D_RUNTIME_ENGINEERING='AUTHORIZED')
if __name__=='__main__':
    from scripts.r20_io import atomic
    result=validate();atomic('reports/r20a/CURRENT_AUTHORITY_GATE.json',result);print(json.dumps(result))
