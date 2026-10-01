"""Stock AMR20 lineage projection; real derived facts require target acceptance."""
from scripts.v4_11_candidate_inputs_r1 import positive_values,seal,projection as original_projection
from src.v4.confirmation import package,bound

def projection(values=None,*,real=False,cutoff=None):
    p=original_projection(values,real=real,cutoff=cutoff)
    erratum=bound(package()[0]['semantic_erratum'])
    p['semantic_erratum_id']=erratum['contract_id']
    for row in p['rows']:
        fact=row['facts']['amr20_mean_prior']
        fact['producer_lineage']=dict(field_family=erratum['field_family'],formula=erratum['formula'],
            numerator_trade_date=p['trade_date'],prior_window_end='2026-09-29',prior_master_sessions=20,
            unit='dimensionless_ratio',source_digest=erratum['source']['sha256'],target_accepted_publication=None)
        if real:fact['reason']=erratum['current_target_capability']
    return seal(p)
