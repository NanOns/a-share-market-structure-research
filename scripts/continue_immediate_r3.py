"""R3 continuation: exact available upstream facts and official alias investigation."""
from immediate_r3_common import *
from datetime import datetime,timezone
import re,html,csv

COUT=OUT/'09_CONTINUATION'
def main():
    head=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');base=git('rev-parse','HEAD')
    write(COUT/'STAGE_CONTRACT.json',dict(stage='R3_OPEN_ITEMS_CONTINUATION',base_sha=base,task=binding('D:/Users/lps/Desktop/阶段任务/V4_IMMEDIATE_EXECUTION_MASTER_AND_TASK_CARDS_R3_20261010.md'),protected=[binding('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),binding('data/v4/V4_DATA_ACCEPTED_HEAD.json')],started_at=datetime.now(timezone.utc).isoformat(),acceptance='IN_PROGRESS',scope='Independent upstream factor windows; official identity-alias investigation; no release'))
    original=load(OUT/'02_P0_ALG/P0_ALG_ORACLE_INPUT.json');ids=set(original['selected_ids']);records=[];sources=[]
    for date in head['published_sessions']:
        o=head['owners'][date];diag=load(o['diagnostic']);hist=diag['owner']['history'];sources.extend([o['core'],hist])
        actual={r['security_id']:r for r in load(o['core']) if r['security_id'] in ids}
        with gzip.open(checked(hist),'rt',encoding='utf8') as stream:
            for line in stream:
                r=json.loads(line);sid=r['security_id']
                if sid not in actual:continue
                # Entire exact adjusted input window, including explicit bar dates.
                bars=[b for b in r['bars'] if b['trade_date']<=date]
                fields=actual[sid]['fields'];names=['tr','atr5','atr20','ma5','ma20','ma60','slope20','slope60','hh_progress','ll_progress','core_price_damage','prior60_percentile','pos60','range_ratio','atr_ratio']
                names += [f'{stem}{n}' for stem in ('hhv','llv','prior_high','prior_low') for n in (5,20,60)]
                records.append(dict(security_id=sid,trade_date=date,bars=bars[-110:],actual={k:fields[k] for k in names if k in fields}))
    write(COUT/'UPSTREAM_ORACLE_INPUT.json',dict(contract='R3_UPSTREAM_FACT_WINDOW_ORACLE_V1',calendar=original['calendar'],records=records,sources=sources,parameters=binding('config/v4_03_parameter_set_v1.json'),damage_atr_multiple=load('config/v4_03_parameter_set_v1.json')['contract_literals']['core_price_damage_atr_multiple'],scope='Declared core windows and unavailable endpoints independently rebuilt; no future data'))
    source=Path('G:/codex_tmp/bse_code_mapping_r3.html')
    if source.exists():
        raw=source.read_bytes();capture=COUT/'official_identity'/('bse_code_mapping_'+hashlib.sha256(raw).hexdigest()+'.html');capture.parent.mkdir(parents=True,exist_ok=True);tmp=capture.with_suffix('.tmp');tmp.write_bytes(raw);os.replace(tmp,capture)
        rows=[]
        for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',raw.decode('utf8'),re.S):
            cells=[html.unescape(re.sub('<[^>]+>','',x)).strip() for x in re.findall(r'<td\b[^>]*>(.*?)</td>',tr,re.S)]
            if len(cells)==5 and re.fullmatch(r'\d{6}',cells[3]) and re.fullmatch(r'\d{6}',cells[4]):rows.append(dict(name=cells[1],listing_date=cells[2],old_code=cells[3],new_code=cells[4]))
        snap=load(head['membership_snapshot']);ident=load(snap['identity_source'])['rows'];lookup={r.get('source_security_key'):r for r in ident};dispositions=[]
        with (OUT/'03_P0_OWNER/P0_OWNER_MEMBER_27_DISPOSITION.csv').open(encoding='utf8',newline='') as f:missing=list(csv.DictReader(f))
        for m in missing:
            code=m['RAW_ID'].split('.')[-1];hits=[r for r in rows if code in (r['old_code'],r['new_code'])];bound=[]
            for hit in hits:
                for alias in (hit['old_code'],hit['new_code']):
                    if lookup.get('BJ.'+alias):bound.append(dict(alias='BJ.'+alias,identity=lookup['BJ.'+alias]))
            dispositions.append(dict(raw_id=m['RAW_ID'],official_mapping_rows=hits,accepted_alias_matches=bound,status='OFFICIAL_ALIAS_FOUND_ACCEPTED_IDENTITY_MATCH' if bound else 'OFFICIAL_LISTING_IDENTITY_FOUND_POOL_IDENTITY_ABSENT' if hits else 'NOT_FOUND_IN_THIS_OFFICIAL_MAPPING_TABLE',source=binding(capture),production_mapping_changed=False))
        write(COUT/'MEMBER27_OFFICIAL_ALIAS_INVESTIGATION.json',dict(url='https://www.bse.cn/service/code_mapping.html',captured_at=datetime.now(timezone.utc).isoformat(),evidence_class='CURRENT_OFFICIAL_WEB_CAPTURE_NOT_HISTORICAL_AS_RECORDED',parsed_rows=len(rows),items=dispositions,accepted_identity=binding(path(snap['identity_source'])),warning='Non-match to this mapping table is not evidence of nonlisting; no pool expansion'))
    print(json.dumps(dict(rows=len(records),official_alias_items=len(dispositions))))
if __name__=='__main__':main()
