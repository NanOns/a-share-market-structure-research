"""Audit-only field provenance; never change canonical entity values or IDs."""
from __future__ import annotations
import hashlib

FIELDS=('symbol','security_type','board','listing_anchor','lifecycle','alias_relation','stable_id_inputs')

def field_matrix(record, *, tnf_present=False, official=None, official_alias=None):
    """Separate observed corroboration from a historical legal lifecycle owner."""
    provider=record.get('source_contract_id')=='BAOSTOCK_LIFECYCLE_FACTS_R5_V1'
    origin='PROVIDER_RECONSTRUCTED_FACT' if provider else 'UNKNOWN'
    source=record.get('source_revision_id')
    result={f:dict(classification=origin,primary_owner=record.get('source_contract_id'),source_revision_id=source,
                   formal_historical_owner='UNRESOLVED_MASTER_AUTHORITY',lineage='RECONSTRUCTED_CORRECTED') for f in FIELDS}
    result['symbol'].update(local_current_corrob='LOCAL_TDX_AUTHORITY_CONFIRMED' if tnf_present else 'UNKNOWN',
                            local_proof_scope='CURRENT_SOURCE_CODE_EXISTS_ONLY',historical_proof_scope='DATED_TDX_QUOTE_SOURCE_KEY')
    result['security_type'].update(local_decoder_proves_historical_type=False,current_official_corrob=bool(official))
    result['board'].update(current_official_board=official.get('board') if official else None,
                           historical_code_pattern_proves_board=False)
    anchor=record.get('list_date')
    result['listing_anchor'].update(value=anchor,official_current_catalogue_date=official.get('list_date') if official else None,
        independent_corrob='MATCH' if official and official.get('list_date')==anchor else 'DISCREPANCY' if official else 'NOT_PRESENT_CURRENT_CATALOGUE')
    result['lifecycle'].update(list_date=anchor,delist_date=record.get('delist_date'),local_day_boundary_proves_legal_lifecycle=False,
                               current_active_catalogue_proves_historical_delist=False)
    result['alias_relation']=dict(classification='OFFICIAL_EXCHANGE_AUTHORITY_CONFIRMED' if official_alias else 'UNKNOWN',
        primary_owner='ACCEPTED_OFFICIAL_CODE_CHANGE_EVENT_INDEX' if official_alias else None,
        evidence=official_alias,ordinary_source_key='NO_ALIAS_RELATION_REQUIRED' if not official_alias else None,
        fingerprint='RESEARCH_ONLY_NO_AUTOMATIC_ENTITY_UNION')
    result['stable_id_inputs'].update(exchange=record.get('exchange'),anchor_symbol=record.get('symbol'),listing_date=anchor,
        derivation_owner='SECURITY_ENTITY_IDENTITY_V1_SHA256',derivation_proves_legal_identity=False)
    return result

def independently_check_stable_id(record, anchor_symbol=None):
    # This check does not import or call the canonical ID producer.
    raw=b'\x00'.join(str(v).encode('ascii') for v in [record['exchange'],anchor_symbol or record['symbol'],record['list_date']])
    expected='SEC-'+hashlib.sha256(raw).hexdigest()[:32].upper()
    return expected==record['security_id']
