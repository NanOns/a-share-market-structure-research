from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json, os, shutil, stat, subprocess, time, uuid, zipfile

from tdx.block_reader import build_industry_memberships, read_industry_names, read_infoharbor_memberships
from tdx.security_master import read_industry_assignments, read_tnf, classify_security, current_a_stock_ids
from tdx.day_reader import validate_day_file

OFFICIAL_HOST = "data.tdx.com.cn"
OFFICIAL_PATH = "/vipdoc/hsjday.zip"
DOWNLOAD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
METADATA_RELATIVE_PATHS = (
    "T0002/hq_cache/tdxhy.cfg", "T0002/hq_cache/tdxzs.cfg",
    "T0002/hq_cache/infoharbor_block.dat", "T0002/hq_cache/gbbq",
    "T0002/hq_cache/gbbq.map", "T0002/hq_cache/shs.tnf",
    "T0002/hq_cache/szs.tnf", "T0002/hq_cache/bjs.tnf",
)

def _hash(path: Path) -> str:
    h=sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+f".{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,path)

@dataclass(frozen=True)
class DownloadPolicy:
    max_bytes: int = 4 * 1024**3
    connect_timeout_seconds: int = 15
    read_timeout_seconds: int = 120

@dataclass(frozen=True)
class ExtractionPolicy:
    max_entries: int = 20_000
    max_expanded_bytes: int = 16 * 1024**3
    max_compression_ratio: float = 200.0

def download_official_package(url: str, destination: Path, policy: DownloadPolicy=DownloadPolicy(), opener=urlopen) -> dict:
    parsed=urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST or parsed.path != OFFICIAL_PATH:
        raise ValueError("UNAPPROVED_DOWNLOAD_SOURCE")
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    part=destination.with_name(destination.name+".part")
    if part.exists(): part.unlink()
    request=Request(url,headers={"User-Agent":DOWNLOAD_USER_AGENT,"Referer":"https://www.tdx.com.cn/article/vipdata.html","Accept":"application/zip,application/octet-stream;q=0.9,*/*;q=0.1"})
    total=0; h=sha256()
    try:
        with opener(request,timeout=policy.read_timeout_seconds) as response, part.open("xb") as out:
            final=urlparse(response.geturl())
            if final.scheme!="https" or final.hostname!=OFFICIAL_HOST or response.geturl()!=url: raise ValueError("UNAPPROVED_REDIRECT")
            content_type=(response.headers.get("Content-Type") or "").lower()
            if "text/html" in content_type: raise ValueError("PACKAGE_HTML_CHALLENGE")
            declared=response.headers.get("Content-Length")
            if declared and int(declared)>policy.max_bytes: raise ValueError("PACKAGE_TOO_LARGE")
            first=True
            while True:
                chunk=response.read(1024*1024)
                if not chunk: break
                if first and not chunk.startswith(b"PK"): raise ValueError("PACKAGE_NOT_ZIP")
                first=False; total+=len(chunk)
                if total>policy.max_bytes: raise ValueError("PACKAGE_TOO_LARGE")
                h.update(chunk); out.write(chunk)
            out.flush(); os.fsync(out.fileno())
            if declared and total!=int(declared): raise ValueError("INCOMPLETE_PACKAGE")
        with zipfile.ZipFile(part) as archive: archive.testzip()
        os.replace(part,destination)
        return {"source_url":url,"resolved_url":response.geturl(),"byte_count":total,"sha256":h.hexdigest(),"etag":response.headers.get("ETag"),"last_modified":response.headers.get("Last-Modified")}
    except Exception:
        if part.exists(): part.unlink()
        raise

