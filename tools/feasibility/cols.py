import sys; sys.path.insert(0,".")
from uniq import uniq
U=uniq()
B=lambda p:int.from_bytes(p[:9],"big")
diffs=[(B(p)^B(U[0]), p[9]^U[0][9]) for p in U[1:]]
# reduced row echelon
basis={}
for x,y in diffs:
    while x:
        h=x.bit_length()-1
        if h in basis: bx,by=basis[h]; x^=bx; y^=by
        else: basis[h]=(x,y); break
# full reduce
keys=sorted(basis)
for h in keys:
    x,y=basis[h]
    for h2 in keys:
        if h2!=h:
            x2,y2=basis[h2]
            if (x2>>h)&1: basis[h2]=(x2^x,y2^y)
def name(bit):  # bit index from LSB of 72-bit field
    pos=71-bit; return f"p[{pos//8}].b{7-pos%8}"
for h in sorted(basis,reverse=True):
    x,y=basis[h]
    terms=[name(i) for i in range(72) if (x>>i)&1]
    print(f"{y:02x} {y:08b} <- "+" ^ ".join(terms))
