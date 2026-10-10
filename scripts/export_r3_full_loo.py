"""Export the whole current operational LOO owner, without executing calculators."""
from immediate_r3_common import *
def main():
    head=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=head['accepted_trade_date'];o=head['owners'][day];profiles={r['security_id']:r for r in load(o['base_profile'])};stocks={}
    for r in load(o['core']):
        f=r['fields'];pr=profiles[r['security_id']]['states'];stocks[r['security_id']]=dict(**{k:f[k]['value'] if f[k]['quality_state']=='OBSERVED' else None for k in ('ret1','ret5','rps5','rps20','rps20_delta3')},compression_state=pr['compression_state']['value'],ma_structure_state=pr['ma_structure_state']['value'])
    sectors={r['sector_id']:sorted(set(r['member_ids'])) for r in load(o['sector'])};actual=[dict(security_id=r['security_id'],memberships=r['memberships']) for r in load(o['relative_sector'])]
    p={x['parameter_id']:x['value'] for x in load('config/v4_08_algorithm_parameter_set_r5.json')['parameters']};profilep={x['parameter_id'].removeprefix('V4_04_'):x['value'] for x in load('config/v4_04_parameter_set_v1.json')['parameters']}
    pack=dict(contract='R3_FULL_CURRENT_OPERATIONAL_LOO_V1',trade_date=day,sources=[o[k] for k in ('core','base_profile','sector','relative_sector')],stocks=stocks,sectors=sectors,actual=actual,min_members=p['V4_08_SECTOR_MIN_MEMBERS'],min_coverage=p['V4_08_SECTOR_MIN_QUOTE_COVERAGE'],parameters=profilep,scope='Actual operational owner exposes exclusion medians and relative states; does not publish LOO cross-section rank or LOO recursive episode')
    dest=OUT/'09_CONTINUATION/FULL_LOO_ORACLE_INPUT.json.gz';tmp=dest.with_suffix('.tmp')
    with gzip.open(tmp,'wt',encoding='utf8') as stream:json.dump(pack,stream,ensure_ascii=False,separators=(',',':'))
    os.replace(tmp,dest);print(json.dumps(dict(stocks=len(stocks),sectors=len(sectors),pairs=sum(len(r['memberships']) for r in actual))))
if __name__=='__main__':main()
