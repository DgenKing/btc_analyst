def compute_metrics(trades):
    n=len(trades)
    if n==0: return {'trades':0,'win_rate':0,'avg_r':0,'profit_factor':0}
    rs=[t['realised_r'] for t in trades]
    wins=[r for r in rs if r>0]; losses=[r for r in rs if r<=0]
    pf=(sum(wins)/abs(sum(losses))) if losses and sum(losses)!=0 else float('inf')
    return {'trades':n,'win_rate':round(100*len(wins)/n,2),'avg_r':round(sum(rs)/n,4),'profit_factor':pf}
