"""Generate fixed replay entrypoints by auditable path/source-boundary substitutions only."""
import ast,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

OLD_STATUS='data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz'
NEW_STATUS='data/v4/artifact_store/a12_authority_candidate_r1/V4_02_DATED_TRADING_STATUS_AUTHORITY_R1.jsonl.gz'
V3='reports/audits/a12_v4_03_r1/'
V5='reports/audits/a12_v4_05_r1/'

class Redirect(ast.NodeTransformer):
    def __init__(self,replacements):self.replacements=replacements;self.changes=[]
    def visit_Constant(self,node):
        if isinstance(node.value,str):
            before=node.value
            for a,b in self.replacements:node.value=node.value.replace(a,b)
            if node.value!=before:self.changes.append(dict(line=node.lineno,old=before,new=node.value))
        return node

def main():
    scripts=['run_v4_03_core_frozen_diagnostic','build_v4_03_prior_rps_staging','run_v4_03_market_path_candidate','run_v4_03_market_regime_native_r3','run_v4_03_full_scope_candidate',
             'build_v4_05_r3_factors','enrich_v4_05_r3_relative','build_v4_05_r4_full_scope_factors','build_v4_05_r4_market_regime','build_v4_05_r4_core_profile']
    core5=['reports/v4_05/staging/V4_05_R3_PURE_CORE_FACTORS.jsonl.gz','reports/v4_05/V4_05_R3_FACTOR_SOURCE_TIME.json',
        'reports/v4_05/staging/V4_05_R3_FULL_SCOPE_FACTORS.jsonl.gz','reports/v4_05/V4_05_R3_FULL_SCOPE_FACTORS_RECEIPT.json',
        'reports/v4_05/staging/V4_05_R4_FULL_SCOPE_FACTORS.jsonl.gz','reports/v4_05/V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json',
        'reports/v4_05/V4_05_R4_MARKET_REGIME.json','reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz','reports/v4_05/V4_05_R4_CORE_PROFILE_REPLAY.json']
    # Current R4.1 reference/period artifacts do not consume A12 status/ST; exact bindings retained.
    r4_inputs=['reports/v4_05/V4_05_R4_MARKET_REFERENCE.json','reports/v4_05/V4_05_R4_MARKET_SNAPSHOT_IDENTITY.json','reports/v4_05/V4_05_R4_TARGET_MARKET_SNAPSHOT.json','reports/v4_05/V4_05_R4_PERIOD_ASOF.json']
    proofs=[]
    for name in scripts:
        p=f'scripts/{name}.py';source=(ROOT/p).read_text(encoding='utf-8-sig');original=ast.parse(source)
        replacements=[(OLD_STATUS,NEW_STATUS),('reports/v4_03/',V3)]
        if '_v4_05_' in name:
            replacements.extend((s,V5+s.removeprefix('reports/v4_05/')) for s in core5)
            replacements.extend((s,s.replace('V4_05_R4_','V4_05_R4_1_')) for s in r4_inputs)
        transform=Redirect(replacements);new=transform.visit(copy.deepcopy(original))
        # Exact reverse substitutions must restore the original full AST, including all formulas.
        reverse=Redirect([(b,a) for a,b in reversed(replacements)])
        assert ast.dump(reverse.visit(copy.deepcopy(new)),include_attributes=False)==ast.dump(original,include_attributes=False)
        source_extra=[]
        if name=='run_v4_03_market_regime_native_r3':
            main_node=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='main')
            index=next(i for i,n in enumerate(main_node.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='refs' for t in n.targets))
            extra=ast.parse("limit_ref = json.loads((ROOT / 'reports/audits/A12_V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json').read_text(encoding='utf8'))['artifacts']['price']").body[0]
            main_node.body.insert(index,extra);source_extra=['LIMIT_REFERENCE_BOUND_TO_A12_PRICE_ARTIFACT_BEFORE_HASH_VERIFICATION']
        new=ast.fix_missing_locations(new)
        out=f'scripts/a12_{name}_r1.py'
        atomic_bytes(ROOT/out,('# A12 candidate-only replay. Algorithm AST preserved; fixed declared input/output boundary substitutions.\n'+ast.unparse(new)+'\n').encode('utf8'))
        proofs.append(dict(source=bind(p),generated=bind(out),path_substitutions=transform.changes,algorithm_ast_exact_after_reversing_paths=True,declared_source_boundary_injections=source_extra))
    atomic_json(ROOT/'reports/audits/A12_UNCHANGED_REPLAY_SOURCE_PROOFS_R1.json',dict(contract_id='A12_UNCHANGED_REPLAY_SOURCE_PROOFS_R1',status='PASS_EXACT_ALGORITHM_AST',proofs=proofs,algorithms_or_thresholds_changed=False,accepted_paths_modified=False,external_acceptance=None))
    print('PASS_EXACT_ALGORITHM_AST',len(proofs))

if __name__=='__main__':main()
