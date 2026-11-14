import sys; sys.path.insert(0,".")
from uniq import uniq
from load import all_frames, payload
def polymod(m, nbits, poly=0x1E6):
    # remainder of m(x) (nbits long) mod poly(x), degree 8
    for i in range(nbits-1, 7, -1):
        if (m>>i)&1: m ^= poly<<(i-8)
    return m
U=uniq()
consts={}
for p in U:
    r=polymod(int.from_bytes(p[:9],"big"),72)
    consts.setdefault(r^p[9],[]).append(p.hex(" "))
for k,v in consts.items(): print(f"const={k:02x} n={len(v)}")
# try alternative: include fewer leading bytes / whole frame incl preamble
for start in range(0,3):
    cs={polymod(int.from_bytes(p[start:9],"big"),8*(9-start))^p[9] for p in U}
    print("start",start,[f"{c:02x}" for c in cs])
# bytewise table-free formulation: crc=0; for b in p[0:9]: crc = shift8(crc) ^ b ... check equivalence
def watts_crc(data):
    crc=0
    for b in data[:-1]:
        crc^=b
        for _ in range(8):
            crc=((crc<<1)^0xE6)&0xFF if crc&0x80 else (crc<<1)&0xFF
    return crc ^ data[-1]
cs={watts_crc(p[:9])^p[9] for p in U}; print("bytewise const",[f"{c:02x}" for c in cs])
# check every captured frame (not just unique)
n=ok=0
for fr in all_frames():
    b=fr["bits"]
    if len(b)==104 and "x" not in b and b[:24]=="1"*23+"0":
        p=payload(b); n+=1; ok+= (watts_crc(p[:9]) ^ 0x30 == p[9])  # 0x30: constant found above
print("all frames",n,"ok",ok)
