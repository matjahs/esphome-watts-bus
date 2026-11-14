import sys; sys.path.insert(0,".")
from load import *
def ck(p):
    c=0
    for b in p[:8]:
        c^=b
        for _ in range(8): c=((c<<1)^0xE6)&0xFF if c&0x80 else (c<<1)&0xFF
    return c^p[8]^0x30
n=ok=0
for h in ["02 38 45 6E 00 CB 00 BF 00 24","02 38 70 2D 00 CB 00 BF 00 52","02 38 45 72 00 CB 00 AA 00 D4"]:
    p=bytes.fromhex(h); print(h, "ok" if ck(p)==p[9] else "FAIL")
for f in FILES:
    last={}
    print("==",f)
    for fr in frames(FIX+f):
        b=decode(fr)
        if not(len(b)==104 and "x" not in b and b[:24]=="1"*23+"0"): continue
        p=payload(b); n+=1; ok+=ck(p)==p[9]
        i=p[2]<<8|p[3]; t=fr["start"]/1e6
        d = t-last[i] if i in last else None
        last[i]=t
        if d is None or d>1:
            print(f"{i:04x} t={t:9.3f} dt={'' if d is None else f'{d:8.3f}'} sp={p[6]<<8|p[7]} tog={(p[6]<<8|p[7])%5} T={(p[4]<<8|p[5])/10} hd={p[8]}")
print("frames",n,"checksum ok",ok)
