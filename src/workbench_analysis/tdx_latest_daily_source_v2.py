"""Latest official package and actual historical bars, without changing V1."""
from datetime import date, datetime, timezone
from pathlib import Path
import json, os, struct, tempfile, zipfile, urllib.request, subprocess, sys
from . import tdx_official_daily_source as old
from .market_source_acquisition import is_stock_code

CONTRACT = 'TDX_LATEST_PACKAGE_TARGET_SESSION_V2'


def persist_package_metadata_pg(project_root, package, *, trade_date, source_role='CURRENT'):
    """Register one independently identified official ZIP source revision in PG."""
    date.fromisoformat(trade_date)
    source=package.get('download')
    if not isinstance(source,dict) or not isinstance(source.get('sha256'),str):
        raise ValueError('TDX_PACKAGE_PG_SOURCE_BINDING_REQUIRED')
    if package.get('provider_package_date') is None or package.get('zip_validation',{}).get('status')!='PASS':
        raise ValueError('TDX_PACKAGE_PG_VALIDATED_METADATA_REQUIRED')
    if source_role not in {'CURRENT','PARENT'}:
        raise ValueError('TDX_PACKAGE_PG_ROLE_INVALID')
    transport=package.get('source_transport_v2')
    available=(transport.get('received_at') if isinstance(transport,dict) else package.get('downloaded_at'))
    record={
        'contract_id':'V4_TDX_OFFICIAL_PACKAGE_SOURCE_PG_R1',
        'contract_version':'1.0.0',
        'candidate_status':'DIAGNOSTIC_ONLY',
        'source_identity':{
            'source_id':f'TDX_OFFICIAL_{source_role}_PACKAGE_R1',
            'source_role':f'OFFICIAL_{source_role}_PACKAGE',
            'provider':'TDX_OFFICIAL_DAILY_PACKAGE',
            'T0':trade_date,
            'provider_package_date':package.get('provider_package_date'),
            'source_revision_number':package.get('source_revision_number'),
            'package_sha256':source['sha256'],
            'package_bytes':source.get('bytes'),
            'first_available_at':available,
            'parser_contract':CONTRACT,
            'zip_validation':package['zip_validation'],
            'transport_validator':package.get('remote_package_validator'),
            'AS_RECORDED':False,
            'PIT_ELIGIBLE':False,
        },
        'publication_id':None,
        'accepted_head':False,
        'AS_RECORDED':False,
        'PIT_ELIGIBLE':False,
    }
    key=old.sha256_bytes(old._json_bytes(record))
    root=Path(project_root).resolve()
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    store=ForwardFactStore(root,'data/v4/historical_source_ingress_pg_r1')
    binding=store.append('tdx_source_package_candidate',key,record,migration_timeout_seconds=120)
    if store.read(binding)!=record:
        raise ValueError('TDX_PACKAGE_PG_READBACK_MISMATCH')
    return dict(binding=binding,readback='PASS',source_id=record['source_identity']['source_id'],
                T0=trade_date,package_sha256=source['sha256'],candidate_status='DIAGNOSTIC_ONLY')


def read_package_metadata_pg(project_root, package):
    receipt=package.get('pg_source_candidate')
    if not isinstance(receipt,dict) or receipt.get('readback')!='PASS':
        raise ValueError('TDX_PACKAGE_PG_CANDIDATE_BINDING_REQUIRED')
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    record=ForwardFactStore(Path(project_root),'data/v4/historical_source_ingress_pg_r1').read(receipt['binding'])
    identity=record.get('source_identity',{})
    source=package.get('download',{})
    if (record.get('contract_id')!='V4_TDX_OFFICIAL_PACKAGE_SOURCE_PG_R1'
            or identity.get('T0')!=receipt.get('T0')
            or identity.get('package_sha256')!=source.get('sha256')
            or identity.get('source_id')!=receipt.get('source_id')
            or record.get('accepted_head') is not False
            or record.get('PIT_ELIGIBLE') is not False):
        raise ValueError('TDX_PACKAGE_PG_BINDING_IDENTITY_MISMATCH')
    return record