def download_official_package_curl(url: str, destination: Path, policy: DownloadPolicy=DownloadPolicy()) -> dict:
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.hostname!=OFFICIAL_HOST or parsed.path!=OFFICIAL_PATH: raise ValueError("UNAPPROVED_DOWNLOAD_SOURCE")
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    part=destination.with_name(destination.name+".part"); headers=destination.with_name(destination.name+".headers.tmp")
    for p in (part,headers):
        if p.exists(): p.unlink()
    try:
        result=subprocess.run(["curl.exe","--fail","--location","--max-redirs","0","--retry","2","--connect-timeout",str(policy.connect_timeout_seconds),"--max-time",str(policy.read_timeout_seconds*5),"--max-filesize",str(policy.max_bytes),"--user-agent",DOWNLOAD_USER_AGENT,"--referer","https://www.tdx.com.cn/article/vipdata.html","--dump-header",str(headers),"--write-out","%{url_effective}","--output",str(part),url],capture_output=True,text=True)
        if result.returncode: raise ValueError("DOWNLOAD_TRANSPORT_FAILED:"+result.stderr[-500:])
        effective=urlparse(result.stdout.strip())
        if result.stdout.strip()!=url or effective.scheme!="https" or effective.hostname!=OFFICIAL_HOST or effective.path!=OFFICIAL_PATH:
            raise ValueError("UNAPPROVED_REDIRECT")
        size=part.stat().st_size
        if size>policy.max_bytes: raise ValueError("PACKAGE_TOO_LARGE")
        with part.open("rb") as probe: magic=probe.read(4)
        if magic not in (b"PK\x03\x04",b"PK\x05\x06",b"PK\x07\x08"): raise ValueError("PACKAGE_NOT_ZIP")
        with zipfile.ZipFile(part) as archive:
            bad=archive.testzip()
            if bad: raise ValueError("PACKAGE_MEMBER_CRC_FAILED:"+bad)
        header_text=headers.read_text(errors="replace") if headers.exists() else ""
        os.replace(part,destination)
        def value(name):
            found=[line.split(":",1)[1].strip() for line in header_text.splitlines() if line.lower().startswith(name.lower()+":")]
            return found[-1] if found else None
        return {"source_url":url,"resolved_url":result.stdout.strip(),"byte_count":size,"sha256":_hash(destination),"etag":value("etag"),"last_modified":value("last-modified"),"transport":"curl-schannel"}
    except Exception:
        if part.exists(): part.unlink()
        raise
    finally:
        if headers.exists(): headers.unlink()

