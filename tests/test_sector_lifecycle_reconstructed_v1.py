import json
import unittest
from pathlib import Path

from sector.lifecycle_reconstructed_v1 import CONTRACT,evaluate_sector
from scripts.audit_sector_lifecycle_reconstructed_r1 import oracle_health


PARAMS=json.loads((Path(__file__).resolve().parents[1]/'config/sector_lifecycle_reconstructed_v1.json').read_bytes())
DAYS=['2026-10-07','2026-10-08','2026-10-09','2026-10-12','2026-10-13']


def sector_row(day,rs5=.01,rs20=.02,breadth1=.55,breadth5=.65,breadth20=.6,retention=.6,participation=.95,coverage=1.0,ready=True):
    values={'sector_rs5':rs5,'sector_rs20':rs20,'breadth_ret1':breadth1,'breadth_ret5':breadth5,
        'breadth_ret20':breadth20,'seed_retention':retention,'participation_proxy':participation,
        'sector_quote_coverage':coverage,'membership_ready':ready}
    return {'sector_id':'INDUSTRY:T0101','trade_date':day,'membership_snapshot_id':'M1',
        'fields':{name:{'value':value,'quality':'PROXY_RECONSTRUCTED'} for name,value in values.items()}}


class SectorLifecycleReconstructedTests(unittest.TestCase):
    def run_rows(self,rows,dates=DAYS):
        return evaluate_sector('INDUSTRY:T0101',rows,dates,
            {'sector':'a'*64,'rotation':'b'*64},PARAMS,producer_sha256='c'*64)

    def test_full_known_inputs_distinguish_mature_from_none_and_keep_prior(self):
        rows=[sector_row(day) for day in DAYS]
        result=self.run_rows(rows)
        self.assertEqual(result['contract_id'],CONTRACT)
        self.assertEqual(result['maturity']['current'],'MATURE')
        self.assertEqual(result['maturity']['prior'],'MATURE')
        self.assertEqual(result['health']['current'],'NONE')
        self.assertEqual(result['health']['prior'],'NONE')
        self.assertEqual(result['input_completeness']['observed_sessions'],5)
        self.assertFalse(result['AS_RECORDED'])
        self.assertFalse(result['PIT_ELIGIBLE'])
        none=self.run_rows([sector_row(day,rs5=-.02,rs20=-.03,breadth1=.3,breadth5=.3,breadth20=.3,retention=.1,participation=.6) for day in DAYS])
        self.assertEqual(none['maturity']['current'],'NONE')
        self.assertEqual(none['health']['current'],'NONE')

    def test_health_requires_acceleration_and_does_not_use_one_day_return_alone(self):
        rows=[sector_row(DAYS[i],rs5=v,breadth1=b,retention=r) for i,(v,b,r) in enumerate([
            (.01,.40,.40),(.02,.50,.50),(.03,.60,.60),(.035,.65,.65),(.03,.60,.60)])]
        self.assertEqual(self.run_rows(rows)['health']['current'],'WEAKENING')
        only_daily_down=[sector_row(day,breadth1=(.2 if i==4 else .6)) for i,day in enumerate(DAYS)]
        self.assertEqual(self.run_rows(only_daily_down)['health']['current'],'WATCH')

    def test_missing_or_low_quality_inputs_remain_unknown(self):
        rows=[sector_row(day) for day in DAYS]
        rows[-1]['fields']['seed_retention']={'value':None,'quality':'UNKNOWN'}
        result=self.run_rows(rows)
        self.assertEqual(result['maturity']['current'],'UNKNOWN')
        self.assertIn('seed_retention',result['maturity']['unknown_predicates'])
        rows=[sector_row(day,ready=(i!=4)) for i,day in enumerate(DAYS)]
        self.assertEqual(self.run_rows(rows)['health']['current'],'UNKNOWN')

    def test_independent_health_oracle_uses_threshold_when_one_earlier_input_is_missing(self):
        rows=[sector_row(day) for day in DAYS]
        rows[-3]=sector_row(DAYS[-3],rs5=.05,breadth1=.5,retention=None)
        rows[-2]=sector_row(DAYS[-2],rs5=.04,breadth1=.5,retention=.5)
        rows[-1]=sector_row(DAYS[-1],rs5=.02,breadth1=.4,retention=.4)
        result=self.run_rows(rows)
        self.assertEqual(result['health']['current'],'WEAKENING')
        self.assertIn('SEED_RETENTION_WORSENED',result['health']['unknown_predicates'])
        self.assertEqual(oracle_health(rows[-1],rows[-2],rows[-3],PARAMS),'WEAKENING')

    def test_no_known_weakening_with_missing_t_minus_2_is_unknown(self):
        rows=[sector_row(day) for day in DAYS]
        rows[-3]=sector_row(DAYS[-3],rs5=None,breadth1=None,retention=None)
        result=self.run_rows(rows)
        self.assertEqual(result['health']['current'],'UNKNOWN')
        self.assertEqual(result['health']['unknown_predicates'],[
            'RS5_WORSENED','BREADTH1_WORSENED','SEED_RETENTION_WORSENED'])
        self.assertEqual(oracle_health(rows[-1],rows[-2],rows[-3],PARAMS),'UNKNOWN')

    def test_noncomparable_membership_and_future_rows_fail_closed(self):
        rows=[sector_row(day) for day in DAYS]
        rows[-2]['membership_snapshot_id']='M2'
        self.assertEqual(self.run_rows(rows)['health']['current'],'UNKNOWN')
        rows[-1]['trade_date']='2026-10-14'
        with self.assertRaisesRegex(ValueError,'DATE_NOT_ACCEPTED|FUTURE_INPUT'):
            self.run_rows(rows)


if __name__=='__main__':
    unittest.main()
