"""Authorized additive formal-role preparation; protected production is unchanged."""
import ctypes,json,os,secrets,sys
from ctypes import wintypes
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo
SOURCE=Path('G:/codex work/大A交易')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/formal_pg_roles')
PRIVATE=Path('G:/codex work/v4-production-20261012/config/native_pg_roles.dpapi')
ROLES=('v4_closeout_reader_20261012','v4_closeout_producer_20261012')

class Blob(ctypes.Structure):
    _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]

def protect(raw):
    if sys.platform!='win32':raise ValueError('WINDOWS_USER_DPAPI_REQUIRED')
    buf=(ctypes.c_ubyte*len(raw)).from_buffer_copy(raw);src=Blob(len(raw),buf);dst=Blob()
    api=ctypes.windll.crypt32.CryptProtectData
    if not api(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst)):raise ctypes.WinError()
    try:return ctypes.string_at(dst.pbData,dst.cbData)
    finally:ctypes.windll.kernel32.LocalFree(dst.pbData)

def load_credentials(path):
    path=Path(path).resolve()
    if path.drive.upper()!='G:' or sys.platform!='win32':raise ValueError('G_LOCAL_WINDOWS_DPAPI_REQUIRED')
    raw=path.read_bytes();buf=(ctypes.c_ubyte*len(raw)).from_buffer_copy(raw);src=Blob(len(raw),buf);dst=Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst)):raise ctypes.WinError()
    try:value=json.loads(ctypes.string_at(dst.pbData,dst.cbData))
    finally:ctypes.windll.kernel32.LocalFree(dst.pbData)
    if set(value)!=set(ROLES):raise ValueError('FORMAL_ROLE_SECRET_CONTRACT_MISMATCH')
    return value

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if PRIVATE.exists() or (OUT/'RESULT.json').exists():raise ValueError('PRESERVE_EXISTING_FORMAL_ROLE_PREPARATION')
    dsn=None
    for line in (SOURCE/'config/.env').read_text(encoding='utf-8-sig').splitlines():
        key,sep,value=line.partition('=')
        if sep and key.strip()=='WORKBENCH_PG_DSN':dsn=value.strip().strip('\"').strip("'")
    if not dsn:raise ValueError('FORMAL_CONFIGURED_ADMIN_DSN_REQUIRED')
    parsed=conninfo_to_dict(dsn)
    if (parsed.get('host'),parsed.get('port'),parsed.get('dbname'))!=('127.0.0.1','5432','market_research'):raise ValueError('FORMAL_TARGET_IDENTITY_MISMATCH')
    protected={name:(SOURCE/'data/v4'/name).read_bytes() for name in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json')}
    password={role:secrets.token_urlsafe(48) for role in ROLES}
    private={role:make_conninfo(dsn,user=role,password=password[role]) for role in ROLES}
    encrypted=protect(json.dumps(private).encode())
    PRIVATE.parent.mkdir(parents=True,exist_ok=True)
    temporary=PRIVATE.with_suffix('.tmp');temporary.write_bytes(encrypted)
    try:
        with psycopg.connect(dsn,connect_timeout=5) as pg:
            observed=pg.execute("SELECT current_user,system_identifier::text,current_database() FROM pg_control_system()").fetchone()
            if observed!=('postgres','7688198230782699460','market_research'):raise ValueError('FORMAL_TARGET_CLUSTER_OR_ADMIN_MISMATCH')
            if pg.execute('SELECT rolname FROM pg_roles WHERE rolname=ANY(%s)',(list(ROLES),)).fetchall():raise ValueError('FORMAL_ROLE_ALREADY_EXISTS_NO_IMPLICIT_CHANGE')
            for role in ROLES:
                pg.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT PASSWORD {}').format(sql.Identifier(role),sql.Literal(password[role])))
                pg.execute(sql.SQL('GRANT CONNECT ON DATABASE market_research TO {}').format(sql.Identifier(role)))
                pg.execute(sql.SQL('GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {}').format(sql.Identifier(role)))
            pg.execute(sql.SQL('GRANT CREATE ON DATABASE market_research TO {}').format(sql.Identifier(ROLES[1])))
        os.replace(temporary,PRIVATE)
    finally:temporary.unlink(missing_ok=True)
    checks=[]
    for role in ROLES:
        with psycopg.connect(private[role],connect_timeout=5) as pg:
            pg.execute('SET TRANSACTION READ ONLY')
            row=pg.execute("SELECT current_user,current_database(),system_identifier::text,has_database_privilege(current_user,current_database(),'CREATE'),rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_control_system(),pg_roles WHERE rolname=current_user").fetchone()
            if row[:3]!=(role,'market_research','7688198230782699460') or any(row[4:]) or row[3]!=(role==ROLES[1]):raise ValueError('FORMAL_ROLE_PRIVILEGES_NOT_ACCEPTED')
            memberships=pg.execute("SELECT rolname FROM pg_roles WHERE rolname<>current_user AND pg_has_role(current_user,oid,'MEMBER')").fetchall()
            if memberships:raise ValueError('FORMAL_ROLE_MEMBERSHIP_NOT_ACCEPTED')
            checks.append(dict(role=role,database=row[1],system_identifier=row[2],database_create=row[3],elevated_privileges=False,inherited_memberships=[]))
    for name,raw in protected.items():
        if (SOURCE/'data/v4'/name).read_bytes()!=raw:raise ValueError('PROTECTED_PRODUCTION_HEAD_CHANGED')
    result=dict(contract_id='V4_FORMAL_PG_ADDITIVE_ROLE_PREPARATION_R1',host='127.0.0.1',port=5432,
        checks=checks,status='ROLE_IDENTITY_AND_PRIVILEGE_CHECK_PASS',private_credentials='WINDOWS_USER_DPAPI_G_LOCAL_ONLY',
        credentials_in_evidence=False,production_heads_changed=False,existing_roles_changed=False,
        business_schema_migration='NEXT_STAGE_REQUIRED',runtime_role_admission='NEXT_STAGE_REQUIRED',production_cutover=False)
    (OUT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status=result['status'],roles=list(ROLES),production_cutover=False)))
if __name__=='__main__':main()
