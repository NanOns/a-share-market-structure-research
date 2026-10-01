"""Numerical family publication and independent acceptance evidence, candidate only."""
from scripts.next_round_execution_r3 import *
from scripts.build_v4_11_target_facts_r3a import compressed
from src.v4.confirmation import digest
from workbench_analysis.today_research_scanner_v3_3 import tri_and
import gzip
from collections import Counter

def main():
    seal=read('reports/v4_11_r3a/R3A_SEALED_PRODUCER_SET_R2.json');ref=seal['calculations']['2026-09-30'];calcs=read_gzip(ref);rows=[]
    fields=['ma5','ma20','slope20','phc20','phh20','ret1_adj','ret5_adj','ret20_adj','amr20_mean_prior','liq20_amount']
    for r in calcs:
        values={f:r['values'][f] for f in fields};v=r['values'];margin=v['break_margin_close20'];count=v['prior5_below_ma20_count']
        values.update(close_above_phc20=None if margin is None else margin>0,
            r5=tri_and([v['recovery_v3'],v['reclaim_ma5']]),r20=tri_and([v['reclaim_ma20'],None if count is None else count>=2,v['ma20_nondeclining_3']]))
        rows.append(dict(security_id=r['security_id'],trade_date=r['trade_date'],fields={f:dict(value=x,quality='UNKNOWN' if x is None else 'KNOWN',
            reason='SOURCE_WINDOW_OR_DENOMINATOR_UNKNOWN' if x is None else None,unit='boolean' if f in ('close_above_phc20','r5','r20') else 'CNY' if f in ('ma5','ma20','phc20','phh20','liq20_amount') else 'fraction') for f,x in values.items()}))
    material=dict(contract_id='V4_11_R3A_NUMERICAL_FAMILY_PUBLICATION_V1',source_calculations=ref,source_seal=bind('reports/v4_11_r3a/R3A_SEALED_PRODUCER_SET_R2.json'),
        rows=rows,accepted=False,AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',permissions=PERMISSIONS,
        exact_source=bind('src/workbench_analysis/today_research_factors_v3_3.py'),exact_branch_AST=read('config/v4_11_legacy_extraction_manifest_r2.json')['branch_AST'])
    material['publication_id']='V4_11_R3A_NUMERIC:'+digest(material);pub=compressed('data/v4/confirmation_candidates_r3/NUMERICAL_FAMILIES_20260930_R3A.json.gz',material)
    oracle=read('reports/v4_11_r3a/INDEPENDENT_ORACLE.json')
    if oracle['status']!='PASS':raise ValueError('INDEPENDENT_REAL_SOURCE_ORACLE_REQUIRED')
    result=dict(status='V4_11_R3A_TARGET_FACT_PRODUCERS_CANDIDATE_READY',active_seal=bind('reports/v4_11_r3a/R3A_SEALED_PRODUCER_SET_R2.json'),numerical_family_publication=pub,
        numerical_family_counts={f:dict(known=sum(r['fields'][f]['value'] is not None for r in rows),unknown=sum(r['fields'][f]['value'] is None for r in rows)) for f in rows[0]['fields']},
        independent_oracle=bind('reports/v4_11_r3a/INDEPENDENT_ORACLE.json'),first_trial_superseded=bind('reports/v4_11_r3a/INDEPENDENT_ORACLE_R1_DECIMAL_COORDINATE_FAILURE.json'),
        acceptance='CANDIDATE_ONLY_NOT_EXTERNAL_ACCEPTANCE',permissions=PERMISSIONS,next_stage='R3C_AFTER_R3B_SEAL')
    write('reports/v4_11_r3a/R3A_STAGE_CLOSURE.json',result);verify_protected();print('R3A_CANDIDATE_READY')
def read_gzip(ref):return __import__('json').loads(gzip.decompress(exact(ref).read_bytes()))
if __name__=='__main__':main()
