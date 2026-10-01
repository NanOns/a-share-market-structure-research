import ast,gzip,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from src.v4.stock_prewatch import load_accepted,build,immutable_gzip_bytes,digest

def main():
    entry=json.loads((ROOT/'reports/audits/A08_STAGE_ENTRY_R1.json').read_text(encoding='utf8'))
    previous=subprocess.check_output(['git','show',entry['baseline_commit']+':src/v4/stock_prewatch.py'],cwd=ROOT,text=True,encoding='utf8')
    old=ast.parse(previous);new=ast.parse((ROOT/'src/v4/stock_prewatch.py').read_text(encoding='utf8'))
    unchanged=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef) and n.name not in ['load_package','_validate_repair_freeze']}
    assert unchanged(old)==unchanged(new)
    head=json.loads((ROOT/'data/v4/V4_09_ACCEPTED_HEAD.json').read_text(encoding='utf8'));context,cores,factors,seeds,package=load_accepted(ROOT)
    records=build(cores,factors,seeds,context,package);payload=immutable_gzip_bytes(records)
    assert payload==(ROOT/head['artifact']['path']).read_bytes() and digest(records)==head['artifact']['logical_digest']
    assert all(bind(b['path'])['sha256']==b['sha256'] for b in entry['protected_bindings'])
    evidence=dict(status='PASS_ACCEPTED_BYTES_LOGICAL_IDENTITY_AND_UNCHANGED_RULE_AST',rows=len(records),accepted_artifact=head['artifact'],producer=bind('src/v4/stock_prewatch.py'),all_algorithm_function_asts_unchanged=True,negative_vectors=['wrong_status','wrong_identity','self_consistent_wrong_authority','missing_binding','extra_binding','wrong_file_hash','wrong_consumer','wrong_original_parent','hash_valid_wrong_amended_parent','changed_unaccepted_receipt'],tests=bind('tests/v4_a08/test_repair_freeze_authority.py'),protected_heads_unchanged=True,external_acceptance=None)
    atomic_json(ROOT/'reports/audits/A08_ACCEPTED_REPLAY_AND_AUTHORITY_EVIDENCE_R1.json',evidence)
    atomic_json(ROOT/'reports/audits/A08_ENGINEERING_GATES_R1.json',dict(status='PENDING_CLEAN_DETACHED',work_package='WP-A08-V4-09-N01',allowed_candidate_status='V4_09_N01_HARDENING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',gates=dict(identity='PASS_ENGINEERING',authority='PASS_ENGINEERING',binding_set='PASS_ENGINEERING',consumer='PASS_ENGINEERING',amended_parent='PASS_ENGINEERING',accepted_replay='PASS_ENGINEERING',clean='PENDING_CLEAN_DETACHED',external='PENDING_INDEPENDENT_EXTERNAL_AUDIT'),evidence=bind('reports/audits/A08_ACCEPTED_REPLAY_AND_AUTHORITY_EVIDENCE_R1.json'),next_stage='Independent external A08 N01 audit; accepted heads unchanged'))
    print(evidence['status'])

if __name__=='__main__':main()
