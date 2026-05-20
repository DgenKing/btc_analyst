import pandas_ta as ta

def ema(close,length): return ta.ema(close, length=length)
def sma(close,length): return ta.sma(close, length=length)
def rsi(close,length=14): return ta.rsi(close, length=length)
def macd(close,fast=12,slow=26,signal=9):
    m=ta.macd(close, fast=fast, slow=slow, signal=signal)
    return m.iloc[:,0], m.iloc[:,1], m.iloc[:,2]
def atr(high,low,close,length=14): return ta.atr(high, low, close, length=length)
