"""FP03 ingress: explicit missing producer ownership over unchanged frozen owners."""
from .r43_operational_bff import OperationalResearchBFF, owner_cell


def gap_contract(path):
    parts = path.split('/')
    domain = parts[0]
    stage = {'home': 'FP05', 'stocks': 'FP07', 'sectors': 'FP06', 'focus': 'FP08', 'forward': 'FP10',
             'market': 'FP09', 'diagnostics': 'FP11', 'replay': 'FP12', 'compare': 'FP12'}.get(domain, 'FP03')
    return dict(contract_id='V4_OPERATIONAL_ROUTE_GAP_V2', task_stage=stage,
                missing_owner='DATED_OPERATIONAL_' + path.replace('/', '_').upper() + '_OWNER',
                owner_scope='2026-10-08 operational research',
                ui_presentation='来源尚未接入；显示缺失 Owner 与修复阶段，保留当前已接受日期',
                next_task='Bind real dated producer, verify source QA and token, then browser acceptance under ' + stage)


class OperationalGapBFFV2(OperationalResearchBFF):
    def project(self, domain, day):
        result = super().project(domain, day)
        if domain != 'focus':
            return result
        forward = self.source('forward', day)
        episodes = {e['entity_id']: e for e in forward.get('episodes', [])}
        reference = self.api.candidate['owners'][day]['forward']
        for row in result:
            episode = episodes[row['entity_id']]
            observations = [o for o in episode.get('observations', []) if o['trade_date'] <= day]
            latest = max(observations, key=lambda o: o['trade_date']) if observations else {}
            for key in ('T0', 'end_date', 'membership', 'event', 'validity', 'path_resolution', 'best_confirmed_state'):
                source = episode if key in ('T0', 'end_date', 'membership') else latest
                value = source.get(key)
                if key not in source:
                    value = dict(value=None, quality='UNKNOWN', reason='NO_DATED_FOCUS_OBSERVATION_FIELD')
                elif value == 'UNKNOWN':
                    value = dict(value=None, quality='UNKNOWN', reason='OWNER_REPORTED_UNKNOWN_' + key.upper())
                elif key == 'end_date' and value is None:
                    value = dict(value=None, quality='KNOWN', reason='NO_RECORDED_EPISODE_END_DATE')
                cell = owner_cell(value, reference, 'episodes.' + episode['episode_id'] + '.' + ('observations.' + latest.get('trade_date', day) + '.' if source is latest else '') + key, day)
                cell['observation_trade_date'] = latest.get('trade_date') if source is latest else episode.get('start_date')
                row['fields'][key] = cell
        return result

    def get(self, path, query):
        if path.startswith('/api/v4/stocks/') and path.endswith('/chart'):
            if query.get('period', 'D') not in ('D', 'W', 'M') or query.get('price_basis', 'QFQ') not in ('QFQ', 'RAW'):
                raise ValueError('INVALID_CHART_QUERY')
            query = {k: v for k, v in query.items() if k not in ('period', 'price_basis')}
        code, payload = super().get(path, query)
        for gap in payload.get('gaps', []):
            gap.update(gap_contract(gap['domain']))
        if path == '/api/v4/home':
            payload['gaps'].extend(dict(domain=d, state='SOURCE_INCOMPLETE', **gap_contract(d))
                                   for d in ('home/changes', 'home/risks', 'home/net-information'))
        return code, payload

    def missing(self, day, path, reason='NO_OPERATIONAL_COMPATIBILITY_OWNER_FOR_ROUTE'):
        code, payload = super().missing(day, path, reason)
        payload['gap'].update(gap_contract(path))
        payload['reason'] = reason + ' | ' + payload['gap']['missing_owner'] + ' | ' + payload['gap']['task_stage']
        return code, payload
