"""Audited local-native fallback only for absent official target Bars.

The official package stays immutable. A derived composite snapshot retains exact
original entry bytes, replacing only absent target entries with frozen local
native files whose entire overlapping history agrees byte for byte.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,struct,tempfile,zipfile
from .tdx_official_daily_source import sha256_file,_atomic_write,_json_bytes
from .tdx_latest_daily_source_v2 import extract_target_session_bars


def fallback(latest,extraction,trade_date,daily_rows,*,snapshot_root,tdx_root=Path('D:/new_tdx')):
    root=Path(snapshot_root);tdx_root=Path(tdx_root).resolve()
    if root.resolve().is_relative_to(tdx_root):raise ValueError('FALLBACK_OUTPUT_INSIDE_TDX')
    target=int(trade_date.replace('-',''))
    if not daily_rows or any(r['date']!=trade_date for r in daily_rows):raise ValueError('FALLBACK_DATED_BAOSTOCK_REQUIRED')
    present={r['source_security_key'] for r in extraction['target_bars']}
    missing=[r for r in daily_rows if r['tradestatus']=='1' and r['code'].upper() not in present]
    if not missing:return latest,extraction,None
    if extraction['source_sha256']!=latest['download']['sha256']:raise ValueError('FALLBACK_OFFICIAL_PROOF_MISMATCH')
    replacements={};sources=[];original=Path(latest['download']['path'])
    if sha256_file(original)!=latest['download']['sha256']:raise ValueError('FALLBACK_OFFICIAL_DIGEST_MISMATCH')
    with zipfile.ZipFile(original) as archive:
        names={n.lower().replace('\\','/'):n for n in archive.namelist()}
        for row in missing:
            code=row['code'].lower();market,number=code.split('.')
            if market not in ('sh','sz','bj') or not number.isdigit() or len(number)!=6:raise ValueError('FALLBACK_SECURITY_KEY_INVALID')
            leaf=market+number+'.day';path=(tdx_root/'vipdoc'/market/'lday'/leaf).resolve()
            if not path.is_relative_to(tdx_root) or not path.is_file():raise ValueError('FALLBACK_LOCAL_TARGET_UNAVAILABLE')
            before=path.stat();data=path.read_bytes();after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('FALLBACK_LOCAL_CHANGED_DURING_READ')
            if len(data)%32:raise ValueError('FALLBACK_NATIVE_RECORD_ALIGNMENT')
            records={};prior=0
            for offset in range(0,len(data),32):
                values=struct.unpack_from('<IIIIIfII',data,offset)
                if values[0]<=prior:raise ValueError('FALLBACK_RECORD_ORDER')
                if not 0<values[3]<=min(values[1],values[4])<=max(values[1],values[4])<=values[2] or values[5]<0:
                    raise ValueError('FALLBACK_HISTORY_NATIVE_OHLC_INVALID')
                prior=values[0];records[values[0]]=data[offset:offset+32]
            if target not in records:raise ValueError('FALLBACK_LOCAL_ACTUAL_TARGET_ABSENT')
            _,o,h,l,c,amount,volume,_=struct.unpack('<IIIIIfII',records[target])
            if any(float(row[k])!=v for k,v in zip(('open','high','low','close','volume'),(o/100,h/100,l/100,c/100,volume))):
                raise ValueError('FALLBACK_NATIVE_BAOSTOCK_OHLCV_MISMATCH')
            matches=[n for norm,n in names.items() if norm.endswith('/lday/'+leaf) and '/'+market+'/' in '/'+norm]
            if len(matches)>1:raise ValueError('FALLBACK_OFFICIAL_SECURITY_ENTRY_AMBIGUOUS')
            name=matches[0] if matches else market+'/lday/'+leaf
            if matches:
                old=archive.read(name)
                if len(old)%32:raise ValueError('FALLBACK_OFFICIAL_RECORD_ALIGNMENT')
                for offset in range(0,len(old),32):
                    record=old[offset:offset+32];date=struct.unpack_from('<I',record)[0]
                    if date<=target and date in records and records[date]!=record:
                        raise ValueError('FALLBACK_OVERLAP_REVISION_QA_REQUIRED')
            frozen=root/'local_native'/hashlib.sha256(data).hexdigest()/leaf
            if not frozen.exists():_atomic_write(frozen,data,tdx_root=tdx_root)
            elif sha256_file(frozen)!=hashlib.sha256(data).hexdigest():raise ValueError('FALLBACK_IMMUTABLE_LOCAL_DIGEST_MISMATCH')
            replacements[name]=data
            sources.append(dict(source_security_key=code.upper(),read_only_address=str(path),path=str(frozen.resolve()),
                sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),observed_at=datetime.now(timezone.utc).isoformat(),
                official_target_bar_absent=True,overlapping_history_exact=True,dated_baostock_ohlcv_exact=True))
        key=hashlib.sha256(_json_bytes(dict(official=latest['download']['sha256'],target=trade_date,
            local={s['source_security_key']:s['sha256'] for s in sources}))).hexdigest()
        final=root/'local_composites'/key/'native_composite.zip';final.parent.mkdir(parents=True,exist_ok=True)
        if not final.exists():
            fd,temp=tempfile.mkstemp(dir=final.parent,suffix='.tmp');os.close(fd)
            try:
                with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as combined:
                    for name in sorted(set(archive.namelist())|set(replacements)):
                        info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3
                        combined.writestr(info,replacements[name] if name in replacements else archive.read(name))
                with open(temp,'r+b') as stream:os.fsync(stream.fileno())
                os.replace(temp,final)
            finally:Path(temp).unlink(missing_ok=True)
    receipt=dict(contract_id='TDX_LOCAL_DATED_FALLBACK_V1',target_session=trade_date,official=latest['download'],
        official_target_evidence=extraction['artifact'],local_sources=sources,AS_RECORDED=False,PIT_ELIGIBLE=False,
        composite=dict(path=str(final.resolve()),sha256=sha256_file(final),bytes=final.stat().st_size),
        provenance='DERIVED_OFFICIAL_PLUS_READ_ONLY_LOCAL_NATIVE_SNAPSHOT; NOT_AN_OFFICIAL_DOWNLOAD')
    receipt_path=final.parent/'FALLBACK_RECEIPT.json'
    if not receipt_path.exists():_atomic_write(receipt_path,_json_bytes(receipt),tdx_root=tdx_root)
    else:receipt=json.loads(receipt_path.read_bytes())
    effective=dict(latest,download=receipt['composite'],local_fallback_receipt=dict(path=str(receipt_path.resolve()),sha256=sha256_file(receipt_path)))
    effective['observed_at']=max([datetime.fromisoformat(latest['observed_at'])]+[datetime.fromisoformat(s['observed_at']) for s in receipt['local_sources']]).isoformat()
    result=extract_target_session_bars(effective,trade_date,snapshot_root=root,tdx_root=tdx_root)
    return effective,result,effective['local_fallback_receipt']
