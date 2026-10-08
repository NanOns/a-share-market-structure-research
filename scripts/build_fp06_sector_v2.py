"""Versioned current-width adapter over the unchanged accepted native kernel."""
import json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts import build_fp06_sector as base
from scripts.fp01_evidence import ref
from sector.native_r5 import build_native

CONTRACT='R2_CURRENT_SECTOR_MA20_WIDTH_ADAPTER_V3'

def width_facts(current,target,expected_price_basis_id):
    output={}
    for sid,row in current.items():
        fields=dict(row.get('fields',{}));dependencies=[fields.get(k,{}) for k in ('close','ma20')]
        basis_matches=bool(expected_price_basis_id) and row.get('price_basis_id')==expected_price_basis_id
        known=row.get('trade_date')==target and basis_matches
        known=known and all(c.get('quality')=='ACCEPTED' and c.get('max_source_date')==target and
            isinstance(c.get('value'),(int,float)) and not isinstance(c.get('value'),bool) and math.isfinite(c['value']) for c in dependencies)
        fields['close_minus_ma20']=dict(value=dependencies[0]['value']-dependencies[1]['value'] if known else None,
            quality='ACCEPTED' if known else 'UNKNOWN',max_source_date=target,
            contract_id=CONTRACT,reason=None if known else ('PRICE_BASIS_ID_MISMATCH' if row.get('trade_date')==target and not basis_matches else 'ACCEPTED_SAME_DATE_SAME_BASIS_CLOSE_AND_MA20_REQUIRED'),
            dependencies=['close','ma20'],price_basis_id=row.get('price_basis_id'))
        output[sid]=dict(row,fields=fields)
    return output

def native(memberships,current,**kwargs):
    market_ref=kwargs['source_bindings'].get('market',{})
    market=json.loads((ROOT/market_ref['path']).read_bytes()) if market_ref.get('path') else {}
    expected=market.get('sources',{}).get('gbbq',{}).get('sha256')
    return build_native(memberships,width_facts(current,kwargs['target'],expected),**kwargs)

def main():
    original=base.ref
    def versioned_ref(path):
        if str(path)=='scripts/build_fp06_sector.py':return ref('scripts/build_fp06_sector_v2.py')
        return original(path)
    base.ref=versioned_ref;base.build_native=native
    base.main()

if __name__=='__main__':main()
