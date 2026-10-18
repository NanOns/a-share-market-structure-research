"""Versioned first-ingress and PG-only reads for bounded historical V4 inputs."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from datetime import datetime, timezone
from contextlib import contextmanager

import psycopg
from psycopg import sql

from . import v4_native
from .v4_forward_pg_r1 import ForwardFactStore, canonical, digest

CONTRACT = "V4_HISTORICAL_SOURCE_INGRESS_PG_R1"
VERSION = "1.1.0"
LEGACY_VERSIONS = {"1.0.0", VERSION}
# Inline JSON/base64 is suitable only for small exact-byte sources. Large
# archives must use the typed package/member ingest path, which stores the
# verified package identity and normalized members without a 4/3-size copy.
MAX_INLINE_SOURCE_BYTES = 64 * 1024 * 1024
KIND = "historical_source_ingress"
FOLDER = "data/v4/historical_source_ingress_pg_r1"
PACKAGE_CONTRACT = "V4_HISTORICAL_SOURCE_PACKAGE_INGRESS_PG_R1"
PACKAGE_VERSION = "1.0.0"
PACKAGE_KIND = "source_package_manifest"
PACKAGE_CHUNK_KIND = "source_package_chunk"
PACKAGE_CHUNK_BYTES = 32 * 1024 * 1024


def source_id_for_path(source_path: str) -> str:
    normalized = Path(source_path).as_posix()
    if not normalized or normalized.startswith("/") or ".." in Path(normalized).parts:
        raise ValueError("HISTORICAL_SOURCE_ID_PATH_INVALID")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _root(root: str | Path) -> Path:
    project = Path(root).resolve()
    folder = (project / FOLDER).resolve()
    if project.drive.upper() != "G:" or not folder.is_relative_to(project):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_G_ROOT_REQUIRED")
    return project


@contextmanager
def _same_instance_read(schema: str):
    """Read on the shared configured PG role inside an explicit read-only transaction."""
    dsn = v4_native.configured_reader_dsn()
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        pg.execute("SET LOCAL statement_timeout='30s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute(sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(sql.Identifier(schema)))
        v4_native.attest_read_role(pg, schema)
        yield pg


def ingest_file(root: str | Path, source_id: str, source_path: str | Path, *,
                expected_sha256: str | None = None, store: ForwardFactStore | None = None) -> dict[str, Any]:
    """Import one explicitly selected historical/source input as immutable PG fact."""
    project = _root(root)
    path = Path(source_path).resolve()
    if not path.is_relative_to(project) or not path.is_file():
        raise ValueError("HISTORICAL_SOURCE_INGRESS_PATH_INVALID")
    relative = path.relative_to(project).as_posix()
    if path.stat().st_size > MAX_INLINE_SOURCE_BYTES:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_INLINE_SIZE_LIMIT_EXCEEDED")
    raw = path.read_bytes()
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        # Git LFS keeps some historical evidence as a small pointer in the
        # checkout. At a source-ingress boundary only, resolve the exact LFS
        # object from Git's local object cache; never ingest the pointer bytes
        # or let a downstream PG reader consult the workspace.
        try:
            pointer = raw.decode("ascii").splitlines()
        except UnicodeDecodeError:
            pointer = []
        oid = next((line.removeprefix("oid sha256:") for line in pointer
                    if line.startswith("oid sha256:")), None)
        declared_size = next((int(line.removeprefix("size ")) for line in pointer
                              if line.startswith("size ") and line.removeprefix("size ").isdigit()), None)
        if (not pointer or oid != expected_sha256 or declared_size is None):
            raise ValueError("HISTORICAL_SOURCE_INGRESS_DIGEST_MISMATCH")
        object_path = project / ".git" / "lfs" / "objects" / oid[:2] / oid[2:4] / oid
        if not object_path.is_file():
            raise ValueError("HISTORICAL_SOURCE_INGRESS_LFS_OBJECT_UNAVAILABLE")
        if declared_size > MAX_INLINE_SOURCE_BYTES:
            raise ValueError("HISTORICAL_SOURCE_INGRESS_INLINE_SIZE_LIMIT_EXCEEDED")
        raw = object_path.read_bytes()
        if len(raw) != declared_size or hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("HISTORICAL_SOURCE_INGRESS_LFS_OBJECT_IDENTITY_MISMATCH")
    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and sha != expected_sha256:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_DIGEST_MISMATCH")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    # PostgreSQL json/jsonb text rejects U+0000. Keep such native/source bytes
    # losslessly in the base64 field and omit the optional text projection.
    if text is not None and "\x00" in text:
        text = None
    if text is not None:
        try:
            decoded: Any = json.loads(text)
        except ValueError:
            decoded = None
    else:
        decoded = None
    record = {
        "contract_id": CONTRACT,
        "contract_version": VERSION,
        "source_id": source_id,
        "source_path": relative,
        "source_sha256": sha,
        "source_bytes": len(raw),
        "source_raw_base64": base64.b64encode(raw).decode("ascii"),
        "source_text_utf8": text,
        "source_json": decoded,
        "first_ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    key = digest(canonical({"contract_id": CONTRACT, "source_id": source_id, "source_sha256": sha}))
    target = store or ForwardFactStore(project, FOLDER)
    try:
        existing = read_bound(project, relative, sha)
    except ValueError as exc:
        if str(exc) != "HISTORICAL_SOURCE_INGRESS_NOT_FOUND":
            raise
    else:
        if existing["raw"] != raw or existing["record"].get("source_id") != source_id:
            raise ValueError("HISTORICAL_SOURCE_INGRESS_IDENTITY_CONFLICT")
        return {"status": "ALREADY_PRESENT", "source_id": source_id,
                "source_path": relative, "source_sha256": sha,
                "source_bytes": len(raw), "binding": None}
    binding = target.append(KIND, key, record, migration_timeout_seconds=120)
    actual = read_bound(project, relative, sha)
    if actual["raw"] != raw:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_READBACK_MISMATCH")
    return {"status": "INGESTED_OR_ALREADY_PRESENT", "source_id": source_id,
            "source_path": relative, "source_sha256": sha, "source_bytes": len(raw),
            "binding": binding}


def ingest_git_revision(root: str | Path, source_path: str, raw: bytes, *,
                        source_revision: str, expected_sha256: str,
                        store: ForwardFactStore | None = None) -> dict[str, Any]:
    """Ingest an exact Git revision when a Head binds an older code/config blob.

    This is an explicit source-ingress operation. Consumers still select only
    the path+digest fact from PostgreSQL and never consult Git/workspace as a
    read fallback.
    """
    project=_root(root);relative=Path(source_path).as_posix()
    source_id=source_id_for_path(relative)
    match=re.fullmatch(r"git:([0-9a-f]{40,64}):(.+)",source_revision or "")
    if (match is None or Path(match.group(2)).as_posix()!=relative
            or hashlib.sha256(raw).hexdigest()!=expected_sha256):
        raise ValueError("HISTORICAL_SOURCE_GIT_REVISION_BINDING_INVALID")
    try:
        revision_bytes=subprocess.check_output(
            ["git","show",f"{match.group(1)}:{relative}"],cwd=project,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError("HISTORICAL_SOURCE_GIT_OBJECT_UNAVAILABLE") from exc
    if revision_bytes!=raw:
        raise ValueError("HISTORICAL_SOURCE_GIT_BLOB_MISMATCH")
    try:
        existing=read_bound(project,relative,expected_sha256)
    except ValueError as exc:
        if str(exc)!="HISTORICAL_SOURCE_INGRESS_NOT_FOUND":raise
        existing=None
    if existing is not None:
        if existing["raw"]!=raw:raise ValueError("HISTORICAL_SOURCE_INGRESS_IDENTITY_CONFLICT")
        return {"status":"ALREADY_PRESENT","source_path":relative,
                "source_sha256":expected_sha256,"source_bytes":len(raw),"binding":None}
    try:text=raw.decode("utf-8")
    except UnicodeDecodeError:text=None
    if text is not None and "\x00" in text:text=None
    try:decoded=json.loads(text) if text is not None else None
    except ValueError:decoded=None
    record={"contract_id":CONTRACT,"contract_version":VERSION,
            "source_id":source_id,"source_path":relative,
            "source_sha256":expected_sha256,"source_bytes":len(raw),
            "source_raw_base64":base64.b64encode(raw).decode("ascii"),
            "source_text_utf8":text,"source_json":decoded,
            "source_revision":source_revision,
            "first_ingested_at":datetime.now(timezone.utc).isoformat()}
    key=digest(canonical({"contract_id":CONTRACT,"source_id":record["source_id"],
                         "source_sha256":expected_sha256}))
    target=store or ForwardFactStore(project,FOLDER)
    binding=target.append(KIND,key,record,migration_timeout_seconds=120)
    actual=read_bound(project,relative,expected_sha256)
    if actual["raw"]!=raw:raise ValueError("HISTORICAL_SOURCE_INGRESS_READBACK_MISMATCH")
    return {"status":"INGESTED_OR_ALREADY_PRESENT","source_path":relative,
            "source_sha256":expected_sha256,"source_bytes":len(raw),"binding":binding}


def ingest_captured_bytes(root: str | Path, source_path: str, raw: bytes, *,
                          source_revision: str, source_origin: str) -> dict[str, Any]:
    """Append exact bytes captured at an explicitly declared external boundary."""
    project=_root(root);relative=Path(source_path).as_posix()
    if len(raw) > MAX_INLINE_SOURCE_BYTES:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_INLINE_SIZE_LIMIT_EXCEEDED")
    if (not isinstance(source_origin,str) or not source_origin.strip()
            or not isinstance(source_revision,str) or not source_revision.strip()):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_PROVENANCE_REQUIRED")
    source_id=source_id_for_path(relative);sha=hashlib.sha256(raw).hexdigest()
    try:existing=read_bound(project,relative,sha)
    except ValueError as exc:
        if str(exc)!="HISTORICAL_SOURCE_INGRESS_NOT_FOUND":raise
        existing=None
    if existing is not None:
        if existing["raw"]!=raw:raise ValueError("HISTORICAL_SOURCE_INGRESS_IDENTITY_CONFLICT")
        return {"status":"ALREADY_PRESENT","source_path":relative,
                "source_sha256":sha,"source_bytes":len(raw),"binding":None}
    try:text=raw.decode("utf-8")
    except UnicodeDecodeError:text=None
    if text is not None and "\x00" in text:text=None
    try:decoded=json.loads(text) if text is not None else None
    except ValueError:decoded=None
    record={"contract_id":CONTRACT,"contract_version":VERSION,
            "source_id":source_id,"source_path":relative,"source_sha256":sha,
            "source_bytes":len(raw),"source_raw_base64":base64.b64encode(raw).decode("ascii"),
            "source_text_utf8":text,"source_json":decoded,"source_revision":source_revision,
            "source_origin":source_origin,"first_ingested_at":datetime.now(timezone.utc).isoformat()}
    key=digest(canonical({"contract_id":CONTRACT,"source_id":source_id,"source_sha256":sha}))
    target=ForwardFactStore(project,FOLDER);binding=target.append(KIND,key,record,migration_timeout_seconds=120)
    actual=read_bound(project,relative,sha)
    if actual["raw"]!=raw:raise ValueError("HISTORICAL_SOURCE_INGRESS_READBACK_MISMATCH")
    return {"status":"INGESTED_OR_ALREADY_PRESENT","source_path":relative,
            "source_sha256":sha,"source_bytes":len(raw),"binding":binding}


def ingest_package_bytes(root: str | Path, source_path: str, raw: bytes, *,
                         expected_sha256: str, source_revision: str,
                         source_origin: str, chunk_bytes: int = PACKAGE_CHUNK_BYTES) -> dict[str, Any]:
    """Append a large exact package to PG in bounded immutable byte chunks."""
    project=_root(root);relative=Path(source_path).as_posix()
    source_id=source_id_for_path(relative)
    if (not isinstance(raw,(bytes,bytearray,memoryview)) or len(raw)<=MAX_INLINE_SOURCE_BYTES
            or len(raw)>2*1024*1024*1024 or not isinstance(expected_sha256,str)
            or not re.fullmatch(r"[0-9a-f]{64}",expected_sha256)
            or not isinstance(source_revision,str) or not source_revision.strip()
            or not isinstance(source_origin,str) or not source_origin.strip()
            or type(chunk_bytes) is not int or not 1024*1024<=chunk_bytes<=PACKAGE_CHUNK_BYTES):
        raise ValueError("HISTORICAL_SOURCE_PACKAGE_INGRESS_ARGUMENT_INVALID")
    total=len(raw);sha=hashlib.sha256(raw).hexdigest()
    if sha!=expected_sha256:
        raise ValueError("HISTORICAL_SOURCE_PACKAGE_DIGEST_MISMATCH")
    chunks=(total+chunk_bytes-1)//chunk_bytes
    project_root=Path(project).resolve();folder=(project_root/FOLDER).resolve()
    target=ForwardFactStore.__new__(ForwardFactStore)
    target.root=project_root;target.folder=folder
    target.schema=v4_native.workspace_schema(folder,"forward")
    target.dsn=v4_native.configured_dsn()
    target.database_identity=None
    with v4_native.connection(target.schema,dsn=target.dsn) as pg:
        pg.execute("SELECT set_config('statement_timeout','120s',true)")
        relation=pg.execute("SELECT to_regclass('forward_facts')").fetchone()
        if not relation or relation[0] is None:
            raise ValueError("HISTORICAL_SOURCE_PACKAGE_STORE_NOT_PROVISIONED")
        target.database_identity=ForwardFactStore._database_identity(pg)
        chunk_refs=[]
        for index,start in enumerate(range(0,total,chunk_bytes)):
            piece=bytes(raw[start:min(start+chunk_bytes,total)])
            chunk_sha=hashlib.sha256(piece).hexdigest()
            record={"contract_id":PACKAGE_CONTRACT,"contract_version":PACKAGE_VERSION,
                "source_id":source_id,"source_path":relative,"source_sha256":sha,
                "source_bytes":total,"source_revision":source_revision,"source_origin":source_origin,
                "chunk_index":index,"chunk_count":chunks,"chunk_sha256":chunk_sha,
                "chunk_bytes":len(piece),"chunk_raw_base64":base64.b64encode(piece).decode("ascii")}
            key=digest(canonical({"contract_id":PACKAGE_CONTRACT,"source_id":source_id,
                "source_sha256":sha,"chunk_index":index}))
            payload=canonical(record);payload_sha=digest(payload)
            pg.execute("INSERT INTO forward_facts(kind,fact_key,payload,payload_sha256,source_sha256) "
                "VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (PACKAGE_CHUNK_KIND,key,payload.decode("utf-8"),payload_sha,sha))
            existing=pg.execute("SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s",
                (PACKAGE_CHUNK_KIND,key)).fetchone()
            if existing!=(payload.decode("utf-8"),payload_sha):
                raise ValueError("HISTORICAL_SOURCE_PACKAGE_CHUNK_CONFLICT")
            chunk_refs.append({"fact_key":key,"payload_sha256":payload_sha,
                "chunk_sha256":chunk_sha,"chunk_bytes":len(piece)})
        manifest={"contract_id":PACKAGE_CONTRACT,"contract_version":PACKAGE_VERSION,
            "source_id":source_id,"source_path":relative,"source_sha256":sha,
            "source_bytes":total,"source_revision":source_revision,"source_origin":source_origin,
            "chunk_bytes":chunk_bytes,"chunk_count":chunks,"chunks":chunk_refs,
            "first_ingested_at":datetime.now(timezone.utc).isoformat()}
        manifest_key=digest(canonical({"contract_id":PACKAGE_CONTRACT,"source_id":source_id,"source_sha256":sha}))
        manifest_payload=canonical(manifest);manifest_sha=digest(manifest_payload)
        pg.execute("INSERT INTO forward_facts(kind,fact_key,payload,payload_sha256,source_sha256) "
            "VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (PACKAGE_KIND,manifest_key,manifest_payload.decode("utf-8"),manifest_sha,sha))
        existing=pg.execute("SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s",
            (PACKAGE_KIND,manifest_key)).fetchone()
        if existing!=(manifest_payload.decode("utf-8"),manifest_sha):
            raise ValueError("HISTORICAL_SOURCE_PACKAGE_MANIFEST_CONFLICT")
    binding=target._binding(PACKAGE_KIND,manifest_key,manifest_sha)
    return {"status":"INGESTED_OR_ALREADY_PRESENT","source_path":relative,
        "source_sha256":sha,"source_bytes":total,"chunk_count":chunks,"binding":binding}


def read_package_bytes(root: str | Path, source_path: str, expected_sha256: str) -> dict[str, Any]:
    """Read and verify a chunked large package from PG without file fallback."""
    project=_root(root);relative=Path(source_path).as_posix()
    source_id=source_id_for_path(relative)
    if not isinstance(expected_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}",expected_sha256):
        raise ValueError("HISTORICAL_SOURCE_PACKAGE_DIGEST_INVALID")
    folder=(Path(project)/FOLDER).resolve();schema=v4_native.workspace_schema(folder,"forward")
    def query(pg):
        expected={}
        try:expected=json.loads(os.environ.get("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON","{}"))
        except ValueError as exc:raise ValueError("PG_DATABASE_IDENTITY_CONFIGURATION_INVALID") from exc
        identity=ForwardFactStore._database_identity(pg)
        if expected and identity!=expected:raise ValueError("HISTORICAL_SOURCE_PACKAGE_DATABASE_IDENTITY_MISMATCH")
        rows=pg.execute("SELECT fact_key,payload,payload_sha256 FROM forward_facts WHERE kind=%s "
            "AND payload::jsonb->>'source_id'=%s AND payload::jsonb->>'source_sha256'=%s "
            "ORDER BY fact_key COLLATE \"C\" LIMIT 2",
            (PACKAGE_KIND,source_id,expected_sha256)).fetchall()
        if len(rows)!=1:
            raise ValueError("HISTORICAL_SOURCE_PACKAGE_NOT_UNIQUE" if rows else "HISTORICAL_SOURCE_PACKAGE_NOT_FOUND")
        key,payload,payload_sha=rows[0]
        if digest(payload.encode("utf-8"))!=payload_sha:raise ValueError("HISTORICAL_SOURCE_PACKAGE_MANIFEST_DIGEST_MISMATCH")
        manifest=json.loads(payload)
        if (manifest.get("contract_id")!=PACKAGE_CONTRACT or manifest.get("contract_version")!=PACKAGE_VERSION
                or manifest.get("source_path")!=relative or manifest.get("source_sha256")!=expected_sha256
                or manifest.get("source_id")!=source_id or type(manifest.get("source_bytes")) is not int
                or not isinstance(manifest.get("chunks"),list)
                or len(manifest["chunks"])!=manifest.get("chunk_count")):
            raise ValueError("HISTORICAL_SOURCE_PACKAGE_MANIFEST_INVALID")
        keys=[item.get("fact_key") for item in manifest["chunks"]]
        if any(not isinstance(value,str) for value in keys):raise ValueError("HISTORICAL_SOURCE_PACKAGE_CHUNK_LIST_INVALID")
        chunk_rows=pg.execute("SELECT fact_key,payload,payload_sha256 FROM forward_facts WHERE kind=%s "
            "AND fact_key=ANY(%s) ORDER BY fact_key COLLATE \"C\"",(PACKAGE_CHUNK_KIND,keys)).fetchall()
        if len(chunk_rows)!=len(keys):raise ValueError("HISTORICAL_SOURCE_PACKAGE_CHUNK_MISSING")
        by_key={key:(payload,payload_sha) for key,payload,payload_sha in chunk_rows}
        output=bytearray()
        for index,ref in enumerate(manifest["chunks"]):
            row=by_key.get(ref["fact_key"])
            if row is None or digest(row[0].encode("utf-8"))!=row[1] or row[1]!=ref.get("payload_sha256"):
                raise ValueError("HISTORICAL_SOURCE_PACKAGE_CHUNK_PAYLOAD_INVALID")
            chunk=json.loads(row[0])
            try:piece=base64.b64decode(chunk.get("chunk_raw_base64",""),validate=True)
            except (ValueError,TypeError) as exc:raise ValueError("HISTORICAL_SOURCE_PACKAGE_CHUNK_ENCODING_INVALID") from exc
            if (chunk.get("contract_id")!=PACKAGE_CONTRACT or chunk.get("source_id")!=source_id
                    or chunk.get("source_path")!=relative or chunk.get("source_sha256")!=expected_sha256
                    or chunk.get("chunk_index")!=index or chunk.get("chunk_count")!=manifest["chunk_count"]
                    or len(piece)!=ref.get("chunk_bytes") or digest(piece)!=ref.get("chunk_sha256")):
                raise ValueError("HISTORICAL_SOURCE_PACKAGE_CHUNK_IDENTITY_MISMATCH")
            output.extend(piece)
        raw=bytes(output)
        if len(raw)!=manifest["source_bytes"] or digest(raw)!=expected_sha256:
            raise ValueError("HISTORICAL_SOURCE_PACKAGE_READBACK_MISMATCH")
        return {"record":manifest,"raw":raw}
    active=v4_native.current_read_snapshot()
    if active is not None:return query(active)
    with _same_instance_read(schema) as pg:return query(pg)


def admit_source_binding_bytes(root: str | Path, binding: dict[str, Any], *,
                               source_origin: str) -> bytes:
    """Return exact PG-bound bytes, performing one verified file/LFS ingress if absent."""
    project=_root(root)
    if (not isinstance(binding,dict) or not isinstance(binding.get('path'),str)
            or not re.fullmatch(r'[0-9a-f]{64}',str(binding.get('sha256') or ''))
            or (binding.get('bytes') is not None and
                (type(binding.get('bytes')) is not int or binding['bytes']<1))
            or not isinstance(source_origin,str) or not source_origin.strip()):
        raise ValueError('HISTORICAL_SOURCE_BINDING_INVALID')
    relative=Path(binding['path']).as_posix();expected_sha=binding['sha256'];expected_bytes=binding.get('bytes')
    try:
        exact=read_bound(project,relative,expected_sha)
        raw=exact['raw']
    except ValueError as exc:
        if str(exc)!='HISTORICAL_SOURCE_INGRESS_NOT_FOUND':raise
        try:
            exact_package=read_package_bytes(project,relative,expected_sha)
            raw=exact_package['raw']
        except ValueError as package_exc:
            if str(package_exc)!='HISTORICAL_SOURCE_PACKAGE_NOT_FOUND':raise
            source=(project/relative).resolve()
            if not source.is_relative_to(project) or not source.is_file():
                raise ValueError('HISTORICAL_SOURCE_INGRESS_PATH_INVALID')
            raw=source.read_bytes()
            if ((expected_bytes is not None and len(raw)!=expected_bytes) or digest(raw)!=expected_sha):
                try:pointer=raw.decode('ascii').splitlines()
                except UnicodeDecodeError:pointer=[]
                oid=next((line.removeprefix('oid sha256:') for line in pointer if line.startswith('oid sha256:')),None)
                declared=next((int(line.removeprefix('size ')) for line in pointer
                               if line.startswith('size ') and line.removeprefix('size ').isdigit()),None)
                if oid!=expected_sha or (expected_bytes is not None and declared!=expected_bytes):
                    raise ValueError('HISTORICAL_SOURCE_INGRESS_DIGEST_MISMATCH')
                expected_bytes=declared
                git_dir=project/'.git'
                if git_dir.is_file():
                    marker=git_dir.read_text(encoding='utf-8').strip()
                    if not marker.lower().startswith('gitdir:'):
                        raise ValueError('HISTORICAL_SOURCE_LFS_GITDIR_INVALID')
                    git_dir=(project/marker.partition(':')[2].strip()).resolve()
                object_path=git_dir/'lfs'/'objects'/oid[:2]/oid[2:4]/oid
                if not object_path.is_file():raise ValueError('HISTORICAL_SOURCE_INGRESS_LFS_OBJECT_UNAVAILABLE')
                raw=object_path.read_bytes()
            if ((expected_bytes is not None and len(raw)!=expected_bytes) or digest(raw)!=expected_sha):
                raise ValueError('HISTORICAL_SOURCE_INGRESS_SOURCE_IDENTITY_MISMATCH')
            if len(raw)>MAX_INLINE_SOURCE_BYTES:
                ingest_package_bytes(project,relative,raw,expected_sha256=expected_sha,
                    source_revision=expected_sha,source_origin=source_origin)
                del raw
                raw=read_package_bytes(project,relative,expected_sha)['raw']
            else:
                ingest_file(project,source_id_for_path(relative),source,
                    expected_sha256=expected_sha)
                raw=read_bound(project,relative,expected_sha)['raw']
    if ((expected_bytes is not None and len(raw)!=expected_bytes) or digest(raw)!=expected_sha):
        raise ValueError('HISTORICAL_SOURCE_INGRESS_SOURCE_IDENTITY_MISMATCH')
    return raw


def _query(root: str | Path, *, source_id: str | None = None,
           source_path: str | None = None, expected_sha256: str | None = None,
           pg: Any | None = None) -> tuple[dict[str, Any], bytes]:
    project = _root(root)
    if (source_id is None) == (source_path is None):
        raise ValueError("HISTORICAL_SOURCE_SELECTOR_REQUIRED")
    folder = (project / FOLDER).resolve()
    schema = v4_native.workspace_schema(folder, "forward")
    expected = {}
    try:
        expected = json.loads(os.environ.get("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", "{}"))
    except ValueError as exc:
        raise ValueError("PG_DATABASE_IDENTITY_CONFIGURATION_INVALID") from exc
    indexed_key=None
    if expected_sha256 is not None:
        selected_id=source_id or source_id_for_path(source_path)
        indexed_key=digest(canonical({"contract_id":CONTRACT,"source_id":selected_id,
                                      "source_sha256":expected_sha256}))
    def query(connection):
        identity = ForwardFactStore._database_identity(connection)
        if expected and identity != expected:
            raise ValueError("HISTORICAL_SOURCE_INGRESS_DATABASE_IDENTITY_MISMATCH")
        if indexed_key is not None:
            indexed_statement=sql.SQL(
                "SELECT payload,payload_sha256 FROM {}.forward_facts WHERE kind=%s AND fact_key=%s"
            ).format(sql.Identifier(schema))
            return connection.execute(indexed_statement,(KIND,indexed_key)).fetchall()
        statement=sql.SQL(
            "SELECT payload,payload_sha256 FROM {}.forward_facts WHERE kind=%s "
            "AND (%s::text IS NULL OR payload::jsonb->>'source_id'=%s) "
            "AND (%s::text IS NULL OR payload::jsonb->>'source_path'=%s) "
            "AND (%s::text IS NULL OR payload::jsonb->>'source_sha256'=%s) "
            "ORDER BY fact_key COLLATE \"C\" LIMIT 2",
        ).format(sql.Identifier(schema))
        return connection.execute(statement,
            (KIND,source_id,source_id,source_path,source_path,expected_sha256,expected_sha256)).fetchall()
    if pg is None:
        from .v4_native import current_read_snapshot
        active=current_read_snapshot()
        if active is not None: rows=query(active)
        else:
            with _same_instance_read(schema) as connection:rows=query(connection)
    else:
        rows = query(pg)
    if len(rows) != 1:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE" if rows else "HISTORICAL_SOURCE_INGRESS_NOT_FOUND")
    payload_raw, payload_sha = rows[0]
    encoded = payload_raw.encode("utf-8")
    if digest(encoded) != payload_sha:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_PG_DIGEST_MISMATCH")
    record = json.loads(payload_raw)
    if (record.get("contract_id") != CONTRACT
            or record.get("contract_version") not in LEGACY_VERSIONS):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_CONTRACT_MISMATCH")
    raw = base64.b64decode(record.get("source_raw_base64", ""), validate=True)
    if (len(raw) != record.get("source_bytes")
            or hashlib.sha256(raw).hexdigest() != record.get("source_sha256")
            or record.get("source_path") != source_path and source_path is not None
            or record.get("source_id") != source_id and source_id is not None
            or record.get("source_sha256") != expected_sha256 and expected_sha256 is not None):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_SOURCE_IDENTITY_MISMATCH")
    return record, raw


def read_source(root: str | Path, source_id: str) -> dict[str, Any]:
    """Resolve a uniquely imported historical source by stable source ID; no disk fallback."""
    record, raw = _query(root, source_id=source_id)
    text = record.get("source_text_utf8")
    if text is None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return {"record": record, "raw": raw, "value": record.get("source_json"),
            "text": text}


def read_latest_candidate_path(root: str | Path, source_path: str | Path, *,
                               source_origin: str | tuple[str, ...]) -> dict[str, Any]:
    """Resolve the latest immutable revision for an explicitly named DEV producer set."""
    project=_root(root);relative=Path(source_path).as_posix()
    origins=[source_origin] if isinstance(source_origin,str) else list(source_origin) if isinstance(source_origin,tuple) else []
    if (not origins or len(origins)>4 or len(set(origins))!=len(origins)
            or any(not isinstance(origin,str) or not origin.startswith('V4_') or not origin.endswith('_CANDIDATE_OUTPUT') for origin in origins)):
        raise ValueError('HISTORICAL_SOURCE_CANDIDATE_ORIGIN_INVALID')
    folder=(Path(project)/FOLDER).resolve();schema=v4_native.workspace_schema(folder,'forward')
    def query(pg):
        expected={}
        try:expected=json.loads(os.environ.get('V4_PG_EXPECTED_DATABASE_IDENTITY_JSON','{}'))
        except ValueError as exc:raise ValueError('PG_DATABASE_IDENTITY_CONFIGURATION_INVALID') from exc
        identity=ForwardFactStore._database_identity(pg)
        if expected and identity!=expected:raise ValueError('HISTORICAL_SOURCE_INGRESS_DATABASE_IDENTITY_MISMATCH')
        rows=pg.execute(sql.SQL(
            "SELECT payload,payload_sha256 FROM {}.forward_facts WHERE kind=%s "
            "AND payload::jsonb->>'source_path'=%s AND payload::jsonb->>'source_origin'=ANY(%s) "
            "ORDER BY (payload::jsonb->>'first_ingested_at')::timestamptz DESC, "
            "payload::jsonb->>'source_sha256' DESC LIMIT 2"
        ).format(sql.Identifier(schema)),(KIND,relative,origins)).fetchall()
        if not rows:raise ValueError('HISTORICAL_SOURCE_INGRESS_NOT_FOUND')
        payload,payload_sha=rows[0];encoded=payload.encode('utf-8')
        if digest(encoded)!=payload_sha:raise ValueError('HISTORICAL_SOURCE_INGRESS_PG_DIGEST_MISMATCH')
        record=json.loads(payload)
        if (record.get('contract_id')!=CONTRACT or record.get('contract_version') not in LEGACY_VERSIONS
                or record.get('source_path')!=relative or record.get('source_origin') not in origins
                or not re.fullmatch(r'[0-9a-f]{64}',str(record.get('source_sha256') or ''))):
            raise ValueError('HISTORICAL_SOURCE_INGRESS_CANDIDATE_BINDING_INVALID')
        if len(rows)>1:
            prior=json.loads(rows[1][0])
            if prior.get('first_ingested_at')==record.get('first_ingested_at'):
                raise ValueError('HISTORICAL_SOURCE_INGRESS_CANDIDATE_REVISION_TIE')
        selected_record,raw=_query(project,source_path=relative,
            expected_sha256=record['source_sha256'],pg=pg)
        return {'record':selected_record,'raw':raw,'value':selected_record.get('source_json'),
                'text':selected_record.get('source_text_utf8')}
    active=v4_native.current_read_snapshot()
    if active is not None:return query(active)
    with _same_instance_read(schema) as pg:return query(pg)


class PGSourceBytes(io.BytesIO):
    """Exact PG-bound source exposed as an in-memory, seekable file object."""

    def __init__(self, source: dict[str, Any], root: str | Path):
        super().__init__(source["raw"])
        self.source_path = (Path(root).resolve() / PurePosixPath(source["record"]["source_path"])).resolve()
        self.sha256 = source["record"]["source_sha256"]

    @property
    def name(self) -> str:
        return self.source_path.name

    @property
    def suffix(self) -> str:
        return self.source_path.suffix

    @property
    def parent(self) -> Path:
        return self.source_path.parent

    def read_bytes(self) -> bytes:
        return self.getvalue()

    def read_text(self, encoding: str = "utf-8", errors: str | None = None) -> str:
        return self.getvalue().decode(encoding, errors or "strict")

    def open(self, mode: str = "rb", *, encoding: str = "utf-8", errors: str | None = None):
        if mode not in {"rb", "r", "rt"}:
            raise ValueError("PG_BOUND_SOURCE_IS_READ_ONLY")
        stream = io.BytesIO(self.getvalue())
        return stream if "b" in mode else io.TextIOWrapper(stream, encoding=encoding, errors=errors)

    def exists(self) -> bool:
        return True

    def is_file(self) -> bool:
        return True

    def resolve(self, *args, **kwargs) -> Path:
        return self.source_path

    def stat(self):
        return type("PGSourceStat", (), {"st_size": len(self.getvalue())})()

    def __fspath__(self) -> str:
        raise TypeError("PG_BOUND_SOURCE_HAS_NO_FILESYSTEM_PATH")


def bound_bytes(root: str | Path, binding: dict[str, Any]) -> PGSourceBytes:
    """Read an exact imported source from PG without creating a workspace file."""
    return PGSourceBytes(read_bound(root, str(binding.get("path") or ""), str(binding.get("sha256") or "")), root)


def read_path_bytes(root: str | Path, source_path: str, *, expected_sha256: str | None = None) -> PGSourceBytes:
    """Read one PG-ingressed path revision directly into memory."""
    source = (read_bound(root, source_path, expected_sha256)
              if expected_sha256 is not None else read_path(root, source_path))
    return PGSourceBytes(source, root)


def materialize_bound(root: str | Path, binding: dict[str, Any]) -> PGSourceBytes:
    """Compatibility name; PG sources are now returned in memory, never materialized."""
    return bound_bytes(root, binding)


def read_bound(root: str | Path, source_path: str, expected_sha256: str) -> dict[str, Any]:
    """Resolve exact historical bytes from PG using the original path and digest binding."""
    record, raw = _query(root, source_path=source_path, expected_sha256=expected_sha256)
    text = record.get("source_text_utf8")
    if text is None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return {"record": record, "raw": raw, "value": record.get("source_json"),
            "text": text}


def admit_bound(root: str | Path, binding: dict[str, Any]) -> dict[str, Any]:
    """Admit one explicitly bound project source once, then return PG bytes.

    This is an ingress operation, not a read fallback: path and SHA-256 come
    from the caller's frozen source binding, the first append is immutable,
    and every returned value is read back from the shared PostgreSQL store.
    """
    project = _root(root)
    relative = binding.get("path")
    expected = binding.get("sha256")
    if (not isinstance(relative, str) or not relative
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_EXACT_BINDING_REQUIRED")
    try:
        admitted = read_bound(project, relative, expected)
    except ValueError as exc:
        if str(exc) != "HISTORICAL_SOURCE_INGRESS_NOT_FOUND":
            raise
        admitted = None
    if admitted is None:
        path = (project / relative).resolve()
        if not path.is_relative_to(project) or not path.is_file():
            raise ValueError("HISTORICAL_SOURCE_INGRESS_PATH_UNAVAILABLE")
        result = ingest_file(project, source_id_for_path(relative), path,
                             expected_sha256=expected)
        admitted = read_bound(project, relative, expected)
        if len(admitted["raw"]) != result["source_bytes"]:
            raise ValueError("HISTORICAL_SOURCE_INGRESS_SIZE_MISMATCH")
    declared_bytes = binding.get("bytes")
    if declared_bytes is not None and len(admitted["raw"]) != declared_bytes:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_BOUND_SIZE_MISMATCH")
    return admitted


def read_bound_many(root: str | Path, bindings: list[dict[str, Any]]) -> list[dict[str, Any] | None]:
    """Resolve exact bindings under one read-only repeatable-read PG snapshot."""
    project = _root(root)
    folder = (project / FOLDER).resolve()
    schema = v4_native.workspace_schema(folder, "forward")
    results: list[dict[str, Any] | None] = []
    with _same_instance_read(schema) as pg:
        for binding in bindings:
            if not isinstance(binding, dict):
                results.append(None)
                continue
            source_path = binding.get("path")
            expected_sha256 = binding.get("sha256")
            if (not isinstance(source_path, str) or not source_path
                    or not isinstance(expected_sha256, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
                results.append(None)
                continue
            try:
                record, raw = _query(project, source_path=source_path,
                                     expected_sha256=expected_sha256, pg=pg)
            except ValueError:
                results.append(None)
                continue
            text = record.get("source_text_utf8")
            if text is None:
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    pass
            results.append({"record": record, "raw": raw,
                            "value": record.get("source_json"), "text": text})
    return results


def read_path(root: str | Path, source_path: str) -> dict[str, Any]:
    """Resolve one immutable imported revision by relative source path; no disk fallback."""
    record, raw = _query(root, source_path=source_path)
    text = record.get("source_text_utf8")
    if text is None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return {"record": record, "raw": raw, "value": record.get("source_json"),
            "text": text}


def ingress_path(root: str | Path, source_path: str, *, expected_sha256: str | None = None) -> dict[str, Any]:
    """Resolve a PG source fact, admitting the exact project input once when absent."""
    project = _root(root)
    relative = Path(source_path).as_posix()
    try:
        if expected_sha256:
            return read_bound(project, relative, expected_sha256)
        return read_path(project, relative)
    except ValueError as exc:
        if str(exc) not in {"HISTORICAL_SOURCE_INGRESS_NOT_FOUND", "HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE"}:
            raise
    path = (project / relative).resolve()
    if not path.is_relative_to(project) or not path.is_file():
        raise ValueError("HISTORICAL_SOURCE_INGRESS_PATH_UNAVAILABLE")
    result = ingest_file(project, source_id_for_path(relative), path, expected_sha256=expected_sha256)
    return read_bound(project, relative, result["source_sha256"])


def materialize_path(root: str | Path, source_path: str, *, expected_sha256: str | None = None) -> PGSourceBytes:
    """Compatibility name; return existing PG-ingressed bytes without writing a file."""
    project = _root(root)
    source = (read_bound(project, source_path, expected_sha256)
              if expected_sha256 is not None else read_path(project, source_path))
    return PGSourceBytes(source, project)
