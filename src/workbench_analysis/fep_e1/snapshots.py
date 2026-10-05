"""FEP_SNAPSHOT_V1: exact consumed inputs, no latest-head resolution."""
import math
from .contracts import digest, exact, instant

DEPENDENCIES = ('publication', 'accepted_head', 'algorithm_contract', 'parameter_contract',
                'calendar', 'universe', 'adjustment_basis', 'feature_contract',
                'membership', 'state_event_revision', 'enrichment_revision')


def build(root, observation, revision, dependencies, values, registry, *, feature_cutoff,
          created_at, evidence_origin, execution_mode):
    if set(dependencies) != set(DEPENDENCIES):
        raise ValueError('FEP_CONSUMED_MANIFEST_INCOMPLETE')
    if instant(feature_cutoff) > instant(observation['slot_deadline']):
        raise ValueError('FEP_FEATURE_CUTOFF_AFTER_DEADLINE')
    if instant(created_at) < instant(feature_cutoff):
        raise ValueError('FEP_SNAPSHOT_CREATED_BEFORE_CUTOFF')
    if evidence_origin not in ('PIT_OBSERVED', 'RECONSTRUCTED_ASOF', 'RECONSTRUCTED_CORRECTED', 'DIAGNOSTIC_NON_PIT'):
        raise ValueError('FEP_EVIDENCE_ORIGIN_INVALID')
    # E1 has no live FIRST_OBSERVED capture service. Reconstruction cannot assert PIT.
    if evidence_origin == 'PIT_OBSERVED' or execution_mode != 'REPLAY':
        raise ValueError('FEP_PIT_CAPTURE_NOT_ENABLED')
    consumed = {}
    for key, binding in dependencies.items():
        if binding == 'NONE' and key in ('membership', 'state_event_revision', 'enrichment_revision'):
            continue
        consumed[key] = exact(root, binding)
        if instant(binding['system_available_at']) > instant(feature_cutoff):
            raise ValueError('FEP_DEPENDENCY_NOT_VISIBLE')
    fields = {f['field_name']: f for f in registry['fields']}
    for name, value in values.items():
        field = fields.get(name)
        if not field or field['status'] != 'IMPLEMENTED_EXACT_MAPPING':
            raise ValueError('FEP_FIELD_NOT_IMPLEMENTED')
        if observation['scope_id'] not in field['allowed_scopes'] or value['quality'] not in field['quality_allowlist']:
            raise ValueError('FEP_FIELD_SCOPE_OR_QUALITY')
        if value['value'] is None and field['required']:
            raise ValueError('FEP_REQUIRED_FEATURE_UNKNOWN')
        if isinstance(value['value'], float) and not math.isfinite(value['value']):
            raise ValueError('FEP_NONFINITE_FEATURE')
        if not all(k in field for k in ('dependency_key', 'field_path', 'quality_path', 'data_type')):
            raise ValueError('FEP_EXACT_FIELD_MAPPING_REQUIRED')
        def path(keys):
            result = consumed[field['dependency_key']]
            for key in keys:
                result = result[key]
            return result
        if path(field['field_path']) != value['value'] or path(field['quality_path']) != value['quality']:
            raise ValueError('FEP_FEATURE_CONSUMED_VALUE_MISMATCH')
        v = value['value']
        dtype = field['data_type']
        if v is not None and ((dtype in ('float64','float') and (type(v) not in (int,float)))
                             or (dtype in ('int64','integer') and type(v) is not int)
                             or (dtype == 'boolean' and type(v) is not bool)
                             or (dtype in ('enum','string') and not isinstance(v,str))):
            raise ValueError('FEP_FEATURE_TYPE_MISMATCH')
        if dtype == 'enum' and v is not None and v not in field.get('enum_values', ()):
            raise ValueError('FEP_FEATURE_ENUM_NOT_REGISTERED')
    if any(f['required'] and f['field_name'] not in values for f in fields.values()):
        raise ValueError('FEP_REQUIRED_FEATURE_MISSING')
    semantic = dict(observation_id=observation['observation_id'], observation_revision=revision,
                    feature_cutoff=feature_cutoff, dependency_manifest=dependencies,
                    values=values, evidence_origin=evidence_origin, execution_mode=execution_mode)
    return dict(semantic, feature_digest=digest(semantic), dependency_digest=digest(dependencies),
                created_at=created_at)
