import numpy as np
def compute_profile(closes, volumes, bins=50):
    h,e=np.histogram(closes,bins=bins,weights=volumes); i=int(np.argmax(h)); return {"poc":float((e[i]+e[i+1])/2),"vah":float(e[min(len(e)-2,i+1)]),"val":float(e[max(0,i-1)]),"hist":h.tolist(),"edges":e.tolist()}
