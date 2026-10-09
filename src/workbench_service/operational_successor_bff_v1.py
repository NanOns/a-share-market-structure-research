"""Dynamic cutoff envelopes over the unchanged operational field projector."""
from .operational_gap_bff_v2 import OperationalGapBFFV2


class OperationalSuccessorBFFV1(OperationalGapBFFV2):
    def envelope(self,day,**payload):
        response=super().envelope(day,**payload)
        response['context'].update(accepted_trade_date=self.api.candidate['accepted_trade_date'],
            data_cutoff_date=self.api.candidate['data_cutoff_date'],
            available_trade_dates=self.api.candidate['published_sessions'],
            data_updated_at=self.api.candidate['observed_at'],bff_contract_id='OPERATIONAL_SUCCESSOR_BFF_V1',
            domain_readiness={'focus':{'earliest_valid_date':self.api.candidate['published_sessions'][0]}})
        return response

    def get(self,path,query):
        query=dict(query)
        query.setdefault('trade_date',self.api.candidate['accepted_trade_date'])
        day=query['trade_date']
        if day in self.api.candidate['source_registry']:
            import json
            from workbench_analysis.r43_owner_replay import checked
            self.api.snapshot=json.loads(checked(self.api.root,self.api.candidate['source_registry'][day]['membership']).read_bytes())
        code,payload=super().get(path,query)
        for gap in payload.get('gaps',[])+([payload['gap']] if payload.get('gap') else []):
            gap['owner_scope']=day+' operational research'
        return code,payload
