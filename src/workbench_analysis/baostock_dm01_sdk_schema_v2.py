"""Exact SDK-hash schema repair; immutable original bytes remain independently bound."""
from workbench_analysis.baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD,_validate_daily_rows,_validate_factor_rows

def normalize_response(rows,metadata,*,target,sdk,contract,method):
    if sdk['version']!=contract['sdk_version'] or sdk['installed_python_sources_sha256']!=contract['sdk_python_sources_sha256']:raise ValueError('SCHEMA_ADAPTER_SDK_HASH_MISMATCH')
    normalized=[dict(r) for r in rows];meta=dict(metadata)
    if method==FACTOR_METHOD:
        if metadata.get('fields')!=contract['factor_raw_schema']:raise ValueError('UNDECLARED_FACTOR_SCHEMA_DRIFT')
        for row in normalized:
            if set(row)!=set(contract['factor_raw_schema']):raise ValueError('FACTOR_ROW_SCHEMA_DRIFT')
            row['adjustFactor']=row.pop('adjustFacto')
        meta['fields']=[contract['factor_header_alias'].get(f,f) for f in meta['fields']]
        _validate_factor_rows(normalized,target)
        dates={r['dividOperateDate'] for r in normalized}
        basis=contract['factor_provider_date_basis']
    elif method==DAILY_METHOD:
        _validate_daily_rows(normalized,target);dates={r['date'] for r in normalized};basis=contract['daily_provider_date_basis']
    else:raise ValueError('SCHEMA_ADAPTER_METHOD_UNDECLARED')
    if dates:
        if dates!={target}:raise ValueError('TARGET_FACT_DATE_NOT_EXACT')
        meta['provider_date']=next(iter(dates));meta['provider_date_basis']=basis
    else:
        # Empty data cannot manufacture a returned target date from an SDK request echo.
        meta['provider_date']=None;meta['provider_date_basis']='EMPTY_RESPONSE_TARGET_FACT_DATE_UNPROVEN'
    return normalized,meta
