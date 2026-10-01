"""Scenario-scoped R3 D0 candidate; frozen scanner and thresholds unchanged."""
from .confirmation import package,SCENARIO_KEYS,digest
from .target_fact_producers_r3 import validate
from .confirmation_input_closure_r3b import scenario_capability_matrix

def detect(publication,root):
    validate(publication,root)
    c,m,p,a,scanner=package();matrix=scenario_capability_matrix(r3a_sealed=True);rows=[]
    for r in publication['rows']:
        facts=r['facts'];values={f:x['value'] if x['quality']=='KNOWN' else None for f,x in facts.items()}
        values.update(security_id=r['security_id'],trade_date=r['trade_date']);legacy=scanner(values)
        matched=[];evidence=[];unknown=[];unavailable={f:x['reason'] for f,x in facts.items() if x['quality']!='KNOWN'}
        for scenario in a['scenario_priority']:
            branch=legacy[SCENARIO_KEYS[scenario]];formal=matrix[scenario]['capability']=='FORMAL_CANDIDATE'
            reasons=[k+':UNKNOWN' for k,v in branch['checks'].items() if v is None]
            if not formal:reasons.append(matrix[scenario]['reason'])
            status='UNKNOWN' if reasons else 'TRUE' if branch['eligible'] is True else 'FALSE'
            if formal and status=='TRUE':matched.append(scenario)
            if formal:unknown.extend(scenario+':'+x for x in reasons)
            evidence.append(dict(scenario=scenario,status=status,scope=matrix[scenario]['capability'],checks=branch['checks'],legacy_eligible=branch['eligible'],
                unknown_reasons=reasons,source_sha256=m['legacy_source']['sha256'],parameter_set_id=p['parameter_set_id']))
        status='TRUE' if matched else 'UNKNOWN' if unknown else 'FALSE'
        rows.append(dict(security_id=r['security_id'],trade_date=r['trade_date'],confirmation_status=status,matched_scenarios=matched,
            primary_scenario=matched[0] if matched else None,scenario_evidence=evidence,unknown_predicates=unknown,unavailable_input_facts=unavailable,
            input_publication_id=publication['publication_id'],input_digest=publication['logical_digest'],
            producer_contract_id='CONFIRMATION_DETECTOR_V1',parameter_set_id=p['parameter_set_id'],
            semantic_erratum_id='V4_11_STOCK_AMR20_SEMANTIC_ERRATUM_R2',sector_amount_A_status_affects_confirmation=False,
            knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
    result=dict(contract_id='V4_11_CONFIRMATION_FACT_CANDIDATE_R3',trade_date=publication['trade_date'],rows=rows,
        scope='REAL_DAG_CANDIDATE_ONLY',accepted=False,input_publication_id=publication['publication_id'],
        knowledge_cutoff=publication['knowledge_cutoff'],scenario_capability_matrix=matrix,permissions=publication['permissions'])
    result['publication_id']='V4_11_D0_R3:'+digest(result)
    return result
