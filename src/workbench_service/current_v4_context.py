"""Exact current accepted V4 read projection; never discovers or writes data."""
import gzip
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class SourceInvalid(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf8')


def resolve_source_mode(permission, accepted_readable):
    return 'PRODUCTION_V4_PROVISIONAL' if permission else ('V4_ACCEPTED_RESEARCH_READONLY' if accepted_readable else 'NO_PERMISSION')


class CurrentAcceptedV4Reader:
    def __init__(self, root, *, contract_path='config/v4_current_accepted_read_contract_v1.json', today=None, follow_runtime=True, require_runtime=False):
        self.root=Path(root).resolve()
        self.contract_path=contract_path
        self.today=today
        self.follow_runtime=follow_runtime
        self.require_runtime=require_runtime
        self._cache={}

    def _path(self, name):
        if not isinstance(name,str) or Path(name).is_absolute():raise SourceInvalid('ABSOLUTE_SOURCE_FORBIDDEN')
        path=(self.root/name).resolve()
        if not path.is_relative_to(self.root):raise SourceInvalid('SOURCE_PATH_ESCAPE')
        return path

    def _read(self, ref):
        path=self._path(ref['path'])
        try:raw=path.read_bytes()
        except OSError as exc:raise SourceInvalid('BOUND_ARTIFACT_MISSING:'+ref['path']) from exc
        if len(raw)!=ref.get('bytes',ref.get('byte_count')) or digest(raw)!=ref['sha256']:
            raise SourceInvalid('BOUND_ARTIFACT_DIGEST_MISMATCH:'+ref['path'])
        key=(ref['path'],ref['sha256'])
        if key not in self._cache:
            payload=gzip.decompress(raw) if ref['path'].endswith('.gz') else raw
            if '.jsonl' in ref['path']:value=[json.loads(line) for line in payload.splitlines() if line]
            else:value=json.loads(payload)
            self._cache[key]=value
        return self._cache[key]

    def _verify(self,ref):
        path=self._path(ref['path']);h=hashlib.sha256();size=0
        try:
            with path.open('rb') as stream:
                while chunk:=stream.read(8*1024*1024):h.update(chunk);size+=len(chunk)
        except OSError as exc:raise SourceInvalid('BOUND_ARTIFACT_MISSING:'+ref['path']) from exc
        if size!=ref.get('bytes',ref.get('byte_count')) or h.hexdigest()!=ref['sha256']:raise SourceInvalid('BOUND_ARTIFACT_DIGEST_MISMATCH:'+ref['path'])

    def _contract(self):
        try:
            runtime_path=self.root/'config/v4_production_runtime_authority_v1.json'
            if self.require_runtime and not runtime_path.is_file():raise SourceInvalid('RUNTIME_AUTHORITY_MISSING')
            if self.follow_runtime and runtime_path.is_file() and self.contract_path=='config/v4_current_accepted_read_contract_v1.json':
                runtime=json.loads(runtime_path.read_bytes())
                if runtime['contract_id']!='V4_PRODUCTION_RUNTIME_AUTHORITY_V1' or not runtime['ui_read_only'] or runtime['tdx_write_authorized'] or runtime['trading_action_authorized']:raise SourceInvalid('RUNTIME_AUTHORITY_INVALID')
                ref=runtime['read_authority'];contract=self._read(ref);contract_digest=ref['sha256']
                if runtime['data_head_binding']['sha256']!=contract['anchors']['data_head']['sha256'] or runtime['stage_authority_binding']['sha256']!=contract['anchors']['stage_authority']['sha256']:raise SourceInvalid('RUNTIME_READ_AUTHORITY_INCONSISTENT')
            else:
                raw=self._path(self.contract_path).read_bytes();contract=json.loads(raw);contract_digest=digest(raw)
            if contract['contract_id']!='V4_CURRENT_ACCEPTED_READ_CONTRACT_V1' or contract['source_discovery'] or contract['fallback']!='NONE':raise SourceInvalid('READ_CONTRACT_INVALID')
            return contract,contract_digest
        except (OSError,KeyError,json.JSONDecodeError) as exc:raise SourceInvalid('READ_CONTRACT_INVALID') from exc

    def _heads(self,contract):
        heads={key:self._read(ref) for key,ref in contract['anchors'].items()}
        a,d,s,o=(heads[k] for k in ['stage_authority','data_head','stage_head','owner_head'])
        if a['data_head']['sha256']!=contract['anchors']['data_head']['sha256'] or a['current_head']['sha256']!=contract['anchors']['owner_head']['sha256']:
            raise SourceInvalid('CURRENT_AUTHORITY_INCONSISTENT')
        if s['v4_15_binding']['sha256']!=contract['anchors']['owner_head']['sha256'] or o['bindings']['data_head']['sha256']!=contract['anchors']['data_head']['sha256']:
            raise SourceInvalid('CURRENT_STAGE_LINEAGE_INVALID')
        if d['accepted_trade_date']!=o['accepted_trade_date'] or not d['external_acceptance'].startswith('EXTERNALLY_ACCEPTED'):
            raise SourceInvalid('DATA_DATE_OR_ACCEPTANCE_INVALID')
        for key,ref in contract['owner_heads'].items():
            if a['immutable_owner_heads'][key]['sha256']!=ref['sha256']:raise SourceInvalid('OWNER_AUTHORITY_INCONSISTENT')
            self._read(ref)
        return heads

    def _permission_map(self,heads):
        registry=heads['permission_authority']['capability_registry']
        result={}
        for key,row in registry.items():
            permission=row['production_permission']
            # This display adapter never invents a receipt or upgrades a v1 design gate.
            if permission:
                for ref in row['accepted_receipts'].values():
                    if not isinstance(ref,dict) or 'sha256' not in ref:raise SourceInvalid('UNBOUND_PRODUCTION_PERMISSION')
                    self._verify(ref)
            result[key]=permission
        return result

    def load_context(self):
        contract,contract_digest=self._contract()
        return self._load_context(contract,contract_digest)

    def _load_context(self,contract,contract_digest):
        heads=self._heads(contract)
        d,o=heads['data_head'],heads['owner_head']
        today=self.today or datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        context=dict(source_mode='V4_ACCEPTED_RESEARCH_READONLY',namespace='V4_CURRENT_ACCEPTED',accepted_trade_date=d['accepted_trade_date'],last_accepted_trade_date=d['accepted_trade_date'],
            data_head_digest=contract['anchors']['data_head']['sha256'],stage_head_digest=contract['anchors']['stage_head']['sha256'],stage=o['stage'],stage_contract_id=o['contract_id'],
            source_revision=d['source_revision'],canonical_data_revision=d['canonical_data_revision'],read_contract_digest=contract_digest,
            data_updated_at=d['promoted_at_utc'],freshness_state='WAIT_NEXT_ACCEPTED_INPUT' if today>d['accepted_trade_date'] else 'CURRENT_ACCEPTED_INPUT',
            knowledge_lineage=d['knowledge_lineage'],historical_pit_effectiveness='NOT_GRANTED')
        token='current-v4-'+digest(canonical({k:v for k,v in context.items() if k!='freshness_state'}))
        return dict(status='READY_CURRENT_ACCEPTED',context=context,context_token=token,production_permission=self._permission_map(heads),focus_write=False,source_mode=context['source_mode'])

    def _source(self,contract,key):
        return self._read(contract['sources'][key])

    def _rows(self,contract,key):
        return [(self._read(ref),ref) for ref in contract['row_bindings'][key]]

    def _cell(self,value,source,field,quality='KNOWN',reason=None):
        return dict(value=value,quality=quality,reason=reason,source={**source,'field_path':field})

    def _sources(self,contract,module):
        for key in contract['modules'][module]:
            for ref in contract['row_bindings'].get(key,[contract['sources'].get(key)]):
                self._verify(ref)

    def read(self,module,query=None):
        query=query or {}
        try:
            contract,contract_digest=self._contract();context=self._load_context(contract,contract_digest)
            if query.get('context_token') and query['context_token']!=context['context_token']:return 409,dict(status='BLOCKED',code='STALE_CONTEXT_REQUIRES_REFRESH',items=[])
            if module=='context':return 200,context
            if module not in contract['modules']:return 404,dict(status='BLOCKED',code='UNKNOWN_CURRENT_MODULE',items=[])
            self._sources(contract,module)
            source=lambda key:contract['sources'][key]
            c=self._cell;items=[];status='READY';metadata={}
            if module=='summary':
                events=self._source(contract,'events')
                for row in events:
                    if row['effective_event'] in ('UNKNOWN','NONE'):continue
                    items.append(dict(entity_id=row['entity_id'],fields={k:c(row.get(k),source('events'),k,'KNOWN' if row['event_quality']=='KNOWN' else 'DEGRADED',row.get('counterevidence')) for k in ['effective_event','primary_scenario','counterevidence','trade_date']}))
                metadata['today_change']='NO_NEW_ACCEPTED_TRADE_DATE' if context['context']['freshness_state']=='WAIT_NEXT_ACCEPTED_INPUT' else 'CURRENT_ACCEPTED_INPUT'
                metadata['last_accepted_why_now']=[dict(fields={'why_now':c(row['why_now'],ref,'why_now','DEGRADED')}) for row,ref in self._rows(contract,'observations')[:5]]
            elif module=='radar':
                publication=self._source(contract,'radar')
                if publication['trade_date']!=context['context']['accepted_trade_date'] or publication['evidence_class']!='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED':raise SourceInvalid('RADAR_REAL_LINEAGE_INVALID')
                for row,ref in self._rows(contract,'ledger'):
                    if row['trade_date']!=publication['trade_date'] or row['publication_id']!=publication['publication_id']:raise SourceInvalid('RADAR_ROW_LINEAGE_INVALID')
                    items.append(dict(entity_id=row['entity_id'],fields={k:c(row.get(k),ref,k,'KNOWN' if row.get(k) is not None else 'UNKNOWN','OWNER_PRIORITY_UNAVAILABLE' if row.get(k) is None else None) for k in ['entity_id','signal_type','eligibility_state','priority_bucket','trade_date']}))
                metadata['evidence_class']=publication['evidence_class'];metadata['signal_quality']='DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY'
            elif module=='entity':
                raw=self._source(contract,'RAW_DAILY')['rows'];identity={r['security_id']:r for r in self._source(contract,'IDENTITY_UNIVERSE')['rows']}
                projection=self._source(contract,'state_view')
                if projection['source']['sha256']!=source('states')['sha256']:raise SourceInvalid('STATE_PROJECTION_LINEAGE_INVALID')
                states={r['entity_id']:r for r in projection['rows']}
                for row in raw:
                    fields={k:c(row[k],source('RAW_DAILY'),'rows[*].'+k) for k in ['source_security_key','close','open','high','low','trade_date']}
                    fields['list_date']=c(identity.get(row['security_id'],{}).get('list_date'),source('IDENTITY_UNIVERSE'),'rows[*].list_date')
                    state=states.get(row['security_id'])
                    if state:
                        for k in ['scenario','scenario_status','state','final_eligibility','state_freshness','health','maturity']:
                            if k in state:fields[k]=c(state[k],source('states'),'rows[*].'+k,'UNKNOWN' if state[k] in ('UNKNOWN',None) else 'DEGRADED','ACCEPTED_OWNER_CAPABILITY_SCOPED')
                    items.append(dict(entity_id=row['security_id'],fields=fields))
            elif module=='sector':
                grouped=defaultdict(set);names={}
                for row in self._source(contract,'membership'):
                    key=row['sector_id'];grouped[key].add(row['security_id']);names[key]=row.get('sector_name',key)
                items=[dict(entity_id=key,fields={'sector_id':c(key,source('membership'),'sector_id'),'sector_name':c(names[key],source('membership'),'sector_name'),'member_count':c(len(members),source('membership'),'COUNT_DISTINCT(security_id)','KNOWN'),'algorithm_state':c(None,contract['owner_heads']['v4_08'],'capabilities.REAL_SIGNAL_CAPABILITY','UNKNOWN','ACCEPTED_OWNER_HISTORY_OR_CAPABILITY_UNAVAILABLE')}) for key,members in sorted(grouped.items())]
                metadata['membership_scope']='FORWARD_PIT_MEMBERSHIP_ONLY';status='DEGRADED'
            elif module=='cohort':
                for row,ref in self._rows(contract,'cohort'):
                    if row['T0']!=context['context']['accepted_trade_date'] or row['evidence_class']!='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED':raise SourceInvalid('COHORT_REAL_LINEAGE_INVALID')
                    items.append(dict(entity_id=row['entity_id'],fields={k:c(row.get(k),ref,k,'DEGRADED' if k=='cohort_namespace' else 'KNOWN') for k in ['entity_id','T0','cohort_namespace','enrollment_id','evidence_class']}))
                status='PENDING';metadata['maturity']=self._source(contract,'maturity')['capability_by_horizon']
            elif module=='settlement':
                for row,ref in self._rows(contract,'outcomes'):
                    fields={k:c(row.get(k),ref,k,'PENDING' if row.get(k)=='PENDING' else 'KNOWN') for k in ['enrollment_id','horizon','outcome_status','due_date','outcome_revision'] if k in row}
                    items.append(dict(entity_id=row.get('enrollment_id'),fields=fields))
                status='PENDING';metadata['maturity_evidence']='NOT_GRANTED_PENDING_MATURITY_EVIDENCE'
            elif module=='health':
                data=self._read(contract['anchors']['data_head'])
                for key in ['RAW_DAILY','IDENTITY_UNIVERSE','ADJUSTED_DAILY','TRADING_STATUS']:
                    ref=source(key);artifact=self._source(contract,key);info=data['component_permissions'][key]
                    if len(artifact['rows'])!=info['row_count'] or artifact['trade_date']!=context['context']['accepted_trade_date']:raise SourceInvalid('COMPONENT_COUNT_OR_DATE_MISMATCH')
                    items.append(dict(entity_id=key,fields={'component':c(key,ref,'contract_id'),'row_count':c(info['row_count'],ref,'rows.length'),'quality':c(info['status'],contract['anchors']['data_head'],'component_permissions.'+key+'.status','DEGRADED' if info['status']=='DEGRADED_PASS' else 'KNOWN')}))
                metadata.update(production_permission=context['production_permission'],focus_write=False,freshness=context['context']['freshness_state'],source_quality=self._source(contract,'replay')['quality'],maturity=self._source(contract,'maturity')['status'])
            if not items:status='EMPTY_VALID';metadata['reason']='NO_ELIGIBLE_OBJECTS'
            if 'identity_names' in contract['modules'][module]:
                names={r['security_id']:r for r in self._source(contract,'identity_names')['records']}
                for item in items:
                    record=names.get(item['entity_id'],{})
                    item['display_name']=' · '.join(str(v) for v in [record.get('symbol'),record.get('security_name')] if v) or item['entity_id']
                    if record.get('security_name'):
                        item['fields']['security_name']=c(record['security_name'],source('identity_names'),'records[*].security_name','DEGRADED',record.get('identity_quality'))
            needle=query.get('q','').strip().casefold();filter_state=query.get('state','').strip().casefold()
            if needle:items=[r for r in items if needle in json.dumps(r,ensure_ascii=False).casefold()]
            if filter_state:items=[r for r in items if any(filter_state==str(cell.get('value','')).casefold() for cell in r['fields'].values())]
            total=len(items);offset=int(query.get('offset','0'));limit=int(query.get('limit','30'))
            if offset<0 or not 1<=limit<=200:raise ValueError('INVALID_PAGE')
            return 200,{**context,'module':module,'module_status':status,'items':items[offset:offset+limit],'total':total,'metadata':metadata}
        except SourceInvalid as exc:return 409,dict(status='BLOCKED',module=module,code='SOURCE_INVALID',reason=str(exc),items=[])
        except (ValueError,KeyError,TypeError) as exc:return 409,dict(status='BLOCKED',module=module,code='SOURCE_INVALID',reason=str(exc),items=[])

    def read_summary(self):return self.read('summary')[1]
    def read_radar(self):return self.read('radar')[1]
    def read_entities(self):return self.read('entity')[1]
    def read_sectors(self):return self.read('sector')[1]
    def read_forward(self):return self.read('cohort')[1]
    def read_health(self):return self.read('health')[1]
