def find_swing_highs(highs,N):
    out=[]
    for i in range(N,len(highs)-N):
        if highs[i]==max(highs[i-N:i+N+1]): out.append((i,highs[i]))
    return out
def find_swing_lows(lows,N):
    out=[]
    for i in range(N,len(lows)-N):
        if lows[i]==min(lows[i-N:i+N+1]): out.append((i,lows[i]))
    return out
def classify_structure(swings):
    if len(swings)<4: return "sideways"
    vals=[p for _,p in swings[-4:]]
    return "HH-HL" if vals[-1]>vals[-2] else "LH-LL"
