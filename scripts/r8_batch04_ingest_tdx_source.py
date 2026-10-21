"""Idempotently ingest verified R8 batch-04 TDX target bars into dev PG."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "v4_r8_batch04_source_ingress"
DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20", "2026-10-21")
HEADS = (ROOT / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json",
         ROOT / "data/v4/V4_DATA_ACCEPTED_HEAD.json")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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


def _load_days(artifact_root: Path, days: tuple[str, ...] = DATES) -> list[dict]:
    rows = []
    if not days or tuple(days) != tuple(sorted(set(days))):
        raise ValueError("R8_BATCH04_DATES_MUST_BE_NONEMPTY_UNIQUE_AND_IN_ORDER")
    if any(day not in DATES for day in days):
        raise ValueError("R8_BATCH04_UNDECLARED_TARGET_SESSION")
    for day in days:
        matches = list((artifact_root / "tdx_targets" / day).glob("*/*.json"))
        if len(matches) != 1:
            raise ValueError(f"R8_BATCH04_TARGET_ARTIFACT_COUNT:{day}:{len(matches)}")
        path = matches[0].resolve()
        if artifact_root.resolve() not in path.parents:
            raise ValueError("R8_BATCH04_TARGET_ARTIFACT_ESCAPES_TEMP_ROOT")
        raw = path.read_bytes()
        document = json.loads(raw)
        if (document.get("target_session") != day or document.get("status") != "TARGET_BARS_EXTRACTED" or
                document.get("provider_package_date") != "2026-10-21" or
                document.get("row_count") != len(document.get("target_bars", [])) or
                document.get("row_count", 0) <= 0 or document.get("tdx_root_write_count") != 0):
            raise ValueError(f"R8_BATCH04_TARGET_ARTIFACT_INVALID:{day}")
        source_sha = document.get("source_sha256")
        if not isinstance(source_sha, str) or len(source_sha) != 64:
            raise ValueError(f"R8_BATCH04_SOURCE_SHA_INVALID:{day}")
        codes = [row.get("source_security_key") for row in document["target_bars"]]
        if any(not code for code in codes) or len(codes) != len(set(codes)):
            raise ValueError(f"R8_BATCH04_TARGET_CODES_INVALID:{day}")
        rows.append(dict(day=day, document=document, artifact_path=str(path),
                         artifact_sha256=_sha(raw), artifact_bytes=len(raw)))
    return rows


def ingest(artifact_root: Path, days: tuple[str, ...] = DATES) -> dict:
    days = _load_days(artifact_root, days)
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
                "POST_CLOSE_LATE_CAPTURE" if day == "2026-10-21" else "RECONSTRUCTED_FROM_LATER_PACKAGE",
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
        return dict(contract_id="R8_BATCH04_TDX_PG_SOURCE_INGRESS_R1", status="SOURCE_INGRESS_READBACK_PASS",
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--days", nargs="+", choices=DATES, default=DATES)
    args = parser.parse_args()
    artifact_root = args.artifact_root.resolve()
    temp_root = Path("G:/codex_tmp").resolve()
    if artifact_root != temp_root and temp_root not in artifact_root.parents:
        raise ValueError("R8_BATCH04_ARTIFACT_ROOT_MUST_BE_G_CODEX_TMP")
    receipt = ingest(artifact_root, tuple(args.days))
    target = args.receipt.resolve()
    if target.drive.upper() != "G:" or target == ROOT or ROOT in target.parents:
        raise ValueError("R8_BATCH04_RECEIPT_MUST_BE_OUTSIDE_REPO_ON_G")
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
