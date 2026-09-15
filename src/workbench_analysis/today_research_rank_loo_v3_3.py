"""P12-04 pure LOO support, scoring, and stable ranking contracts."""
from __future__ import annotations
from collections.abc import Mapping,Sequence
import hashlib,json,math,statistics
from typing import Any
CONTRACT_ID="TODAY_RESEARCH_RANK_AND_LOO_V3_3_CANDIDATE_01"
PRIMARY_ORDER=("LAUNCH_CONFIRM","RECOVERY_TURN","STRONG_PULLBACK","TREND_CONTINUE")
def _n(v):
 try:x=float(v)
 except(TypeError,ValueError):return None
 return x if math.isfinite(x) else None
def tri_or(xs):
 xs=list(xs)
 if any(x is True for x in xs):return True
 return None if any(x is None for x in xs) else False
def current_loo(target:str,members:Sequence[Mapping[str,Any]],track_current:bool|None)->dict:
 others={str(x['security_id']):x for x in members if str(x['security_id'])!=target}; valid=[_n(x.get('ret1')) for x in others.values() if x.get('actual_bar') is True and _n(x.get('ret1')) is not None]
 n=len(others);coverage=len(valid)/n if n else None
 enough=n>0 and len(valid)>=5 and coverage>=.70
 b=sum(x>0 for x in valid)/len(valid) if valid else None;m=statistics.median(valid) if valid else None
 support=(None if track_current is None or not enough else bool(track_current and b>=.55 and m>0))
 reason="TRACK_UNKNOWN" if track_current is None else "SAMPLE_INSUFFICIENT" if not enough else "SUPPORTED" if support else "BREADTH_FAILED"
 return {'support':support,'other_members':n,'valid_members':len(valid),'coverage':coverage,'b1_loo':b,'m1_loo':m,'reason':reason}
def change_loo(target,current_members,prior_members,*,potential,metric)->dict:
 if current_members is None or prior_members is None:return {'support':None,'reason':'HISTORIC_MEMBERSHIP_UNKNOWN','j_hash':None}
 c={str(x['security_id']):x for x in current_members if str(x['security_id'])!=target};p={str(x['security_id']):x for x in prior_members if str(x['security_id'])!=target};j=sorted(set(c)&set(p));den=max(len(c),len(p));pairs=[(_n(c[s].get(metric)),_n(p[s].get(metric))) for s in j];pairs=[x for x in pairs if None not in x];coverage=len(pairs)/den if den else None
 jhash=hashlib.sha256(json.dumps(j,separators=(',',':')).encode()).hexdigest()
 if potential is None or len(pairs)<5 or coverage is None or coverage<.70:return {'support':None,'reason':'TRACK_OR_SAMPLE_UNKNOWN','j_hash':jhash,'valid':len(pairs),'coverage':coverage}
 delta=(sum(a>0 for a,b in pairs)-sum(b>0 for a,b in pairs))/len(pairs) if metric=='ret1' else sum(a-b for a,b in pairs)/len(pairs)
 return {'support':bool(potential and delta>=.05),'reason':'SUPPORTED' if potential and delta>=.05 else 'IMPROVEMENT_FAILED','j_hash':jhash,'valid':len(pairs),'coverage':coverage,'delta':delta}
def support_audit(relations:Sequence[Mapping[str,Any]])->dict:
 unique={str(x['sector_id']):x for x in relations if x.get('sector_type') in ('INDUSTRY','THEME')};values=[x.get('support') if type(x.get('support')) is bool else None for x in unique.values()];ind=[x.get('support') for x in unique.values() if x['sector_type']=='INDUSTRY'];theme=[x.get('support') for x in unique.values() if x['sector_type']=='THEME']; overall=tri_or(values) if values else False
 def one(xs):return tri_or(xs) if xs else False
 return {'support':overall,'sector_relations_tested':len(unique),'evaluable_relations_count':sum(x is not None for x in values),'unknown_relations_count':sum(x is None for x in values),'supported_relations_count':sum(x is True for x in values),'industry_relations_count':len(ind),'theme_relations_count':len(theme),'industry_support':one(ind),'theme_support':one(theme),'relationship_set_hash':hashlib.sha256(json.dumps(sorted(unique),separators=(',',':')).encode()).hexdigest()}