def persist_target_candidate_pg(project_root, package, bars):
    """Append the validated target-session barset as a diagnostic PG fact.

    The read-only TDX ZIP remains a source artifact. Downstream daily work
    consumes the exact extracted rows from this immutable PG fact, bound to
    the official package revision and its provider/observation clocks.
    """
    if bars.get('status') != 'TARGET_BARS_EXTRACTED' or not bars.get('target_bars'):
        raise ValueError('TDX_TARGET_PG_CANDIDATE_REQUIRES_EXTRACTED_ROWS')
    day=bars.get('target_session')
    date.fromisoformat(day)
    source=package.get('download')
    if not isinstance(source,dict) or not isinstance(source.get('sha256'),str):
        raise ValueError('TDX_TARGET_PG_PACKAGE_BINDING_REQUIRED')
    if bars.get('source_sha256')!=source['sha256']:
        raise ValueError('TDX_TARGET_PG_PACKAGE_DIGEST_MISMATCH')
    rows=bars['target_bars']
    identities=[row.get('source_security_key') for row in rows]
    if any(not isinstance(key,str) or not key for key in identities) or len(identities)!=len(set(identities)):
        raise ValueError('TDX_TARGET_PG_SECURITY_IDENTITY_INVALID')
    record={
        'contract_id':'V4_TDX_TARGET_BARSET_CANDIDATE_PG_R1',
        'contract_version':'1.0.0',
        'candidate_status':'DIAGNOSTIC_ONLY',
        'source_identity':{
            'source_id':'TDX_OFFICIAL_DAILY_CURRENT_PACKAGE_R1',
            'provider':'TDX_OFFICIAL_DAILY_PACKAGE',
            'T0':day,
            'provider_package_date':package.get('provider_package_date'),
            'source_revision_number':package.get('source_revision_number'),
            'package_sha256':source['sha256'],
            'package_bytes':source.get('bytes'),
            'first_available_at':bars.get('source_available_at'),
            'parser_contract':CONTRACT,
            'AS_RECORDED':False,
            'PIT_ELIGIBLE':False,
        },
        'rows':rows,
        'rows_sha256':old.sha256_bytes(old._json_bytes(rows)),
        'row_count':len(rows),
        'scope':'TYPED_A_STOCK_BARS_ONLY',
        'AS_RECORDED':False,
        'PIT_ELIGIBLE':False,
        'publication_id':None,
        'accepted_head':False,
    }
    key=old.sha256_bytes(old._json_bytes(record))
    root=Path(project_root).resolve()
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    store=ForwardFactStore(root,'data/v4/historical_source_ingress_pg_r1')
    binding=store.append('tdx_target_candidate',key,record,migration_timeout_seconds=120)
    readback=store.read(binding)
    if readback!=record or readback['rows_sha256']!=old.sha256_bytes(old._json_bytes(readback['rows'])):
        raise ValueError('TDX_TARGET_PG_READBACK_MISMATCH')
    return dict(binding=binding,readback='PASS',row_count=len(rows),rows=readback['rows'],
                trade_date=day,package_sha256=source['sha256'],
                candidate_status='DIAGNOSTIC_ONLY')


def _package_validator(url,timeout):
    """The provider can replace ZIP bytes without changing publication metadata."""
    old.validate_official_url(url)
    request=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'Mozilla/5.0',
        'Referer':old.PAGE_URL,'Cache-Control':'no-cache, max-age=0','Pragma':'no-cache'})
    with urllib.request.build_opener(old._AllowlistedRedirect()).open(request,timeout=timeout) as response:
        old.validate_official_url(response.geturl())
        headers=response.headers
        length=headers.get('Content-Length','')
        if 'zip' not in headers.get('Content-Type','').lower() or not length.isdigit():
            return None
        etag=headers.get('ETag');modified=headers.get('Last-Modified')
        if not etag and not modified:return None
        return dict(bytes=int(length),etag=etag,last_modified=modified)


def _refresh_existing_downloader():
    # V1's challenge adapter can share a one-hour receipt. A provider revision
    # must refresh that receipt too, including when the new ZIP has equal size.
    root=Path(__file__).resolve().parents[2]
    downloader=root/'scripts/capture_dm01_a01_r3_tdx_package.py'
    # The legacy R3 helper is not part of every current checkout. Its absence
    # must not prevent this module's own bounded official-page/package path
    # from running; any challenge response still fails closed in the adapter.
    if not downloader.is_file():
        return
    from common.paths import resolve_ingest_temp_root
    temp=str(resolve_ingest_temp_root(root))
    Path(temp).mkdir(parents=True,exist_ok=True)
    env={**os.environ,'TMP':temp,'TEMP':temp,'TMPDIR':temp}
    result=subprocess.run([sys.executable,'-X','utf8','-B',
        str(downloader)],cwd=root,env=env,
        capture_output=True,timeout=480)
    if result.returncode:raise ValueError('TDX_REVISED_PACKAGE_FRESH_ADAPTER_FAILED')


