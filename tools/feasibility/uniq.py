import sys; sys.path.insert(0,".")
from load import *
def uniq():
    U=[]
    for fr in all_frames():
        b=fr["bits"]
        if len(b)==104 and "x" not in b and b[:24]=="1"*23+"0":
            p=payload(b)
            if p not in U: U.append(p)
    # add the user-provided live samples
    for h in ["02 38 45 6E 00 CB 00 BF 00 24","02 38 70 2D 00 CB 00 BF 00 52","02 38 45 72 00 CB 00 AA 00 D4"]:
        p=bytes.fromhex(h)
        if p not in U: U.append(p)
    return U
if __name__=="__main__":
    U=uniq(); print(len(U))
    for p in sorted(U): print(p.hex(" "), f"{p[9]:08b}")
