"""Latest official package and actual historical bars, without changing V1."""
from datetime import date, datetime, timezone
from pathlib import Path
import json, os, struct, tempfile, zipfile, urllib.request, subprocess, sys
from . import tdx_official_daily_source as old
from .market_source_acquisition import is_stock_code

CONTRACT = 'TDX_LATEST_PACKAGE_TARGET_SESSION_V2'


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
    result=subprocess.run([sys.executable,'-X','utf8','-B',
        str(root/'scripts/capture_dm01_a01_r3_tdx_package.py')],cwd=root,
        capture_output=True,timeout=480)
    if result.returncode:raise ValueError('TDX_REVISED_PACKAGE_FRESH_ADAPTER_FAILED')


def capture_latest_tdx_package(*, snapshot_root, tdx_root=Path('D:/new_tdx'), timeout=30, force_refresh=False):
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
            return dict(cached,status='NOOP_SOURCE_ALREADY_FROZEN')
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
    return result


def extract_target_session_bars(latest_package_ref, trade_date, *, snapshot_root,
                                tdx_root=Path('D:/new_tdx')):
    date.fromisoformat(trade_date)
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
