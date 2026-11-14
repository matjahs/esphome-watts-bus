import sys
import os
FIX=os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../tests/fixtures/")
FILES=["watts-capture.txt","watts-capture-long.txt","watts-capture-setpoints.txt"]
def frames(path):
    out=[];cur=[];t=0;start=None;gap=None
    for line in open(path,encoding="ascii",errors="replace"):
        line=line.strip()
        if line.startswith("# gap"):
            g=int(line.split()[2])
            if cur: out.append(dict(start=start,gap=gap,edges=cur))
            t+=g; cur=[]; start=t; gap=g; continue
        p=line.split()
        if len(p)!=2: continue
        cur.append((int(p[0]),int(p[1]))); t+=int(p[1])
    if cur: out.append(dict(start=start,gap=gap,edges=cur))
    return out
def halfbits(edges):
    hb=[]
    for l,d in edges: hb+= [l]*round(d/450)
    if len(hb)%2: hb.append(1)
    return hb
def bits(hb):
    s=""
    for i in range(0,len(hb)-1,2):
        a,b=hb[i],hb[i+1]
        s+= "1" if (a,b)==(0,1) else "0" if (a,b)==(1,0) else "x"
    return s
def decode(fr):
    b=bits(halfbits(fr["edges"]))
    return b
def payload(b):
    d=b[24:104]
    return bytes(int(d[i:i+8],2) for i in range(0,80,8))
def all_frames():
    res=[]
    for f in FILES:
        for fr in frames(FIX+f):
            fr["file"]=f; fr["bits"]=decode(fr); res.append(fr)
    return res
