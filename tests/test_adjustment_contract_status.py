from pathlib import Path
from validation.phase0_2c import REQUIRED, release_gate

ROOT = Path(__file__).resolve().parents[1]


def test_release_contract_and_dataset_permissions_agree():
    result = release_gate(dict.fromkeys(REQUIRED, True))
    contract = (ROOT/'docs/ADJUSTMENT_CONTRACT_V0_3.md').read_text('utf8')
    dataset = (ROOT/'docs/ADJUSTED_DATASET_CONTRACT_V0_3.md').read_text('utf8')
    for key in ('adjustment_identity','project_price_basis','adjustment_status'):
        assert result[key] in contract
        assert result[key] in dataset
    assert 'external_vendor_exact_match_required = FALSE' in contract
    assert 'amount_basis = RAW' in contract and 'volume_basis = RAW' in contract
    assert 'data/normalized/adjusted_daily.parquet' in dataset
    assert 'emits no adjusted dataset' in dataset
    assert 'raw fields are null' in dataset


def test_required_limitations_and_examples_present():
    text = (ROOT/'docs/KNOWN_LIMITATIONS.md').read_text('utf8')
    for required in ('known-limitations-v0.3','CROSS_VENDOR_QFQ_EXACT_EQUALITY_NOT_GUARANTEED',
                     'HISTORICAL_ADJUSTMENT_GOVERNANCE','Category 15', 'TDX-native adjustment is authoritative',
                     '276.00/10','276.73/10','MULTIPLICATIVE_CHAIN_ALIGNED',
                     'CASH_ADJUSTMENT_HISTORY_DIVERGENT','PROVIDER_BASIS_SENSITIVE_DEEP_HISTORY'):
        assert required in text
