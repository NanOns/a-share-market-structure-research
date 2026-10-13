"""Versioned research-operation admission, independent of statistical proof gates.

No network, source capture, scanner, Focus mutation, or trading actions occur here.
Callers supply exact references to real producer outputs and independent QA receipts.
"""
import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

POLICY_ID = 'V4_OPERATIONAL_PRODUCTION_RELEASE_POLICY_V1'
STATES = {'OPERATIONAL_PRODUCTION_ACTIVE', 'DATA_PENDING', 'SOURCE_INCOMPLETE',
          'QUALITY_DEGRADED', 'ENGINEERING_NOT_READY'}


class AdmissionError(ValueError):
    pass


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def project_path(root, name):
    root = Path(root).resolve()
    if not isinstance(name, str) or Path(name).is_absolute() or ':' in name or '\\' in name:
        raise AdmissionError('PROJECT_RELATIVE_PATH_REQUIRED')
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise AdmissionError('PATH_ESCAPE')
    return path


def read_ref(root, ref):
    path = project_path(root, ref['path'])
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AdmissionError('BOUND_SOURCE_UNAVAILABLE:' + ref['path']) from exc
    if len(raw) != ref['bytes'] or sha(raw) != ref['sha256']:
        raise AdmissionError('BOUND_SOURCE_CHANGED:' + ref['path'])
    return raw


def binding(root, name):
    raw = project_path(root, name).read_bytes()
    return dict(path=name, bytes=len(raw), sha256=sha(raw))


