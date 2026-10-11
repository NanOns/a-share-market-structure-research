"""Enumerate every actual isolated FEP SQL field and registered feature identity."""
from pathlib import Path
import hashlib,json,sys
import psycopg
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_semantics_focus_20261011/FEP_FULL_CATALOG_FIELD_EXPANSION_R2.json'
if OUT.exists():raise ValueError('EXISTING_FIELD_EVIDENCE_MUST_BE_RETAINED')
ddl=[ROOT/'artifacts/fep_r2_20260930/FEP_R2_SCHEMA_DESIGN_20260930.sql',
    *sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*_fep_*.sql'))]
registry=ROOT/'config/fep_feature_registry_v1.json'
with psycopg.connect('host=127.0.0.1 port=55794 user=r4_isolated_admin dbname=fep_e5b_fresh connect_timeout=5') as pg:
    pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
    database=pg.execute('SELECT current_database(),current_setting(\'data_directory\'),system_identifier::text FROM pg_control_system()').fetchone()
    if database[0]!='fep_e5b_fresh' or Path(database[1]).resolve()!=Path('G:/codex_tmp/r4_r3_fep_fixtures/fresh_data').resolve():
        raise ValueError('ISOLATED_FEP_CATALOG_DATABASE_REQUIRED')
    columns=pg.execute("SELECT table_schema,table_name,column_name,ordinal_position,data_type,udt_name,is_nullable,column_default FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY table_schema COLLATE \"C\",table_name COLLATE \"C\",ordinal_position").fetchall()
    constraints=pg.execute("SELECT n.nspname,c.relname,t.conname,t.contype,pg_get_constraintdef(t.oid) FROM pg_constraint t JOIN pg_class c ON c.oid=t.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') ORDER BY n.nspname COLLATE \"C\",c.relname COLLATE \"C\",t.conname COLLATE \"C\"").fetchall()
    indexes=pg.execute("SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname COLLATE \"C\",tablename COLLATE \"C\",indexname COLLATE \"C\"").fetchall()
bindings=[dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in [*ddl,registry]]
fields=[]
for schema,table,column,position,kind,udt,nullable,default in columns:
    if schema!='fep':continue
    references=[]
    for path in ddl:
        for number,line in enumerate(path.read_text(encoding='utf8').splitlines(),1):
            if column in line and line.strip().startswith(column):references.append(dict(path=str(path.relative_to(ROOT)),line=number,text=line.strip()))
    fields.append(dict(identity=[schema,table,column],ordinal=position,data_type=kind,udt=udt,nullable=nullable=='YES',default=default,
        declaration_candidates=references,producer_binding='OPEN_EXACT_FIELD_MAPPING_REQUIRED',
        unit_formula_window='OPEN_PER_FIELD_CONTRACT',cutoff_quality='OPEN_PER_FIELD_CONTRACT',
        actual_consumer_and_oracle='OPEN',structural_enumeration='ACTUAL_POSTGRESQL_CATALOG_READ'))
features=json.loads(registry.read_bytes())['fields']
keys=[row['field_name'] for row in features]
if len(set(keys))!=len(keys):raise ValueError('DUPLICATE_REGISTERED_FEATURE_IDENTITY')
result=dict(contract='R4_R3_FEP_ACTUAL_SQL_AND_FEATURE_FULL_FIELD_EXPANSION_R1',database_identity=dict(database=database[0],data_directory=database[1],system_identifier=database[2]),
    source_bindings=bindings,all_native_catalog_column_records=len(columns),fep_sql_column_denominator=len(fields),
    fep_tables=sorted(set(row['identity'][1] for row in fields)),sql_fields=fields,
    constraints=[list(row) for row in constraints if row[0]=='fep'],
    indexes=[list(row) for row in indexes if row[0]=='fep'],
    feature_denominator=len(features),feature_rows=[dict(original=row,qualification='REGISTERED_FEATURE_PRESERVED',semantic_acceptance='OPEN_REAL_SOURCE_PRODUCER_CONSUMER_ORACLE') for row in features],
    excluded_native_catalog_columns=[list(row[:3]) for row in columns if row[0]!='fep'],
    prior_failed_enumeration=dict(path='docs/audits/r4_r3_semantics_focus_20261011/FEP_FULL_CATALOG_FIELD_EXPANSION_R1.json',
        sha256=hashlib.sha256((OUT.parent/'FEP_FULL_CATALOG_FIELD_EXPANSION_R1.json').read_bytes()).hexdigest(),
        disposition='FAILED_ZERO_FIELD_PREFIX_SELECTION_NOT_ACCEPTED'),
    status='ACTUAL_FEP_FIELD_ENUMERATION_COMPLETE_SEMANTIC_ACCEPTANCE_OPEN',
    limitation='SQL storage fields and feature identities are separate denominators; neither replaces the complete normative V4 denominator. Declaration candidates are references, not an approved field-to-producer mapping.',production_changed=False)
if not fields or not result['constraints'] or not result['indexes']:raise ValueError('INCOMPLETE_NATIVE_FEP_CATALOG')
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(sql_fields=len(fields),tables=len(result['fep_tables']),features=len(features),status=result['status'])))
