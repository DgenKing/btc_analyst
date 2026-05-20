import pandas as pd
from backtest.harness import run_walk_forward

def test_backtest_runs():
    df=pd.DataFrame({"open_time":list(range(200)),"open":[100+i*0.1 for i in range(200)],"high":[101+i*0.1 for i in range(200)],"low":[99+i*0.1 for i in range(200)],"close":[100+i*0.1 for i in range(200)],"volume":[1]*200})
    r=run_walk_forward(df)
    assert 'metrics' in r
