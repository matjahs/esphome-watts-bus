import sys

HALF_US = 450


def read_frames(path):
  frames, current = [], []
  with open(path, "rb") as fh:
    for raw in fh:
      line = raw.decode("ascii", "replace").strip()
      if line.startswith("# gap"):
        if current:
          frames.append(current)
        current = []
        continue
      parts = line.split()
      if len(parts) != 2 or parts[0] not in ("0", "1") or not parts[1].isdigit():
        continue
      current.append((int(parts[0]), int(parts[1])))
  if current:
    frames.append(current)
  return frames


def to_halfbits(frame):
  out = []
  for level, held in frame:
    units = round(held / HALF_US)
    out.extend([level] * units)
  return out


def manchester(halfbits, offset):
  bits = []
  for i in range(offset, len(halfbits) - 1, 2):
    pair = (halfbits[i], halfbits[i + 1])
    if pair == (0, 1):
      bits.append("1")
    elif pair == (1, 0):
      bits.append("0")
    else:
      bits.append("x")
  return "".join(bits)


