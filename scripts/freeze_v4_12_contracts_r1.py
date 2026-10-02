"""R1 generator retired by external audit; use explicit R2 owner table."""
from scripts.validate_v4_12_contract_freeze_r1 import load_configs

if __name__ == "__main__":
    if load_configs()['field_registry'].get('time_counter_amendment')=='R2.1':
        from scripts.repair_v4_12_time_counter_r2_1 import repair
    else:
        from scripts.repair_v4_12_authority_r2 import repair
    repair()
