import sys
sys.path.insert(0, sys.argv[2])
from frames_lib import to_halfbits, manchester

# Rebuild frames with absolute timestamps from gap + edge durations.
frames, current, t, start = [], [], 0, None
with open(sys.argv[1], "rb") as fh:
  for raw in fh:
    line = raw.decode("ascii", "replace").strip()
    if line.startswith("# gap"):
      t += int(line.split()[2])
      if current:
        frames.append((start, current))
      current, start = [], t
      continue
    parts = line.split()
    if len(parts) != 2 or parts[0] not in ("0", "1") or not parts[1].isdigit():
      continue
    current.append((int(parts[0]), int(parts[1])))
    t += int(parts[1])
if current:
  frames.append((start, current))

first = frames[0][0]
for start, frame in frames:
  bits = manchester(to_halfbits(frame), 0)
  if "x" in bits or len(bits) < 100:
    print(f"{(start - first) / 1e6:7.2f}s  (bad frame, {len(frame)} edges)")
    continue
  data = bits[24:]
  words = [data[i:i + 8] for i in range(0, 80, 8)]
  hexs = " ".join(f"{int(w, 2):02X}" for w in words)
  print(f"{(start - first) / 1e6:7.2f}s  {hexs}")
