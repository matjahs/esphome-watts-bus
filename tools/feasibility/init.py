import sys; sys.path.insert(0,".")
from uniq import uniq
U=uniq()
def step(crc,b):
    crc^=b
    for _ in range(8): crc=((crc<<1)^0xE6)&0xFF if crc&0x80 else (crc<<1)&0xFF
    return crc
def chk(p,init,start):
    c=init
    for b in p[start:8]: c=step(c,b)
    return c^p[8]
for start in (0,2):
    sols=[i for i in range(256) if all(chk(p,i,start)==p[9] for p in U)]
    print("start",start,"inits with xorout=0:",[f"{i:02x}" for i in sols])
# bitwise incl preamble+start bit: non-augmented remainder
def polymod(m,n,poly=0x1E6):
    for i in range(n-1,7,-1):
        if (m>>i)&1: m^=poly<<(i-8)
    return m
for pre in range(0,25):
    bits=("1"*23+"0")[24-pre:]
    cs={polymod(int(bits+"".join(f"{b:08b}" for b in p[:9]),2),pre+72)^p[9] for p in U}
    if cs=={0}: print("preamble bits included:",pre)
# Also MSB-first alt poly views
print("check 0x1E6 = x*(0xF3):", bin(0x1E6), bin(0xF3))
