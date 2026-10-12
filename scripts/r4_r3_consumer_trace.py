"""Record real call frames against the unchanged original 56-consumer set."""
import hashlib,json,sys,threading,marshal
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
class ConsumerTrace:
    def __init__(self,output,entry):
        self.output=Path(output);self.entry=entry;self.calls=Counter();self.code_hashes={}
        original=json.loads((ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5/A4_CONSUMER_IMPACT.json').read_bytes())['consumers']
        self.paths={str((ROOT/item['path']).resolve()).casefold():item['path'].replace('\\','/') for item in original}
        if len(self.paths)!=56:raise ValueError('ORIGINAL_CONSUMER_DENOMINATOR_DRIFT')
        self.before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in self.paths.values()}
    def record(self,frame,event,arg):
        if event=='call':
            path=self.paths.get(frame.f_code.co_filename.casefold())
            if path:
                key=(path,frame.f_code.co_name,frame.f_code.co_firstlineno)
                self.calls[key]+=1
                if key not in self.code_hashes:self.code_hashes[key]=hashlib.sha256(marshal.dumps(frame.f_code)).hexdigest()
    def start(self):
        self.old_sys=sys.getprofile();self.old_thread=threading.getprofile()
        sys.setprofile(self.record);threading.setprofile(self.record)
    def close(self):
        sys.setprofile(self.old_sys);threading.setprofile(self.old_thread)
        rows=[]
        for path in self.paths.values():
            calls=[dict(function=f,line=l,calls=n,executed_code_sha256=self.code_hashes[(p,f,l)]) for (p,f,l),n in self.calls.items() if p==path]
            after=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
            rows.append(dict(path=path,source_sha256=after,source_sha256_before_run=self.before[path],source_unchanged_during_run=after==self.before[path],actual_call_count=sum(x['calls'] for x in calls),calls=calls,classification='OBSERVED_IN_ACTUAL_ENTRY' if calls else 'UNRESOLVED_NOT_OBSERVED_IN_ENTRY',numerical_acceptance='SEPARATE_ORACLE_REQUIRED'))
        value=dict(contract_id='R4_R3_PRESERVED_56_REAL_CALL_TRACE',entry=self.entry,denominator=56,observed=sum(bool(r['actual_call_count']) for r in rows),rows=rows,full_acceptance='OPEN',limitation='Call execution alone does not establish exact adjustment semantics; lack of observation does not establish exclusion')
        temp=self.output.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8');temp.replace(self.output)
