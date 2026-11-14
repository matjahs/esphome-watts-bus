import sys; sys.path.insert(0,".")
from uniq import uniq
U=uniq()
def tobits(p,n=9):
    v=int.from_bytes(p[:n],"big"); return v
# Gaussian elimination over GF(2): rows = (input bits(72) + 1 const) -> output 8 bits
rows=[]
for p in U:
    x=(tobits(p)<<1)|1   # 73 bits incl constant
    rows.append([x,p[9]])
# reduce
basis=[]  # list of (x,y) with distinct leading bit
incons=0
for x,y in rows:
    for bx,by in basis:
        if x ^ bx < x: x^=bx; y^=by
    if x==0:
        if y!=0: incons+=1; print("INCONSISTENT residual y=%02x"%y)
    else:
        basis.append((x,y)); basis.sort(key=lambda t:-t[0])
print("rank",len(basis),"of",len(rows),"inconsistencies",incons)
# which input bits vary
var=0
for p in U: var|= tobits(p)^tobits(U[0])
print("varying bits mask %018x"%var, bin(var).count("1"))
