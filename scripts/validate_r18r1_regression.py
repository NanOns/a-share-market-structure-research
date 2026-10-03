"""All inherited owner/governance/runtime regressions plus edge repair gates."""
import sys,json
from scripts import validate_r18_regression
inherited=validate_r18_regression.inherited
inherited.EXTRA=inherited.EXTRA+['tests/test_r18r1_owner_edges.py','tests/test_r18r1_canonical.py']
if __name__=='__main__':print(json.dumps(inherited.run(sys.argv[1]),sort_keys=True,ensure_ascii=False))
