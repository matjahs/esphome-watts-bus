import sys
sys.path.insert(0, sys.argv[2])
from frames_lib import read_frames, to_halfbits, manchester

frames = read_frames(sys.argv[1])
msgs = []
for frame in frames:
  bits = manchester(to_halfbits(frame), 0)
  if "x" in bits or len(bits) < 100:
    continue
  msgs.append(bits[23:])

unique = []
for m in msgs:
  if m not in unique:
    unique.append(m)

base = unique[0]
print("pos  " + "".join(str(i // 10 % 10) for i in range(len(base))))
print("pos  " + "".join(str(i % 10) for i in range(len(base))))
for m in unique:
  print("msg  " + m)
print("diff " + "".join("^" if len({u[i] for u in unique}) > 1 else " " for i in range(len(base))))
