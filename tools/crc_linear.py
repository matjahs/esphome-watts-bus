import sys
from itertools import combinations
sys.path.insert(0, sys.argv[1])
from frames_lib import read_frames, to_halfbits, manchester

msgs = []
for path in sys.argv[2:]:
  for frame in read_frames(path):
    bits = manchester(to_halfbits(frame), 0)
    if "x" in bits or len(bits) < 100:
      continue
    data = bits[24:104]
    b = [int(data[i:i + 8], 2) for i in range(0, 80, 8)]
    if b not in msgs:
      msgs.append(b)
print(len(msgs), "unique messages")
for m in msgs:
  print(" ".join(f"{x:02X}" for x in m))


def rev8(v):
  return int(f"{v:08b}"[::-1], 2)


def crc8_raw(data, poly, refin):
  crc = 0
  for byte in data:
    crc ^= rev8(byte) if refin else byte
    for _ in range(8):
      crc = ((crc << 1) ^ poly) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
  return crc


for skip in range(0, 3):
  for end in (9, 8):
    for poly in range(1, 256):
      for refin in (False, True):
        for refout in (False, True):
          consts = set()
          for m in msgs:
            c = crc8_raw(m[skip:end], poly, refin)
            c = rev8(c) if refout else c
            consts.add(c ^ m[9])
            if len(consts) > 1:
              break
          if len(consts) == 1:
            print(f"CRC8 skip={skip} end={end} poly=0x{poly:02X} refin={refin} refout={refout} const=0x{consts.pop():02X}")
print("done")
