"""Freeze a new semantic erratum without rewriting the accepted legacy source."""
import ast
from scripts.next_round_bundle_r2 import ROOT,read,write,bind,AUDIT,DOCROOT

def main():
    manifest=read('config/v4_11_legacy_extraction_manifest_r1.json')
    manifest['contract_id']='V4_11_LEGACY_EXTRACTION_MANIFEST_R2'
    manifest['input_time_roles']['amr20_mean_prior']='TARGET_SESSION_D0'
    manifest['input_window_roles']={'amr20_mean_prior':'PRIOR_20_MASTER_SESSIONS_EXCLUDING_TARGET'}
    manifest['supersedes_semantics_only']=bind('config/v4_11_legacy_extraction_manifest_r1.json')
    write('config/v4_11_legacy_extraction_manifest_r2.json',manifest)
    path='src/workbench_analysis/today_research_factors_v3_3.py'
    tree=ast.parse((ROOT/path).read_text(encoding='utf8'))
    nodes={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    erratum=dict(contract_id='V4_11_STOCK_AMR20_SEMANTIC_ERRATUM_R2',version='2.0.0',authority=bind(AUDIT),
        field='amr20_mean_prior',field_family='STOCK_AMOUNT_VOLUME_STATE_V1',unit='dimensionless_ratio',
        formula='stock_raw_amount_CNY[T] / mean(stock_raw_amount_CNY[T-20:T-1])',
        target_role='TARGET_SESSION_D0',prior_window='20 contiguous master sessions excluding target',
        source=bind(path),exact_function_AST=nodes,accepted_native_contract=bind('config/v4_03_algorithm_contracts_v1.json'),
        legacy_technical_amount_ratio20_includes_current_and_is_not_interchangeable=True,
        stock_ratio_is_not_sector_amount_a_value=True,sector_membership_is_not_an_input=True,
        sector_amount_A_status_affects_confirmation=False,sector_audit='AUD-AMOUNT-A-06',
        sector_audit_scope='SECTOR_AMOUNT_A_ONLY',target_accepted_AMR20_publication=None,
        current_target_capability='STOCK_AMR20_TARGET_ACCEPTED_PRODUCER_PUBLICATION_UNAVAILABLE',
        raw_source_acceptance_does_not_accept_derived_AMR20=True,
        retired_golden_vectors=['AMOUNT_A_DISABLED'],active_semantic_vectors=['AMR20_KNOWN_TRUE','AMR20_KNOWN_FALSE','AMR20_UNKNOWN','SECTOR_AMOUNT_A_STATUS_IRRELEVANT'],
        thresholds=dict(LAUNCH_CONFIRM_min=1.20,RECOVERY_TURN_min=1.05,TREND_CONTINUE_min=.80,TREND_CONTINUE_max=2.50))
    write('config/v4_11_stock_amr20_semantic_erratum_r2.json',erratum)
    c=read('config/v4_11_confirmation_detector_contract_r1.json');c.pop('amount_A');c.update(version='2.0.0',
        semantic_erratum=bind('config/v4_11_stock_amr20_semantic_erratum_r2.json'),legacy_manifest=bind('config/v4_11_legacy_extraction_manifest_r2.json'),
        stage_contract=bind(DOCROOT+'V4_11_R2_AMR20_AMOUNT_A_SEMANTIC_REPAIR_TASK_20261001.md'),
        external_audit_authority=bind(AUDIT),supersedes=bind('config/v4_11_confirmation_detector_contract_r1.json'),
        migration_allocation=read('config/v4_migration_allocation_registry_r3.json'),status='SEMANTIC_REPAIR_CANDIDATE')
    write('config/v4_11_confirmation_detector_contract_r2.json',c)

if __name__=='__main__':main()
