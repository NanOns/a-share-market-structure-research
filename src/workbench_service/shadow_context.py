"""V4-17 read-only projection. No discovery, writers or production connection.

Real readback requires an externally accepted, content-addressed manifest of
exact publication/fact bindings. Until that independently accepted manifest is
configured, no database is opened. Engineering injection is constructor-only.
"""
import copy
import hashlib
import json
import sqlite3
from pathlib import Path

from .research_context import ResearchContextError

IDENTITY = ('namespace', 'trade_date', 'publication_id', 'publication_revision',
            'model_contract_id', 'parameter_set_id', 'state_lineage_id',
            'daily_input_digest', 'source_manifest_digest', 'evidence_origin')
COMPONENTS = ('summary', 'radar', 'entity', 'cohort', 'settlement', 'health')
PREFIX = '/api/v4/shadow/'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition, code):
    if not condition:
        raise ResearchContextError(code)


def context_token(context):
    require(set(context) == set(IDENTITY), 'CONTEXT_FIELDS_MISMATCH')
    require(all(context[k] is not None and context[k] != '' for k in IDENTITY), 'CONTEXT_INCOMPLETE')
    require(context['namespace'] == 'SHADOW_V4', 'NAMESPACE_MISMATCH')
    require(type(context['publication_revision']) is int and context['publication_revision'] > 0, 'REVISION_INVALID')
    return 'shadow-' + digest(context)


def unknown(reason='SOURCE_FIELD_UNAVAILABLE'):
    return {'value': None, 'quality': 'UNKNOWN', 'reason': reason, 'source': None}


