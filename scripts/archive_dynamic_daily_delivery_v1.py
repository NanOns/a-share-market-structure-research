"""Auditable DD delivery delta and new published-owner bytes with checked manifest."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.tdx_official_daily_source import sha256_file

def archive():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    changes=subprocess.check_output(['git','diff','--name-only','6f0cf3c5a983eab481283d0436e050d70b77fe29',head],cwd=ROOT,text=True,encoding='utf8').splitlines()
    files={ROOT/p for p in changes if (ROOT/p).is_file()}
    files.update(p for p in (ROOT/'docs/evidence/dynamic_daily_20261009').rglob('*') if p.is_file() and '.tmp' not in p.name)
    files={p for p in files if p.name not in {'DELIVERY_ARCHIVE_LOCAL.json','DELIVERY_DRIVE_FINAL_READBACK.json'}}
    operational=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    candidate=json.loads(operational.read_bytes());files.add(operational)
    omitted=[];seen=set();historical_references=[]
    def collect(value,strict=True):
        if isinstance(value,dict):
            if value.get('path') and value.get('sha256'):
                p=Path(value['path']);p=p if p.is_absolute() else ROOT/p;p=p.resolve()
                if p.is_relative_to(ROOT.resolve()) and p.is_file() and p not in seen:
                    seen.add(p)
                    actual=sha256_file(p)
                    if actual!=value['sha256']:
                        if strict:raise ValueError('ARCHIVE_INPUT_BINDING_MISMATCH:'+str(p))
                        historical_references.append(dict(path=p.relative_to(ROOT).as_posix(),observed_sha256=value['sha256'],current_sha256=actual,
                            reason='Historical evidence observation of a mutable pointer; not a current published input'))
                        return
                    # Inherited original artifacts already have their original archive.
                    if 'dynamic_daily_' in str(p) or 'source_evidence/dm01_a01_r3/tdx/' in p.as_posix() or p==operational:
                        if p.suffix.lower()=='.zip':omitted.append(dict(path=str(p),sha256=value['sha256'],bytes=p.stat().st_size,reason='Official/composite source ZIP retained as separate immutable local source; not duplicated in evidence bundle'))
                        else:
                            files.add(p)
                            if p.suffix=='.json':collect(json.loads(p.read_bytes()),strict)
            for item in value.values():collect(item,strict)
        elif isinstance(value,list):
            for item in value:collect(item,strict)
    collect(candidate)
    if candidate.get('contract_id')=='V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1':
        day=candidate['accepted_trade_date'];collect(candidate['owners'][day]);collect(candidate['source_registry'][day])
    files.add(ROOT/'reports/v4_baostock/request_ledger.json')
    for target in {'20261008','20261009',candidate['accepted_trade_date'].replace('-','')}:
        receipt_folder=ROOT/'reports/v4_baostock/runtime_acceptance'/target
        if receipt_folder.exists():files.update(p for p in receipt_folder.glob('*.json') if p.is_file())
    # Numeric audit receipts can reference a real replay without moving Head.
    for evidence in list(files):
        if evidence.suffix=='.json':
            collect(json.loads(evidence.read_bytes()),strict=False)
    payload=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha256_file(p),bytes=p.stat().st_size) for p in sorted(files)]
    manifest=dict(contract_id='DYNAMIC_DAILY_DELIVERY_ARCHIVE_V1',git_sha=head,payload=payload,
        operational_head_sha256=sha256_file(operational),accepted_trade_date=candidate['accepted_trade_date'],
        omitted_large_source_packages=omitted,external_acceptance='NOT_GRANTED',
        historical_mutable_pointer_observations=historical_references,
        scope='DD engineering code/evidence and all newly referenced daily owner/source artifacts; inherited original owners stay in prior archive')
    # Independent ZIP volumes keep connector transfers bounded. The master
    # manifest binds every volume and payload; no binary concatenation needed.
    final=Path('E:/codex_tmp/DYNAMIC_DAILY_DELIVERY_20261009.zip');temporary=final.with_suffix('.tmp.zip')
    groups=[];group=[];size=0
    for item in payload:
        if group and size+item['bytes']>128*1024*1024:
            groups.append(group);group=[];size=0
        group.append(item);size+=item['bytes']
    if group:groups.append(group)
    volumes=[]
    for number,group in enumerate(groups,1):
        volume=final.with_name(final.stem+f'.part{number:02d}.zip');tmp=volume.with_suffix('.tmp.zip')
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
            for item in group:
                z.write(ROOT/item['path'],item['path'],compress_type=zipfile.ZIP_STORED if item['path'].endswith('.gz') else zipfile.ZIP_DEFLATED)
            z.writestr('VOLUME_MANIFEST.json',json.dumps(dict(git_sha=head,payload=group),sort_keys=True,separators=(',',':')))
        with zipfile.ZipFile(tmp) as z:
            if z.testzip() is not None:raise ValueError('DELIVERY_ZIP_CRC_FAILED')
            for item in group:
                data=z.read(item['path'])
                if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('DELIVERY_PAYLOAD_DIGEST_FAILED')
        os.replace(tmp,volume)
        volumes.append(dict(path=str(volume),name=volume.name,sha256=sha256_file(volume),bytes=volume.stat().st_size,payload_count=len(group)))
    manifest['volumes']=volumes
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('DELIVERY_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')))
    os.replace(temporary,final)
    result=dict(contract_id='DYNAMIC_DAILY_DELIVERY_LOCAL_ARCHIVE_RECEIPT_V1',path=str(final),bytes=final.stat().st_size,
        sha256=sha256_file(final),git_sha=head,payload_count=len(payload),volumes=volumes,crc='PASS',every_payload_sha256='PASS',omitted_large_source_packages=omitted)
    atomic_json(ROOT,ROOT/'docs/evidence/dynamic_daily_20261009/DELIVERY_ARCHIVE_LOCAL.json',result)
    print(json.dumps(result,ensure_ascii=False));return result

if __name__=='__main__':archive()
