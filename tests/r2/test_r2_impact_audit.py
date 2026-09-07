import json
from pathlib import Path
def test_impact_audit_schema():
    p=Path('reports/r2/R2_IMPACT_AUDIT.json')
    if p.exists():assert {'before','after','reason_categories'}<=json.loads(p.read_text('utf8')).keys()
