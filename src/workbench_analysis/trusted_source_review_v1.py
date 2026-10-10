"""Fail-closed deployed boundary plus an explicitly isolated authority protocol.

No production trust anchor/service is installed. The HMAC authority below is a
test transport oracle, never an accepted production signer or Writer Grant.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
from .v4_14_replay_io import canonical, exact, ref, publish
from .validation_cohort_read_contract_r3 import instant
from .operational_daily_storage_v1 import atomic_json, exclusive_lock
from .tdx_official_daily_source import _atomic_write

CONTRACT='INDEPENDENT_SOURCE_REVIEW_TRUST_BOUNDARY_V1'


def resolve(root, *, capability, review_binding=None, **context):
    if review_binding:exact(root,review_binding)
    return dict(contract_id=CONTRACT,status='NOT_ADMITTED',
        candidate_status='UNTRUSTED_REVIEW_CANDIDATE',capability=capability,
        review_binding=review_binding,reason='ACCEPTED_INDEPENDENT_REVIEW_SERVICE_NOT_DEPLOYED',
        trusted_source_resolved=False,production_write_authorized=False,
        STATE_SOURCE_ADMITTED=False,IDENTITY_AUTHORITY_ADMITTED=False)


class IsolatedReviewAuthority:
    """Pinned issuer/secret/scope/revocation state live outside document inputs.

    Only isolated tests construct this transport. Production resolve() has no
    parameter that accepts it, a caller key, a local Head or a claimed role.
    """
    def __init__(self, *, secret, issuer, capabilities, revoked=(), epoch=1):
        self._secret=secret;self._issuer=issuer;self._capabilities=frozenset(capabilities)
        self._revoked=frozenset(revoked);self._epoch=epoch

    def verify(self, root, *, review_binding, expected, cutoff):
        try:
            envelope=json.loads(exact(root,review_binding));claim=envelope['claims']
            signature=hmac.new(self._secret,canonical(claim),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature,envelope.get('signature','')):
                raise ValueError('ISSUER_SIGNATURE_INVALID')
            if claim.get('issuer')!=self._issuer or claim.get('capability') not in self._capabilities:
                raise ValueError('ISSUER_OR_CAPABILITY_NOT_PINNED')
            if claim.get('audience')!='ISOLATED_SOURCE_ADMISSION_TEST_ONLY':
                raise ValueError('PRODUCTION_AUDIENCE_FORBIDDEN')
            if claim.get('review_id') in self._revoked or claim.get('revoked') is not False or claim.get('revocation_epoch')!=self._epoch:
                raise ValueError('REVIEW_REVOKED_OR_REVOCATION_STATE_STALE')
            if not instant(claim['valid_from'])<=instant(cutoff)<=instant(claim['valid_until']):
                raise ValueError('REVIEW_NOT_CURRENT')
            if any(claim.get(k)!=v for k,v in expected.items()):
                raise ValueError('EXACT_SCOPE_REVISION_SOURCE_OR_HEAD_CAS_MISMATCH')
            if claim.get('evidence_class')!='SYNTHETIC_ISOLATED_TEST_ONLY':
                raise ValueError('ISOLATED_AUTHORITY_CANNOT_ADMIT_REAL_SOURCE')
            exact(root,claim['candidate'])
            # Parent bytes are checked atomically at publication. Its signed
            # binding remains the predecessor after successful CAS/readback.
            if len(claim['parent_head'].get('sha256',''))!=64:
                raise ValueError('EXACT_HEAD_CAS_BINDING_REQUIRED')
            if not claim.get('sources'):raise ValueError('ORIGINAL_SOURCE_SET_REQUIRED')
            for binding in claim['sources'].values():
                doc=json.loads(exact(root,binding))
                if doc.get('T0')!=claim['trade_date'] or doc.get('revision')!=claim['revision']:
                    raise ValueError('ORIGINAL_SOURCE_DATE_OR_REVISION_MISMATCH')
                if not (instant(doc['first_available'])<=instant(doc['received_at'])<=instant(cutoff)):
                    raise ValueError('ORIGINAL_SOURCE_CLOCK_MISMATCH')
            return dict(contract_id=CONTRACT,status='ISOLATED_REVIEW_VERIFIED',
                claims=claim,review=review_binding,production_write_authorized=False,
                STATE_SOURCE_ADMITTED=False,IDENTITY_AUTHORITY_ADMITTED=False)
        except (KeyError,TypeError,ValueError,OSError) as error:
            return dict(contract_id=CONTRACT,status='NOT_ADMITTED',candidate_status='UNTRUSTED_REVIEW_CANDIDATE',
                reason=str(error),production_write_authorized=False,
                STATE_SOURCE_ADMITTED=False,IDENTITY_AUTHORITY_ADMITTED=False)

    def publish_identity(self, root, *, candidate_binding, review_binding, head_path, cutoff, readback):
        path=Path(head_path)
        if path.is_absolute() or '..' in path.parts or path.parts[:2]!=('docs','evidence'):
            raise ValueError('ISOLATED_CAS_ONLY_NO_PRODUCTION_HEAD')
        candidate=json.loads(exact(root,candidate_binding))
        if candidate.get('status')!='IDENTITY_AUTHORITY_CANDIDATE_COMPLETE' or candidate.get('source_gaps'):
            raise ValueError('IDENTITY_SOURCE_GAPS')
        expected=dict(capability='DATED_IDENTITY_SOURCE_REVIEW',trade_date=candidate['T0'],
            revision=candidate['revision'],candidate=candidate_binding,sources=candidate['sources'],
            parent_head=candidate['parent_head'],scope='MAIN_DD_DATED_IDENTITY_CANDIDATE')
        verified=self.verify(root,review_binding=review_binding,expected=expected,cutoff=cutoff)
        if verified['status']!='ISOLATED_REVIEW_VERIFIED':raise ValueError(verified['reason'])
        root=Path(root);head=root/path
        with exclusive_lock(root,head.with_suffix('.lock')):
            current=json.loads(head.read_bytes())
            if (current.get('contract_id')=='ISOLATED_DATED_IDENTITY_OWNER_V1' and
                    current.get('owner')==candidate_binding and current.get('review')==review_binding and
                    current.get('predecessor')==candidate['parent_head']):
                return dict(status='ISOLATED_IDENTITY_OWNER_ALREADY_PUBLISHED',head=ref(root,path),
                    candidate=candidate_binding,review=review_binding,production_write_authorized=False)
            if ref(root,path)!=candidate['parent_head']:raise ValueError('ISOLATED_HEAD_CAS_STALE')
            before=head.read_bytes()
            new=dict(contract_id='ISOLATED_DATED_IDENTITY_OWNER_V1',accepted_trade_date=candidate['T0'],
                owner=candidate_binding,review=review_binding,predecessor=candidate['parent_head'],
                evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY',production_write_authorized=False)
            atomic_json(root,head,new);published=ref(root,path)
            try:
                # Revalidate revocation, source bytes and scope after CAS too.
                second=self.verify(root,review_binding=review_binding,expected=expected,cutoff=cutoff)
                if second['status']!='ISOLATED_REVIEW_VERIFIED' or readback(new).get('head_sha256')!=published['sha256']:
                    raise ValueError('ISOLATED_OWNER_READBACK_FAILED')
            except Exception:
                if ref(root,path)!=published:raise ValueError('ISOLATED_ROLLBACK_HEAD_MOVED')
                _atomic_write(head,before,tdx_root=Path('D:/new_tdx'))
                raise
            return dict(status='ISOLATED_IDENTITY_OWNER_PUBLISHED',head=published,
                candidate=candidate_binding,review=review_binding,production_write_authorized=False)
