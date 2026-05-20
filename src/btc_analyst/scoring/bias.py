def determine_bias(state):
    wt,dt,h4=state.get('weekly_trend','sideways'),state.get('daily_trend','sideways'),state.get('trend_4h','sideways')
    if wt==dt==h4=='up': b='Bullish'
    elif wt==dt==h4=='down': b='Bearish'
    elif wt=='sideways': b='Range'
    elif len({wt,dt,h4})>1: b='Neutral'
    else: b='Uncertain'
    return {'bias':b,'rationale':f'weekly={wt}, daily={dt}, 4h={h4}'}
