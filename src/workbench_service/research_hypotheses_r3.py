"""Conditional competing explanations from observed cells, never account facts."""
import math

CONTRACT = 'OBSERVED_FR_COMPETING_EXPLANATIONS_R3_V1'

def competing_explanations(fields):
    keys = ('close', 'ma20', 'ret5', 'rps20')
    evidence = {key: fields.get(key) for key in keys}
    missing = [key for key, cell in evidence.items()
               if not cell or cell.get('quality') not in ('KNOWN', 'OBSERVED', 'ACCEPTED')
               or type(cell.get('value')) not in (int, float)
               or not math.isfinite(cell['value']) or not (cell.get('source') or cell.get('source_digest'))]
    if not missing:
        price_basis=evidence['close'].get('adjustment_basis')
        if not price_basis or price_basis!=evidence['ma20'].get('adjustment_basis'):
            missing.append('CONSISTENT_PRICE_BASIS')
    result = dict(contract_id=CONTRACT, scope='CONDITIONAL_RESEARCH_HYPOTHESES',
                  evidence=evidence, missing_fields=missing, account_behavior_observed=False,
                  probability=None, items=[])
    if missing:
        return dict(result, status='SOURCE_INCOMPLETE')
    close, ma20, ret5 = (evidence[k]['value'] for k in keys[:3])
    trend = close > ma20 and ret5 > 0
    result.update(status='READY', items=[
        dict(id='STRUCTURAL_CONTINUATION', title='结构性趋势延续的解释',
             support={'close_above_ma20': close > ma20, 'positive_ret5': ret5 > 0},
             counterevidence='收盘不高于 MA20 或五日收益非正时，当前截面不支持这两个趋势条件。',
             current_support=trend,
             next_discriminator='在后续真实可评估会话检查收盘与当日 MA20、五日收益及正式结构状态；维持条件支持延续，结构失效否定该解释。'),
        dict(id='TRANSIENT_MOVE', title='短暂反弹或波动、尚未形成持续趋势的解释',
             support={'trend_conditions_incomplete': not trend, 'single_snapshot_cannot_prove_persistence': True},
             counterevidence='后续多个真实会话持续满足趋势条件且正式结构保持有效，会削弱短暂波动解释。',
             current_support=not trend,
             next_discriminator='检查后续真实会话是否重新跌回 MA20、五日收益转为非正或正式结构失效；不可把尚未发生的结果写回当前判断。')])
    return result
