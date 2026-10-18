"""Versioned research releases stored in the single PostgreSQL schema v4."""
from __future__ import annotations

import hashlib
import json
import re

from psycopg import sql

CONTRACT='V4_PG_RESEARCH_SNAPSHOT_R3_SINGLE_SCHEMA'
MIGRATION='V4_SINGLE_SCHEMA_RESEARCH_STORAGE_R1'
TABLE_RELATIONS={
    'objects':('research_objects',('domain','id','name','symbol','state','payload')),
    'aliases':('research_aliases',('alias','id')),
    'members':('research_members',('sector','security')),
    'metadata':('research_metadata',('key','value')),
    'bars':('research_series_bars',('security','day','payload')),
    'days':('research_journal_days',('day','source_digest','payload')),
    'day_inputs':('research_journal_inputs',('day','payload')),
}
_LEGACY_TABLE=re.compile(r'\b(FROM|JOIN)\s+(objects|aliases|members|metadata|bars|days|day_inputs)(?:\s+(?:AS\s+)?(?!WHERE\b|JOIN\b|LEFT\b|RIGHT\b|INNER\b|ORDER\b|LIMIT\b|GROUP\b|UNION\b|ON\b|AND\b|OR\b)([a-z_][a-z0-9_]*))?',re.I)
_TABLE_COLUMNS={
    'objects':'domain,id,name,symbol,state,payload',
    'aliases':'alias,id',
    'members':'sector,security',
    'metadata':'key,value',
    'bars':'security,day,payload',
    'days':'day,source_digest,payload',
    'day_inputs':'day,payload',
}


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')


def digest(value):
    return hashlib.sha256(value if isinstance(value,bytes) else canonical(value)).hexdigest()


def _central_table_manifest(pg,release_id,storage_kind):
    from .v4_snapshot_pg_r2 import EXTRA_TABLES,TABLES,ORDER,canonical_json_payload
    definitions={name:tuple((column,'text') for column in columns) for name,columns in TABLES.items()}
    definitions.update(EXTRA_TABLES[storage_kind])
    result={}
    for source_table,(relation,columns) in TABLE_RELATIONS.items():
        if source_table not in definitions:continue
        definition=definitions[source_table]
        order=ORDER.get(source_table,(columns[0],))
        def sort_expr(column):
            is_date=column=='day' and source_table in {'bars','days','day_inputs'}
            if is_date:return sql.SQL('{} NULLS FIRST').format(sql.Identifier(column))
            return (sql.SQL('{} COLLATE "C" NULLS FIRST').format(sql.Identifier(column))
                    if dict(definition)[column]=='text' else sql.SQL('{} NULLS FIRST').format(sql.Identifier(column)))
        query=sql.SQL('SELECT {} FROM v4.{} WHERE release_id=%s ORDER BY {}').format(
            sql.SQL(',').join(map(sql.Identifier,columns)),sql.Identifier(relation),
            sql.SQL(',').join(sort_expr(column) for column in order))
        h=hashlib.sha256();count=0
        with pg.cursor(name='v4_release_verify_'+hashlib.sha256((release_id+source_table).encode()).hexdigest()[:16]) as cur:
            cur.itersize=128;cur.execute(query,(release_id,))
            for row in cur:
                values=[value.isoformat() if (kind=='date' or (column=='day' and source_table in {'bars','days','day_inputs'})) and value is not None else value
                        for value,(_,kind),column in zip(row,definition,columns)]
                if source_table=='objects' and values[-1] is not None:
                    values[-1]=canonical_json_payload(values[-1])
                h.update(canonical(values)+b'\n');count+=1
        result[source_table]={'rows':count,'digest':h.hexdigest()}
    return result


def resolve_legacy_schema(pg,schema):
    """Resolve only an exact, already-migrated schema; never inspect it."""
    if not isinstance(schema,str) or not schema.startswith('v4_research_'):
        raise ValueError('PG_CANDIDATE_RELEASE_ID_REQUIRED')
    rows=pg.execute('SELECT DISTINCT canonical_version FROM v4.legacy_schema_migration_map WHERE source_schema=%s ORDER BY canonical_version',(schema,)).fetchall()
    if len(rows)!=1:raise ValueError('LEGACY_SCHEMA_RELEASE_MAPPING_NOT_UNIQUE')
    return rows[0][0]


