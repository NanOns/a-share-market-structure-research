"""Units from hash-bound owner registries; values and algorithms unchanged."""
from .current_v4_context import SourceInvalid

CONTRACT='R2_BOUND_OWNER_UNIT_PROJECTION_V1'

def project(field,cell,registries,price_basis):
    matches=[r for registry in registries for r in registry['fields'] if r['field_id']==field]
    if not matches:return dict(cell)
    selected=next((r for r in matches if r['parameter_set_id']==cell.get('parameter_set_id')),None)
    if selected is None:
        if cell.get('value') is None or cell.get('unknown_reason'):return dict(cell)
        raise SourceInvalid('STOCK_UNIT_PARAMETER_CONTRACT_MISMATCH:'+field)
    if not selected.get('unit'):raise SourceInvalid('STOCK_OWNER_REGISTRY_UNIT_MISSING:'+field)
    result=dict(cell,unit=selected['unit'])
    basis=selected.get('price_basis')
    if basis in ('QFQ','verified_affine_adjusted_OHLC'):result['coordinate_basis']=price_basis
    elif basis:result['coordinate_basis']=basis
    return result
