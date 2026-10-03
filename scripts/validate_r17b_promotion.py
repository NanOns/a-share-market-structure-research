"""Independent exact-byte P01-P15 authority gate; no promotion/runtime imports."""
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE='f12315bf8e3142aa44e9068c5895004c35c4e23c';TESTED='d370788688c7e1be0fe2e3c9b0b160d93374b4ee'
HEAD='data/v4/V4_13_ACCEPTED_HEAD.json';STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
MANIFEST='reports/v4_13_runtime_r16/real/2026-09-30/r6/manifest.json'
M_SHA='a02e7918826627c2b496d89e546d3f5a408e4c68a1a89bc93946e152e7ca42ec'
AUDIT='docs/evidence/r17/V4_R16R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md';A_SHA='652621971b019a383d387cef2ba40b78eb1000993b55bb6418f5378c80c52222'
def read(path):return json.loads((ROOT/path).read_bytes())
def exact(ref):
    p=(ROOT/ref['path']).resolve();assert p.is_relative_to(ROOT)
    with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    assert h==ref['sha256'] and all(p.stat().st_size==ref[k] for k in ('bytes','byte_count') if k in ref)
    return True
def same_git(ref,commit):
    raw=subprocess.check_output(['git','show',commit+':'+ref['path']],cwd=ROOT)
    return hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref.get('bytes',len(raw)) and exact(ref)
