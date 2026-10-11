"""Independent pg_attribute recount of the retained full FEP field inventory."""
from pathlib import Path
import hashlib,json
import psycopg
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'docs/audits/r4_r3_semantics_focus_20261011/FEP_FULL_CATALOG_FIELD_EXPANSION_R2.json'
output=source.with_name('FEP_FULL_CATALOG_FIELD_INDEPENDENT_R2.json')
if output.exists():raise ValueError('RETAIN_EXISTING_FIELD_RECOUNT')
document=json.loads(source.read_bytes())
with psycopg.connect('host=127.0.0.1 port=55794 user=r4_isolated_admin dbname=fep_e5b_fresh connect_timeout=5') as pg:
    pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
    identity=pg.execute("SELECT current_database(),current_setting('data_directory'),system_identifier::text FROM pg_control_system()").fetchone()
    if identity!=(document['database_identity']['database'],document['database_identity']['data_directory'],document['database_identity']['system_identifier']):
        raise ValueError('EXACT_NATIVE_CATALOG_DATABASE_MISMATCH')
    independent=pg.execute("SELECT n.nspname,c.relname,a.attname FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='fep' AND c.relkind IN ('r','p','v','m','f') AND a.attnum>0 AND NOT a.attisdropped ORDER BY n.nspname COLLATE \"C\",c.relname COLLATE \"C\",a.attname COLLATE \"C\"").fetchall()
actual={tuple(row['identity']) for row in document['sql_fields']}
expected=set(independent)
missing=sorted(expected-actual);extra=sorted(actual-expected)
if missing or extra or len(actual)!=len(document['sql_fields']) or len(expected)!=document['fep_sql_column_denominator']:
    raise ValueError('FEP_FIELD_DENOMINATOR_INCOMPLETE')
negative=dict(deliberately_removed_one_field_detected=(actual-{next(iter(actual))})!=expected,
    deliberate_extra_field_detected=(actual|{('fep','invented_table','invented_field')})!=expected)
result=dict(contract='R4_R3_INDEPENDENT_FEP_CATALOG_FIELD_RECOUNT_R2',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    independent_pg_attribute_count=len(expected),independent_table_count=len({row[1] for row in expected}),
    field_identity_equal=True,missing=missing,extra=extra,negative_checks=negative,
    field_semantic_acceptance='OPEN',status='SCOPED_STRUCTURAL_DENOMINATOR_PASS',production_changed=False)
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result))