def capture_latest_tdx_package(*, snapshot_root=None, tdx_root=None, timeout=30, force_refresh=False,
                              pg_candidate=False, target_trade_date=None, source_role='CURRENT'):
    from common.paths import resolve_tdx_snapshot_root
    project_root=Path(__file__).resolve().parents[2]
    snapshot_root=resolve_tdx_snapshot_root(project_root,snapshot_root)
    tdx_root=old._tdx_root_or_configured(tdx_root)
    # Probe current metadata first. V1 rechecks it before downloading, so a
    # provider revision race becomes WAIT rather than mislabeled bytes.
    response=old._request(old.PAGE_URL, timeout=timeout)
    try:
        page=old._read_bounded(response, old.DEFAULT_MAX_PAGE_BYTES)
        url=old.discover_download_url(page,old.validate_official_url(response.geturl()))
    finally:
        response.close()
    info=old.discover_update_info_url(page,url)
    response=old._request(info,timeout=timeout)
    try:
        info_bytes=old._read_bounded(response,old.DEFAULT_MAX_INFO_BYTES)
        provider_day,_=old.parse_update_date(info_bytes)
    finally:
        response.close()
    pointer=Path(snapshot_root)/'tdx_latest_v2.json'
    old.ensure_outside_tdx(pointer,tdx_root)
    validator=_package_validator(url,timeout)
    if pointer.is_file():
        cached=json.loads(pointer.read_bytes())
        source=cached.get('download',{})
        artifact=Path(source.get('path',''))
        if (not force_refresh and cached.get('probe_info_sha256')==old.sha256_bytes(info_bytes)
                and validator is not None and cached.get('remote_package_validator')==validator
                and validator['bytes']==source.get('bytes')
                and cached.get('resolved_download_url')==url and artifact.is_file()
                and artifact.stat().st_size==source.get('bytes')
                and old.sha256_file(artifact)==source.get('sha256')):
            cached_result=dict(cached,status='NOOP_SOURCE_ALREADY_FROZEN')
            if pg_candidate:
                cached_result['pg_source_candidate']=persist_package_metadata_pg(
                    project_root,cached_result,trade_date=target_trade_date or provider_day,source_role=source_role)
            return cached_result
    _refresh_existing_downloader()
    receipt=old.capture_tdx_official_daily_package(target_date=provider_day,
                snapshot_root=Path(snapshot_root),tdx_root=tdx_root,timeout=timeout)
    result=dict(receipt,contract_id=CONTRACT,provider_package_date=receipt['update_date'],
                mode='LATEST_PACKAGE',strict_capture_contract=receipt['contract_id'],
                probe_info_sha256=old.sha256_bytes(info_bytes),remote_package_validator=validator)
    if result.get('download'):
        after=_package_validator(url,timeout)
        if validator is not None and (after!=validator or result['download']['bytes']!=validator['bytes']):
            return dict(result,status='WAIT_TDX_PACKAGE_REVISION_RACE',download=None)
        old._atomic_write(pointer,old._json_bytes(result),tdx_root=tdx_root)
        if pg_candidate:
            result['pg_source_candidate']=persist_package_metadata_pg(
                project_root,result,trade_date=target_trade_date or provider_day,source_role=source_role)
    return result


