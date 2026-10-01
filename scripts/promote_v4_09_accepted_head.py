"""Exact externally authorized promotion; no change to protected input heads."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json, atomic_bytes

DECISION = 'V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE'
AUDITED = '981332582c1982d9da3af922688e682946822119'
IMPLEMENTATION = '5eca56d3555a826c4cca94d6e3d7ae9d11628be6'
HEAD = 'data/v4/V4_09_ACCEPTED_HEAD.json'
GLOBAL = 'data/v4/V4_STAGE_ACCEPTED_HEAD.json'
MANIFEST = 'reports/v4_09/V4_09_R1_1_STAGE_CANDIDATE_MANIFEST.json'
AUDIT = 'docs/evidence/V4_09_R1_1_INDEPENDENT_EXTERNAL_ACCEPTANCE_FINAL_20260930.md'
RECEIPT = 'reports/v4_joint/V4_09_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json'
VALIDATION = 'reports/v4_joint/V4_09_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json'
ENTRY = 'AUTHORIZED_FOR_STATE_REDUCER_INTERFACE_AND_INDEPENDENT_VECTORS'
CAPABILITIES = dict(V4_09_ENGINEERING='ENGINEERING_ACCEPTED', STOCK_PREWATCH_RAW='ENGINEERING_ACCEPTED',
                    PRIORITY_V1='ENGINEERING_ACCEPTED', REAL_SIGNAL_CAPABILITY='DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN')
PERMISSIONS = ['production_permission', 'shadow_production_permission', 'focus_cutover_permission']

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf8'))

def bind(path):
    data = (ROOT / path).read_bytes()
    return dict(path=path, sha256=hashlib.sha256(data).hexdigest(), byte_count=len(data))

def exact(b):
    return all(bind(b['path'])[k] == b[k] for k in ('sha256', 'byte_count') if k in b)

def source_checks():
    m = read(MANIFEST)
    audit = (ROOT / AUDIT).read_text(encoding='utf8')
    bindings = [*m['contracts'].values(), *m['evidence_bindings'].values(), *m['source_implementation_bindings'],
                *m['accepted_input_bindings'].values(), *m['materialized_vector_artifacts'].values(), m['artifact'], m['amended_v4_08_head']]
    with gzip.open(ROOT / m['artifact']['path'], 'rt', encoding='utf8') as f:
        records = [json.loads(line) for line in f]
    from src.v4.stock_prewatch import digest
    scan = read('reports/v4_09/V4_09_R1_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json')
    pinned = ['config/v4_09_stock_prewatch_contract_v1.json','config/v4_09_machine_ast_v1.json',
              'config/v4_09_parameter_set_v1.json','src/v4/stock_prewatch.py']
    def git_exact(path):
        data = subprocess.run(['git', 'show', AUDITED + ':' + path], cwd=ROOT, capture_output=True, check=True).stdout
        return hashlib.sha256(data).hexdigest() == bind(path)['sha256']
    return dict(
        external_exact=all(x in audit for x in [DECISION, AUDITED, IMPLEMENTATION]),
        implementation_exact=m['tested_implementation_commit'] == IMPLEMENTATION,
        audited_ancestor=subprocess.run(['git','merge-base','--is-ancestor',AUDITED,'HEAD'], cwd=ROOT).returncode == 0,
        all_candidate_bindings_exact=all(exact(b) for b in bindings),
        runtime_contracts_match_audited_commit=all(git_exact(p) for p in pinned),
        amended_upstream_exact=m['amended_v4_08_head']['path']=='data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json' and
            bind(m['amended_v4_08_head']['path'])['sha256']=='f2a35cebd18e8caf723e7900133333ce4b8df1a8314cb190dade7b0ea7624a3f',
        artifact_exact=m['artifact']['path']=='data/v4/artifact_store/v4_09/V4_09_STOCK_PREWATCH_2026-09-28_edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e.jsonl.gz' and
            m['artifact']['sha256']=='8b92cbd96a8145005bad89374349582c075cf367722b956a75243d59aa64d18d' and
            digest(records)==m['artifact']['logical_digest']=='edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e',
        evidence_pass=all(read('reports/v4_09/V4_09_R1_1_'+n+'.json')['status'].startswith('PASS') for n in
            ['PRIORITY_PRODUCER_CONTRACT_GATE','ARTIFACT_IMMUTABILITY','MATERIALIZED_MULTI_CONTEXT','INDEPENDENT_POSTCHECK',
             'SCHEMA_MIGRATION_RECEIPT','CLEAN_CHECKOUT_RECEIPT','ISOLATED_REGRESSION']),
        no_symbol_pass=scan['status']=='PASS' and scan['hard_gated_equity_symbol_hits']==0 and not scan['unclassified_paths'])

def validate_head(h, g, receipt):
    checks = source_checks()
    effective_global = bind(GLOBAL)
    if g.get('accepted_stage_range') == 'V4_00_TO_V4_10_ACCEPTED':
        # A later, independently accepted stage keeps the exact V4-09 promotion parent.
        from scripts.validate_v4_10_promotion_r1 import validate as validate_child, ARCHIVE
        checks['accepted_child_stage_exact'] = validate_child()['status'] == 'PASS'
        effective_global = bind(ARCHIVE)
        effective_global['path'] = GLOBAL
        g = read(ARCHIVE)
    m = read(MANIFEST)
    checks.update(
        accepted_identity=h['status']=='ENGINEERING_PASS_CAPABILITY_SCOPED' and h['external_acceptance']=='EXTERNALLY_ACCEPTED' and
            h['external_acceptance_decision']==DECISION and h['audited_head']==AUDITED and h['implementation_commit']==IMPLEMENTATION,
        accepted_evidence_exact=all(exact(b) for b in h['evidence_bindings'].values()),
        canonical_evidence_set=h['evidence_bindings']==expected_evidence(),
        upstream_exact=h['upstream_binding']==m['amended_v4_08_head'],
        artifact_exact_binding=h['artifact']==m['artifact'],
        protected_unchanged=h['protected_head_bindings']==m['protected_head_bindings'] and all(exact(b) for b in h['protected_head_bindings']),
        capabilities_exact=h['capabilities']==CAPABILITIES,
        permissions_false=all(h[k] is False and g[k] is False for k in PERMISSIONS),
        global_binding=g['accepted_stage_range']=='V4_00_TO_V4_09_ACCEPTED' and g['v4_09_binding']==bind(HEAD) and
            g['v4_08_binding']==m['amended_v4_08_head'] and g['v4_10_entry']==ENTRY,
        audits_preserved=h['open_audits']==read(m['amended_v4_08_head']['path'])['open_audits'],
        parent_exact=exact(h['global_head_parent_archive']) and h['global_head_parent_archive']['sha256']==h['global_head_parent']['sha256'],
        promotion_idempotent=receipt['accepted_head']==bind(HEAD) and receipt['global_head_after']==effective_global)
    return dict(contract_id='V4_09_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1', status='PASS' if all(checks.values()) else 'FAIL', checks=checks,
                accepted_head=bind(HEAD), global_head=bind(GLOBAL), protected_head_bindings=h['protected_head_bindings'])

def expected_evidence():
    m=read(MANIFEST)
    evidence=dict(m['contracts']); evidence.update(m['evidence_bindings'])
    evidence.update({b['path']:b for b in m['source_implementation_bindings']})
    evidence.update(candidate_manifest=bind(MANIFEST), external_acceptance_document=bind(AUDIT),
                    amended_v4_08_head=m['amended_v4_08_head'])
    return evidence

def validate():
    return validate_head(read(HEAD), read(GLOBAL), read(RECEIPT))

def promote():
    if (ROOT/HEAD).exists():
        result=validate()
        if result['status']!='PASS': raise ValueError(result)
        return result
    checks=source_checks()
    if not all(checks.values()): raise ValueError(checks)
    m=read(MANIFEST); g=read(GLOBAL)
    if bind(GLOBAL)!=m['global_stage_head'] or g['accepted_stage_range']!='V4_00_TO_V4_08_ACCEPTED':
        raise ValueError('EXACT_PROMOTION_PARENT_REQUIRED')
    archive='reports/v4_joint/V4_09_PROMOTION_PARENT_STAGE_HEAD.json'
    atomic_bytes(ROOT/archive,(ROOT/GLOBAL).read_bytes())
    h=dict(contract_id='V4_09_ACCEPTED_HEAD_V1', stage='V4-09', accepted_at='2026-10-01',
        status='ENGINEERING_PASS_CAPABILITY_SCOPED', external_acceptance='EXTERNALLY_ACCEPTED', external_acceptance_decision=DECISION,
        audited_head=AUDITED, implementation_commit=IMPLEMENTATION, upstream_binding=m['amended_v4_08_head'],
        artifact=m['artifact'], evidence_bindings=expected_evidence(), capabilities=CAPABILITIES,
        protected_head_bindings=m['protected_head_bindings'], open_audits=read(m['amended_v4_08_head']['path'])['open_audits'],
        global_head_parent=bind(GLOBAL), global_head_parent_archive=bind(archive), next_stage=ENTRY,
        **{k:False for k in PERMISSIONS})
    atomic_json(ROOT/HEAD,h)
    g.update(accepted_stage_range='V4_00_TO_V4_09_ACCEPTED', v4_09_binding=bind(HEAD), v4_09_external_acceptance=DECISION,
             v4_09_status=h['status'], v4_09_capabilities=CAPABILITIES, v4_10_entry=ENTRY, **{k:False for k in PERMISSIONS})
    atomic_json(ROOT/GLOBAL,g)
    atomic_json(ROOT/RECEIPT,dict(status='PASS',accepted_head=bind(HEAD),global_head_after=bind(GLOBAL),
        global_head_parent=h['global_head_parent'], external_acceptance_decision=DECISION, protected_head_bindings=h['protected_head_bindings']))
    result=validate(); atomic_json(ROOT/VALIDATION,result)
    if result['status']!='PASS': raise ValueError(result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--promote',action='store_true');a=p.parse_args()
    result=promote() if a.promote else validate(); print(json.dumps(result));sys.exit(result['status']!='PASS')
