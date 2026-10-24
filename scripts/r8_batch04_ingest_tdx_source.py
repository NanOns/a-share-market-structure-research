"""持续维护入口：按显式来源 manifest 幂等接入 TDX 原始事实到开发 PG。

保留脚本名和既有 schema 兼容 D0 消费者；V2 不再绑定历史批次日期。
本入口只准入原始来源，不发布 Owner、Head、调度或 PIT 资格。
"""
from __future__ import annotations

import argparse
from datetime import date,datetime,timezone
import hashlib
import json
import os
import math
import struct
import sys
import zipfile
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT/'src') not in sys.path:sys.path.insert(0,str(ROOT/'src'))
SCHEMA = "v4_r8_batch04_source_ingress"
CONTRACT = "V4_TDX_SOURCE_INGRESS_V2"
HEADS = (ROOT / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json",
         ROOT / "data/v4/V4_DATA_ACCEPTED_HEAD.json")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _completion_scope() -> dict:
    """Make it impossible to interpret source admission as a completed V4 day."""
    return dict(
        completion_scope="SOURCE_INGRESS_ONLY",
        business_chain_status="NOT_RUN",
        business_chain_complete=False,
        required_downstream_domains=(
            "CORE", "PROFILE", "SECTOR", "MARKET", "D0", "D2",
            "PRIORITY", "FOCUS", "FORWARD", "READ_INDEX", "API_PAGE_READBACK",
        ),
    )


def _dsn() -> str:
    values = {}
    for line in (ROOT / "config/.env").read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip().strip('"').strip("'")
    value = values.get("WORKBENCH_PG_DSN")
    parsed = conninfo_to_dict(value or "")
    if (parsed.get("host"), parsed.get("port"), parsed.get("dbname")) != (
            "127.0.0.1", "5432", "market_research"):
        raise ValueError("R8_BATCH04_PG_TARGET_IDENTITY_MISMATCH")
    return value


def _checked_source(binding):
    path=Path(binding['path']).resolve()
    if not path.is_file() or path.stat().st_size!=binding.get('bytes',path.stat().st_size):
        raise ValueError('SOURCE_INGRESS_BINDING_MISSING_OR_SIZE_MISMATCH')
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):digest.update(block)
    if digest.hexdigest()!=binding['sha256']:raise ValueError('SOURCE_INGRESS_BINDING_SHA_MISMATCH')
    return path


def _verify_package_rows(package_path,items):
    """逐字段重读已绑定的原始包；manifest 不能自行声明行情数值。"""
    from workbench_analysis.market_source_acquisition import is_stock_code
    wanted={int(item['day'].replace('-','')):item['day'] for item in items}
    expected={day:{} for day in wanted.values()}
    with zipfile.ZipFile(package_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)):raise ValueError('SOURCE_INGRESS_PACKAGE_MEMBER_AMBIGUOUS')
        for name in names:
            parts=name.lower().replace('\\','/').split('/')
            market=next((part for part in parts if part in {'sh','sz','bj'}),None)
            leaf=parts[-1]
            if not leaf.endswith('.day') or not market:continue
            code=(market+'.'+leaf[-10:-4]).upper()
            if not is_stock_code(code):continue
            raw=archive.read(name)
            if len(raw)%32:raise ValueError('SOURCE_INGRESS_DAY_RECORD_ALIGNMENT')
            entry_sha=_sha(raw)
            for stamp,o,h,l,c,amount,volume,_ in struct.iter_unpack('<IIIIIfII',raw):
                day=wanted.get(stamp)
                if day:
                    if code in expected[day]:raise ValueError('SOURCE_INGRESS_NATIVE_CODE_DATE_AMBIGUOUS')
                    expected[day][code]=(name,entry_sha,o/100,h/100,l/100,c/100,amount,volume)
    for item in items:
        actual={row['source_security_key']:(row.get('source_entry'),row.get('entry_sha256'),
            row['open'],row['high'],row['low'],row['close'],row['amount'],row['volume']) for row in item['document']['target_bars']}
        if actual!=expected[item['day']]:raise ValueError('SOURCE_INGRESS_NATIVE_BAR_REPLAY_MISMATCH:'+item['day'])