def load_release(pg,release_id,*,verify_content=True):
    from .v4_snapshot_pg_r2 import EXTRA_FIELDS,database_identity
    rows=pg.execute('SELECT storage_kind,contract_id,t0,source_schema,legacy_digest,original_descriptor,original_descriptor_sha256,canonical_manifest,sealed FROM v4.research_releases WHERE release_id=%s',(release_id,)).fetchall()
    if len(rows)!=1:raise ValueError('PG_CANDIDATE_RELEASE_NOT_UNIQUE')
    kind,contract_id,t0,source_schema,legacy_digest,original,original_sha,manifest,sealed=rows[0]
    if not sealed or kind not in EXTRA_FIELDS:raise ValueError('PG_CANDIDATE_RELEASE_NOT_SEALED')
    migrated=original is not None
    if migrated:
        if contract_id!='V4_PG_RESEARCH_SNAPSHOT_R2' or digest(bytes(original))!=str(original_sha).strip():
            raise ValueError('PG_CANDIDATE_LEGACY_DESCRIPTOR_SHA_MISMATCH')
        old=json.loads(bytes(original).decode('utf8'))
        if (old.get('schema'),old.get('release_id'),old.get('T0'),old.get('logical_digest'))!=(source_schema,release_id,t0.isoformat(),legacy_digest):
            raise ValueError('PG_CANDIDATE_LEGACY_DESCRIPTOR_BINDING_MISMATCH')
        if old.get('content_manifest')!=dict((key,value) for key,value in manifest.items() if key!='migration_contract_id'):
            raise ValueError('PG_CANDIDATE_MANIFEST_MIGRATION_MISMATCH')
        map_rows=pg.execute('SELECT source_table,canonical_relation,original_sha256,verification FROM v4.legacy_schema_migration_map WHERE source_schema=%s AND canonical_version=%s ORDER BY source_table',(source_schema,release_id)).fetchall()
    else:
        if contract_id!=CONTRACT or source_schema is not None or legacy_digest is not None or original_sha is not None:
            raise ValueError('PG_CANDIDATE_CANONICAL_RELEASE_IDENTITY_INVALID')
        map_rows=[]
    expected_tables=manifest.get('tables',{})
    if migrated and len(map_rows)!=len(expected_tables):raise ValueError('PG_CANDIDATE_MIGRATION_MAP_INCOMPLETE')
    for table,relation,sha,proof in map_rows:
        expected=expected_tables.get(table)
        if not expected or proof.get('status')!='VERIFIED' or str(sha).strip()!=expected['digest'] or proof.get('target_digest')!=expected['digest'] or proof.get('target_rows')!=expected['rows']:
            raise ValueError('PG_CANDIDATE_MIGRATION_MAP_INVALID:'+table)
    if verify_content and _central_table_manifest(pg,release_id,kind)!={
            table:{'rows':meta['rows'],'digest':meta['digest']} for table,meta in expected_tables.items()}:
        raise ValueError('PG_CANDIDATE_CANONICAL_CONTENT_MISMATCH')
    if kind=='snapshot':
        metadata_rows=pg.execute("SELECT value FROM v4.research_metadata WHERE release_id=%s AND key='snapshot'",(release_id,)).fetchall()
        if len(metadata_rows)!=1:raise ValueError('PG_CANDIDATE_SNAPSHOT_MANIFEST_NOT_UNIQUE')
        metadata=json.loads(metadata_rows[0][0])
        if metadata!=manifest.get('metadata'):raise ValueError('PG_CANDIDATE_SNAPSHOT_MANIFEST_MISMATCH')
    else:metadata=manifest.get('metadata')
    db_identity=database_identity(pg)
    migration_digest=digest([(row[0],row[1],str(row[2]).strip(),row[3]) for row in map_rows])
    descriptor={'contract_id':CONTRACT,'engine':'postgresql','schema':'v4','release_id':release_id,
        'T0':t0.isoformat(),'content_manifest':manifest,'database_identity':db_identity}
    if migrated:
        descriptor.update(legacy_schema=source_schema,legacy_logical_digest=legacy_digest,
                          legacy_descriptor_sha256=str(original_sha).strip(),migration_map_digest=migration_digest)
        old_descriptor=json.loads(bytes(original).decode('utf8'))
        descriptor.update({key:old_descriptor[key] for key in EXTRA_FIELDS[kind]})
        if kind=='journal':descriptor['registry_schema']='v4'
    elif kind=='series':
        row=pg.execute('SELECT series_contract_id,source_digest,bar_count,symbol_count FROM v4.research_series_versions WHERE release_id=%s',(release_id,)).fetchone()
        if not row:raise ValueError('PG_SERIES_VERSION_ROW_MISSING')
        descriptor.update(dict(zip(('series_contract_id','source_digest','bar_count','symbol_count'),row)))
    elif kind=='journal':
        row=pg.execute('SELECT journal_contract,registry_schema,registry_key FROM v4.research_journal_versions WHERE release_id=%s',(release_id,)).fetchone()
        if not row:raise ValueError('PG_JOURNAL_VERSION_ROW_MISSING')
        descriptor.update(dict(journal_contract=row[0],head=manifest['metadata']['head'],registry_schema=row[1],registry_key=row[2]))
    descriptor['logical_digest']=digest(descriptor)
    return descriptor,metadata,kind


