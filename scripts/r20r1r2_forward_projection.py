"""Native accepted DM01 -> frozen deterministic V4-15 evaluation projection."""
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
import sys,json
from scripts.r20r1r2_io import ROOT,ref,exact,require,digest,atomic
from scripts.r20r1r2_dm01_resolver import resolve_accepted_adjusted_daily_path
sys.path.insert(0,str(ROOT/'src'))
from tdx.gbbq_reader import read_gbbq
from adjustment.tdx_adjustment import build_affine_factors,xrxd_from_gbbq

CONTRACT='V4_15_ACCEPTED_FORWARD_EVALUATION_PROJECTION_V1'
FORBIDDEN={'evaluation_basis_date','verified_identity','verified_adjustment','T0_basis_verified','transform_coefficients','T0_transform_coefficients'}

@lru_cache(maxsize=8)
def events(path,sha):return tuple(read_gbbq(Path(path)))

def native_row(binding,security_id,date,root):
    payload=exact(binding,root);rows=[r for r in payload['rows'] if r['security_id']==security_id and r['trade_date']==date]
    require(len(rows)==1,'NATIVE_IDENTITY_AMBIGUITY');r=rows[0]
    require(not FORBIDDEN.intersection(r),'NATIVE_ROWS_CANNOT_PRETEND_PROJECTION')
    require(r['price_basis']=='TDX_NATIVE_AFFINE_QFQ' and r['adjustment_readiness']=='READY' and not r.get('unknown_reason'),'UNKNOWN_ADJUSTMENT_REJECTED')
    require(r['source_authority']=='TDX_OFFICIAL_PACKAGE' and r['bao_stock_ohlc_substitution_permitted'] is False and r['record_quality']=='SOURCE_FILE_VALIDATED_RECORD' and r['identity_quality']=='R6_2_DATED_ROSTER_OBSERVED','EXACT_TDX_NATIVE_IDENTITY')
    require(Decimal(r['qfq_mul'])==1 and Decimal(r['qfq_add'])==0,'NATIVE_SINGLE_TARGET_AFFINE_SEMANTICS')
    require(all(Decimal(r[k]).is_finite() and Decimal(r[k])>0 for k in ['open','high','low','close']),'NATIVE_PRICE_REQUIRED')
    return r

