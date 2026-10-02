"""R1 generator retired by external audit; use explicit R2 owner table."""
from scripts.repair_v4_12_authority_r2 import repair

if __name__ == "__main__":
    repair()