def _load_days(artifact_root: Path, days: tuple[str, ...], source_manifest: Path) -> list[dict]:
    rows = []
    if not days or tuple(days) != tuple(sorted(set(days))):
        raise ValueError("R8_BATCH04_DATES_MUST_BE_NONEMPTY_UNIQUE_AND_IN_ORDER")
    if any(date.fromisoformat(day).isoformat()!=day for day in days):raise ValueError('SOURCE_INGRESS_TARGET_DATE_INVALID')
    manifest=json.loads(Path(source_manifest).read_bytes())
    if manifest.get('contract_id')!='V4_TDX_SOURCE_INGRESS_INPUT_V2':raise ValueError('SOURCE_INGRESS_INPUT_CONTRACT_REQUIRED')
    capture=json.loads(_checked_source(manifest['capture_receipt']).read_bytes())
    package=manifest['package'];package_path=_checked_source(package)
    if (capture.get('contract_id')!='TDX_OFFICIAL_DAILY_PACKAGE_SOURCE_V1'
            or capture.get('status') not in ('TDX_PACKAGE_READY','NOOP_SOURCE_ALREADY_FROZEN')
            or capture.get('download',{}).get('sha256')!=package['sha256']
            or capture.get('download',{}).get('bytes')!=package.get('bytes')
            or capture.get('tdx_root_write_count')!=0):raise ValueError('SOURCE_INGRESS_OFFICIAL_CAPTURE_MISMATCH')
    for day in days:
        binding=manifest.get('dates',{}).get(day)
        if not binding:raise ValueError('SOURCE_INGRESS_TARGET_BINDING_MISSING:'+day)
        path=_checked_source(binding)
        if artifact_root.resolve() not in path.parents:
            raise ValueError("R8_BATCH04_TARGET_ARTIFACT_ESCAPES_TEMP_ROOT")
        raw = path.read_bytes()
        document = json.loads(raw)
        if (document.get("target_session") != day or document.get("status") != "TARGET_BARS_EXTRACTED" or
                document.get("provider_package_date") != capture.get('update_date') or
                document.get('provider_package_date','') < day or
                document.get('source_sha256')!=package['sha256'] or
                document.get('reconstruction_from_later_snapshot')!=(document.get('provider_package_date','')>day) or
                document.get("row_count") != len(document.get("target_bars", [])) or
                document.get("row_count", 0) <= 0 or document.get("tdx_root_write_count") != 0):
            raise ValueError(f"R8_BATCH04_TARGET_ARTIFACT_INVALID:{day}")
        source_sha = document.get("source_sha256")
        if not isinstance(source_sha, str) or len(source_sha) != 64 or any(c not in '0123456789abcdef' for c in source_sha):
            raise ValueError(f"R8_BATCH04_SOURCE_SHA_INVALID:{day}")
        codes = [row.get("source_security_key") for row in document["target_bars"]]
        if any(not code for code in codes) or len(codes) != len(set(codes)):
            raise ValueError(f"R8_BATCH04_TARGET_CODES_INVALID:{day}")
        for row in document['target_bars']:
            values=[row.get(key) for key in ('open','high','low','close','amount','volume')]
            if row.get('trade_date')!=day or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
                raise ValueError('SOURCE_INGRESS_BAR_DATE_OR_NUMBER_INVALID:'+day)
            o,h,l,c,amount,volume=values
            if not 0<l<=min(o,c)<=max(o,c)<=h or amount<0 or volume<0 or int(volume)!=volume:
                raise ValueError('SOURCE_INGRESS_BAR_OHLCV_INVALID:'+day)
        observed=datetime.fromisoformat(document['source_available_at'].replace('Z','+00:00'))
        if observed.tzinfo is None or observed>datetime.now(timezone.utc):raise ValueError('SOURCE_INGRESS_OBSERVATION_TIME_INVALID')
        complete=capture.get('source_transport_v2',{}).get('received_at') or capture.get('downloaded_at')
        if not complete or observed<datetime.fromisoformat(complete.replace('Z','+00:00')):
            raise ValueError('SOURCE_INGRESS_DOWNLOAD_AVAILABILITY_NOT_PROVEN')
        rows.append(dict(day=day, document=document, artifact_path=str(path),
                         artifact_sha256=_sha(raw), artifact_bytes=len(raw)))
    _verify_package_rows(package_path,rows)
    return rows


