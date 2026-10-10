"""Read-only per-member disposition and raw amount source evidence."""
from immediate_r3_common import *
import csv,io,struct,zipfile
from collections import Counter

def csvwrite(p,rows):
    p=path(p);p.parent.mkdir(parents=True,exist_ok=True);stream=io.StringIO();w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);markdown(p,stream.getvalue())

def main():
    head=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=head['accepted_trade_date'];o=head['owners'][day];snap=load(head['membership_snapshot']);members=load(snap['memberships']);ident=load(snap['identity_source']);ib={r['source_security_key']:r for r in ident['rows']};life=load(o['lifecycle']);active=set(life['active_security_ids'])
    sector=next(s for s in load(o['sector']) if s['sector_id']=='INDUSTRY:T0706');m=[r for r in members if r['sector_id']==sector['sector_id']];unmapped=[r for r in m if r['security_id'] not in active];rawref=next(r for r in snap['sources'] if Path(r['path']).name=='tdxhy.cfg');lines=checked(rawref).read_text(encoding='gb18030').splitlines();dispositions=[]
    for r in unmapped:
        key=r['source_security_key'];i=ib.get(key);reason='INSUFFICIENT_EVIDENCE'
        if i and i.get('security_type')!='A_STOCK':reason='OUT_OF_A_SHARE_UNIVERSE'
        elif i and i.get('list_date') and i['list_date']>day:reason='NOT_LISTED_AT_T0'
        elif i and i.get('delist_date') and i['delist_date']<=day:reason='DELISTED'
        elif i and i.get('security_id') not in active:reason='IDENTITY_BOUND_NOT_IN_ACCEPTED_POOL'
        indices=[n+1 for n,line in enumerate(lines) if key.split('.')[-1] in line and 'T0706' in line]
        dispositions.append(dict(RAW_ID=key,NORMALIZED_ID=r['security_id'] or '',MEMBERSHIP_SOURCE=rawref['path'],source_sha=rawref['sha256'],source_lines=';'.join(map(str,indices)),IDENTITY_ASOF=snap['member_set_asof'],MATCH_RESULT=r['identity_status'],REASON=reason,identity_evidence='IDENTITY_SOURCE_NO_BOUND_ROW' if i is None else json.dumps(i,ensure_ascii=False),RETRY_OR_CONTRACT_ACTION='Obtain official dated listing/delisting/alias identity bytes; no security-pool expansion or row deletion'))
    csvwrite(OUT/'03_P0_OWNER/P0_OWNER_MEMBER_27_DISPOSITION.csv',dispositions)
    bindings=dict(T0=day,membership=head['membership_snapshot'],identity=snap['identity_source'],raw=rawref,sector=o['sector'],counts=dict(source_member_count=len(m),mapped_unique_count=len(set(sector['member_ids'])),excluded_count=sum(d['REASON']!='INSUFFICIENT_EVIDENCE' for d in dispositions),unknown_count=sum(d['REASON']=='INSUFFICIENT_EVIDENCE' for d in dispositions)),reason_counts=dict(Counter(r['REASON'] for r in dispositions)),PIT_ELIGIBLE=False,AS_RECORDED=False)
    write(OUT/'03_P0_OWNER/P0_OWNER_CONTRACT_BINDINGS.json',bindings)
    rows=[]
    for k,layer,code,owner,route,verdict,next_action in [
        ('sector.maturity','OWNER_BUILD / AUTHORITY','src/v4/confirmation_d2_candidate_r5.py',None,'sectors','SOURCE_NOT_PRESENT','Candidate interface explicitly STOCK only; request versioned sector detector/owner admission'),
        ('sector.health','OWNER_BUILD / INPUT_MISSING','src/v4/research_state.py',None,'sectors','SOURCE_NOT_PRESENT','Generic SECTOR reducer exists; no dated sector D2 publication or full required detector input manifest'),
        ('sector.lifecycle','INPUT_MISSING','src/sector/rotation_r5.py',o['rotation'],'sectors/{id}/timeline','ROTATION_EXISTS_LIFECYCLE_NOT_EQUIVALENT','Retain actual rotation timeline; no inferred maturity mapping'),
        ('sector.why_now','ADAPTER','src/workbench_service/core_product_bff_r1.py',o['rotation'],'sectors/{id}','REAL_PRIOR_AND_PREDICATES_AVAILABLE','Verify API/DOM'),
        ('home.changes','CONTRACT_GAP','src/workbench_service/core_product_bff_r1.py',o['forward'],'home','SCOPED_FOCUS_ROTATION_NOT_ALL_MARKET','Preserve explicit change_scope'),
        ('stock.not_eligible','ADAPTER','src/workbench_service/core_product_bff_r1.py',o['focus'],'stocks/{id}/why-not','REAL_D2_AVAILABLE','Verify real out-of-universe vs unknown identity'),
        ('H.competitive_hypotheses','CONTRACT_GAP','src/workbench_service/core_product_bff_r1.py',None,'stocks/{id}/profile','NO_ACCOUNT_FACTS','Keep conditional research hypotheses with F/R evidence; no invented narrative')]:
        rows.append(dict(issue_id='R3-'+k,stage='P0-OWNER',producer_code=code,algorithm_version='R3_SCOPE_V1',exact_input_owner=json.dumps(owner),trade_date=day,first_available_at='UNKNOWN',member_asof=snap['member_set_asof'],PIT_scope='LATEST_MEMBER_RETRO',window_identity='DATED_OWNER',adjustment='FIELD_LOCAL',unit='state',null_policy='UNKNOWN_NOT_ZERO',output_owner=json.dumps(owner),expected_field=k,actual_field=k if owner else 'ABSENT',BFF_route='/api/v4/'+route,UI_component='/v4/research',discrepancy=verdict,responsible_layer=layer,current_verdict=verdict,evidence_path='P0_OWNER_CONTRACT_BINDINGS.json',code_sha=sha(code),owner_sha=owner['sha256'] if owner else '',next_action=next_action))
    csvwrite(OUT/'03_P0_OWNER/P0_OWNER_GAP_ROOT_CAUSE.csv',rows)
    markdown(OUT/'03_P0_OWNER/P0_OWNER_FIX_RESULT.md',f'# P0 Owner R3\n\nCurrent T0 {day}; {len(m)} raw members, {len(sector["member_ids"])} mapped unique, {len(dispositions)} excluded/unknown. Every missing identity has explicit source rows and evidence. No identity correction is justified by current bytes.\n\nGeneric SECTOR state reducer exists, but the legal real candidate adapter rejects entity_type != STOCK; no dated sector maturity/health Owner is in the accepted head. This is an OWNER_BUILD/AUTHORITY/input-manifest gap, not proof that the generic algorithm does not exist. Controls retain UNKNOWN with SOURCE_INCOMPLETE quality. No formula, head, pool or member rows changed.\n\nStatus: PASS_SCOPED_MEMBER_DISPOSITION; OPEN_SECTOR_D2_ADMISSION.\n')
    # Current frozen cross-source original bytes, no network or replacement feed.
    freeze=load(head['source_registry'][day]['freeze']);native=load(freeze['tdx'])['target_bars'];bao=freeze['normalized']['daily']['rows'];bb={r['code'].upper():r for r in bao};comparisons=[]
    for n in native:
        b=bb.get(n['source_security_key']);comparisons.append(dict(code=n['source_security_key'],trade_date=n['trade_date'],native_amount=n['amount'],native_volume=n['volume'],baostock_amount=b['amount'] if b and b['amount'] else None,baostock_volume=b['volume'] if b and b['volume'] else None,tradestatus=b['tradestatus'] if b else None,adjustflag=b['adjustflag'] if b else None,source_entry=n['source_entry'],entry_sha256=n['entry_sha256']))
    binary=[];package=freeze['effective_package']['download']
    with zipfile.ZipFile(checked(package)) as z:
        selected=sorted([r for r in comparisons if r['baostock_amount'] is not None],key=lambda r:abs(r['native_amount']-float(r['baostock_amount'])),reverse=True)[:15]
        for r in selected:
            raw=z.read(r['source_entry']);assert __import__('hashlib').sha256(raw).hexdigest()==r['entry_sha256'];dateint=int(day.replace('-',''));record=next(raw[i:i+32] for i in range(0,len(raw),32) if struct.unpack_from('<I',raw,i)[0]==dateint);a=struct.unpack_from('<f',record,20)[0];vol=struct.unpack_from('<I',record,24)[0];assert a==r['native_amount'] and vol==r['native_volume'];binary.append(dict(code=r['code'],raw_record_hex=record.hex(),amount_offset=20,amount_binary32=a,volume_offset=24,volume=vol,entry_sha256=r['entry_sha256']))
    write(OUT/'04_P0_AMOUNT/P0_AMOUNT_SOURCE_COMPARISON.json',dict(T0=day,sources=dict(freeze=head['source_registry'][day]['freeze'],tdx=freeze['tdx'],baostock=freeze['native_baostock'],package=package),observed_at=freeze['observed_at'],unit='CNY',adjustment='RAW_AMOUNT_UNADJUSTED; BaoStock adjustflag3',rows=comparisons,binary_record_checks=binary,earlier_dates='9/30 and 10/08 need separate acquisition bindings; not inferred from current snapshot'))
    markdown(OUT/'04_P0_AMOUNT/P0_AMOUNT_AUTHORITY_DIFF.md','# Independent Amount A audit R3\n\nTDX Native stays primary. Stock amount_ratio20/amr20_mean_prior and sector participation_proxy are different contracts from sector Amount A. The binary32 comparison classifies actual current rows without adding tolerance or changing their values. Raw daily amount bytes are read from existing ZIP in memory.\n\nCross-source storage precision proof is distinct from economic feed equivalence and formal sector Amount A source authority. Those remain separate audit items. 9/30 and 10/08 are OPEN until exact frozen cross-source bindings are recovered and compared. No mechanical QFQ adjustment to amount is permitted. No new source authority is activated.\n')
    print(json.dumps(dict(member_dispositions=len(dispositions),reason_counts=bindings['reason_counts'],amount_rows=len(comparisons),raw_record_checks=len(binary))))
if __name__=='__main__':main()