def project(freeze_binding,due_date,root=ROOT,data_head=None):
    root=Path(root);freeze=exact(freeze_binding,root);resolved=resolve_accepted_adjusted_daily_path(freeze['T0'],due_date,data_head,root=root)
    require(resolved['path'],'NO_MATURED_ACCEPTED_ENDPOINT')
    t0=native_row(resolved['T0_adjusted_daily'],freeze['signal_id'],freeze['T0'],root)
    require(Decimal(str(freeze['comparison_reference']))==Decimal(t0['close']),'EXACT_T0_REFERENCE_MAPPING')
    last=resolved['path'][-1];ctx=exact(last['source_context'],root);inputs=ctx['inputs'][due_date]['inputs'];gbbq=inputs['GBBQ'];exact(gbbq,root)
    disp=exact(inputs['GBBQ_DISPOSITIONS'],root);rules=exact(json.loads((root/'config/dm01_incremental_builders_contract_r3_3.json').read_bytes())['gbbq_classification_binding'],root)
    require(disp['gbbq_sha256']==gbbq['sha256'] and disp['first_eligible_formal_trade_date']<=due_date and disp['category_dispositions']=={k:v['formal_disposition'] for k,v in rules['dispositions'].items()},'ACCEPTED_ADJUSTMENT_DISPOSITION')
    dr=[r for r in disp['rows'] if r['security_id']==freeze['signal_id']]
    require(len(dr)==1 and not dr[0].get('blocking_categories'),'UNSUPPORTED_ACTION_TRANSFORM')
    all_events=[e for e in events(str((root/gbbq['path']).resolve()),gbbq['sha256']) if e.security_id.upper()==t0['source_security_key'].upper() and e.event_date<=int(due_date.replace('-',''))]
    classifications={int(k):v['formal_disposition'] for k,v in rules['dispositions'].items()}
    require(not any(classifications.get(e.category,'UNKNOWN_PRICE_IMPACT') in ['UNKNOWN_PRICE_IMPACT','PRICE_AFFECTING_UNSUPPORTED'] for e in all_events),'UNSUPPORTED_ACTION_TRANSFORM')
    factors=build_affine_factors([int(freeze['T0'].replace('-',''))]+[int(x['trade_date'].replace('-','')) for x in resolved['path']],[xrxd_from_gbbq(e) for e in all_events if e.category==1])
    coefficient=lambda day:dict(alpha=float(factors[int(day.replace('-',''))].qfq_mul),beta=float(factors[int(day.replace('-',''))].qfq_add))
    t0_coeff=coefficient(freeze['T0']);rows=[]
    for item in resolved['path']:
        r=native_row(item['artifact'],freeze['signal_id'],item['trade_date'],root);receipt=exact(item['receipt'],root)
        src=exact(item['source_context'],root)['inputs'][item['trade_date']]['inputs']
        require(all(src[k]['sha256'] in receipt['input_publication_ids'] for k in ['GBBQ','GBBQ_DISPOSITIONS','TDX_PACKAGE_DELTA']) and r['identity_source_revision'] in receipt['input_publication_ids'],'SOURCE_INPUTS_BOUND_BY_ACCEPTED_RECEIPT')
        marker=exact(item['candidate'],root);raw_receipt=marker['components']['RAW_DAILY'];raw_binding=dict(path=raw_receipt['artifact_path'],sha256=raw_receipt['artifact_sha256'],bytes=raw_receipt['artifact_bytes']);raw=exact(raw_binding,root)
        adjusted=exact(item['artifact'],root)
        require(adjusted['raw_daily_artifact_sha256']==raw_binding['sha256'] and r['raw_daily_digest']==raw_receipt['logical_digest'] and raw['contract_id']=='DM01_RAW_DAILY_ARTIFACT_R3_3' and raw['trade_date']==r['trade_date'] and digest(raw['rows'])==raw_receipt['logical_digest'],'EXACT_ACCEPTED_RAW_ADJUSTED_DEPENDENCY')
        delta=exact(src['TDX_PACKAGE_DELTA'],root)
        require(r['source_digest']==src['TDX_PACKAGE_DELTA']['sha256'] and delta['contract_id']=='TDX_PACKAGE_DELTA_V1' and delta['target_date']==r['trade_date'] and delta['future_rows_consumed']==0 and delta['current_snapshot_id']==r['source_snapshot_id'],'EXACT_TDX_SOURCE_DELTA')
        bars=[b for b in delta['target_bars'] if b['source_security_key']==r['source_security_key'] and str(b['trade_date'])==r['trade_date'].replace('-','')]
        require(len(bars)==1 and all(abs(Decimal(str(bars[0][k]))-Decimal(r[k]))<Decimal('1e-10') for k in ['open','high','low','close']),'EXACT_NATIVE_SOURCE_BAR')
        require(r['source_security_key']==t0['source_security_key'] and r['adjustment_source_revision']==src['GBBQ']['sha256'] and r['identity_source_revision']==receipt['identity_publication_id'],'EXACT_NATIVE_SOURCE_REVISIONS')
        rows.append(dict(source_data_head=item['source_data_head'],source_adjusted_daily_artifact=item['artifact'],source_component_receipt=item['receipt'],source_row_identity=dict(security_id=r['security_id'],source_security_key=r['source_security_key'],trade_date=r['trade_date']),source_row_digest=digest(r),security_id=r['security_id'],trade_date=r['trade_date'],evaluation_basis_date=due_date,verified_identity=True,verified_adjustment=True,T0_basis_verified=True,transform_coefficients=coefficient(r['trade_date']),T0_transform_coefficients=t0_coeff,source_authority=r['source_authority'],status='ACTUAL',**{k:r[k] for k in ['open','high','low','close']}))
    return dict(contract_id=CONTRACT,contract=ref('config/v4_15_forward_projection_r20r1r2_v1.json',root),freeze=freeze_binding,resolution=resolved,evaluation_basis_date=due_date,accepted_adjustment_source=gbbq,accepted_adjustment_disposition=inputs['GBBQ_DISPOSITIONS'],T0_source_row_digest=digest(t0),T0_transform_coefficients=t0_coeff,T0_OBSERVATION_SCOPE='RECONSTRUCTED_ASOF',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',raw_provider_fallback=False,rows=rows)

def persist(freeze_binding,due_date,root=ROOT):
    root=Path(root);binding=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json',root)
    snapshot=atomic('reports/r20r1r2/accepted_data_snapshots/'+binding['sha256']+'.json',(root/binding['path']).read_bytes(),root,raw=True,immutable=True)
    value=project(freeze_binding,due_date,root,snapshot)
    return atomic('reports/r20r1r2/projections/'+digest(value)+'.json',value,root,immutable=True)
