"""Preserve arithmetic-oracle ancestry and attach truthful frozen provenance."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = Path('G:/codex_tmp/r4_r3_pg_publication_v2')
RUN = WORK/'runtime/v4_full_closeout_focus_20261012_R2'
record = json.loads((ROOT/'docs/audits/r4_r3_local_delivery_20261012/S1_IDENTITY_REPAIR_R2/RESULT.json').read_bytes())
frozen = json.loads(gzip.decompress((WORK/record['result']['focus']['path']).read_bytes()))
projection = json.loads(gzip.decompress((RUN/'CURRENT_ACTION_FOCUS.json.gz').read_bytes()))
result = json.loads((ROOT/'docs/audits/v4_full_closeout_20261012/focus_R2/RESULT.json').read_bytes())
old = {e['episode_id']:e for e in frozen['episodes']}
provenance = 'membership_mode taxonomy membership_snapshot_id membership_observed_at member_set_asof knowledge_lineage AS_RECORDED PIT_ELIGIBLE HISTORICAL_FIRST_AVAILABLE_PROVEN production_eligible_scope survivorship_bias_risk'.split()
for episode in projection['episodes']:
    previous = old[episode['episode_id']]
    for row in [episode]+episode['observations']+episode['anchors']+episode['outcomes']:
        row.update({k:previous[k] for k in provenance})
projection['source_bindings'] = result['bindings']
target = RUN/'CURRENT_ACTION_FOCUS_ORACLE_INPUT.json.gz'
target.write_bytes(gzip.compress(json.dumps(projection, sort_keys=True, separators=(',',':')).encode(), mtime=0))
record['result']['focus'] = dict(path=target.relative_to(WORK).as_posix(),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
receipt = ROOT/'docs/audits/r4_r3_local_delivery_20261012/CLOSEOUT_ORACLE_INPUT.json'
receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
source = ROOT/'scripts/audit_r4_r3_focus_semantics_s1.py'
code = source.read_text(encoding='utf8').replace("OUT = ROOT / 'docs/audits/r4_r3_local_delivery_20261012/S1_ORACLE'", "OUT = ROOT / 'docs/audits/v4_full_closeout_20261012/oracle/S1_ORACLE'")
old_check = "blocked = any(dispositions.get(str(e.category), {}).get('formal_disposition', 'UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED', 'UNKNOWN_PRICE_IMPACT') for e in relevant)"
new_check = "blocked = any((dispositions.get(str(e.category), {}).get('formal_disposition') not in ('PRICE_AFFECTING_SUPPORTED', 'SUPPORTED_PRICE_AFFECTING') if e.category == 1 else dispositions.get(str(e.category), {}).get('formal_disposition') != 'NON_PRICE_AFFECTING') for e in relevant)"
assert old_check in code
code = code.replace(old_check,new_check)
(ROOT/'scripts/v4_closeout_focus_oracle.py').write_text(code,encoding='utf8')
print(receipt)
