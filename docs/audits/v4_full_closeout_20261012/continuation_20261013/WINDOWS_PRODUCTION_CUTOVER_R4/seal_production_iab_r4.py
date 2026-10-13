import json,hashlib
from pathlib import Path
folder=Path(__file__).parent/'IAB_PRODUCTION_R4'
checks={
 'home':('HOME_AX.txt',['28765/v4/research/home','2026-10-12','5224','400','自动日更：开启','V4_PACKAGE_1.0.0_fe11c18cfdf7']),
 'stocks':('STOCKS_AX.txt',['28765/v4/research/stocks','5224','2026-10-12']),
 'sectors':('SECTORS_AX.txt',['28765/v4/research/sectors','400','2026-10-12']),
 'focus':('FOCUS_AX.txt',['28765/v4/research/focus','3025','不是 Validation Cohort']),
 'market':('MARKET_AX.txt',['28765/v4/research/market','15376.09','5224','2026-10-12']),
 'diagnostics':('DIAGNOSTICS_AX.txt',['28765/v4/research/diagnostics','5212','2026-10-12']),
 'alias_search':('SEARCH_ALIAS_AX.txt',['302132','中航成飞','共 1 条']),
 'source_drawer':('SOURCE_DRAWER_AX.txt',['WEAK','2026-10-12','MARKET_REGIME_TREND_WEAK_ERRATUM_V1']),
 'historical_date_cross_page':('HISTORY_MARKET_AX.txt',['2026-10-09','19003.65']),
 'historical_comparison':('HISTORY_COMPARE_AX.txt',['截至 2026-10-09','中航成飞','-0.093'])}
records=[]
for name,(file,terms) in checks.items():
 p=folder/file;text=p.read_text(encoding='utf8');missing=[t for t in terms if t not in text];assert not missing,(name,missing)
 records.append(dict(check=name,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status='PASS'))
result=dict(contract_id='V4_ACTUAL_INSTALLED_ORIGINAL_PORT_IAB_INTERACTION_R4',acceptance='PASS_REAL_ORIGINAL_PORT_IAB_SIX_ENTRIES',browser='CODEX_IN_APP_BROWSER',port=28765,actual_after_restart=True,package='V4_PACKAGE_1.0.0_fe11c18cfdf7',records=records,performance_test=False,mobile_test=False,scope='Actual original-port six-entry rendering plus search, source disclosure, date propagation and explicit historical comparison; prior 14 staging interactions conserved by identical business payloads and frozen package')
path=folder/'RESULT.json';assert not path.exists();temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path);print(json.dumps(dict(acceptance=result['acceptance'],checks=len(records))))
