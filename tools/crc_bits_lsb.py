import sys
sys.path.insert(0, sys.argv[1])
from frames_lib import read_frames, to_halfbits, manchester

msgs = []
for path in sys.argv[2:]:
  for frame in read_frames(path):
    bits = manchester(to_halfbits(frame), 0)
    if "x" in bits or len(bits) < 104:
      continue
    if bits[:104] not in msgs:
      msgs.append(bits[:104])

TRAILER = 96


def crc_bits_lsb(bitstr, poly):
  crc = 0
  for ch in bitstr:
    fb = (crc & 1) ^ (ch == "1")
    crc >>= 1
    if fb:
      crc ^= poly
  return crc


def rev(v):
  return int(f"{v:08b}"[::-1], 2)


for start in range(0, 40):
  for poly in range(1, 256):
    for refout in (False, True):
      consts = set()
      for m in msgs:
        trailer = int(m[TRAILER:104], 2)
        c = crc_bits_lsb(m[start:TRAILER], poly)
        c = rev(c) if refout else c
        consts.add(c ^ trailer)
        if len(consts) > 1:
          break
      if len(consts) == 1:
        print(f"MATCH start={start} poly=0x{poly:02X} refout={refout} const=0x{consts.pop():02X}")
print("done")
