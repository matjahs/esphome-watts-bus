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

TRAILER = 96  # data starts at 24, trailer is the last 8 bits


def crc_bits(bitstr, poly, width=8):
  crc, top = 0, 1 << (width - 1)
  mask = (1 << width) - 1
  for ch in bitstr:
    fb = ((crc & top) != 0) ^ (ch == "1")
    crc = ((crc << 1) & mask)
    if fb:
      crc ^= poly
  return crc


def rev(v, width=8):
  return int(f"{v:0{width}b}"[::-1], 2)


for start in range(0, 40):
  for poly in range(1, 256):
    for refout in (False, True):
      for invert in (False, True):
        consts = set()
        for m in msgs:
          body = m[start:TRAILER]
          if invert:
            body = "".join("1" if c == "0" else "0" for c in body)
          trailer = int(m[TRAILER:104], 2)
          c = crc_bits(body, poly)
          c = rev(c) if refout else c
          consts.add(c ^ trailer)
          if len(consts) > 1:
            break
        if len(consts) == 1:
          print(f"MATCH start={start} poly=0x{poly:02X} refout={refout} invert={invert} const=0x{consts.pop():02X}")
print("done,", len(msgs), "messages")
