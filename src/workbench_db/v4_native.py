"""Native PG V4 candidate connections: explicit configuration, no fallback."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import os
from pathlib import Path
import re
import configparser
import psycopg
from psycopg import sql

CONTRACT = 'V4_NATIVE_POSTGRESQL_CONNECTION_R5'
_SCHEMA = re.compile(r'(?:v4|v4_[a-z0-9_]{1,56})')
_READ_SNAPSHOT = ContextVar('v4_read_snapshot_connection',default=None)
_WORKSPACE_SCHEMA_CACHE = {}

@contextmanager
def bind_read_snapshot(pg):
    """Share one caller-owned RR/RO connection across nested V4 readers."""
    token=_READ_SNAPSHOT.set(pg)
    try:yield pg
    finally:_READ_SNAPSHOT.reset(token)

def current_read_snapshot():
    return _READ_SNAPSHOT.get()

def configured_dsn():
    # Prefer a dedicated V4 name when present, but the current authorized
    # development connection may serve both explicit writes and RO reads.
    # PostgreSQL privileges remain authoritative; read paths still set RO.
    value=os.environ.get('V4_NATIVE_PG_DSN')
    if value:
        return value
    # Entry points which do not load dotenv may use the explicitly named V4
    # writer setting from project configuration. Never print or copy secrets.
    project_root=Path(__file__).resolve().parents[2]
    for env_path in (project_root/'config/.env', project_root/'.env'):
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding='utf-8-sig').splitlines():
            key,sep,configured=raw.partition('=')
            if sep and key.strip() == 'V4_NATIVE_PG_DSN':
                configured=configured.strip().strip('"').strip("'")
                if configured:
                    return configured
    try:
        return configured_reader_dsn()
    except RuntimeError as exc:
        raise RuntimeError('WORKBENCH_PG_DSN_REQUIRED') from exc

def configured_reader_dsn():
    """Reuse the project's existing shared DSN; no separate reader instance."""
    value=os.environ.get('WORKBENCH_PG_DSN')
    if value:
        return value
    project_root=Path(__file__).resolve().parents[2]
    for env_path in (project_root/'config/.env', project_root/'.env'):
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding='utf-8-sig').splitlines():
            key,sep,configured=raw.partition('=')
            if sep and key.strip()=='WORKBENCH_PG_DSN':
                configured=configured.strip().strip('"').strip("'")
                if configured:
                    return configured
    raise RuntimeError('WORKBENCH_PG_DSN_REQUIRED')

def _legacy_workspace_schema(root, purpose):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,24}',purpose): raise ValueError('INVALID_PG_PURPOSE')
    return 'v4_'+purpose+'_'+hashlib.sha256(str(Path(root).resolve()).casefold().encode()).hexdigest()[:16]

def _resolve_workspace_schema_alias(root, purpose):
    """Resolve a moved Git workspace to its existing PG namespace, if registered."""
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,24}',purpose): raise ValueError('INVALID_PG_PURPOSE')
    path=Path(root).resolve()
    if not any((candidate/'.git').exists() for candidate in (path,*path.parents)):
        return None
    logical_id=workspace_logical_id(path)
    dsn=configured_reader_dsn()
    cache_key=(hashlib.sha256(dsn.encode()).hexdigest(),logical_id,purpose)
    if cache_key in _WORKSPACE_SCHEMA_CACHE:
        return _WORKSPACE_SCHEMA_CACHE[cache_key]
    # Namespace lookup is deliberately read-only and path-free. An absent table
    # means this deployment has not applied migration 046 yet, so legacy
    # root-bound namespaces remain readable during the one-time transition.
    try:
        with psycopg.connect(dsn,connect_timeout=5) as pg:
            pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            pg.execute("SET LOCAL statement_timeout='5s'")
            row=pg.execute(
                "SELECT physical_schema,status FROM v4.workspace_namespace_aliases_r1 "
                "WHERE logical_workspace_id=%s AND purpose=%s",
                (logical_id,purpose),
            ).fetchone()
    except psycopg.errors.UndefinedTable:
        row=None
    if row is None:
        _WORKSPACE_SCHEMA_CACHE[cache_key]=None
        return None
    schema,status=row
    if status!='ACTIVE' or not isinstance(schema,str) or not _SCHEMA.fullmatch(schema):
        raise RuntimeError('V4_WORKSPACE_NAMESPACE_ALIAS_INVALID')
    _WORKSPACE_SCHEMA_CACHE[cache_key]=schema
    return schema

def workspace_schema(root, purpose):
    legacy=_legacy_workspace_schema(root,purpose)
    alias=_resolve_workspace_schema_alias(root,purpose)
    return alias or legacy

