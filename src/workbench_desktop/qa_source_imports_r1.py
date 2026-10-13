"""Offline frozen source-dispatch import gate; no network or accepted workspace."""
from pathlib import Path
import sys
from .storage import verify_resources

def run(root):
    if not getattr(sys,'frozen',False):raise ValueError('ACTUAL_FROZEN_EXECUTABLE_REQUIRED')
    manifest=verify_resources()
    from scripts import capture_dm01_a01_r3_tdx_package
    from scripts import accept_dynamic_daily_baostock_v2
    from scripts import enter_source_authority_remediation_r2
    import v4_01_security_entity_map_r5
    modules=[capture_dm01_a01_r3_tdx_package,accept_dynamic_daily_baostock_v2,
             enter_source_authority_remediation_r2,v4_01_security_entity_map_r5]
    records=[]
    for module in modules:
        loader=module.__spec__.loader
        if not type(loader).__name__.startswith('PyiFrozen'):raise ValueError('SOURCE_LOADER_FALLBACK_FORBIDDEN')
        records.append(dict(module=module.__name__,loader=type(loader).__name__,original=module.__file__))
    return dict(status='PASS',contract_id='V4_FROZEN_DAILY_LATE_IMPORT_GATE_R1',
                modules=records,source_sha=manifest['source_sha'],network=False,production_written=False)
