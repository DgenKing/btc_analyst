def simulate_trade(entry, stop, target, direction='long', fee=0.0005, slippage_ticks=0.5, tick_size=0.5):
    slip = slippage_ticks * tick_size
    if direction=='long':
        e = entry + slip; x = target - slip
    else:
        e = entry - slip; x = target + slip
    gross = (x-e) if direction=='long' else (e-x)
    cost = (e+x) * fee
    risk = abs(entry-stop)
    realised = (gross-cost)/risk if risk else 0
    return {'entry_fill':e,'exit_fill':x,'realised_r':realised}
