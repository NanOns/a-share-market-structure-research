"""All prior accepted-owner/governance/runtime scopes, with consumption repair."""
import sys,json
from scripts import validate_r18r1_regression
inherited=validate_r18r1_regression.inherited
inherited.EXTRA=inherited.EXTRA+['tests/test_r18r1r1_consumption.py','tests/test_r18r1r1_canonical.py']
if __name__=='__main__':print(json.dumps(inherited.run(sys.argv[1]),sort_keys=True,ensure_ascii=False))
