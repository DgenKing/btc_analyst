def tier_from_score(score,cfg):
    t=cfg['scoring']['tier_thresholds']
    if score>=t['strong']: return 'strong'
    if score>=t['medium']: return 'medium'
    if score>=t['weak']: return 'weak'
    return 'noise'
