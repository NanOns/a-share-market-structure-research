"""Read-only name decoration, separately dated; never an identity/PIT input."""
import hashlib
import json
import re
import sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tdx.security_master import read_tnf
from tdx.block_reader import read_industry_names,read_infoharbor_memberships
from workbench_service.current_v4_context import canonical,digest
from workbench_service.v4_daily_refresh import atomic_bytes
from workbench_service.production_v4 import reference

def main():
    text=(ROOT/'config/paths.yaml').read_text('utf8')
    tdx=Path(json.loads(re.search(r'^  root: ("[^"\n]+")\s*$',text,re.M)[1]));cache=tdx/'T0002/hq_cache'
    paths=[cache/f for f in ('shs.tnf','szs.tnf','bjs.tnf','tdxzs.cfg','infoharbor_block.dat')]
    def refs():return [dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
    before=refs();stocks={}
    for market,file in [('SH','shs.tnf'),('SZ','szs.tnf'),('BJ','bjs.tnf')]:stocks.update(read_tnf(cache/file,market)[0])
    sectors={'INDUSTRY:'+k:v for k,v in read_industry_names(cache/'tdxzs.cfg').items()}
    _,meta=read_infoharbor_memberships(cache/'infoharbor_block.dat')
    for row in meta['sector_headers']:
        prefix={'concept':'THEME','style':'STYLE','index_group':'INDEX_GROUP'}[row['sector_type']]
        sectors[prefix+':'+row['sector_code']]=row['sector_name']
    if before!=refs():raise ValueError('READ_ONLY_NAME_INPUT_CHANGED_DURING_CAPTURE')
    record=dict(contract_id='V4_DISPLAY_NAMES_OBSERVED_V1',observed_at=datetime.now(timezone.utc).isoformat(),
        historical_identity_authority=False,qualification_input=False,pit_safe=False,encoding='GB18030',
        sources=before,stocks={k:v for k,v in stocks.items() if v and '\ufffd' not in v},sectors={k:v for k,v in sectors.items() if v and '\ufffd' not in v})
    raw=canonical(record);path=ROOT/'data/v4/display_names'/digest(raw)/'names.json';atomic_bytes(path,raw)
    atomic_bytes(ROOT/'config/v4_display_names_authority_v1.json',canonical(dict(contract_id='V4_DISPLAY_NAMES_AUTHORITY_V1',source=reference(ROOT,path),scope='OBSERVED_DISPLAY_SEARCH_ONLY_NOT_PIT_OR_QUALIFICATION')))
    atomic_bytes(ROOT/'docs/evidence/fp02_20261008/DISPLAY_NAMES_QA.json',canonical(dict(before=before,after=refs(),unchanged=True,stock_names=len(record['stocks']),sector_names=len(record['sectors']),scope='DISPLAY_ONLY_SEPARATELY_DATED')))
    print(len(record['stocks']),len(record['sectors']))
if __name__=='__main__':main()