def load_snapshot_release(pg,release_id,*,verify_content=True):
    descriptor,metadata,kind=load_release(pg,release_id,verify_content=verify_content)
    if kind!='snapshot':raise ValueError('PG_CANDIDATE_RELEASE_NOT_SEALED_SNAPSHOT')
    return descriptor,metadata


def resolve_legacy_release(pg,descriptor,*,verify_content=True):
    """Resolve one frozen legacy descriptor through the central migration map."""
    if (not isinstance(descriptor,dict)
            or not isinstance(descriptor.get('schema'),str)
            or not re.fullmatch(r'v4_research_[a-f0-9]{24}',descriptor['schema'])
            or not isinstance(descriptor.get('release_id'),str)):
        raise ValueError('PG_CANDIDATE_LEGACY_DESCRIPTOR_INVALID')
    rows=pg.execute('''SELECT storage_kind,contract_id,t0,source_schema,legacy_digest,
        original_descriptor,original_descriptor_sha256,sealed
        FROM v4.research_releases WHERE release_id=%s''',(descriptor['release_id'],)).fetchall()
    if len(rows)!=1:raise ValueError('PG_CANDIDATE_LEGACY_RELEASE_NOT_MIGRATED')
    kind,contract_id,t0,source_schema,legacy_digest,original,original_sha,sealed=rows[0]
    if (not sealed or source_schema!=descriptor['schema']
            or contract_id!='V4_PG_RESEARCH_SNAPSHOT_R2' or original is None
            or digest(bytes(original))!=str(original_sha).strip()):
        raise ValueError('PG_CANDIDATE_LEGACY_DESCRIPTOR_SHA_MISMATCH')
    frozen=json.loads(bytes(original).decode('utf-8'))
    if (frozen.get('schema'),frozen.get('release_id'),frozen.get('T0'),frozen.get('logical_digest'))!=(source_schema,descriptor['release_id'],t0.isoformat(),legacy_digest):
        raise ValueError('PG_CANDIDATE_LEGACY_DESCRIPTOR_BINDING_MISMATCH')
    if (descriptor.get('logical_digest'),descriptor.get('release_id'),descriptor.get('schema'))!=(legacy_digest,descriptor['release_id'],source_schema):
        raise ValueError('PG_CANDIDATE_LEGACY_DESCRIPTOR_BINDING_MISMATCH')
    canonical,_,canonical_kind=load_release(pg,descriptor['release_id'],verify_content=verify_content)
    if canonical_kind!=kind:raise ValueError('PG_CANDIDATE_LEGACY_RELEASE_KIND_MISMATCH')
    return canonical


class ReleaseReadTransaction:
    """Compatibility SQL facade that scopes every legacy table read by release_id."""
    def __init__(self,pg,release_id):self.pg=pg;self.release_id=release_id
    def execute(self,query,params=()):
        from .v4_snapshot_pg_r1 import translate
        original=list(params);ordered=[];last=0
        def replace(match):
            nonlocal last
            segment=query[last:match.start()]
            count=segment.count('?')
            ordered.extend(original[:count]);del original[:count]
            table=match.group(2).casefold();alias=match.group(3) or table
            relation={
                'objects':'research_objects','aliases':'research_aliases',
                'members':'research_members','metadata':'research_metadata',
                'bars':'research_series_bars','days':'research_journal_days',
                'day_inputs':'research_journal_inputs',
            }[table]
            replacement=f'(SELECT {_TABLE_COLUMNS[table]} FROM v4.{relation} WHERE release_id=%s) AS {alias}'
            ordered.append(self.release_id);last=match.end()
            return match.group(1)+' '+replacement
        rewritten=_LEGACY_TABLE.sub(replace,query)
        ordered.extend(original)
        return self.pg.execute(translate(rewritten),ordered)