def canon(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def guarded(fn):
    try:return bool(fn())
    except (KeyError,ValueError,AssertionError,OSError,TypeError,StopIteration,subprocess.CalledProcessError):return False
def validate(candidate=None):
    h=read(HEAD) if candidate is None else candidate;m=read(MANIFEST);s=read(STAGE);parent=read('reports/r17b/PARENT_STAGE_HEAD.json');a=read('reports/r17a/completion_gate.json');c=read('reports/r17b/stage_contract.json')
    def authority():
        r=h['external_authority'];assert r==dict(path=AUDIT,sha256=A_SHA,bytes=5488);exact(r)
        text=(ROOT/AUDIT).read_text(encoding='utf8');return all(x in text for x in [BASE,TESTED,'R16R1_EXTERNAL_AUDIT = PASS_SCOPED_ENGINEERING','V4_13_ACCEPTED_HEAD_PROMOTION = AUTHORIZED_AFTER_R17A_PASS']) and h['external_acceptance']=='EXTERNALLY_ACCEPTED_ENGINEERING_SCOPE' and h['external_acceptance_decision']=='R16R1_EXTERNAL_AUDIT_PASS_SCOPED_ENGINEERING_AFTER_R17A_PASS'
    def lineage():
        p=next(r for r in h['contract_refs'] if r['path']=='config/v4_13_projection_v1_2.json');exact(p);v=read(p['path']);old=v['supersedes'];exact(old)
        return p['sha256']=='567b498c9e0f828dc041d56ab56e79c8a4d34877fd09eef46a9c1f504396b19c' and v['version']=='1.2.0' and v['contract_id']==read(old['path'])['contract_id']
    def a_gate():
        assert exact(h['r17a_gate']) and h['r17a_gate']==c['entry_gate'];assert a['R17A_CROSS_STAGE_GOVERNANCE_REPAIR']=='PASS'
        assert exact(a['clean_detached']);clean=read(a['clean_detached']['path']);assert clean['status']=='PASS' and clean['git_clean_before'] and clean['git_clean_after'];assert clean['source_sha']==a['tested_source'];assert not any(clean['test_totals'][k] for k in ['failed','errors','skipped','deselected']);return True
    def parent_gate():
        ref=h['global_head_parent_archive'];assert ref['path']=='reports/r17b/PARENT_STAGE_HEAD.json';assert exact(ref)
        return ref['sha256']==h['global_head_parent']['sha256']=='b0e1c2402efdd71d706a87f45280206a87fbe9e637a4168255b7ff4c036520f7' and ref['bytes']==h['global_head_parent']['bytes']==11381 and parent['accepted_stage_range']=='V4_00_TO_V4_12_ACCEPTED' and subprocess.check_output(['git','show',BASE+':'+STAGE],cwd=ROOT)==(ROOT/ref['path']).read_bytes()
    def stage_gate():
        exact(s['v4_13_binding']);assert s['v4_13_binding']['path']==HEAD
        return s['accepted_stage_range']=='V4_00_TO_V4_13_ACCEPTED' and s['v4_13_promotion_parent_archive']==h['global_head_parent_archive'] and all(s[k]==v for k,v in parent.items() if k!='accepted_stage_range') and s['v4_13_capabilities']==h['capabilities']
    def scope():
        expected=dict(V4_13_PROFILE_ADVANCED_PROJECTION='ENGINEERING_ACCEPTED',V4_13_CURRENT_MEMBERSHIP_RELATION='ENGINEERING_ACCEPTED_PIT_20260930',V4_13_TARGET_EXCLUDED_LOO_CORE='ENGINEERING_ACCEPTED_CAPABILITY_SCOPED',V4_13_STRUCTURE_READ_ONLY_PROJECTION='ENGINEERING_ACCEPTED',V4_13_COMPONENT_PROVENANCE='ENGINEERING_ACCEPTED',V4_13_REVISION_PUBLICATION='ENGINEERING_ACCEPTED',V4_13_REAL_SIGNAL_CAPABILITY='DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY',algorithmic_support_sector='UNKNOWN_REAL_ACCEPTED_CAPABILITY',relative_sector_state='UNKNOWN_REAL_ACCEPTED_CAPABILITY',historical_LOO='NOT_VERIFIABLE',legacy_B2='NOT_IMPLEMENTED')
        return h['capabilities']==expected and h['status']=='ENGINEERING_PASS_CAPABILITY_SCOPED' and h['knowledge_lineage']==m['knowledge_lineage'] and h['AS_RECORDED'] is False
    checks={
      'P01_EXTERNAL_AUDIT_EXACT':guarded(authority),
      'P02_AUDITED_SEALED_HEAD_EXACT':guarded(lambda:h['audited_sealed_head']==BASE and subprocess.check_output(['git','rev-parse',BASE],cwd=ROOT,text=True).strip()==BASE and same_git(h['candidate'],BASE)),
      'P03_TESTED_SOURCE_EXACT':guarded(lambda:h['tested_runtime_source']==TESTED and h['runtime_source_bindings']==m['runtime_source_refs'] and all(same_git(r,TESTED) and same_git(dict(r,path=r['original_path']),TESTED) for r in h['runtime_source_bindings'])),
      'P04_R6_MANIFEST_EXACT':guarded(lambda:h['candidate']['path']==MANIFEST and h['candidate']['sha256']==M_SHA and exact(h['candidate'])),
      'P05_R6_ARTIFACT_REFS_EXACT':guarded(lambda:h['artifact_refs']==m['artifacts'] and all(exact(r) for r in h['artifact_refs']) and h['input_accepted_head_refs']==m['input_accepted_head_refs'] and all(exact(r) for r in h['input_accepted_head_refs'])),
      'P06_CONTRACT_PACKAGE_EXACT':guarded(lambda:h['contract_refs']==m['contract_refs'] and all(exact(r) for r in h['contract_refs']) and h['contract_digest']==m['contract_digest']==hashlib.sha256(canon(h['contract_refs'])).hexdigest() and h['formal_entry_contract']['path']=='config/v4_13_accepted_entry_contract_v1.json' and exact(h['formal_entry_contract']) and read(h['formal_entry_contract']['path'])['contract_id']=='V4_13_ACCEPTED_CONTRACT_PACKAGE_ENTRY_V1' and read(h['formal_entry_contract']['path'])['contract_digest']==h['contract_digest'] and read(h['formal_entry_contract']['path'])['contract_refs']==h['contract_refs'] and read(h['formal_entry_contract']['path'])['amendment_receipt_presence_is_authority'] is False),
      'P07_PROJECTION_V1_2_LINEAGE_EXACT':guarded(lineage),
      'P08_R17A_GATE_PASS':guarded(a_gate),
      'P09_PARENT_STAGE_ARCHIVE_EXACT':guarded(parent_gate),
      'P10_NEW_STAGE_PREDECESSOR_EXACT':guarded(stage_gate),
      'P11_DATA_HEAD_BYTE_IDENTICAL':guarded(lambda:h['protected_head_bindings']['data/v4/V4_DATA_ACCEPTED_HEAD.json']==c['protected']['data/v4/V4_DATA_ACCEPTED_HEAD.json'] and exact(c['protected']['data/v4/V4_DATA_ACCEPTED_HEAD.json']) and same_git(c['protected']['data/v4/V4_DATA_ACCEPTED_HEAD.json'],BASE)),
      'P12_V4_12_HEAD_BYTE_IDENTICAL':guarded(lambda:h['protected_head_bindings']['data/v4/V4_12_ACCEPTED_HEAD.json']==c['protected']['data/v4/V4_12_ACCEPTED_HEAD.json'] and exact(c['protected']['data/v4/V4_12_ACCEPTED_HEAD.json']) and same_git(c['protected']['data/v4/V4_12_ACCEPTED_HEAD.json'],BASE)),
      'P13_NO_PRODUCTION_SHADOW_FOCUS':guarded(lambda:all(h[k] is False for k in ['production','shadow','focus','global_mandatory_adoption']) and all(s[k] is False for k in ['production_permission','shadow_production_permission','focus_cutover_permission','global_mandatory_adoption']) and exact(c['protected']['AGENTS.md'])),
      'P14_DEGRADATION_NOT_OVERCLAIMED':guarded(scope),
      'P15_V4_14_NOT_ACCEPTED':guarded(lambda:h['ALGORITHM_STATE_REPLAY_PASS']=='NOT_GRANTED' and not (ROOT/'data/v4/V4_14_ACCEPTED_HEAD.json').exists() and s['v4_14_entry']=='CONTRACT_FREEZE_ONLY_NOT_REPLAY_PASS')}
    return dict(contract_id='R17B_INDEPENDENT_PROMOTION_GATE_P01_P15_V1',status='PASS' if all(checks.values()) else 'FAIL',checks=checks,engineering_scope_only=True,ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED')
if __name__=='__main__':
    result=validate();print(json.dumps(result));raise SystemExit(result['status']!='PASS')