def _time(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise AdmissionError('TIMEZONE_REQUIRED')
    return result


def admit(root, policy_ref, request, dependencies=None):
    """Return scoped admission; no historical production_permission is modified."""
    policy = json.loads(read_ref(root, policy_ref))
    if policy['contract_id'] != POLICY_ID or policy['trading_action_authorized'] or policy['tdx_write_authorized']:
        raise AdmissionError('POLICY_INVALID')
    if request['feature_id'] not in policy['feature_ids']:
        raise AdmissionError('UNREGISTERED_FEATURE')
    metadata = request['metadata']
    required = policy['required_metadata']
    if any(not metadata.get(k) for k in required):
        raise AdmissionError('METADATA_INCOMPLETE')
    if metadata['evidence_origin'] not in ('REAL_ACCEPTED_SOURCE', 'REAL_PRODUCER_RUN'):
        raise AdmissionError('NON_REAL_OUTPUT')
    if metadata['trading_date'] > metadata['source_as_of'][:10] or _time(metadata['source_as_of']) > _time(metadata['published_at']):
        raise AdmissionError('FUTURE_SOURCE')
    if metadata['input_digest'] != request['input']['sha256'] or metadata['source_snapshot'] != request['input']['sha256']:
        raise AdmissionError('INPUT_IDENTITY_MISMATCH')
    for key in ('input', 'output', 'code', 'contract', 'qa'):
        read_ref(root, request[key])
    qa = json.loads(read_ref(root, request['qa']))
    if qa.get('contract_id') != 'V4_OPERATIONAL_INDEPENDENT_QA_V1' or qa.get('status') != 'PASS':
        raise AdmissionError('INDEPENDENT_QA_REQUIRED')
    if qa.get('feature_id') != request['feature_id'] or qa.get('checked_by') == metadata['owner']:
        raise AdmissionError('QA_SCOPE_OR_INDEPENDENCE_INVALID')
    if qa.get('verifier') != policy['independent_verifier']:
        raise AdmissionError('UNAPPROVED_QA_VERIFIER')
    read_ref(root, qa['verifier'])
    for key in ('input', 'output', 'code', 'contract'):
        if qa.get(key) != request[key]:
            raise AdmissionError('QA_BINDING_MISMATCH:' + key)
    if qa.get('metadata') != metadata or qa.get('policy') != policy_ref:
        raise AdmissionError('QA_CONTEXT_MISMATCH')
    mandatory = {'REAL_LINEAGE', 'SCHEMA', 'FIELD_QUALITY', 'NO_FUTURE', 'SOURCE_READBACK', 'ROLLBACK_COMPATIBLE'}
    if any(qa.get('checks', {}).get(k) != 'PASS' for k in mandatory):
        raise AdmissionError('QA_CHECK_MISSING')
    quality = metadata['data_quality_state']
    if quality not in ('KNOWN', 'QUALITY_DEGRADED', 'SOURCE_INCOMPLETE', 'PENDING', 'RIGHT_CENSORED'):
        raise AdmissionError('INVALID_QUALITY')
    # PENDING/right censoring are valid lifecycle outputs, not evidence of matured returns.
    if quality == 'SOURCE_INCOMPLETE':
        raise AdmissionError('REQUIRED_SOURCE_INCOMPLETE')
    evidence = metadata['evidence_state']
    if evidence not in ('VALIDATION_ONGOING', 'HISTORICALLY_ACCEPTED_SCOPED', 'STATISTICALLY_VALIDATED_SCOPED'):
        raise AdmissionError('INVALID_EVIDENCE_STATE')
    if evidence == 'STATISTICALLY_VALIDATED_SCOPED':
        raise AdmissionError('STATISTICAL_CLAIM_REQUIRES_SEPARATE_POLICY')
    deps = policy['dependencies'].get(request['feature_id'], [])
    for name in deps:
        if not dependencies or dependencies.get(name, {}).get('operational_state') != 'OPERATIONAL_PRODUCTION_ACTIVE':
            raise AdmissionError('DEPENDENCY_NOT_OPERATIONAL:' + name)
    return dict(feature_id=request['feature_id'], operational_state='OPERATIONAL_PRODUCTION_ACTIVE',
                evidence_state=evidence, data_quality_state=quality, metadata=metadata,
                policy=policy_ref, request=request, old_permission_migration='HISTORICAL_FACT_PRESERVED',
                long_term_validation_blocks_operation=False, trading_action_authorized=False)


def presentation(admission, requested_date):
    """A missing next session never destroys the last actual production result."""
    return dict(operational_state='DATA_PENDING' if requested_date > admission['metadata']['trading_date'] else admission['operational_state'],
                last_successful_trading_date=admission['metadata']['trading_date'],
                evidence_state=admission['evidence_state'], data_quality_state=admission['data_quality_state'],
                result_available=True)


class ReleaseStore:
    """Blue/green immutable releases; serialized CAS and exact rollback/readback.

    Store is restricted to a new project-owned subtree. Legacy accepted pointers
    and TDX paths cannot be used as store destinations.
    """
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.directory = project_path(root, 'runtime/operational_release_v1')
        self.directory.mkdir(parents=True, exist_ok=True)
        self.pointer = self.directory / 'active.json'

    @contextmanager
    def _lock(self):
        lock = self.directory / 'publish.lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise AdmissionError('PUBLISH_BUSY') from exc
        try:
            os.close(fd)
            yield
        finally:
            lock.unlink()

    def _write(self, path, raw):
        if not path.resolve().is_relative_to(self.directory):
            raise AdmissionError('WRITE_SCOPE_ESCAPE')
        temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with temp.open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()

    def current_digest(self):
        return sha(self.pointer.read_bytes()) if self.pointer.exists() else None

    def read(self):
        pointer = json.loads(self.pointer.read_bytes())
        release = json.loads(read_ref(self.root, pointer['release']))
        if release['contract_id'] != 'V4_OPERATIONAL_RELEASE_V1':
            raise AdmissionError('INVALID_RELEASE')
        for item in release['admissions']:
            actual = admit(self.root, item['policy'], item['request'], {r['feature_id']: r for r in release['admissions']})
            if actual != item:
                raise AdmissionError('ADMISSION_CHANGED')
        return release

    def publish(self, release, expected_digest, readback=None):
        if release.get('contract_id') != 'V4_OPERATIONAL_RELEASE_V1' or not release.get('admissions'):
            raise AdmissionError('EMPTY_OR_INVALID_RELEASE')
        if len({r['feature_id'] for r in release['admissions']}) != len(release['admissions']):
            raise AdmissionError('DUPLICATE_FEATURE')
        if any(r['metadata']['release_id'] != release.get('release_id') for r in release['admissions']):
            raise AdmissionError('RELEASE_ID_MISMATCH')
        dates = {r['metadata']['trading_date'] for r in release['admissions']}
        inputs = {r['metadata']['source_snapshot'] for r in release['admissions']}
        if len(dates) != 1 or len(inputs) != 1:
            raise AdmissionError('MIXED_CONTEXT')
        deps = {r['feature_id']: r for r in release['admissions']}
        for item in release['admissions']:
            if admit(self.root, item['policy'], item['request'], deps) != item:
                raise AdmissionError('ADMISSION_CHANGED')
        raw = encoded(release)
        target = self.directory / (sha(raw) + '.json')
        with self._lock():
            if self.current_digest() != expected_digest:
                raise AdmissionError('STALE_PREDECESSOR')
            previous = self.pointer.read_bytes() if self.pointer.exists() else None
            if previous:
                # Retain exact rollback bytes even when the caller exits after swap.
                self._write(self.directory / ('prior_' + sha(previous) + '.json'), previous)
            if target.exists() and target.read_bytes() != raw:
                raise AdmissionError('IMMUTABLE_RELEASE_COLLISION')
            if not target.exists():
                self._write(target, raw)
            pointer = encoded(dict(release=binding(self.root, target.relative_to(self.root).as_posix())))
            self._write(self.pointer, pointer)
            try:
                result = self.read()
                if result != release:
                    raise AdmissionError('POST_SWAP_READBACK_FAILED')
                if readback:
                    readback(result)
            except Exception:
                if previous is None:
                    self.pointer.unlink()
                else:
                    self._write(self.pointer, previous)
                raise
        return dict(status='PASS', pointer_digest=sha(pointer), release_sha256=sha(raw),
                    previous_pointer_digest=sha(previous) if previous else None)

    def rollback(self, previous_pointer_digest, expected_digest):
        """Restore an exact retained predecessor after validating its sources."""
        if not isinstance(previous_pointer_digest, str) or len(previous_pointer_digest) != 64 or any(c not in '0123456789abcdef' for c in previous_pointer_digest):
            raise AdmissionError('INVALID_PREDECESSOR_DIGEST')
        with self._lock():
            if self.current_digest() != expected_digest:
                raise AdmissionError('STALE_PREDECESSOR')
            previous = (self.directory / ('prior_' + previous_pointer_digest + '.json')).read_bytes()
            if sha(previous) != previous_pointer_digest:
                raise AdmissionError('PREDECESSOR_CORRUPT')
            old = self.pointer.read_bytes()
            self._write(self.pointer, previous)
            try:
                self.read()
            except Exception:
                self._write(self.pointer, old)
                raise
        return dict(status='PASS', restored_pointer_digest=previous_pointer_digest)
