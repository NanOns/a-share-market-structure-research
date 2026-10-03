"""Expanded accepted-owner and R18 regression; no deselection."""
import sys,json
from scripts import validate_r17r1_regression as inherited
inherited.EXTRA=inherited.EXTRA+['tests/test_r18a_runtime.py','tests/test_r18b_persisted.py','tests/test_r18c_oracle.py','tests/v4_11/test_confirmation.py','tests/v4_11/test_semantic_r2.py']
if __name__=='__main__':print(json.dumps(inherited.run(sys.argv[1]),sort_keys=True,ensure_ascii=False))
