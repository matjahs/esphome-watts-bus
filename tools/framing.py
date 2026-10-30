import sys
from functools import reduce
sys.path.insert(0, sys.argv[2])
from frames_lib import read_frames, to_halfbits, manchester

msgs = []
for frame in read_frames(sys.argv[1]):
  bits = manchester(to_halfbits(frame), 0)
  if "x" not in bits and len(bits) >= 100 and bits[23:] not in msgs:
    msgs.append(bits[23:])


def to_bytes(bits, offset, lsb_first):
  out = []
  for i in range(offset, len(bits) - 7, 8):
    chunk = bits[i:i + 8]
    if lsb_first:
      chunk = chunk[::-1]
    out.append(int(chunk, 2))
  return out


CHECKS = {
  "sum": lambda b: sum(b) & 0xFF,
  "neg_sum": lambda b: (-sum(b)) & 0xFF,
  "xor": lambda b: reduce(lambda a, c: a ^ c, b, 0),
}

for offset in range(9):
  for lsb in (False, True):
    for name, fn in CHECKS.items():
      for skip in range(3):
        ok = 0
        for m in msgs:
          data = to_bytes(m, offset, lsb)
          if fn(data[skip:-1]) == data[-1]:
            ok += 1
        if ok == len(msgs):
          print(f"MATCH offset={offset} lsb_first={lsb} check={name} skip={skip}")

for m in msgs:
  print(" ".join(f"{b:02X}" for b in to_bytes(m, 1, False)), "|", " ".join(f"{b:02X}" for b in to_bytes(m, 1, True)))
