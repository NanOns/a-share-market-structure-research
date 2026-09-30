"""Exact extracted V3 raw qualification; Amount A branches stay diagnostic."""
import math
from statistics import median
from sector.native_r5 import observed
from sector.machine_ast_r3 import ast_digest,validate_ast,evaluate_ast_explain


def build_b2_inputs(native_rows,current,target,source_config):
    """Reproduce CURRENT quote facts on accepted PIT membership and Core.

    Market reference uses the unique Core universe, never flattened memberships.
    Original SETUP/RECOVERY and Amount A facts are unavailable unless supplied
    by a separately accepted exact producer; Base Seed is not an alias.
    """
    cfg=source_config['thresholds'];coverage=cfg['coverage']
    all_ret=[v for r in current.values() if (v:=observed(r,'ret1',target)) is not None]
    market_coverage=len(all_ret)/len(current) if current else None
    market_median=median(all_ret) if all_ret else None
    result={}
    for row in native_rows:
        returns=[v for m in row['member_ids'] if (v:=observed(current.get(m),'ret1',target)) is not None]
        m1=median(returns) if returns else None
        positive=[max(v,0) for v in returns]
        rel=m1-market_median if m1 is not None and market_median is not None else None
        values=dict(allowed_sector_type=row['sector_type'] in cfg['current']['allowed_sector_types'],normal_rank_eligible=True,
            total_member_count=len(row['member_ids']),quote_coverage=len(returns)/len(row['member_ids']),
            market_ok=market_coverage>=coverage['min_full_market_quote_coverage'] if market_coverage is not None else None,
            m1=m1,b1=sum(v>0 for v in returns)/len(returns) if returns else None,rel1=rel,
            positive_count=sum(v>0 for v in returns) if returns else None,
            top1_positive_share=max(positive)/sum(positive) if sum(positive)>0 else None,
            ma20_width=row['fields']['ma20_width']['value'],b_delta3=row['fields']['breadth_delta3']['value'],ma20_delta3=row['fields']['ma20_delta3']['value'],
            dq5_3=row['fields']['dq5']['value']/100 if row['fields']['dq5']['value'] is not None else None,
            q20=row['fields']['sector_rs20_pct']['value']/100 if row['fields']['sector_rs20_pct']['value'] is not None else None)
        result[row['sector_id']]={k:{'value':v,'quality':'ACCEPTED' if v is not None else 'UNKNOWN'} for k,v in values.items()}
    for typ in ('INDUSTRY','THEME'):
        rows=[r for r in native_rows if r['sector_type']==typ]
        qualified=[r for r in rows if result[r['sector_id']]['rel1']['value'] is not None]
        cross=len(qualified)/len(rows) if rows else None
        for row in rows:
            facts=result[row['sector_id']];facts['type_cross_section_coverage']={'value':cross,'quality':'ACCEPTED' if cross is not None else 'UNKNOWN'}
            value=None
            if len(qualified)>=5 and cross>=coverage['min_sector_cross_section_coverage'] and row in qualified:
                rel=facts['rel1']['value'];values=[result[r['sector_id']]['rel1']['value'] for r in qualified]
                value=(sum(v<rel for v in values)+(sum(v==rel for v in values)+1)/2)/len(values)
            facts['p1']={'value':value,'quality':'ACCEPTED' if value is not None else 'UNKNOWN'}
    return result


def evaluate_b2(values, ast, *, source_sha256, source_parameter_sha256, parameter_set_sha256):
    if source_sha256!=ast['source_sha256'] or source_parameter_sha256!=ast['source_parameter_sha256'] or parameter_set_sha256!=ast['parameter_set_sha256']:
        raise ValueError('B2_SOURCE_OR_PARAMETER_BINDING_MISMATCH')
    if ast_digest(ast['rules'])!=ast['ast_digest'] or ast_digest(ast['fields'])!=ast['field_registry_digest']:
        raise ValueError('B2_AST_OR_FIELD_DIGEST_MISMATCH')
    validate_ast(ast['rules'],ast['fields'],{})
    facts={}
    for field,spec in ast['fields'].items():
        entry=values.get(field,{})
        facts[field]={**spec,'value':entry.get('value'),'quality':entry.get('quality','UNKNOWN'),'reason_code':entry.get('reason_code')}
    count=facts.get('risk_coverage',{}).get('value')
    if count==0:
        facts['risk_coverage']['quality']='UNKNOWN';facts['extended_share']['quality']='UNKNOWN'
    setup=values.get('setup_count',{});evaluable=values.get('setup_evaluable_count',{})
    cfg=ast['setup_count_gate']['parameters']
    if setup.get('quality')=='ACCEPTED' and evaluable.get('quality')=='ACCEPTED' and setup.get('value') is not None and evaluable.get('value') is not None:
        facts['setup_count_gate'].update(value=setup['value']>=max(cfg['setup_count_min'],math.ceil(cfg['setup_count_ratio']*evaluable['value'])),quality='ACCEPTED')
    table={}
    def run(rule):
        result=evaluate_ast_explain(rule,ast['rules'],facts,{})
        table[rule]={'state':'TRUE' if result.state is True else 'FALSE' if result.state is False else 'UNKNOWN','reason_code':result.reason_code}
        return result.state
    current=run('confirmed_raw')
    # Source explicitly treats full-market coverage as a publication gate.
    if facts['market_ok'].get('value') is not True or facts['market_ok']['quality']!='ACCEPTED':
        current=None;table['confirmed_raw']={'state':'UNKNOWN','reason_code':'UNKNOWN_MARKET_COVERAGE'}
    facts['current']={**facts['current'],'value':current,'quality':'ACCEPTED' if current is not None else 'UNKNOWN'}
    weak=run('weak');facts['weak']={**facts['weak'],'value':weak,'quality':'ACCEPTED' if weak is not None else 'UNKNOWN'}
    for rule in ('BREADTH_BUILD','BASE_BUILD','RECOVERY_BUILD','warm_diagnostic'):run(rule)
    return dict(model_contract_id=ast['model_contract_id'],confirmed_raw=table['confirmed_raw']['state'],warm_raw='UNKNOWN',
        warm_reason='AUD_AMOUNT_A_06_OPEN',warm_diagnostic=table['warm_diagnostic']['state'],predicates=table,
        capabilities={'B2_NON_AMOUNT_A':'ENABLED_ENGINEERING','B2_AMOUNT_A':'DIAGNOSTIC'},ast_digest=ast['ast_digest'])
