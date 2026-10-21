"""Candidate-only FROZEN_INVALIDATION_CONTRACT_R2 evaluator."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


CONTRACT_ID='FROZEN_INVALIDATION_CONTRACT_R2'
ROOT=Path(__file__).resolve().parents[2]


def _number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0


def evaluate_frozen_invalidation(*,prior_episode,current_close,frozen_invalidation_level,
        current_price_basis_id,frozen_price_basis_id,current_bar_status,current_source_sha256,
        trade_date,source_trade_date):
    """Evaluate a frozen threshold without treating missing evidence as FALSE."""
    if not isinstance(prior_episode,dict) or not prior_episode.get('episode_id'):
        return dict(value='UNKNOWN' if prior_episode else 'NOT_APPLICABLE',status='NOT_APPLICABLE' if not prior_episode else 'UNKNOWN',
            reason='NO_PRIOR_EPISODE' if not prior_episode else 'PRIOR_EPISODE_ID_MISSING',contract_id=CONTRACT_ID)
    if prior_episode.get('invalidation_contract_id')!=CONTRACT_ID:
        return dict(value='UNKNOWN',status='UNKNOWN',reason='PRIOR_INVALIDATION_CONTRACT_MISSING_OR_UNSUPPORTED',contract_id=CONTRACT_ID)
    if current_bar_status!='ACTUAL':
        return dict(value='UNKNOWN',status='UNKNOWN',reason='CURRENT_ACTUAL_BAR_UNAVAILABLE',contract_id=CONTRACT_ID)
    if trade_date!=source_trade_date or not isinstance(trade_date,str) or trade_date>'2026-10-14':
        return dict(value='UNKNOWN',status='UNKNOWN',reason='T0_SOURCE_DATE_MISMATCH_OR_CUTOFF_EXCEEDED',contract_id=CONTRACT_ID)
    if not _number(current_close) or not _number(frozen_invalidation_level):
        return dict(value='UNKNOWN',status='UNKNOWN',reason='CLOSE_OR_FROZEN_LEVEL_MISSING_OR_INVALID',contract_id=CONTRACT_ID)
    if not isinstance(current_price_basis_id,str) or not current_price_basis_id or current_price_basis_id!=frozen_price_basis_id:
        return dict(value='UNKNOWN',status='UNKNOWN',reason='PRICE_BASIS_IDENTITY_MISMATCH',contract_id=CONTRACT_ID)
    if (not isinstance(current_source_sha256,str) or len(current_source_sha256)!=64 or
            any(c not in '0123456789abcdef' for c in current_source_sha256.lower())):
        return dict(value='UNKNOWN',status='UNKNOWN',reason='CURRENT_SOURCE_SHA256_INVALID',contract_id=CONTRACT_ID)
    value='TRUE' if current_close<=frozen_invalidation_level else 'FALSE'
    return dict(value=value,status='IMPLEMENTED',reason=None,contract_id=CONTRACT_ID,
        episode_id=prior_episode['episode_id'],current_close=current_close,
        frozen_invalidation_level=frozen_invalidation_level,price_basis_id=current_price_basis_id,
        current_source_sha256=current_source_sha256,trade_date=trade_date,source_trade_date=source_trade_date)


def load_contract():
    path=ROOT/'config/v4_r7_frozen_invalidation_contract_r2.json'
    raw=path.read_bytes();contract=json.loads(raw)
    if contract.get('contract_id')!=CONTRACT_ID or len(contract.get('vector_set',[]))<12:
        raise ValueError('R7_FROZEN_INVALIDATION_CONTRACT_INVALID')
    return contract,hashlib.sha256(raw).hexdigest()
