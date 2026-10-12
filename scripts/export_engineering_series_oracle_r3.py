"""Dedicated read-only SQLite migration oracle; never a runtime consumer."""
import hashlib,json,os,sqlite3,sys
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while part:=f.read(1024*1024):h.update(part)
    return h.hexdigest()
source,out=map(lambda p:Path(p).resolve(),sys.argv[1:3])
if not source.is_relative_to(Path('G:/codex_tmp').resolve()) or not out.is_relative_to(Path('G:/codex_tmp').resolve()):raise ValueError('ISOLATED_G_ORACLE_REQUIRED')
before=sha(source);count=0;logical=hashlib.sha256()
temporary=out.with_suffix('.tmp')
with sqlite3.connect(source.as_uri()+'?mode=ro&immutable=1',uri=True) as db,temporary.open('w',encoding='utf8') as stream:
    for sid,day,payload in db.execute('SELECT security,day,payload FROM bars ORDER BY security,day'):
        value=json.loads(payload);value['trade_date']=day
        raw=json.dumps([sid,day,value],sort_keys=True,ensure_ascii=False,separators=(',',':'))
        stream.write(raw+'\n');logical.update((raw+'\n').encode());count+=1
if sha(source)!=before:raise ValueError('SOURCE_MUTATED_DURING_ORACLE')
os.replace(temporary,out)
out.with_suffix('.receipt.json').write_text(json.dumps(dict(contract_id='R4_R3_ISOLATED_READONLY_SERIES_MIGRATION_ORACLE',source_sha256=before,source_sha256_after=sha(source),rows=count,logical_sha256=logical.hexdigest(),source_unchanged=True,sqlite_uri_mode='mode=ro&immutable=1',sql='SELECT security,day,payload FROM bars ORDER BY security,day',scope='MIGRATION_READONLY_INPUT_ONLY_NOT_RUNTIME_CONSUMER',export_source_sha256=sha(Path(__file__)))),encoding='utf8')
