import sys; sys.path.insert(0,".")
from load import *
def watts_check(p):          # p = 9 payload bytes
    c=0x0F
    for b in p[:8]:
        c^=b
        for _ in range(8): c=((c<<1)^0xE6)&0xFF if c&0x80 else (c<<1)&0xFF
    return c^p[8]
def build(tid,temp,sp,toggle,hd):
    raw=round(sp*10)+toggle; t=round(temp*10)&0xFFFF
    p=bytes([0x02,0x38,tid>>8,tid&0xFF,t>>8,t&0xFF,raw>>8,raw&0xFF,hd])
    return p+bytes([watts_check(p)])
def halfbits_of(p):
    bits="1"*23+"0"+"".join(f"{b:08b}" for b in p)
    hb=[]
    for c in bits: hb+= [0,1] if c=="1" else [1,0]
    return hb
def edges(hb):   # run-length, drop trailing high (idle)
    out=[]
    for v in hb:
        if out and out[-1][0]==v: out[-1][1]+=450
        else: out.append([v,450])
    if out[-1][0]==1: out.pop()
    return out
# roundtrip: every captured good frame must equal the re-encoded one, edge for edge (in 450us units)
n=ok=0
for fr in all_frames():
    b=fr["bits"]
    if len(b)==104 and "x" not in b and b[:24]=="1"*23+"0":
        p=payload(b); n+=1
        mine=[(l,round(d/450)) for l,d in edges(halfbits_of(p))]
        cap=[(l,round(d/450)) for l,d in fr["edges"]]
        ok+= mine==cap
print("re-encode matches capture edge-for-edge:",ok,"/",n)
print("example spoof (NOT sent): 4584 T=23.6 sp=21.0 tog=1 hd=0 ->", build(0x4584,23.6,21.0,1,0).hex(" "))
print("check vs captured 4584 ec b5 ->", build(0x4584,23.6,18.0,1,0).hex(" "), "(captured: 02 38 45 84 00 ec 00 b5 00 5e)")