def extract_target_session_bars(latest_package_ref, trade_date, *, snapshot_root=None,
                                tdx_root=None):
    from common.paths import resolve_tdx_snapshot_root
    project_root=Path(__file__).resolve().parents[2]
    snapshot_root=resolve_tdx_snapshot_root(project_root,snapshot_root)
    tdx_root=old._tdx_root_or_configured(tdx_root)
    date.fromisoformat(trade_date)
    if latest_package_ref.get('pg_source_candidate') is not None:
        identity=read_package_metadata_pg(project_root,latest_package_ref)['source_identity']
        if identity.get('T0')!=trade_date:
            raise ValueError('TDX_PACKAGE_PG_T0_MISMATCH')
    source=latest_package_ref['download']; package=Path(source['path'])
    if package.stat().st_size!=source['bytes'] or old.sha256_file(package)!=source['sha256']:
        raise ValueError('LATEST_PACKAGE_BINDING_MISMATCH')
    cache=Path(snapshot_root)/'tdx_target_refs'/source['sha256']/(trade_date+'.json')
    old.ensure_outside_tdx(cache,tdx_root)
    if cache.is_file():
        cached=json.loads(cache.read_bytes());binding=cached['artifact'];artifact=Path(binding['path'])
        if artifact.is_file() and old.sha256_file(artifact)==binding['sha256']:
            content=json.loads(artifact.read_bytes())
            if content['target_session']==trade_date and content['source_sha256']==source['sha256']:
                return dict(content,artifact=binding,frozen_at=cached['frozen_at'])
    old._zip_validate(package)
    target=int(trade_date.replace('-','')); bars=[]; maximum=0; coverage=set(); excluded=[]
    with zipfile.ZipFile(package) as archive:
        for name in sorted(archive.namelist()):
            if not name.lower().endswith('.day'):
                continue
            parts=name.lower().replace('\\','/').split('/')
            market=next((p for p in parts if p in {'sh','sz','bj'}),None)
            leaf=parts[-1]
            code=market+'.'+leaf[-10:-4] if market else ''
            if not is_stock_code(code):
                excluded.append(name);continue
            raw=archive.read(name)
            if len(raw)%32:
                raise ValueError('DAY_RECORD_LENGTH_INVALID')
            previous=0; hit=None
            for record in struct.iter_unpack('<IIIIIfII',raw):
                day=record[0]
                if day<=previous:
                    raise ValueError('DAY_RECORD_ORDER_INVALID')
                previous=day; maximum=max(maximum,day)
                stamp=str(day)
                date.fromisoformat(stamp[:4]+'-'+stamp[4:6]+'-'+stamp[6:])
                if day==target:
                    hit=record
            if hit:
                _,o,h,l,c,amount,volume,_=hit
                if not 0<l<=min(o,c)<=max(o,c)<=h or amount<0:
                    raise ValueError('TARGET_BAR_OHLC_INVALID')
                bars.append(dict(source_entry=name,source_security_key=code.upper(),trade_date=trade_date,
                    open=o/100,high=h/100,low=l/100,close=c/100,amount=amount,volume=volume,
                    entry_sha256=old.sha256_bytes(raw)))
                coverage.add(trade_date)
    content=dict(contract_id=CONTRACT,target_session=trade_date,
        provider_package_date=latest_package_ref['provider_package_date'],
        package_content_max_trade_date=str(maximum)[:4]+'-'+str(maximum)[4:6]+'-'+str(maximum)[6:] if maximum else None,
        bars_date_coverage=sorted(coverage),source_sha256=source['sha256'],
        reconstruction_from_later_snapshot=latest_package_ref['provider_package_date']>trade_date,
        source_available_at=latest_package_ref.get('source_transport_v2',{}).get('received_at',latest_package_ref['observed_at']),
        AS_RECORDED=False,PIT_ELIGIBLE=False,status='TARGET_BARS_EXTRACTED' if bars else 'WAIT_TDX_TARGET_BARS',
        target_bars=bars,row_count=len(bars),tdx_root_write_count=0,
        excluded_non_stock_entries=excluded,scope='TYPED_A_STOCK_BARS_ONLY')
    if latest_package_ref.get('source_transport_v2'):
        content['source_transport_v2']=latest_package_ref['source_transport_v2']
    # Stable target artifact identity; runtime timestamps belong to its receipt.
    data=old._json_bytes(content); key=old.sha256_bytes(data)
    output=Path(snapshot_root)/'tdx_targets'/trade_date/key/'bars.json'
    old.ensure_outside_tdx(output,tdx_root)
    if output.exists():
        if output.read_bytes()!=data:
            raise ValueError('IMMUTABLE_TARGET_COLLISION')
    else:
        old._atomic_write(output,data,tdx_root=tdx_root)
    binding=dict(path=str(output.resolve()),sha256=key,bytes=len(data))
    frozen_at=datetime.now(timezone.utc).isoformat()
    old._atomic_write(cache,old._json_bytes(dict(artifact=binding,frozen_at=frozen_at)),tdx_root=tdx_root)
    return dict(content,artifact=binding,
                frozen_at=frozen_at)
