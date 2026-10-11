"""Independent expected risk precedence across all ordered event subsets."""
from itertools import permutations
from types import SimpleNamespace
from unittest.mock import patch

from workbench_service.core_product_bff_r1 import CoreProductBFFR1, OperationalSuccessorBFFV1

ORDER=('INVALIDATED','EXITED','WEAKENED','UPGRADED','REENTERED','NEW')
DAY='2026-10-09'

class Fixture(CoreProductBFFR1):
    def source(self,domain,day):
        return {'events':self.events} if domain=='forward' else []
    def project(self,domain,day):
        return [{'entity_id':'S','symbol':'S','fields':{}}] if domain=='stocks' else []

def test_all_event_permutations_preserve_risk_and_unique_denominator():
    obj=Fixture.__new__(Fixture)
    ref={'path':'synthetic','sha256':'0'*64}
    obj.api=SimpleNamespace(candidate={'accepted_trade_date':DAY,'owners':{DAY:{'forward':ref,'rotation':ref}}},token='fixture')
    with patch.object(OperationalSuccessorBFFV1,'get',return_value=(200,{'gaps':[]})):
        for size in range(1,len(ORDER)+1):
            for values in permutations(ORDER,size):
                obj.events=[{'entity_id':'S','event':v} for v in values]
                _,data=obj._get_product('/api/v4/home',{'context_token':'fixture'})
                expected=next(v for v in ORDER if v in values)
                assert data['changes'][0]['fields']['effective_event']['value']==expected
                assert data['net_information_count']==data['change_total']==1
                assert len(data['risks'])==int(expected in ('INVALIDATED','EXITED','WEAKENED'))
