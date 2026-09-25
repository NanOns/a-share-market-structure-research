"""Reproducible, asset-stratified TDX .day overlap acceptance (read-only inputs)."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
from datetime import date, datetime, timezone
from zipfile import ZipFile
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from v4.contracts.source_overlap import ASSET_TYPES, compare_day_values, classify_asset, parse_security_filename, research_a_stock_ids, sessions_from_index_chains

RECORD = struct.Struct("<IIIIIfII")
FIELDS = ("open", "high", "low", "close", "amount", "volume")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def day_map(root: Path, sessions: set[int], a_ids: set[str], market: str):
    rows = {}
    malformed = []
    file_ids = set()
    file_info = {}
    unit_checks = 0
    unit_plausible = 0
    lday = root / market.lower() / "lday"
    for path in sorted(lday.glob("*.day")):
        identity = parse_security_filename(path, market)
        if not identity:
            malformed.append({"file": path.name, "reason": "FILENAME_IDENTITY_MISMATCH"})
            continue
        mkt, code = identity
        sid = f"{mkt}.{code}"
        file_ids.add(sid)
        raw_size = path.stat().st_size
        if raw_size % RECORD.size:
            malformed.append({"file": path.name, "reason": "INCOMPLETE_TAIL_RECORD", "bytes": raw_size})
            continue
        errors = Counter()
        previous_date = None
        with path.open("rb") as stream:
            if raw_size >= RECORD.size:
                stream.seek(-RECORD.size, 2)
                file_info[sid]={"last_record_date":RECORD.unpack(stream.read(RECORD.size))[0],"mtime_ns":path.stat().st_mtime_ns}
                stream.seek(0)
            for record in RECORD.iter_unpack(stream.read()):
                date_value, o, h, low, c, amount, volume, _ = record
                year=date_value//10000; month=(date_value//100)%100; day=date_value%100
                valid_date=19900101<=date_value<=21001231 and 1<=month<=12 and 1<=day<=31
                if valid_date:
                    try: date(year,month,day)
                    except ValueError: valid_date=False
                if not valid_date: errors["INVALID_TRADE_DATE"]+=1
                if previous_date is not None and date_value<=previous_date:
                    errors["DUPLICATE_TRADE_DATE" if date_value==previous_date else "NON_INCREASING_TRADE_DATE"]+=1
                previous_date=date_value
                if not (o==h==low==c==0) and (h<max(o,low,c) or low>min(o,h,c)):
                    errors["INVALID_OHLC"]+=1
                if not math.isfinite(amount) or amount<0:
                    errors["INVALID_AMOUNT"]+=1
                if sid in a_ids and amount>0 and volume>0 and low>0 and h>0:
                    unit_checks+=1
                    implied=amount/volume
                    if (low/100.0)*0.95<=implied<=(h/100.0)*1.05:
                        unit_plausible+=1
                if date_value in sessions:
                    rows[(sid, date_value)] = (o, h, low, c, amount, volume)
        if errors:
            malformed.append({"file":path.name,"reason":"RECORD_VALIDATION_FAILURE","error_counts":dict(sorted(errors.items()))})
    types = {sid: classify_asset(sid.split(".")[0], sid.split(".")[1], a_ids) for sid in file_ids}
    return rows, file_ids, types, malformed, file_info, {"checks":unit_checks,"plausible":unit_plausible}


def run(args: argparse.Namespace) -> dict:
    package = Path(args.package).resolve()
    metadata = Path(args.metadata_root).resolve()
    local_root = Path(args.local_tdx_root).resolve()
    if not package.is_file() or not metadata.is_dir() or not local_root.is_dir():
        raise ValueError("PACKAGE_OR_READ_ONLY_ROOT_MISSING")
    package_sha = sha256(package)
    extracted = Path(args.package_root).resolve() if args.package_root else None
    if extracted is None:
        parts = package.parts
        if "packages" in parts:
            pos = parts.index("packages")
            datepart = parts[pos + 1]
            extracted = ROOT / "data" / "input_staging" / "extracted" / datepart / package_sha
        else:
            raise ValueError("--package-root is required when package is outside project staging")
    if not extracted.is_dir():
        raise ValueError("EXTRACTED_PACKAGE_ROOT_MISSING")
    a_ids = research_a_stock_ids(metadata)
    sessions = sessions_from_index_chains(extracted, args.sessions)
    session_set = set(sessions)
    package_rows, package_ids, package_types, package_malformed, package_info, package_units = day_map(extracted, session_set, a_ids, "sh")
    local_rows, local_ids, local_types, local_malformed, local_info = {}, set(), {}, [], {}
    local_units={"checks":0,"plausible":0}
    for market in ("sh", "sz", "bj"):
        rows, ids, types, malformed, info, units = day_map(local_root / "vipdoc", session_set, a_ids, market)
        local_rows.update(rows); local_ids.update(ids); local_types.update(types); local_malformed.extend(malformed); local_info.update(info)
        local_units["checks"]+=units["checks"]; local_units["plausible"]+=units["plausible"]
    # package root is a source ZIP extraction and contains these same three markets
    for market in ("sz", "bj"):
        rows, ids, types, malformed, info, units = day_map(extracted, session_set, a_ids, market)
        package_rows.update(rows); package_ids.update(ids); package_types.update(types); package_malformed.extend(malformed); package_info.update(info)
        package_units["checks"]+=units["checks"]; package_units["plausible"]+=units["plausible"]
    package_ratio=package_units["plausible"]/package_units["checks"] if package_units["checks"] else 0
    local_ratio=local_units["plausible"]/local_units["checks"] if local_units["checks"] else 0
    zip_entry_times={}
    with ZipFile(package) as archive:
        for info in archive.infolist():
            name=info.filename.replace("\\","/")
            match=__import__("re").search(r"(?:^|/)((?:sh|sz|bj)/lday/(?:sh|sz|bj)\d{6}\.day)$",name.lower())
            if match:
                zip_entry_times[Path(match.group(1)).stem.upper()]=datetime(*info.date_time).date().isoformat()
    selected = set(ASSET_TYPES if args.security_type == "ALL" else [args.security_type])
    result_by_type = {}
    all_mismatch_samples = []
    for kind in sorted(selected):
        pkeys = {k for k in package_rows if package_types.get(k[0]) == kind}
        lkeys = {k for k in local_rows if local_types.get(k[0]) == kind}
        common = pkeys & lkeys
        exact = 0
        field_mismatch = Counter()
        unexplained = 0
        normalized = 0
        price_tolerance_rows = 0
        refresh_revisions = 0
        volume_abs_deltas=[]
        samples = []
        for key in sorted(common):
            left, right = package_rows[key], local_rows[key]
            pinfo=package_info.get(key[0],{}); linfo=local_info.get(key[0],{})
            archive_day=zip_entry_times.get(key[0].replace(".","",1))
            local_mtime_day=datetime.fromtimestamp(linfo.get("mtime_ns",0)/1_000_000_000,timezone.utc).date().isoformat()
            source_refresh=(pinfo.get("last_record_date",0)>linfo.get("last_record_date",0)
                and archive_day is not None
                and archive_day>=date(int(str(pinfo["last_record_date"])[:4]),int(str(pinfo["last_record_date"])[4:6]),int(str(pinfo["last_record_date"])[6:])).isoformat()
                and archive_day>local_mtime_day)
            comparison,reason,diffs=compare_day_values(left,right,source_refresh_eligible=source_refresh)
            if comparison=="EXACT":
                exact += 1
                continue
            if reason=="TOLERATED_PRICE_ROUNDING":
                normalized += 1
                price_tolerance_rows += 1
                for field in diffs: field_mismatch[field] += 1
            elif reason=="TOLERATED_SOURCE_REFRESH_VOLUME_REVISION":
                normalized += 1
                refresh_revisions += 1
                volume_abs_deltas.append(abs(int(left[FIELDS.index("volume")])-int(right[FIELDS.index("volume")])) )
                field_mismatch["volume"] += 1
            else:
                unexplained += 1
                for field in diffs: field_mismatch[field] += 1
                if len(samples) < 100:
                    samples.append({"security_id":key[0],"trade_date":key[1],"fields":diffs,"package":left,"local":right})
        pkg_only = pkeys - lkeys
        loc_only = lkeys - pkeys
        def reason(key, side):
            sid = key[0]
            known = sid in a_ids
            if side=="package_only" and sid in local_ids and key[1]>local_info.get(sid,{}).get("last_record_date",0):
                return "PACKAGE_INCREMENTAL_SESSION_AFTER_LOCAL_SNAPSHOT"
            if side=="local_only" and sid in package_ids and key[1]>package_info.get(sid,{}).get("last_record_date",0):
                return "LOCAL_SESSION_ABSENT_FROM_PACKAGE"
            if known:
                return "CURRENT_RESEARCH_UNIVERSE_MEMBER_LOCAL_BAR_COVERAGE"
            return "NON_CURRENT_MEMBER_OR_HISTORICAL_LIFECYCLE_UNKNOWN"
        only_reasons = Counter()
        for key in pkg_only: only_reasons["package_only:" + reason(key,"package_only")] += 1
        for key in loc_only: only_reasons["local_only:" + reason(key,"local_only")] += 1
        mismatch_reasons={"TOLERATED_PRICE_ROUNDING":price_tolerance_rows,"TOLERATED_SOURCE_REFRESH_VOLUME_REVISION":refresh_revisions,"UNEXPLAINED_MISMATCH":unexplained}
        hard_malformed = []
        for m in package_malformed + local_malformed:
            name=m.get("file", "")
            code=name[2:8] if len(name)>=8 else ""
            mkt=name[:2].upper()
            if re.fullmatch(r"\d{6}",code) and classify_asset(mkt,code,a_ids)==kind:
                hard_malformed.append(m)
        identity_mismatch = sum(1 for sid in package_ids & local_ids if package_types.get(sid) != local_types.get(sid))
        unit_fail = kind=="A_STOCK" and (package_ratio<0.98 or local_ratio<0.98)
        accepted = identity_mismatch == 0 and not hard_malformed and unexplained == 0 and not unit_fail
        result_by_type[kind] = {
            "security_type":kind,"session_count":len(sessions),"sessions":{"first":sessions[0],"last":sessions[-1]},
            "comparable_rows":len(common),"exact_match_rows":exact,"normalized_match_rows":normalized,
            "unexplained_mismatch_rows":unexplained,"source_refresh_volume_revision_rows":refresh_revisions,
            "source_refresh_volume_abs_delta_max":max(volume_abs_deltas,default=0),"package_only_rows":len(pkg_only),"local_only_rows":len(loc_only),
            "identity_mismatch_count":identity_mismatch,"malformed_count":len(hard_malformed)+(1 if unit_fail else 0),
            "field_mismatch_counts":dict(sorted(field_mismatch.items())),"reason_classification":{**dict(sorted(only_reasons.items())),**mismatch_reasons},
            "acceptance":"ACCEPTED_SOURCE_PACKAGE" if accepted else "BLOCKED",
            "mismatch_samples":samples,
            "identity_semantics":"TDX venue + six-digit security code verified against paired .day filenames and source master where present; issuer/legal-entity identity is not represented by TDX and is not claimed."
        }
        all_mismatch_samples.extend({"security_type":kind,**s} for s in samples[:20])
    selected_accept = all(v["acceptance"] == "ACCEPTED_SOURCE_PACKAGE" for v in result_by_type.values())
    metadata_cache=metadata/"T0002"/"hq_cache"
    local_cache=local_root/"T0002"/"hq_cache"
    local_metadata_hashes={p.name:sha256(p) for p in sorted(local_cache.glob("*")) if p.is_file() and p.name in {"gbbq","gbbq.map","tdxhy.cfg","tdxzs.cfg","infoharbor_block.dat","shs.tnf","szs.tnf","bjs.tnf"}}
    local_day_entries=[]
    for folder in (local_root/"vipdoc"/"sh"/"lday",local_root/"vipdoc"/"sz"/"lday",local_root/"vipdoc"/"bj"/"lday"):
        for p in sorted(folder.glob("*.day")):
            local_day_entries.append({"relative_path":p.relative_to(local_root).as_posix(),"bytes":p.stat().st_size,"sha256":sha256(p)})
    local_snapshot_id=hashlib.sha256(json.dumps({"day_files":local_day_entries,"metadata":local_metadata_hashes},sort_keys=True,separators=(",",":")).encode()).hexdigest()
    manifest = {
        "contract_id":"TDX_VIPDATA_OVERLAP_ACCEPTANCE_V1","source_package_sha256":package_sha,
        "package_path":str(package),"local_snapshot_identity":{"root":"D:/new_tdx/vipdoc","snapshot_sha256":local_snapshot_id,"day_file_count":len(local_day_entries),"metadata_sha256":local_metadata_hashes},
        "parser_version":"v4-day-raw-v1.1","comparison_key":"exchange + six-digit TDX security code + YYYYMMDD",
        "security_type_requested":args.security_type,"session_count":len(sessions),"sessions":{"first":sessions[0],"last":sessions[-1]},
        "core_security_type":"A_STOCK","asset_types":result_by_type,
        "a_stock_unit_crosscheck":{"storage_unit":"volume=uint32 shares; amount=float32 CNY; OHLC=uint32 price/100","rule":"positive amount/volume records have amount/volume within 5% of stored low/high","minimum_plausibility_ratio":0.98,"package":{"checks":package_units["checks"],"plausible":package_units["plausible"],"ratio":package_ratio},"local":{"checks":local_units["checks"],"plausible":local_units["plausible"],"ratio":local_ratio}},
        "acceptance":"ACCEPTED_SOURCE_PACKAGE" if result_by_type.get("A_STOCK",{}).get("acceptance")=="ACCEPTED_SOURCE_PACKAGE" else "BLOCKED",
        "all_selected_types_accepted":selected_accept,"created_at_utc":datetime.now(timezone.utc).isoformat(),
        "normalization_policy":{"ohlc":"raw storage integer difference <= 1 is counted separately as TOLERATED_PRICE_ROUNDING","volume":"exact integer except TDX_SAME_SOURCE_REFRESH_REVISION_V1: the official package's same-security last record and ZIP entry timestamp must both be newer than local; OHLC and amount must match exactly","amount":"exact decoded IEEE-754 float32"},
        "limits":["No legal-entity identifier is available in the TDX .day format.","Rows present in one snapshot only are coverage/lifecycle facts, not value mismatches.","Source-refresh revisions are distinguished from numeric tolerance and counted separately."]
    }
    out=Path(args.output).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(out.suffix+".tmp"); tmp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); os.replace(tmp,out)
    return manifest


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--package",required=True,help="Official ZIP package")
    p.add_argument("--package-root",help="Already verified extracted package root")
    p.add_argument("--metadata-root",required=True,help="Read-only source bundle metadata root")
    p.add_argument("--local-tdx-root",required=True,help="Read-only TDX installation root")
    p.add_argument("--sessions",type=int,default=60)
    p.add_argument("--security-type",choices=[*ASSET_TYPES,"ALL"],default="A_STOCK")
    p.add_argument("--output",required=True)
    return p.parse_args()


if __name__ == "__main__":
    report=run(parse_args())
    print(json.dumps({"acceptance":report["acceptance"],"source_package_sha256":report["source_package_sha256"],"asset_types":{k:{"acceptance":v["acceptance"],"comparable_rows":v["comparable_rows"],"exact_match_rows":v["exact_match_rows"],"normalized_match_rows":v["normalized_match_rows"],"unexplained_mismatch_rows":v["unexplained_mismatch_rows"],"package_only_rows":v["package_only_rows"],"local_only_rows":v["local_only_rows"]} for k,v in report["asset_types"].items()}},ensure_ascii=False))