class ShadowContextReader:
    def __init__(self, root, *, simulation_fixture=None):
        self.root = Path(root).resolve()
        schema_root = self.root if (self.root / 'config/v4_17_shadow_ui_contract_v1.json').is_file() else Path(__file__).resolve().parents[2]
        self.contract = json.loads((schema_root / 'config/v4_17_shadow_ui_contract_v1.json').read_bytes())
        require(self.contract['identity_fields'] == list(IDENTITY), 'CONTRACT_IDENTITY_DRIFT')
        require(list(self.contract['components']) == list(COMPONENTS), 'COMPONENT_REGISTRY_DRIFT')
        require(set(self.contract['routes']) == {PREFIX+k for k in ('context', *COMPONENTS)}
                and all(route['methods'] == ['GET'] for route in self.contract['routes'].values()), 'READ_ONLY_ROUTE_REGISTRY_DRIFT')
        self.fixture = copy.deepcopy(simulation_fixture)

    def _exact(self, binding):
        require(set(binding) == {'path', 'sha256', 'bytes'}, 'EXACT_BINDING_REQUIRED')
        path = (self.root / binding['path']).resolve()
        require(path.is_relative_to(self.root) and not Path(binding['path']).is_absolute(), 'PATH_OUTSIDE_REPOSITORY')
        raw = path.read_bytes()
        require(len(raw) == binding['bytes'] and hashlib.sha256(raw).hexdigest() == binding['sha256'], 'SOURCE_DIGEST_MISMATCH')
        return json.loads(raw)

    def _real(self):
        authority_path = self.root / 'config/v4_17_shadow_ui_source_v1.json'
        if not authority_path.is_file():
            return None
        authority = json.loads(authority_path.read_bytes())
        require(authority['contract_id'] == 'V4_17_EXACT_READBACK_SOURCE_V1', 'SOURCE_CONTRACT_MISMATCH')
        if authority['accepted_readback'] is None:
            return None
        # No query, environment variable, directory scan or latest-head lookup can
        # confer acceptance. Receipt pins the entire readback manifest.
        manifest = self._exact(authority['accepted_readback'])
        receipt = self._exact(authority['external_acceptance'])
        require(receipt['decision'] == 'PASS_REAL_SHADOW_UI_READBACK'
                and receipt['readback_sha256'] == authority['accepted_readback']['sha256'], 'READBACK_NOT_EXTERNALLY_ACCEPTED')
        context = manifest['context']
        token = context_token(context)
        require(context['evidence_origin'] == 'PIT_OBSERVED', 'REAL_ORIGIN_REQUIRED')
        require(receipt['context_token'] == token, 'ACCEPTANCE_CONTEXT_MISMATCH')
        path = (self.root / manifest['database_path']).resolve()
        require(not Path(manifest['database_path']).is_absolute() and path.is_relative_to(self.root), 'DATABASE_OUTSIDE_REPOSITORY')
        # mode=ro never creates a missing SQLite file; no runtime writer import.
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as connection:
            connection.execute('PRAGMA query_only=ON')
            connection.execute('BEGIN')
            require(connection.execute('SELECT environment,evidence_origin FROM storage_identity WHERE singleton=1').fetchall()
                    == [('REAL', 'PIT_OBSERVED')], 'STORAGE_ORIGIN_MISMATCH')
            facts = {}
            for name, binding in manifest['facts'].items():
                row = connection.execute('SELECT namespace,execution_mode,evidence_origin,payload,digest FROM facts WHERE kind=? AND id=?',
                                         (binding['kind'], binding['id'])).fetchone()
                require(row is not None, 'EXACT_FACT_MISSING')
                require(row[:3] == ('SHADOW_V4', 'SHADOW', 'PIT_OBSERVED'), 'FACT_ORIGIN_MISMATCH')
                value = json.loads(row[3])
                require(digest(value) == row[4] == binding['sha256'], 'FACT_DIGEST_MISMATCH')
                require(all(value.get(k) == v for k, v in zip(('namespace', 'execution_mode', 'evidence_origin'), row[:3])), 'FACT_IDENTITY_MISMATCH')
                for payload in (value, value.get('value', {})):
                    for key in ('model_contract_id', 'state_lineage_id'):
                        require(key not in payload or payload[key] == context[key], 'MODEL_LINEAGE_MISMATCH')
                    for key in ('publication_id', 'shadow_publication_id'):
                        # Older enrollments remain valid; exact accepted readback
                        # binds them explicitly rather than relabeling their T0.
                        if binding['kind'] in ('publication', 'slot', 'state', 'observation', 'health'):
                            require(key not in payload or payload[key] == context['publication_id'], 'FACT_PUBLICATION_MISMATCH')
                facts[name] = value
            self._check_native_identity(context, facts)
            components = {}
            for component, spec in self.contract['components'].items():
                try:
                    items = []
                    for record in manifest['components'][component]:
                        require(set(record) <= set(spec['fields']), 'UNREGISTERED_FIELDS')
                        fields = {}
                        for field, mapping in spec['fields'].items():
                            binding = record.get(field)
                            if binding is None:
                                fields[field] = unknown()
                                continue
                            fact = facts[binding['fact']]
                            require(manifest['facts'][binding['fact']]['kind'] in mapping['fact_kinds'], 'FIELD_SOURCE_KIND_MISMATCH')
                            require(binding['path'] in mapping['paths'], 'FIELD_SOURCE_PATH_MISMATCH')
                            value = fact
                            for segment in binding['path'].split('.'):
                                value = value.get(segment) if isinstance(value, dict) else None
                            fields[field] = unknown(str(value) if value is not None else 'SOURCE_FIELD_UNAVAILABLE') if value is None or (isinstance(value, str) and value.startswith('UNKNOWN')) else {
                                'value': value, 'quality': binding['quality'], 'reason': binding.get('reason'),
                                'source': dict(manifest['facts'][binding['fact']], field_path=binding['path'])}
                        items.append({'fields': fields})
                    components[component] = {'context_token': token, 'context': context, 'source_quality': manifest['source_quality'], 'items': items}
                except (KeyError, TypeError, ResearchContextError) as exc:
                    components[component] = {'error': str(exc) if isinstance(exc, ResearchContextError) else 'COMPONENT_SOURCE_INVALID'}
            return {'context': context, 'context_token': token, 'components': components,
                    'source_quality': manifest['source_quality'], 'real_sample_count': facts['health']['PIT_OBSERVED_REAL_SAMPLES'],
                    'evidence_label': 'PIT_OBSERVED'}

    @staticmethod
    def _check_native_identity(context, facts):
        publication, slot, state, daily = (facts[k] for k in ('publication', 'slot', 'state', 'daily_input'))
        require(slot['slot_status'] == 'ACCEPTED_ON_TIME', 'PUBLICATION_SLOT_NOT_ACCEPTED')
        require(publication['slot_id'] == slot['slot_id'], 'SLOT_BINDING_MISMATCH')
        for value in (publication, slot, state):
            for field, native in (('publication_id', 'publication_id'), ('publication_revision', 'revision'), ('trade_date', 'trade_date')):
                require(value[native] == context[field], 'PUBLICATION_CONTEXT_MISMATCH')
        for value in (slot, state):
            require(all(value[k] == context[k] for k in ('model_contract_id', 'state_lineage_id')), 'MODEL_LINEAGE_MISMATCH')
        require(slot['parameter_set_id'] == context['parameter_set_id'], 'PARAMETER_MISMATCH')
        require(slot['source_manifest_digest'] == publication['source_manifest_digest'] == context['source_manifest_digest'], 'MANIFEST_MISMATCH')
        require(daily['daily_input_digest'] == context['daily_input_digest'] and daily['target_trade_date'] == context['trade_date'], 'DAILY_INPUT_MISMATCH')

    def _load(self):
        try:
            bundle = copy.deepcopy(self.fixture) if self.fixture is not None else self._real()
            if bundle is None:
                return None
            expected_origin = 'ACTIVATION_SIMULATION' if self.fixture is not None else 'PIT_OBSERVED'
            require(bundle['context']['evidence_origin'] == expected_origin, 'EVIDENCE_ORIGIN_MISMATCH')
            require(self.fixture is None or (bundle['evidence_label'] == 'NOT_REAL_EVIDENCE' and bundle['real_sample_count'] == 0), 'SIMULATION_LABEL_REQUIRED')
            require(bundle['context_token'] == context_token(bundle['context']), 'CONTEXT_TOKEN_MISMATCH')
            require(bundle['source_quality'] in ('KNOWN', 'DEGRADED', 'UNKNOWN'), 'SOURCE_QUALITY_REQUIRED')
            require(set(bundle['components']) == set(COMPONENTS), 'COMPONENTS_INCOMPLETE')
            # Validate per-component on read, so one malformed scope does not
            # silently promote data or block otherwise valid scopes.
            return bundle
        except ResearchContextError:
            raise
        except (KeyError, TypeError, ValueError, OSError, sqlite3.Error) as exc:
            raise ResearchContextError('SHADOW_SOURCE_INVALID') from exc

    def _component(self, name, bundle):
        component = bundle['components'][name]
        require('error' not in component, component.get('error', 'COMPONENT_SOURCE_INVALID'))
        require(component['context_token'] == bundle['context_token'] and component['context'] == bundle['context'], 'COMPONENT_CONTEXT_MISMATCH')
        require(component.get('source_quality') in ('KNOWN', 'DEGRADED', 'UNKNOWN'), 'SOURCE_QUALITY_REQUIRED')
        registry = self.contract['components'][name]['fields']
        for item in component['items']:
            require(set(item) == {'fields'} and set(item['fields']) == set(registry), 'UNREGISTERED_FIELDS')
            fields = item['fields']
            for cell in fields.values():
                require(set(cell) == {'value', 'quality', 'reason', 'source'}, 'FIELD_QUALITY_REQUIRED')
                require(cell['quality'] in ('KNOWN', 'DEGRADED', 'UNKNOWN', 'PENDING', 'RIGHT_CENSORED', 'NOT_AUTHORIZED'), 'FIELD_QUALITY_INVALID')
                if cell['quality'] in ('UNKNOWN', 'PENDING', 'RIGHT_CENSORED', 'NOT_AUTHORIZED'):
                    require(cell['value'] is None and bool(cell['reason']), 'UNKNOWN_OR_PENDING_VALUE_FORBIDDEN')
                else:
                    require(cell['value'] is not None and not (isinstance(cell['value'], str) and cell['value'].startswith('UNKNOWN')) and bool(cell['source']), 'KNOWN_VALUE_REQUIRES_SOURCE')
                if self.fixture is None and cell['source'] is not None:
                    require(set(cell['source']) == {'kind', 'id', 'sha256', 'field_path'}, 'UNVERIFIED_FIELD_SOURCE')
            if name == 'settlement':
                outcome, revision, expected, censor = (fields[k] for k in ('outcome', 'outcome_revision', 'bound_outcome_revision', 'right_censor'))
                if revision['value'] is not None:
                    require(revision['value'] == expected['value'], 'STALE_OUTCOME_REVISION')
                require(not (censor['value'] in (True, 'RIGHT_CENSORED') and outcome['quality'] in ('KNOWN', 'DEGRADED')), 'RIGHT_CENSORED_OUTCOME_FORBIDDEN')
                if fields['outcome_status']['value'] in ('PENDING', 'MATURED_DATA_MISSING', 'IDENTITY_UNKNOWN', 'ADJUSTMENT_UNKNOWN'):
                    require(outcome['value'] is None, 'PENDING_OUTCOME_FORBIDDEN')
                if outcome['quality'] in ('KNOWN', 'DEGRADED'):
                    require(fields['outcome_status']['value'] == 'OBSERVED' and censor['value'] in (False, 'OBSERVED')
                            and revision['value'] is not None and expected['value'] is not None, 'OBSERVED_OUTCOME_IDENTITY_REQUIRED')
        return component

    def handle(self, path, query):
        try:
            name = path.removeprefix(PREFIX)
            if name not in ('context', *COMPONENTS):
                return 404, {'status': 'BLOCKED', 'code': 'SHADOW_ROUTE_NOT_FOUND'}
            require(set(query) <= {'context_token', 'q', 'page', 'page_size', 'entity_id', *IDENTITY}, 'UNSUPPORTED_QUERY_NO_DISCOVERY')
            bundle = self._load()
            if bundle is None:
                require(not query, 'NO_REAL_CONTEXT_TO_RESOLVE')
                return 200, {'status': 'NO_REAL_SHADOW_DATA', 'context': None, 'context_token': None,
                             'real_sample_count': 0, 'source_quality': 'UNKNOWN', 'items': [],
                             'evidence_label': 'NO_REAL_SHADOW_DATA', 'component': name}
            if name != 'context':
                require(query.get('context_token') == bundle['context_token'], 'CONTEXT_TOKEN_MISMATCH')
            elif 'context_token' in query:
                require(query['context_token'] == bundle['context_token'], 'CONTEXT_TOKEN_MISMATCH')
            for key in IDENTITY:
                if key in query:
                    require(str(query[key]) == str(bundle['context'][key]), key.upper() + '_MISMATCH')
            output = {k: copy.deepcopy(bundle[k]) for k in ('context', 'context_token', 'source_quality', 'real_sample_count', 'evidence_label')}
            output.update(status='ACTIVATION_SIMULATION' if self.fixture is not None else 'READY', component=name)
            if name == 'context':
                output['items'] = []
            else:
                component = self._component(name, bundle)
                output['source_quality'] = component['source_quality']
                items = component['items']
                if query.get('entity_id'):
                    items = [i for i in items if i['fields'].get('entity_id', {}).get('value') == query['entity_id']]
                if query.get('q'):
                    items = [i for i in items if query['q'].casefold() in canonical(i).decode().casefold()]
                page, size = int(query.get('page', 1)), int(query.get('page_size', 20))
                require(page > 0 and 1 <= size <= 100, 'PAGINATION_INVALID')
                output.update(items=copy.deepcopy(items[(page-1)*size:page*size]), total=len(items), page=page, page_size=size,
                              has_more=page*size < len(items))
            return 200, output
        except ResearchContextError as exc:
            return 409, {'status': 'BLOCKED', 'code': str(exc), 'component': path.removeprefix(PREFIX), 'items': [], 'real_sample_count': 0}
        except (KeyError, TypeError, ValueError) as exc:
            return 409, {'status': 'BLOCKED', 'code': 'COMPONENT_INVALID', 'component': path.removeprefix(PREFIX), 'items': [], 'real_sample_count': 0}
