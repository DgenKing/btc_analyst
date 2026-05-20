
import pandas as pd
from backtest.execution import simulate_trade
from backtest.metrics import compute_metrics

def _regime_from_window(w):
    if len(w)<30: return 'range'
    first=float(w['close'].iloc[0]); last=float(w['close'].iloc[-1])
    ch=(last-first)/first if first else 0
    if ch>0.05: return 'bull_trend'
    if ch<-0.05: return 'bear_trend'
    return 'range'

def run_walk_forward(candles: pd.DataFrame):
    candles=candles.sort_values('open_time').reset_index(drop=True)
    trades=[]
    if len(candles)<80: return {'trades':[], 'metrics':compute_metrics([]), 'weekday':{}, 'regime':{}}
    for i in range(40, len(candles)-3, 8):
        signal_close=float(candles.iloc[i]['close'])
        # strict next-bar-open entry (anti-lookahead)
        entry=float(candles.iloc[i+1]['open'])
        stop=signal_close*0.99
        target=signal_close*1.015
        sim=simulate_trade(entry, stop, target, 'long')
        weekday=int(pd.to_datetime(candles.iloc[i+1]['open_time'], unit='ms', utc=True).weekday())
        regime=_regime_from_window(candles.iloc[max(0,i-30):i+1])
        trades.append({'entry_ts':int(candles.iloc[i+1]['open_time']), 'exit_ts':int(candles.iloc[i+2]['open_time']), 'direction':'long', 'entry_price':entry, 'exit_price':sim['exit_fill'], 'stop_price':stop, 'realised_r':sim['realised_r'], 'weekday':weekday, 'regime':regime})

    metrics=compute_metrics(trades)
    by_wd={k:[] for k in range(7)}
    by_reg={}
    for t in trades:
        by_wd[t['weekday']].append(t['realised_r'])
        by_reg.setdefault(t['regime'], []).append(t['realised_r'])
    wd={k:(sum(v)/len(v) if v else 0) for k,v in by_wd.items()}
    rg={k:(sum(v)/len(v) if v else 0) for k,v in by_reg.items()}
    return {'trades':trades, 'metrics':metrics, 'weekday':wd, 'regime':rg}
