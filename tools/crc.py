import sys
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
    out.append(int(chunk[::-1] if lsb_first else chunk, 2))
  return out


def crc8(data, poly, init, refin):
  crc = init
  for byte in data:
    if refin:
      byte = int(f"{byte:08b}"[::-1], 2)
    crc ^= byte
    for _ in range(8):
      crc = ((crc << 1) ^ poly) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
  return crc


def rev8(v):
  return int(f"{v:08b}"[::-1], 2)


for offset in range(1, 2):
  for lsb in (False, True):
    frames = [to_bytes(m, offset, lsb) for m in msgs]
    for skip in range(3):
      for poly in range(1, 256):
        for init in (0x00, 0xFF):
          for refin in (False, True):
            for refout in (False, True):
              for xorout in (0x00, 0xFF):
                ok = True
                for f in frames:
                  c = crc8(f[skip:-1], poly, init, refin)
                  c = rev8(c) if refout else c
                  if (c ^ xorout) != f[-1]:
                    ok = False
                    break
                if ok:
                  print(f"CRC8 MATCH lsb={lsb} skip={skip} poly=0x{poly:02X} init=0x{init:02X} refin={refin} refout={refout} xorout=0x{xorout:02X}")
print("done")