def ingest(artifact_root: Path, days: tuple[str, ...], *, source_manifest: Path) -> dict:
    days = _load_days(artifact_root, days, source_manifest)
    before_heads = {str(path): _sha(path.read_bytes()) for path in HEADS}
    connection = psycopg.connect(_dsn(), connect_timeout=5)
    try:
        connection.execute("SET TRANSACTION READ WRITE")
        identity = connection.execute("""select current_database(), current_user,
            (select oid from pg_database where datname=current_database()),
            current_setting('server_version_num'), current_setting('transaction_read_only')""").fetchone()
        if identity[0] != "market_research" or identity[4] != "off":
            raise ValueError("R8_BATCH04_PG_WRITE_SESSION_IDENTITY_MISMATCH")
        connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
        connection.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".source_receipts (
            trade_date date PRIMARY KEY,
            source_contract text NOT NULL,
            source_sha256 text NOT NULL,
            package_date date NOT NULL,
            available_at timestamptz NOT NULL,
            time_role text NOT NULL,
            evidence_class text NOT NULL,
            artifact_path text NOT NULL,
            artifact_sha256 text NOT NULL,
            artifact_bytes bigint NOT NULL,
            row_count integer NOT NULL,
            candidate_only boolean NOT NULL CHECK (candidate_only),
            production_accepted boolean NOT NULL CHECK (NOT production_accepted),
            recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )''')
        connection.execute(f'''CREATE TABLE IF NOT EXISTS "{SCHEMA}".tdx_bars (
            trade_date date NOT NULL REFERENCES "{SCHEMA}".source_receipts(trade_date),
            source_security_key text NOT NULL,
            open double precision NOT NULL,
            high double precision NOT NULL,
            low double precision NOT NULL,
            close double precision NOT NULL,
            amount double precision NOT NULL,
            volume bigint NOT NULL,
            source_sha256 text NOT NULL,
            evidence_class text NOT NULL,
            PRIMARY KEY (trade_date, source_security_key)
        )''')
        before_counts = dict(
            receipts=connection.execute(f'SELECT count(*) FROM "{SCHEMA}".source_receipts').fetchone()[0],
            bars=connection.execute(f'SELECT count(*) FROM "{SCHEMA}".tdx_bars').fetchone()[0])
        counts = []
        for item in days:
            day, doc = item["day"], item["document"]
            evidence = "RECONSTRUCTED_NON_PIT" if doc["reconstruction_from_later_snapshot"] else "CAPTURED_AFTER_CLOSE_NON_PIT"
            available_at = doc.get("source_available_at")
            if not available_at:
                raise ValueError("R8_BATCH04_SOURCE_CLOCK_MISSING")
            receipt = (day, "TDX_LATEST_PACKAGE_TARGET_SESSION_V2", doc["source_sha256"],
                doc["provider_package_date"], available_at,
                "POST_CLOSE_LATE_CAPTURE" if day == doc['provider_package_date'] else "RECONSTRUCTED_FROM_LATER_PACKAGE",
                evidence, item["artifact_path"], item["artifact_sha256"], item["artifact_bytes"],
                doc["row_count"], True, False)
            inserted = connection.execute(f'''INSERT INTO "{SCHEMA}".source_receipts
                (trade_date,source_contract,source_sha256,package_date,available_at,time_role,
                 evidence_class,artifact_path,artifact_sha256,artifact_bytes,row_count,
                 candidate_only,production_accepted)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (trade_date) DO NOTHING RETURNING trade_date''', receipt).fetchone()
            stored = connection.execute(f'''SELECT source_contract,source_sha256,package_date,
                available_at,time_role,evidence_class,artifact_path,artifact_sha256,artifact_bytes,row_count,
                candidate_only,production_accepted FROM "{SCHEMA}".source_receipts
                WHERE trade_date=%s''', (day,)).fetchone()
            if (stored[0:2] != receipt[1:3] or stored[2].isoformat() != receipt[3] or
                    stored[3] != datetime.fromisoformat(available_at.replace("Z", "+00:00")) or
                    stored[4:] != receipt[5:]):
                raise ValueError(f"R8_BATCH04_IMMUTABLE_RECEIPT_CONFLICT:{day}")
            bars = doc["target_bars"]
            with connection.cursor() as cursor:
                cursor.executemany(f'''INSERT INTO "{SCHEMA}".tdx_bars
                (trade_date,source_security_key,open,high,low,close,amount,volume,source_sha256,evidence_class)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (trade_date,source_security_key) DO NOTHING''',
                [(day, row["source_security_key"], row["open"], row["high"], row["low"],
                  row["close"], row["amount"], row["volume"], doc["source_sha256"], evidence)
                 for row in bars])
            actual = connection.execute(f'''SELECT count(*),count(DISTINCT source_security_key),
                min(source_sha256),max(source_sha256),count(*) FILTER (WHERE evidence_class=%s)
                FROM "{SCHEMA}".tdx_bars WHERE trade_date=%s''', (evidence, day)).fetchone()
            if actual != (len(bars), len(bars), doc["source_sha256"], doc["source_sha256"], len(bars)):
                raise ValueError(f"R8_BATCH04_BAR_READBACK_MISMATCH:{day}")
            stored_bars = connection.execute(f'''SELECT source_security_key,open,high,low,close,amount,
                volume,source_sha256,evidence_class FROM "{SCHEMA}".tdx_bars
                WHERE trade_date=%s ORDER BY source_security_key''', (day,)).fetchall()
            expected_bars = sorted((
                row["source_security_key"], float(row["open"]), float(row["high"]),
                float(row["low"]), float(row["close"]), float(row["amount"]),
                int(row["volume"]), doc["source_sha256"], evidence,
            ) for row in bars)
            if stored_bars != expected_bars:
                raise ValueError(f"R8_BATCH04_BAR_VALUE_READBACK_MISMATCH:{day}")
            counts.append(dict(trade_date=day, row_count=actual[0], inserted_receipt=inserted is not None,
                               value_readback="EXACT_ALL_FIELDS", evidence_class=evidence,
                               source_sha256=doc["source_sha256"],
                               artifact_sha256=item["artifact_sha256"], available_at=available_at))
        after_counts = dict(
            receipts=connection.execute(f'SELECT count(*) FROM "{SCHEMA}".source_receipts').fetchone()[0],
            bars=connection.execute(f'SELECT count(*) FROM "{SCHEMA}".tdx_bars').fetchone()[0])
        formal_head_unchanged = all(_sha(path.read_bytes()) == digest for path, digest in
                                    ((Path(name), value) for name, value in before_heads.items()))
        if not formal_head_unchanged:
            raise ValueError("R8_BATCH04_FORMAL_HEAD_BYTES_CHANGED")
        connection.commit()
        return dict(contract_id=CONTRACT, status="SOURCE_INGRESS_READBACK_PASS",
            **_completion_scope(),
            source_manifest=dict(path=str(Path(source_manifest).resolve()),sha256=_sha(Path(source_manifest).read_bytes())),
            database=dict(database=identity[0], database_oid=identity[2], server_version_num=identity[3],
                          write_role=identity[1], session_read_only=identity[4]),
            schema=SCHEMA, before_counts=before_counts, after_counts=after_counts,
            days=counts, formal_head_unchanged=formal_head_unchanged,
            publication_created=False, development_head_modified=False,
            production_head_modified=False, production_accepted=False)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='按明确日期与来源 manifest 接入开发 PG 原始事实，保留正式 Head')
    parser.add_argument("--artifact-root", type=Path, required=True,help='G 盘冻结原始产物根目录')
    parser.add_argument("--receipt", type=Path, required=True,help='G 盘任务收据输出路径')
    parser.add_argument("--source-manifest",type=Path,required=True,help='版本化包、采集收据与逐日原始产物绑定')
    parser.add_argument("--days", nargs="+", required=True,help='显式 ISO 交易日，严格递增且不重复')
    args = parser.parse_args()
    artifact_root = args.artifact_root.resolve()
    temp_root = Path("G:/codex_tmp").resolve()
    if artifact_root != temp_root and temp_root not in artifact_root.parents:
        raise ValueError("R8_BATCH04_ARTIFACT_ROOT_MUST_BE_G_CODEX_TMP")
    target = args.receipt.resolve()
    if target.drive.upper() != "G:" or target == ROOT or ROOT in target.parents:
        raise ValueError("R8_BATCH04_RECEIPT_MUST_BE_OUTSIDE_REPO_ON_G")
    receipt = ingest(artifact_root, tuple(args.days),source_manifest=args.source_manifest)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
