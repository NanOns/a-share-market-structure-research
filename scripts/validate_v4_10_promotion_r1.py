"""Read-only independent exact-byte validator for the externally accepted R1.2 seal."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = '6a339e71d38ced6e97c077fddef8dc7a8dfbd104'
SEALED = 'f0c6eb57f7c0c8fc2d0d6875d73295e349e7d315'
DECISION = 'V4_10_EXTERNAL_ACCEPTANCE_PASS_R1_2_ENGINEERING_SCOPE'
PARENT = 'data/v4/V4_09_ACCEPTED_HEAD.json'
GLOBAL = 'data/v4/V4_STAGE_ACCEPTED_HEAD.json'
HEAD = 'data/v4/V4_10_ACCEPTED_HEAD.json'
CANDIDATE = 'reports/v4_joint/V4_10_ACCEPTED_HEAD_CANDIDATE_R1.json'
CLEAN = 'reports/v4_joint/V4_10_PROMOTION_CLEAN_DETACHED_R1.json'
ARCHIVE = 'reports/v4_joint/V4_10_PROMOTION_PARENT_STAGE_HEAD_R1.json'
AUDIT = 'docs/evidence/V4_10_R1_2_INDEPENDENT_EXTERNAL_ACCEPTANCE_FINAL_20261001.md'
MANIFEST = 'reports/v4_10/V4_10_R1_2_STAGE_CANDIDATE_MANIFEST.json'
CAPABILITIES = {**{k:'ENGINEERING_ACCEPTED' for k in ('STATE_REDUCER_INTERFACE','STATE_REDUCER_AUTHORITY',
    'STATE_REDUCER_PERSISTENCE','STATE_REDUCER_MACHINE_VECTORS')},
    **{k:'NOT_IMPLEMENTED' for k in ('FULL_D0_D1_D2_DAG','V4_11_CONFIRMATION','V4_12_STRUCTURE_SUPPORT')}}
PERMISSIONS = ('production_permission','shadow_production_permission','focus_cutover_permission')
EVIDENCE_NAMES = ('CONTRACT_FREEZE','INDEPENDENT_POSTCHECK','MODEL_BOUNDARY_ACCEPTANCE','INPUT_PROVENANCE_ACCEPTANCE',
    'INPUT_MANIFEST_SHAPE_ACCEPTANCE','CONTROLLED_PUBLISHER_ACCEPTANCE','SCHEMA_MIGRATION_RECEIPT',
    'ISOLATED_REGRESSION','CLEAN_CHECKOUT_RECEIPT','NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN')

def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf8'))

def bind(path):
    data=(ROOT/path).read_bytes()
    return dict(path=path,sha256=hashlib.sha256(data).hexdigest(),byte_count=len(data))

def exact(b):
    try: return all(bind(b['path'])[k]==b[k] for k in ('sha256','byte_count') if k in b)
    except (OSError,KeyError,TypeError): return False

def git_exact(path, commit):
    result=subprocess.run(['git','show',commit+':'+path],cwd=ROOT,capture_output=True)
    return result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==bind(path)['sha256']

def expected_evidence():
    return {**{n:bind('reports/v4_10/V4_10_R1_2_'+n+'.json') for n in EVIDENCE_NAMES},
            'STAGE_CANDIDATE_MANIFEST':bind(MANIFEST),'EXTERNAL_ACCEPTANCE':bind(AUDIT)}

def validate(candidate=None, *, detached_probe=False):
    h=read(CANDIDATE) if candidate is None else candidate
    m=read(MANIFEST); freeze=read(m['evidence_bindings']['CONTRACT_FREEZE']['path'])
    checks={}
    def check(n, ok): checks[n]='PASS' if ok else 'FAIL'
    check('P01_schema', h.get('contract_id')=='V4_10_ACCEPTED_HEAD_V1' and h.get('stage')=='V4-10'
          and h.get('status')=='ENGINEERING_PASS_INTERFACE_SCOPE' and h.get('external_acceptance')=='EXTERNALLY_ACCEPTED'
          and h.get('external_acceptance_decision')==DECISION and h.get('capabilities')==CAPABILITIES)
    check('P02_parent_exact', h.get('parent_binding')==bind(PARENT) and bind(PARENT)['sha256']==
          '641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d')
    check('P03_implementation_exact', h.get('implementation_commit')==m['tested_implementation_commit']==IMPLEMENTATION
          and all(exact(b) and git_exact(b['path'],IMPLEMENTATION) for b in m['source_implementation_bindings']))
    check('P04_seal_descendant', h.get('audited_sealed_head')==SEALED and subprocess.run(
        ['git','merge-base','--is-ancestor',IMPLEMENTATION,SEALED],cwd=ROOT).returncode==0
        and subprocess.run(['git','merge-base','--is-ancestor',SEALED,'HEAD'],cwd=ROOT).returncode==0)
    evidence=h.get('evidence_bindings',{})
    check('P05_external_exact', evidence.get('EXTERNAL_ACCEPTANCE')==bind(AUDIT)
          and bind(AUDIT)['sha256']=='61a40e57f6dd1e03bee6334c9b18a833b051050784b5c8ade64f40077e565ce0'
          and all(s in (ROOT/AUDIT).read_text(encoding='utf8') for s in (DECISION,IMPLEMENTATION,SEALED)))
    for number,name in ((6,'CONTRACT_FREEZE'),(8,'INDEPENDENT_POSTCHECK'),(9,'MODEL_BOUNDARY_ACCEPTANCE'),
                        (10,'INPUT_PROVENANCE_ACCEPTANCE'),(11,'CONTROLLED_PUBLISHER_ACCEPTANCE'),(12,'SCHEMA_MIGRATION_RECEIPT')):
        b=m['evidence_bindings'][name]
        check(f'P{number:02d}_{name}',evidence.get(name)==b and exact(b) and git_exact(b['path'],SEALED)
              and read(b['path'])['status'].startswith('PASS'))
    check('P07_manifest_exact',evidence.get('STAGE_CANDIDATE_MANIFEST')==bind(MANIFEST) and git_exact(MANIFEST,SEALED)
          and all(exact(b) for b in m['contracts'].values()) and all(exact(b) for b in m['evidence_bindings'].values())
          and evidence==expected_evidence())
    regression=read(m['evidence_bindings']['ISOLATED_REGRESSION']['path']); clean=read(m['evidence_bindings']['CLEAN_CHECKOUT_RECEIPT']['path'])
    check('P13_clean_regression_exact',all(exact(m['evidence_bindings'][n]) and git_exact(m['evidence_bindings'][n]['path'],SEALED)
          for n in ('ISOLATED_REGRESSION','CLEAN_CHECKOUT_RECEIPT')) and regression['summary']['passed']==1116
          and regression['summary']['failures']==regression['summary']['errors']==0 and clean['detached_head']
          and clean['config_dot_env_present'] is False and clean['config_dot_env_read'] is False)
    scan=read(m['evidence_bindings']['NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN']['path'])
    check('P14_no_symbol_exact',exact(m['evidence_bindings']['NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN'])
          and scan['status']=='PASS' and scan['hard_gated_equity_symbol_hits']==0 and not scan['unclassified_paths'])
    for n in (22,23,24):
        paths=list((ROOT/'src/workbench_db/migrations/v4_postgres').glob(f'{n:03d}_*.sql'))
        paths+=list((ROOT/'src/workbench_db/migrations/v4_postgres/rollback').glob(f'{n:03d}_*.sql'))
        check(f'P{n-7:02d}_migration_{n}',len(paths)==2 and all(git_exact(p.relative_to(ROOT).as_posix(),IMPLEMENTATION) for p in paths))
    check('P18_thresholds', m['business_thresholds']==dict(downgrade_sessions=2,expiry_sessions=10,expiry_improvement_pp=3,health_deadband_pp=3)
          and freeze['business_thresholds_unchanged'] and all(exact(b) for b in freeze['bindings'].values()))
    for n,path in ((19,'data/v4/V4_DATA_ACCEPTED_HEAD.json'),(20,'data/v4/V4_DEV_BASELINE_HEAD.json'),
                   (21,'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json')):
        b=next(x for x in freeze['protected_bindings'] if x['path']==path)
        check(f'P{n:02d}_protected', exact(b) and b in h.get('protected_head_bindings',[]))
    registry=m['cross_stage_registry']; r=read(registry['path'])
    check('P22_audits_open',h.get('open_audit_registry')==registry and exact(registry) and len(r['entries'])==9
          and all(e['status']=='OPEN' and e['external_acceptance'] is None for e in r['entries']))
    parent=read(ARCHIVE); g=read(GLOBAL)
    check('P23_permissions_false',all(h.get(k) is False and g.get(k) is False for k in PERMISSIONS)
          and exact(h.get('global_head_parent_archive',{})) and h.get('global_head_parent',{}).get('sha256')==bind(ARCHIVE)['sha256']
          and parent['accepted_stage_range']=='V4_00_TO_V4_09_ACCEPTED')
    # Preserve every existing global field, except the range and version explicitly advanced by this task.
    allowed= g==parent or (g.get('accepted_stage_range')=='V4_00_TO_V4_10_ACCEPTED' and
        all(g.get(k)==v for k,v in parent.items() if k not in ('accepted_stage_range','version')) and
        g.get('v4_10_binding')==bind(HEAD) and g.get('open_audit_registry')==registry and
        g.get('v4_11_entry')=='AUTHORIZED_CONFIRMATION_EVENTS_CONTRACT_ENTRY_ONLY')
    check('P24_idempotent_and_global_lineage',allowed and (not (ROOT/HEAD).exists() or read(HEAD)==h))
    if detached_probe:
        detached=subprocess.run(['git','symbolic-ref','-q','HEAD'],cwd=ROOT,capture_output=True).returncode!=0
        check('P25_clean_detached',detached and not (ROOT/'config/.env').exists() and not subprocess.check_output(
            ['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    else:
        c=read(CLEAN) if (ROOT/CLEAN).exists() else {}
        current_sources=[bind(p) for p in ('scripts/validate_v4_10_promotion_r1.py','scripts/promote_v4_10_accepted_head_r1.py')]
        check('P25_clean_detached',c.get('status')=='PASS' and c.get('checks',{}).get('P25_clean_detached')=='PASS'
              and c.get('validator_bindings')==current_sources and c.get('candidate_sha256')==bind(CANDIDATE)['sha256'])
    return dict(contract_id='V4_10_PROMOTION_VALIDATOR_R1',status='PASS' if all(v=='PASS' for v in checks.values()) else 'FAIL',
                checks=checks,candidate_sha256=bind(CANDIDATE)['sha256'],validator_bindings=[bind(p) for p in (
                    'scripts/validate_v4_10_promotion_r1.py','scripts/promote_v4_10_accepted_head_r1.py')])

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--detached-probe',action='store_true');a=p.parse_args()
    result=validate(detached_probe=a.detached_probe); print(json.dumps(result));raise SystemExit(result['status']!='PASS')