def _safe_member(name: str) -> PurePosixPath:
    normalized=name.replace("\\","/")
    p=PurePosixPath(normalized)
    reserved={"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}
    unsafe_component=any(":" in part or part.rstrip(" .")!=part or part.split(".",1)[0].upper() in reserved for part in p.parts)
    if not normalized or normalized.startswith("/") or p.is_absolute() or ".." in p.parts or unsafe_component:
        raise ValueError("ZIP_PATH_ESCAPE")
    return p

def safe_extract_zip(package: Path, destination: Path, policy: ExtractionPolicy=ExtractionPolicy()) -> dict:
    package=Path(package); destination=Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage=destination.with_name(destination.name+f".{uuid.uuid4().hex}.extracting")
    stage.mkdir(parents=True,exist_ok=False); seen=set(); expanded=0; count=0
    try:
        with zipfile.ZipFile(package) as z:
            infos=z.infolist()
            if len(infos)>policy.max_entries: raise ValueError("ZIP_TOO_MANY_ENTRIES")
            for info in infos:
                rel=_safe_member(info.filename); key="/".join(rel.parts).casefold()
                if key in seen: raise ValueError("ZIP_CASE_COLLISION")
                seen.add(key); mode=info.external_attr>>16
                if stat.S_ISLNK(mode): raise ValueError("ZIP_LINK_REJECTED")
                count+=1; expanded+=info.file_size
                if expanded>policy.max_expanded_bytes: raise ValueError("ZIP_EXPANDED_LIMIT")
                ratio=info.file_size/max(1,info.compress_size)
                if ratio>policy.max_compression_ratio: raise ValueError("ZIP_COMPRESSION_RATIO")
                target=stage.joinpath(*rel.parts)
                if info.is_dir(): target.mkdir(parents=True,exist_ok=True); continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src, target.open("xb") as dst: shutil.copyfileobj(src,dst,1024*1024)
        if destination.exists(): raise ValueError("EXTRACTION_DESTINATION_EXISTS")
        os.replace(stage,destination)
        return {"entry_count":count,"expanded_bytes":expanded,"package_sha256":_hash(package)}
    except Exception:
        shutil.rmtree(stage,ignore_errors=True)
        raise

def _manifest(root: Path, relative_paths=METADATA_RELATIVE_PATHS) -> dict:
    rows={}
    for rel in relative_paths:
        p=root/rel
        if p.is_file(): rows[rel]={"size":p.stat().st_size,"sha256":_hash(p)}
    return rows

def capture_stable_metadata(source_root: Path, destination: Path, *, stable_seconds: float=1.0, relative_paths=METADATA_RELATIVE_PATHS, sleeper=time.sleep) -> dict:
    source_root=Path(source_root).resolve(); destination=Path(destination).resolve()
    if source_root==destination or source_root in destination.parents: raise ValueError("METADATA_DESTINATION_INSIDE_SOURCE")
    a=_manifest(source_root,relative_paths)
    missing=sorted(set(relative_paths)-set(a))
    if missing: raise ValueError("METADATA_REQUIRED_FILES_MISSING:"+",".join(missing))
    sleeper(stable_seconds)
    pre_copy=_manifest(source_root,relative_paths)
    if a!=pre_copy: raise ValueError("METADATA_SOURCE_CHANGING")
    stage=destination.with_name(destination.name+f".{uuid.uuid4().hex}.copying")
    try:
        for rel in a:
            target=stage/rel; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source_root/rel,target)
        b=_manifest(source_root,relative_paths); copied=_manifest(stage,relative_paths)
        if a!=b or a!=copied: raise ValueError("METADATA_SOURCE_CHANGED_DURING_COPY")
        structural=_validate_metadata_structure(stage)
        if destination.exists(): raise ValueError("METADATA_DESTINATION_EXISTS")
        os.replace(stage,destination)
        identity=sha256(json.dumps(a,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return {"metadata_snapshot_id":identity,"files":a,"stability":"PASS","structural_integrity":"PASS","structure":structural,"freshness":"UNKNOWN","root":str(destination)}
    except Exception:
        shutil.rmtree(stage,ignore_errors=True); raise

def _validate_metadata_structure(snapshot_root: Path) -> dict:
    cache=snapshot_root/"T0002/hq_cache"; tnf={}
    for market,name in (("SH","shs.tnf"),("SZ","szs.tnf"),("BJ","bjs.tnf")):
        names,audit=read_tnf(cache/name,market)
        if audit["tail_remainder"] or not names: raise ValueError("METADATA_TNF_INVALID:"+name)
        tnf[market]=audit
    assignments=read_industry_assignments(cache/"tdxhy.cfg")
    sectors=read_industry_names(cache/"tdxzs.cfg")
    members,meta=read_infoharbor_memberships(cache/"infoharbor_block.dat")
    if not assignments or not sectors or not meta["sector_headers"]: raise ValueError("METADATA_CATALOG_EMPTY")
    for name in ("gbbq","gbbq.map"):
        if (cache/name).stat().st_size==0: raise ValueError("METADATA_FILE_EMPTY:"+name)
    return {"tnf":tnf,"industry_assignments":len(assignments),"industry_names":len(sectors),"extra_memberships":len(members)}

def validate_extracted_day_data(root: Path, target_trade_date: int | None=None, current_security_ids: set[str] | None=None) -> dict:
    root=Path(root); files=sorted(root.rglob("*.day"))
    if not files: raise ValueError("DAY_FILES_MISSING")
    rows=[]; latest_counts={}; records=0
    for path in files:
        stem=path.stem.lower(); market=stem[:2]
        if market not in ("sh","sz","bj"): continue
        item=validate_day_file(path,market); rows.append(item); records+=item["record_count"]
        latest_counts[(market,item.get("last_date"))]=latest_counts.get((market,item.get("last_date")),0)+1
    if target_trade_date is None:
        candidates={d:c for (m,d),c in latest_counts.items() if d}
        target_trade_date=max(candidates,key=lambda d:candidates[d])
    normal=[]
    for x in rows:
        kind=classify_security(x["market"],x["code"],current_security_ids or set())
        if current_security_ids is not None and x["security_id"] not in current_security_ids: continue
        if kind=="A_STOCK" and not x["valid"]: normal.append(x)
    counts={m:latest_counts.get((m,target_trade_date),0) for m in ("sh","sz","bj")}
    major={"SH.000001","SZ.399001","SZ.399006"}
    present={x["security_id"] for x in rows if x.get("last_date")==target_trade_date}
    result={"file_count":len(rows),"record_count":records,"target_trade_date":target_trade_date,"target_counts":counts,"major_indices_present":major<=present,"normal_a_share_invalid_count":len(normal),"normal_a_share_invalid_samples":[x["security_id"] for x in normal[:30]]}
    result["status"]="PASS" if all(counts.values()) and result["major_indices_present"] and not normal else "FAIL"
    return result

def analyze_dynamic_metadata(snapshot_root: Path, previous: dict | None=None, *, available_security_ids: set[str] | None=None) -> dict:
    root=Path(snapshot_root); cache=root/"T0002/hq_cache"; previous=previous or {}
    securities={}
    for market,name in (("SH","shs.tnf"),("SZ","szs.tnf"),("BJ","bjs.tnf")):
        path=cache/name
        if path.is_file(): securities.update(read_tnf(path,market)[0])
    assignments=read_industry_assignments(cache/"tdxhy.cfg")
    industry=build_industry_memberships(assignments,read_industry_names(cache/"tdxzs.cfg"))
    extra,meta=read_infoharbor_memberships(cache/"infoharbor_block.dat")
    memberships=industry+[x for x in extra if x["sector_type"] in ("concept","style")]
    sectors={f'{x["sector_type"]}:{x["sector_code"]}':x["sector_name"] for x in memberships}
    refs={x["security_id"] for x in memberships}; missing=sorted(refs-set(securities))
    blocking=missing if available_security_ids is None else sorted(set(missing)&available_security_ids)
    if blocking: raise ValueError("MEMBERSHIP_SECURITY_REFERENCE_MISSING:"+",".join(blocking[:10]))
    prior_sec=set(previous.get("securities",{})); prior_sectors=set(previous.get("sectors",{})); prior_members={tuple(x) for x in previous.get("memberships",[])}
    current_members=sorted((x["sector_type"],str(x["sector_code"]),x["security_id"]) for x in memberships)
    current_set=set(current_members)
    return {
        "securities":dict(sorted(securities.items())),"sectors":dict(sorted(sectors.items())),"memberships":current_members,
        "changes":{"new_securities":sorted(set(securities)-prior_sec),"new_sectors":sorted(set(sectors)-prior_sectors),"member_joins":[list(x) for x in sorted(current_set-prior_members)],"member_exits":[list(x) for x in sorted(prior_members-current_set)]},
        "header_counts":meta["headers_by_prefix"],"reference_integrity":"PASS","source_absent_references":missing,
    }

def seal_source_bundle(bundle_dir: Path, *, target_trade_date: str, package: dict, extraction: dict, metadata: dict, calendar_sha256: str, validation: dict | None=None, parser_version: str="m3-tdx-input-v1.0") -> dict:
    body={"contract":"source-bundle-v1.0","target_trade_date":target_trade_date,"package":package,"extraction":extraction,"metadata":metadata,"validation":validation or {},"calendar_sha256":calendar_sha256,"parser_version":parser_version,"read_only":True}
    identity=sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    body["source_bundle_id"]=identity
    path=Path(bundle_dir)/identity/"source_bundle.json"
    # A sealed identity is immutable.  Re-validating the same inputs must not
    # try to overwrite its read-only receipt.
    if path.is_file():
        existing=json.loads(path.read_text(encoding="utf-8"))
        if existing != body: raise ValueError("SOURCE_BUNDLE_IDENTITY_COLLISION")
        return existing
    _atomic_json(path,body)
    try: path.chmod(stat.S_IREAD)
    except OSError: pass
    return body

def verify_source_bundle(bundle_path: Path) -> dict:
    path=Path(bundle_path); body=json.loads(path.read_text(encoding="utf-8")); claimed=body.pop("source_bundle_id",None)
    actual=sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    body["source_bundle_id"]=claimed
    if claimed!=actual: raise ValueError("SOURCE_BUNDLE_IDENTITY_MISMATCH")
    project_root=path.parents[3].resolve()
    def safe_project_path(raw: str | Path) -> Path:
        value=Path(raw)
        raw_candidate=value if value.is_absolute() else project_root/value
        for item in (raw_candidate, *raw_candidate.parents):
            if item.is_symlink(): raise ValueError("SOURCE_PATH_SYMLINK_FORBIDDEN")
            if item == project_root: break
        candidate=raw_candidate.resolve()
        if candidate!=project_root and project_root not in candidate.parents:
            raise ValueError("SOURCE_PATH_OUTSIDE_PROJECT")
        return candidate
    package_path=safe_project_path(Path("data/input_staging/packages")/str(body["target_trade_date"]).replace("-","")/"hsjday.zip")
    if not package_path.is_file() or _hash(package_path)!=body["package"]["sha256"]: raise ValueError("SOURCE_PACKAGE_MISMATCH")
    metadata_root=safe_project_path(body["metadata"]["root"])
    copied=_manifest(metadata_root)
    if copied!=body["metadata"]["files"]: raise ValueError("METADATA_SNAPSHOT_MISMATCH")
    _validate_metadata_structure(metadata_root)
    ids=current_a_stock_ids(read_industry_assignments(metadata_root/"T0002/hq_cache/tdxhy.cfg"))
    extraction_root=safe_project_path(body["extraction"]["root"])
    validation=validate_extracted_day_data(extraction_root,int(str(body["target_trade_date"]).replace("-","")),ids)
    if validation["status"]!="PASS": raise ValueError("EXTRACTED_DAY_VALIDATION_FAILED")
    return {"status":"PASS","source_bundle_id":claimed,"package_sha256":body["package"]["sha256"],"validation":validation}