def u(x,a,b):return None if _n(x) is None else max(0,min(1,(float(x)-a)/(b-a)))
def center(x,m,w):return None if _n(x) is None else max(0,1-abs(float(x)-m)/w)
def score_launch(row):
 vals=[center(row.get('break_margin_close20'),.02,.06),u(row.get('clv'),.60,.90),center(row.get('amr20_mean_prior'),1.80,1.20),u(row.get('rps5_delta3'),0,.15),_n(row.get('freshness'))]
 return None if None in vals else 100*sum(w*x for w,x in zip((.25,.25,.20,.20,.10),vals))
def score_category(category,row):
 if category=='LAUNCH_CONFIRM':return score_launch(row)
 fresh=_n(row.get('freshness'))
 if category=='STRONG_PULLBACK':
  a,b=u(row.get('slope20_prior'),0,.015),u(row.get('r2_20_prior'),.40,.80);trend=None if a is None or b is None else a*b
  vals=[trend,center(row.get('pullback_depth'),.06,.06),center(row.get('pullback_contraction'),.65,.35),u(row.get('clv'),.55,.90),center(row.get('close_to_prior_ma10_minus1'),.01,.06),fresh];weights=(.20,.20,.20,.20,.10,.10)
 elif category=='RECOVERY_TURN':
  vals=[u(row.get('clv'),.55,.90),u(row.get('rps5_delta3'),0,.15),center(row.get('amr20_mean_prior'),1.50,1.00),center(row.get('close_to_ma20_minus1'),.01,.06),fresh];weights=(.30,.25,.20,.15,.10)
 elif category=='TREND_CONTINUE':
  a,b=u(row.get('slope20'),0,.015),u(row.get('r2_20'),.40,.80);trend=None if a is None or b is None else a*b
  vals=[trend,u(row.get('clv'),.55,.90),center(row.get('amr20_mean_prior'),1.20,1.30),u(row.get('rps20'),.70,.95),center(row.get('bias20'),.04,.10),fresh];weights=(.25,.25,.20,.10,.10,.10)
 else:return None
 return None if None in vals else 100*sum(w*x for w,x in zip(weights,vals))
def rank(rows:Sequence[Mapping[str,Any]])->list[dict]:
 out=[]
 for row in rows:
  matched=[x for x in PRIMARY_ORDER if x in row.get('matched_categories',())];primary=matched[0] if matched else None; score=score_category(primary,row);mode=row.get('selection_mode','INDEPENDENT');out.append({**row,'primary_category':primary,'category_score':score,'rank_status':'SCORED' if score is not None else 'QUALIFIED_UNRANKED','selection_mode':mode})
 for primary in PRIMARY_ORDER:
  for mode in ('SUPPORTED','INDEPENDENT','OBSERVATION'):
   group=[x for x in out if x['primary_category']==primary and x['selection_mode']==mode and x['category_score'] is not None];group.sort(key=lambda x:(-x['category_score'],x.get('signal_age') if x.get('signal_age') is not None else math.inf,-(_n(x.get('liq20_amount')) or 0),str(x['security_id']))); 
   for i,x in enumerate(group,1):x['category_rank']=i
 for x in out:x.setdefault('category_rank',None)
 return out
def simple_shadow(rows):return sorted(rows,key=lambda x:(str(x.get('primary_category')),str(x.get('selection_mode')),-(_n(x.get('clv')) or -math.inf),-(_n(x.get('liq20_amount')) or 0),str(x['security_id'])))
