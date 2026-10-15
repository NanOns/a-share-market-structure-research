"""Explicit SH/SZ projection; original native bytes and in-scope values retained."""
from pathlib import Path
import json
import re
from .storage import require_owned

CONTRACT='TDX_SH_SZ_NATIVE_SOURCE_VIEW_V1'


def _require_worker_admission(root):
    from .storage import require_producer
    require_producer(root)


def _require_project_admission(root):
    try:
        require_owned(root)
    except ValueError as lease_error:
        try:
            _require_worker_admission(root)
        except (ValueError, RuntimeError):
            raise lease_error


def project(root, extraction):
    _require_project_admission(root)
    from workbench_analysis.tdx_official_daily_source import sha256_file,sha256_bytes,_json_bytes,_atomic_write
    from workbench_analysis.operational_daily_storage_v1 import output_path
    binding=extraction['artifact']
    source=Path(binding['path'])
    if not source.is_absolute():source=Path(root)/source
    if sha256_file(source)!=binding['sha256']:
        raise ValueError('SOURCE_VIEW_RAW_SHA_MISMATCH')
    raw=json.loads(source.read_bytes())
    if raw.get('contract_id')!='TDX_LATEST_PACKAGE_TARGET_SESSION_V2' or raw.get('status')!='TARGET_BARS_EXTRACTED':
        raise ValueError('SOURCE_VIEW_INPUT_CONTRACT_INVALID')
    excluded=[row for row in raw['target_bars'] if re.fullmatch(r'BJ\.\d{6}',row['source_security_key'].upper())]
    if not excluded:return extraction
    kept=[row for row in raw['target_bars'] if not re.fullmatch(r'BJ\.\d{6}',row['source_security_key'].upper())]
    document=dict(raw,contract_id=CONTRACT,original_contract_id=raw['contract_id'],
        original_target_artifact=binding,target_bars=kept,row_count=len(kept),
        source_scope='SH_SZ_SUPPORTED_V4_BOARDS; OTHER_UNKNOWN_KEYS_RETAINED_FOR_FAIL_CLOSED_GATE',
        excluded_source_security_keys=sorted(row['source_security_key'] for row in excluded),
        excluded_reason='BJ_OUTSIDE_CURRENT_BAOSTOCK_AND_V4_SUPPORTED_BOARD_SCOPE',
        original_source_available_at=raw['source_available_at'],AS_RECORDED=False,PIT_ELIGIBLE=False)
    data=_json_bytes(document);digest=sha256_bytes(data)
    path=output_path(root,Path(root)/'data/v4/dynamic_daily_sources/sh_sz_native_views'/raw['target_session']/(digest+'.json'))
    if path.exists():
        if path.read_bytes()!=data:raise ValueError('SOURCE_VIEW_IMMUTABLE_COLLISION')
    else:_atomic_write(path,data,tdx_root=Path('D:/new_tdx'))
    return dict(extraction,**document,artifact=dict(path=str(path.resolve()),sha256=digest,bytes=len(data)))
