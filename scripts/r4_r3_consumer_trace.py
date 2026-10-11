"""Record real call frames against the unchanged original 56-consumer set."""
import hashlib,json,sys,threading
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
class ConsumerTrace:
    def __init__(self,output,entry):
        self.output=Path(output);self.entry=entry;self.calls=Counter()
        original=json.loads((ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5/A4_CONSUMER_IMPACT.json').read_bytes())['consumers']
        self.paths={str((ROOT/item['path']).resolve()).casefold():item['path'].replace('\\','/') for item in original}
        if len(self.paths)!=56:raise ValueError('ORIGINAL_CONSUMER_DENOMINATOR_DRIFT')
    def record(self,frame,event,arg):
        if event=='call':
            path=self.paths.get(frame.f_code.co_filename.casefold())
            if path:self.calls[(path,frame.f_code.co_name,frame.f_code.co_firstlineno)]+=1
    def start(self):
        self.old_sys=sys.getprofile();self.old_thread=threading.getprofile()
        sys.setprofile(self.record);threading.setprofile(self.record)
    def close(self):
        sys.setprofile(self.old_sys);threading.setprofile(self.old_thread)
        rows=[]
        for path in self.paths.values():
            calls=[dict(function=f,line=l,calls=n) for (p,f,l),n in self.calls.items() if p==path]
            rows.append(dict(path=path,source_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),actual_call_count=sum(x['calls'] for x in calls),calls=calls,classification='OBSERVED_IN_ACTUAL_ENTRY' if calls else 'UNRESOLVED_NOT_OBSERVED_IN_ENTRY',numerical_acceptance='SEPARATE_ORACLE_REQUIRED'))
        value=dict(contract_id='R4_R3_PRESERVED_56_REAL_CALL_TRACE',entry=self.entry,denominator=56,observed=sum(bool(r['actual_call_count']) for r in rows),rows=rows,full_acceptance='OPEN',limitation='Call execution alone does not establish exact adjustment semantics; lack of observation does not establish exclusion')
        temp=self.output.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8');temp.replace(self.output)
