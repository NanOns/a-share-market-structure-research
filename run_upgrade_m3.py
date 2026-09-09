from __future__ import annotations
"""M3 acceptance: capture a fresh official package and a stable local snapshot."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, sys, uuid

ROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT/"src"))
from common.paths import resolve_tdx_root
from tdx.security_master import read_industry_assignments, current_a_stock_ids
from workbench_db import WorkbenchRepository
from workbench_input import (analyze_dynamic_metadata, capture_stable_metadata,
    download_official_package_curl, safe_extract_zip, seal_source_bundle,
    validate_extracted_day_data, verify_source_bundle)
OFFICIAL_URL="https://data.tdx.com.cn/vipdoc/hsjday.zip"

def atomic(path,text):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f".{uuid.uuid4().hex}.tmp");tmp.write_text(text,encoding="utf-8");os.replace(tmp,path)
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def official_info():
 url="https://data.tdx.com.cn/vipdoc/_hsjdayinfo.js"
 p=subprocess.run(["curl.exe","--fail","--location","--max-time","30","--user-agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0","--write-out","\n%{url_effective}",url],capture_output=True,text=True,encoding="gb18030",errors="replace")
 if p.returncode:return {"status":"UNAVAILABLE","error":p.stderr[-500:]}
 text,effective=p.stdout.rsplit("\n",1);m=re.search(r'HSJDAY_SOFT_TIME="([^"]+)',text);size=re.search(r'HSJDAY_SOFT_SIZE="([^"]+)',text)
 return {"status":"PASS" if m and effective.strip()==url else "FAIL","update_time":m.group(1) if m else None,"declared_size":size.group(1) if size else None,"resolved_url":effective.strip()}
def info_day(info):
 m=re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})",info.get("update_time") or "")
 if not m:raise ValueError("OFFICIAL_DATE_UNPARSEABLE")
 return f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"
def manifest(root):
 values={}
 for p in sorted(Path(root).rglob("*")):
  if p.is_file():values[str(p.relative_to(root)).replace("\\","/")]={"size":p.stat().st_size,"sha256":sha(p)}
 return values
def stage_inputs(day):
 """Probe the official ZIP and live TDX metadata every run; reuse staging only after identity equality."""
 staging=ROOT/"data/input_staging"; scratch=ROOT/"runtime/m3"/uuid.uuid4().hex;scratch.mkdir(parents=True,exist_ok=False)
 try:
  downloaded=scratch/"hsjday.zip";package=download_official_package_curl(OFFICIAL_URL,downloaded)
  target=staging/"packages"/day/"hsjday.zip";target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():
   if sha(target)!=package["sha256"]:raise ValueError("STAGED_PACKAGE_IDENTITY_CONFLICT")
  else:os.replace(downloaded,target)
  extraction=staging/"extracted"/day
  if extraction.is_symlink():raise ValueError("STAGED_EXTRACTION_SYMLINK")
  if extraction.exists():shutil.rmtree(extraction)
  extraction_result=safe_extract_zip(target,extraction)
  captured=scratch/"metadata";meta=capture_stable_metadata(resolve_tdx_root(ROOT),captured,stable_seconds=3)
  metadata=staging/"metadata"/day
  if metadata.exists():
   if manifest(metadata)!=meta["files"]:raise ValueError("STAGED_METADATA_IDENTITY_CONFLICT")
   shutil.rmtree(captured)
  else:metadata.parent.mkdir(parents=True,exist_ok=True);os.replace(captured,metadata)
  package["staged_path"]=str(target.relative_to(ROOT)).replace("\\","/")
  return package,extraction,metadata,extraction_result
 finally:shutil.rmtree(scratch,ignore_errors=True)
def main():
 tests=subprocess.run([sys.executable,"-m","pytest","-q","tests/upgrade_m3"],cwd=ROOT,text=True,capture_output=True);blockers=[];info=official_info();package_meta={};validation={};catalog={};bundle={}
 try:
  if info.get("status")!="PASS":raise ValueError("OFFICIAL_DATE_UNVERIFIED")
  day=info_day(info);package_meta,extracted,metadata_root,extraction_result=stage_inputs(day)
  current_ids=current_a_stock_ids(read_industry_assignments(metadata_root/"T0002/hq_cache/tdxhy.cfg"));validation=validate_extracted_day_data(extracted,int(day),current_ids)
  if validation["status"]!="PASS":raise ValueError("DAY_VALIDATION_FAILED")
  metadata_manifest=manifest(metadata_root);catalog=analyze_dynamic_metadata(metadata_root,available_security_ids={x.stem[:2].upper()+"."+x.stem[2:] for x in extracted.rglob("*.day")})
  extraction={**extraction_result,"root":str(extracted.relative_to(ROOT)).replace("\\","/")}
  metadata={"metadata_snapshot_id":hashlib.sha256(json.dumps(metadata_manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"files":metadata_manifest,"stability":"PASS","structural_integrity":"PASS","freshness":"UNKNOWN","root":str(metadata_root.relative_to(ROOT)).replace("\\","/")}
  bundle=seal_source_bundle(ROOT/"data/source_bundles",target_trade_date=f"{day[:4]}-{day[4:6]}-{day[6:]}",package=package_meta,extraction=extraction,metadata=metadata,calendar_sha256=sha(ROOT/"config/trading_calendar.yaml"),validation=validation)
  verify_source_bundle(ROOT/"data/source_bundles"/bundle["source_bundle_id"]/'source_bundle.json')
  with WorkbenchRepository(ROOT) as repo:
   repo.connection.execute("INSERT INTO source_packages VALUES (?, ?) ON CONFLICT DO NOTHING",[package_meta["sha256"],json.dumps(package_meta,ensure_ascii=False)]);repo.connection.execute("INSERT INTO metadata_snapshots VALUES (?, ?) ON CONFLICT DO NOTHING",[metadata["metadata_snapshot_id"],json.dumps(metadata,ensure_ascii=False)]);repo.connection.execute("INSERT INTO source_bundles VALUES (?, ?) ON CONFLICT DO UPDATE SET payload_json=excluded.payload_json",[bundle["source_bundle_id"],json.dumps(bundle,ensure_ascii=False)])
 except Exception as exc:blockers.append(str(exc))
 if tests.returncode:blockers.append("IMPLEMENTATION_TESTS_FAILED")
 status="FULL_PASS" if not blockers else "BLOCKED";receipt={"phase":"M3_AUTOMATIC_INPUT","contract":"m3-automatic-input-v1.2","created_at_utc":datetime.now(timezone.utc).isoformat(),"official_info":info,"implementation_tests":"PASS" if not tests.returncode else "FAIL","test_output":tests.stdout.strip(),"fresh_official_download":bool(package_meta),"package_sha256":package_meta.get("sha256"),"source_bundle_sealed":bool(bundle and not blockers),"source_bundle_id":bundle.get("source_bundle_id"),"day_validation":validation,"dynamic_metadata":{"security_count":len(catalog.get("securities",{})),"sector_count":len(catalog.get("sectors",{})),"membership_count":len(catalog.get("memberships",[]))},"final_status":status,"blockers":blockers,"next_stage":"M4_ONE_CLICK_PUBLICATION" if status=="FULL_PASS" else "NONE"}
 out=ROOT/"reports/upgrade_m3";atomic(out/"M3_AUTOMATIC_INPUT_RECEIPT.json",json.dumps(receipt,ensure_ascii=False,indent=2)+"\n");atomic(out/"M3_AUTOMATIC_INPUT.md",f"# M3 自动输入验收\n\n- 状态：`{status}`\n- 测试：`{receipt['test_output']}`\n- 官方更新时间：`{info.get('update_time')}`\n- SHA-256：`{receipt['package_sha256']}`\n- bundle：`{receipt['source_bundle_id']}`\n- 阻断项：`{blockers}`\n");print(json.dumps(receipt,ensure_ascii=False,indent=2));return 0 if status=="FULL_PASS" else 2
if __name__=="__main__":raise SystemExit(main())
