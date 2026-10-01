"""Reuse R1 candidate replay machinery with reversible AST string I/O substitutions."""
import ast,copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.compile_a12_bound_replays_r1 import Redirect
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    sources=sorted((ROOT/'scripts').glob('a12_*_r1.py'))
    # Exclude unrelated helpers: the original compiler generated exactly ten entrypoints.
    names=['run_v4_03_core_frozen_diagnostic','build_v4_03_prior_rps_staging','run_v4_03_market_path_candidate','run_v4_03_market_regime_native_r3','run_v4_03_full_scope_candidate','build_v4_05_r3_factors','enrich_v4_05_r3_relative','build_v4_05_r4_full_scope_factors','build_v4_05_r4_market_regime','build_v4_05_r4_core_profile']
    sources=[ROOT/f'scripts/a12_{n}_r1.py' for n in names]+[ROOT/'scripts/replay_a12_v4_04_r1.py',ROOT/'scripts/complete_a12_cascade_r1.py']
    replacements=[('data/v4/artifact_store/a12_authority_candidate_r1/','data/v4/artifact_store/a12_authority_candidate_r2/'),('reports/audits/a12_v4_03_r1/','reports/audits/a12_v4_03_r2/'),('reports/audits/a12_v4_05_r1/','reports/audits/a12_v4_05_r2/'),('reports/audits/a12_candidate_r1/','reports/audits/a12_candidate_r2/'),('reports/audits/A12_','reports/audits/A12_R2_'),('_AUTHORITY_AVAILABLE_R1','_AUTHORITY_AVAILABLE_R2'),('_AUTHORITY_R1','_AUTHORITY_R2')]
    proofs=[];generated=[]
    for p in sources:
        original=ast.parse(p.read_text(encoding='utf-8-sig'));t=Redirect(replacements);new=t.visit(copy.deepcopy(original));rev=Redirect([(b,a) for a,b in reversed(replacements)])
        assert ast.dump(rev.visit(copy.deepcopy(new)),include_attributes=False)==ast.dump(original,include_attributes=False)
        if p.name.startswith('a12_'):name='a12_r2_'+p.name[4:].removesuffix('_r1.py')+'.py'
        else:name=p.name.replace('_r1.py','_r2.py')
        out='scripts/'+name;atomic_bytes(ROOT/out,('# Candidate-only R2 replay. Exact R1 AST after reversing declared I/O strings.\n'+ast.unparse(ast.fix_missing_locations(new))+'\n').encode('utf8'))
        generated.append(out);proofs.append(dict(source=bind(p.relative_to(ROOT).as_posix()),generated=bind(out),substitutions=t.changes,algorithm_ast_exact_after_reversing_paths=True,algorithm_parameters_changed=False))
    atomic_json(ROOT/'reports/audits/A12_R2_UNCHANGED_REPLAY_SOURCE_PROOFS_R1.json',dict(status='PASS_EXACT_ALGORITHM_AST',proofs=proofs,generated_execution_order=generated,r1_original_algorithm_proof=bind('reports/audits/A12_UNCHANGED_REPLAY_SOURCE_PROOFS_R1.json'),additional_boundary_injections=[],external_acceptance=None))
    print('PASS_R2_EXACT_R1_ALGORITHM_AST',len(proofs))
if __name__=='__main__':main()