def register_workspace_schema_alias(pg, root, purpose, *, physical_schema=None):
    """Bind a stable workspace key to an existing schema without moving data."""
    legacy=_legacy_workspace_schema(root,purpose)
    schema=physical_schema or legacy
    if not _SCHEMA.fullmatch(schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    logical_id=workspace_logical_id(root)
    root_identity=hashlib.sha256(str(Path(root).resolve()).casefold().encode()).hexdigest()
    exists=pg.execute('SELECT to_regnamespace(%s)',(schema,)).fetchone()
    if not exists or exists[0] is None: raise RuntimeError('V4_WORKSPACE_ALIAS_TARGET_SCHEMA_MISSING')
    pg.execute(
        "INSERT INTO v4.workspace_namespace_aliases_r1 "
        "(logical_workspace_id,purpose,physical_schema,source_root_identity_sha256) "
        "VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (logical_id,purpose,schema,root_identity),
    )
    row=pg.execute(
        "SELECT physical_schema,source_root_identity_sha256,status "
        "FROM v4.workspace_namespace_aliases_r1 WHERE logical_workspace_id=%s AND purpose=%s",
        (logical_id,purpose),
    ).fetchone()
    if row!=(schema,root_identity,'ACTIVE'):
        raise RuntimeError('V4_WORKSPACE_NAMESPACE_ALIAS_CONFLICT')
    _WORKSPACE_SCHEMA_CACHE.clear()
    return {'logical_workspace_id':logical_id,'purpose':purpose,'physical_schema':schema,
            'source_root_identity_sha256':root_identity,'status':'ACTIVE'}

def workspace_logical_id(root):
    """Return a location-independent project/workspace key for alias migration.

    Existing physical schemas remain root-bound until an explicit PG alias is
    registered.  This stable key gives that migration an identity which can be
    resolved after the checkout moves to another drive or machine.
    """
    path = Path(root).resolve()
    for repo_root in (path, *path.parents):
        marker = repo_root / '.git'
        if not marker.exists():
            continue
        git_dir = marker
        if marker.is_file():
            match = re.match(r'^gitdir:\s*(.+?)\s*$', marker.read_text(encoding='utf-8').strip(), re.I)
            if not match:
                continue
            git_dir = (repo_root / match.group(1)).resolve()
        config_path = git_dir / 'config'
        if not config_path.is_file():
            common = git_dir / 'commondir'
            if common.is_file():
                config_path = (git_dir / common.read_text(encoding='utf-8').strip() / 'config').resolve()
        if not config_path.is_file():
            continue
        config = configparser.ConfigParser()
        try:
            config.read(config_path, encoding='utf-8')
            remote = config.get('remote "origin"', 'url', fallback='').strip()
        except (configparser.Error, OSError):
            remote = ''
        if not remote:
            continue
        # Normalize the public repository identity without retaining credentials
        # or exposing a remote URL in the workspace identity.
        remote = re.sub(r'\.git$', '', remote, flags=re.I)
        if '://' in remote:
            from urllib.parse import urlsplit
            parsed = urlsplit(remote)
            remote = f'{parsed.scheme.casefold()}://{parsed.hostname or ""}{parsed.path}'.casefold().rstrip('/')
        else:
            remote = re.sub(r'^[^@]+@', '', remote).casefold().replace(':', '/', 1).rstrip('/')
        relative = path.relative_to(repo_root).as_posix().casefold() or '.'
        material = f'git-origin:{remote}|workspace:{relative}'
        return 'v4w_' + hashlib.sha256(material.encode()).hexdigest()[:32]
    # Preserve useful root separation for temporary or non-Git workspaces.
    canonical_root = str(path).casefold()
    return 'v4w_' + hashlib.sha256(f'local-root:{canonical_root}'.encode()).hexdigest()[:32]

def workspace_namespace_identity(root, purpose):
    """Return a non-path-leaking, root-bound namespace/capability identity."""
    canonical_root = str(Path(root).resolve()).casefold()
    return {
        "contract_id": "V4_PG_WORKSPACE_NAMESPACE_ID_R1",
        "root_identity_sha256": hashlib.sha256(canonical_root.encode()).hexdigest(),
        "logical_workspace_id": workspace_logical_id(root),
        "workspace_identity_sha256": hashlib.sha256(workspace_logical_id(root).encode()).hexdigest(),
        "schema": workspace_schema(root, purpose),
        "purpose": purpose,
        "capabilities": {
            "read": "SHARED_DATABASE_DSN_AND_READ_ONLY_TRANSACTION_REQUIRED",
            "write": "USER_AUTHORIZED_DEVELOPMENT_WRITE_INTENT_REQUIRED",
            "owner_mapping": "MUST_BE_AUTHORITY_BOUND",
        },
    }

def attest_read_role(pg, schema):
    """Attest that this transaction cannot write, irrespective of role grants."""
    mode = pg.execute('SHOW transaction_read_only').fetchone()
    if not mode or str(mode[0]).lower() != 'on':
        raise RuntimeError('PG_READER_TRANSACTION_NOT_READ_ONLY')
    return True

@contextmanager
def connection(schema, *, read_only=False, dsn=None, row_factory=None):
    if not _SCHEMA.fullmatch(schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    with psycopg.connect(dsn or (configured_reader_dsn() if read_only else configured_dsn()),connect_timeout=5,row_factory=row_factory) as pg:
        if read_only: pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        pg.execute("SET LOCAL statement_timeout='30s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute(sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(sql.Identifier(schema)))
        if read_only: attest_read_role(pg, schema)
        yield pg

def create_schema(pg,schema):
    if not _SCHEMA.fullmatch(schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    pg.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
