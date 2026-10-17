"""Dynamic cutoff envelopes over the unchanged operational field projector."""
from .operational_gap_bff_v2 import OperationalGapBFFV2


def read_pg_validation_cohort_statistics(api, owner_binding, trade_date):
    """Read the Head-bound cohort payload from PG and retain the existing grant gate."""
    from workbench_analysis.validation_cohort_read_contract_r3 import read_authorized_statistics
    from workbench_db.v4_cohort_pg_r1 import load_owner

    owner = load_owner(api.root, owner_binding)
    return read_authorized_statistics(
        api.root,
        accepted_head={'path': 'pg://v4/operational_research_heads/current', 'sha256': api.token},
        owner_binding=owner_binding,
        trade_date=trade_date,
        accepted_head_data=api.candidate,
        owner_reader=lambda binding: owner if binding == owner_binding else None,
    )


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
        if ('context_token' in query and query['context_token']!=self.api.token):
            raise ValueError('CONTEXT_TOKEN_MISMATCH')
        query.setdefault('trade_date',self.api.candidate['accepted_trade_date'])
        day=query['trade_date']
        if day not in self.api.candidate['published_sessions']:
            raise ValueError('TARGET_DATE_NOT_GRANTED')
        if path in ('/api/v4/forward/statistics','/api/v4/forward/plans'):
            if (query.get('context_token')!=self.api.token):
                raise ValueError('CONTEXT_TOKEN_MISMATCH')
            from workbench_analysis.validation_cohort_read_contract_r3 import read_statistics, maturity_schedule, enrollment_identity
            owner=self.api.candidate['owners'][day].get('validation_cohort')
            if owner:
                stats=read_pg_validation_cohort_statistics(self.api,owner,day)
            else:
                stats=read_statistics(None,cutoff=None,trade_date=day)
            rows=stats['items']
            count=stats['observed_count']
            plans=[dict(enrollment_id=enrollment_identity(r),T0=r['T0'],horizons=maturity_schedule(r['T0'],self.api.candidate['published_sessions'],day,horizons=(1,3,5,10,20))) for r in rows]
            statistics=dict(stats,enrollment_denominator=count,planned_horizon_denominator=None if count is None else count*5,
                published_outcomes=None,published_enrollment_count=None,mature_eligible_count=None,
                win_rate=None,return_quantiles=None,reason='NO_AUTHORIZED_COHORT_OWNER' if owner is None else 'SEPARATE_ACCEPTED_SETTLEMENT_OWNER_REQUIRED')
            return 200,self.envelope(day,status='READY' if owner else 'SOURCE_INCOMPLETE',
                reason=None if owner else 'NO_AUTHORIZED_COHORT_OWNER',data=statistics,
                items=plans if path.endswith('/plans') else [],total=len(plans) if owner else None,
                source=owner,contract_id='VALIDATION_COHORT_STATISTICS_BFF_R3_V1',
                missing_inputs=[] if owner else ['COMPLETE_FIRST_CAPTURE_SIGNAL_PRODUCER','ACCEPTED_COHORT_OWNER','EXPLICIT_READ_GRANT'],
                engineering_route_implemented=True,focus_is_validation_cohort=False,write_authorized=False,PIT_ELIGIBLE=False)
        if day in self.api.candidate['source_registry'] and 'native_membership_reference' not in self.api.candidate:
            raise ValueError('PG_MEMBERSHIP_REFERENCE_REQUIRED_NO_FILE_FALLBACK')
        code,payload=super().get(path,query)
        for gap in payload.get('gaps',[])+([payload['gap']] if payload.get('gap') else []):
            gap['owner_scope']=day+' operational research'
        return code,payload
