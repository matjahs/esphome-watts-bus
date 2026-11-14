# Watts WFHT BUS: can an ESP8266 write setpoints? Feasibility report

Scope: analysis only. Nothing was sent on the bus. The analysis scripts are in
`tools/feasibility/`
(`load.py`, `uniq.py`, `lin.py`, `cols.py`, `verify.py`, `init.py`, `timing.py`, `encode.py`).

## Verdict: feasible with caveats, but not in the way the question assumes

- **Sending valid frames: feasible.** The checksum is solved and checked against every captured frame. A Python encoder rebuilds all 98 captured frames edge for edge. A simple open-drain pull-down is enough hardware to transmit.
- **Changing a thermostat's setpoint over the bus: not possible.** All the evidence says the bus is one-way, thermostat to connection box. No traffic goes to the thermostats, so there is nothing that could tell a thermostat to change its setpoint.
- **What is realistic: make the ESP a virtual thermostat for the box.** Either the ESP replaces a zone's physical thermostat (its data line is disconnected and the ESP sends under that thermostat's ID), or the ESP sits in the middle and rewrites that thermostat's frames.
- **Spoofing while the real thermostat stays on the bus gives at most a short override.** The real thermostat sends its own report again within about 155 to 182 s, sooner if someone touches it.

## 1. Checksum (p[9]): solved (VERIFIED)

```
crc = 0x0F
for i in 0..7:                      # p[0] .. p[7]
    crc ^= p[i]
    repeat 8: crc = (crc & 0x80) ? ((crc << 1) ^ 0xE6) & 0xFF : (crc << 1) & 0xFF
p[9] = crc ^ p[8]                   # heat-demand byte XORed in without shifting
```

Two equivalent forms:
- the remainder of the 72-bit polynomial p[0..8] modulo 0x1E6, XORed with 0x30;
- init 0xFC instead of 0x0F.

The polynomial 0x1E6 = x·(x⁷+x⁶+x⁵+x⁴+x+1), so it is really a 7-bit CRC shifted left one bit. As a result p[9] bit 0 always equals p[8] bit 0. That is why p[9] has always been even: the observed heat-demand values are 0 and 100.

**Evidence**
- **Affine over GF(2), checked first without assuming a CRC.** There are 37 distinct payloads (34 from the fixtures plus the 3 live samples). With a constant term, the system has rank 16, which leaves 21 independent 8-bit consistency checks. All 21 pass. A non-linear checksum would fail these with probability of about 1 − 2⁻⁸ each. (`lin.py`)
- **Per-bit contributions solved directly** (`cols.py`):
  - p[5] bits 0 to 4 give 54, A8, B6, 8A, F2. Each value is the previous one shifted left, reduced by 0xE6.
  - p[7] bit 0 gives E6, which is x⁸ mod P.
  - p[8] contributes its own value, for example 0x64 gives 0x64.
- **The model holds on every frame.** It matches all 98 decoded frames in the 3 fixtures and the 3 live samples. (`verify.py`, `timing.py`)
- **The setpoint toggle bit gets no special handling.** Flipping p[7] bit 0 always changes p[9] by XOR 0xE6. Eight pairs show this.

**Why the earlier tools missed it.** `crc.py`, `crc_linear.py`, `crc_bits*.py` all computed an augmented CRC over p[0..8], i.e. M·x⁸ mod P. `crc_linear.py` with end=8 left out the plain XOR of p[8]. The actual checksum is a non-augmented remainder: p[8] is added without being shifted.

## 2. Traffic direction: one-way, thermostat to box (VERIFIED in captures; supported by the manuals)

**Captures**
- **171 bursts in total.**
  - 98 are valid 104-bit `02 38` thermostat frames.
  - 73 are 2-edge stubs in `watts-capture-long.txt`. Each has exactly the same `# gap 133176968 us` and the same 2 edges. A physical signal would not repeat identically 73 times, so these are capture-tool artefacts, not bus traffic.
  - Every pulse in all files decodes as a 450 or 900 µs Manchester unit. Nothing has another length, frame size or bit rate.
- **No other frames at all.** There are no acks, no polls and no frames from the box. Nothing appears in the 406 ms gap between the two copies of a frame, or after them.
- **Real bus time covered is about 19 minutes:** 37 s + about 1,008 s + about 89 s.
- **Timing**
  - Each frame lasts 93.3 ms and is sent twice; the second copy starts 499.5 ms after the first.
  - Periodic reports: ID 0x4584 every 154.5 to 155.0 s; IDs 0x456E, 0x4572 and 0x702D every 181.0 to 182.0 s.
  - A local change triggers an immediate report and a second report 4.5 s later. The periodic timer restarts after each report.
  - Each thermostat's timing sits on its own 0.5 s grid. The grids are not shared, so there is no central clock or sync.
- **Setpoint "toggle" = a 1-bit sequence number.** Setpoint × 10 is always a multiple of 5, so the field can carry the bit. The bit alternates on every new report, periodic or event, for all four IDs, without exception. A receiver can use it to drop the repeated copy, so a sender should flip it on each new message.
- **A coordinated change near the end of the long capture.**
  - At t≈10836–10863 s, all four thermostats sent event reports within 26 s. Three changed setpoint:
    - 0x702D: 19.5 → 19.0
    - 0x456E: 22.0 → 19.0
    - 0x4584: 18.0 → 16.0
  - 0x4572 sent a second report 8.5 s after its periodic one, without changing its setpoint.
  - The reports come in a room-by-room order, which looks like a person walking round (GUESS). None of this involved any downstream traffic.

**Manuals (Watts WFHC-MASTER H&C-BUS & Slave manual)**
- **Pairing is one-way.** The box goes into "rF init" and the thermostat sends an init ("ignition") signal. The box display shows "2 squares = reception of correct init signal", "1 square = reception of standard signal", or nothing.
- **Same model as the one-way RF products.** Pairing is a listener learning a transmitter's ID, as in the RF range. There is no addressing from the box.
- **The thermostat is powered by the bus.** Its manual says "Power Supply: Done by the WFHC-MODULE-BUS". So the 2-wire "+ R/T −" bus carries both power and data. The thermostat display shows "moving bars when transmitting a Bus signal".
- **Regulation happens in the thermostat.** The WFHT-BASIC-BUS uses "Proportional band 15 min for 2 K (PWM)" and the WFHT-LCD uses "Proportional Integral regulation (PWM)". This fits p[8] being 0 or 100 (time-proportional on/off): for example, 0x456E reports 0 % at setpoint 22.0 and 21.2 °C measured.
- **The Master H&C box can change zone setpoints itself.** "Reduced" mode uses the comfort setpoint minus dt, "Automatic" follows per-zone programs. It does this locally from what the thermostats report, again with nothing sent back.

**Limits on this conclusion**
- About 19 minutes of capture cannot rule out rare downstream messages, for example during learn mode or heat/cool changeover.
- If the box signalled by current modulation instead of voltage, the voltage divider would not see it (GUESS, unlikely).

## 3. What "writing" can mean here

| Option | How | Result | Problems |
|---|---|---|---|
| A. Spoof alongside the real thermostat | Send frames with the real ID and a new setpoint, flipping the toggle relative to the last real frame | The box adopts it until the next real report (≤ ~182 s, or 155 s for 0x4584) | The value flips back and forth. The thermostat's display and own PWM heat demand (p[8]) don't change. If the box drives valves from p[8], changing the setpoint may do nothing. Constant collision risk. |
| **B. Replace (virtual thermostat), recommended** | Disconnect the zone thermostat's data path. The ESP sends under that thermostat's ID (already learned, so no re-pairing), every ~3 min and on change. Temperature comes from an HA sensor; the ESP computes setpoint and heat demand (PWM/hysteresis) itself. | Full HA `climate` control of that zone | That room loses its wall thermostat, unless it stays on as a read-only sensor somewhere else. You become responsible for regulation and fail-safes. The thermostat needs bus power, so you can't cut "data only" on a 2-wire bus. |
| C. Man in the middle | Split the bus at the thermostat. The ESP powers and listens to the thermostat side (needs to copy the box's supply), and re-sends frames to the box with the setpoint and heat demand overridden by HA | The wall thermostat still works locally, but HA can override | Most hardware: a second supply and two interfaces per zone. Needs the bus voltage and current measured first. |
| D. No bus writes | Use the box's dry-contact "External control" input (Master H&C manual: closed = OFF mode) through a relay | Global on/off only | Not per-zone setpoints. Depends on which box model you have. |

**E. Pair the ESP as an extra virtual thermostat (new option, see section 8).** The init frame is now known: `03 38 <id> <temp> <setpoint> <demand> <crc>`. The ESP can use its own ID, send the init frame while the box is in "rF init" for a free or chosen zone, and then send normal `02` reports. No physical thermostat has to be removed. The other problems of option B still apply (regulation, fail-safe, collisions).

## 4. Web research

- **No public reverse-engineering of the wired WFHT BUS was found.** No GitHub project, ESPHome component, rtl_433 decoder or forum write-up turned up, so this project appears to be first.
- **Watts WFHC-MASTER H&C-BUS & Slave manual**
  - Bus terminals "+ R/T −", polarity matters, up to 12 thermostats.
  - Shielded LiYCY above 10 m, maximum 25 m, at least 10 cm away from 230 V wiring.
  - The "rF init" learning procedure, and "External control".
  - Sources: https://www.manualslib.fr/manual/87053/Watts-Wfhc-Masterhandc-Bus-And-Slave.html (pages 4, 6, 10, 13), and the Watts PDF https://www.watts.eu/dfsmedia/0533DBBA-1771-4B1A-B581-AB07A4CBB521/639459-source/PPLIMF09825Ab.pdf
- **Dutch "Master BUS en slave" manual (includes the WFHT-BASIC-BUS and LCD thermostat sheets)**
  - "Power Supply: Done by the WFHC-MODULE-BUS" and "Power supply failed (check the WFHC-MODULE-BUS)".
  - "The thermostat will send now the ignition signal to the receiver".
  - PWM regulation.
  - Source: https://www.watts.eu/dfsmedia/0533DBBA-1771-4B1A-B581-AB07A4CBB521/652709-source/638599278190000000/Handleiding%20Master%20BUS%20en%20slave.pdf
  - **No bus voltage is stated in any document found.**
- **rtl_433 decoder for the RF sibling (WFHT-RF / WFHC-MASTERH&C-RF)**
  - The radio format is different: OOK PWM, 54 bits, an additive 8-bit sum checksum, and a pairing flag.
  - It is also a one-way thermostat-to-receiver design, so it supports the same architecture.
  - Source: https://github.com/merbanan/rtl_433/blob/master/src/devices/watts_thermostat.c
- **BT-D03 is not a BUS product.** It belongs to the Watts Vision Wireless range: 868 MHz, battery-powered, bidirectional RF with the BT-CT02 central unit. It doesn't apply here.
  - Sources: https://www.watts.eu/en/products/eu/smart-home-and-controls/vision-wireless/thermostat-bt-d03-rf-black and https://www.github.com/merbanan/rtl_433/issues/2885 (a Vision RF decoding effort)

## 5. Hardware to transmit

**Known**
- The line idles high.
- The thermostat signals by pulling the line low for 450/900 µs. The line also powers the thermostat.

**Bus voltage: measured (see README).** `+` is 4.8 V and R/T idles at 4.7 V against `−`. The divider has 10k on top, so GPIO14 sees about 3.1 V.

**Measure first, with a multimeter or scope; not yet done**
1. How low a real thermostat pulls the line (scope).
2. The box's source current: put a 1 kΩ load briefly across the line and measure the voltage drop. This shows whether the box limits current.

**Suggested driver (sketch)**
```
R/T ──[ R_s 100–220 Ω ]──┬── drain  2N7000/BSS138 (or NPN BC547 + 1 kΩ base resistor)
                         │   source ── bus "−"
GPIO (e.g. D6/GPIO12) ───┴─[100 Ω]── gate, 100 kΩ gate pull-down (line stays idle while the ESP boots)
Existing RX: R/T → 10k/20k → GPIO14 (keep it; use it for loopback and listen-before-talk)
```
- **Optional isolation:** use a PC817 optocoupler instead of the MOSFET. That gives galvanic isolation if the ESP has a USB/PC ground. At 450 µs half-bits a PC817 is fast enough.
- **Choosing R_s:** pick it so the pulled-low level matches a real thermostat's low level and the current stays within the box's limit. A PTC fuse in series is cheap insurance.
- **Firmware polarity:** GPIO high means line low. Encoding:
  - 23 bits of "1" (low then high), then a "0" start bit (high then low), then 10 bytes MSB-first.
  - Send twice, 500 ms apart (start to start).
  - Flip the toggle bit on each new report.
  - A frame is 93 ms of busy-wait or a timer ISR on the ESP8266. A timer ISR is better because of WiFi.
- **Before sending:** wait until no edges have been seen for at least 50 ms. Bus load is about 0.4 %: 4 thermostats × 2 × 93 ms every ~170 s.

## 6. Risks

- **Damaging the box or thermostats.** The bus voltage and current limit are unknown. A hard short without R_s could brown out every thermostat, which run from the same pair, or stress the box's supply. Reversed polarity is a known installation pitfall.
- **Collisions.** There is no arbitration or ack, so a collision corrupts both frames silently. The double send and the 4.5 s re-send reduce the impact.
- **The real thermostat overrides spoofed values** (option A) within ≤ 182 s. Its display and its own heat-demand byte stay unchanged.
- **The box may ignore the setpoint.** It may drive valves from p[8] (heat demand), at least with the plain module, in which case changing the setpoint alone does nothing. Not verified; it could also differ between the Master H&C box (which regulates itself in Reduced/Auto modes) and a basic module.
- **Fail-safe.** With option B, if the ESP or HA dies, the zone stops reporting. What the box does when a thermostat goes silent is unknown and has to be tested, for example by unplugging a thermostat and watching the zone LED or valve.
- **Pairing side effects** if you experiment with init frames.
- **Mains wiring** inside the connection box. Only work on the low-voltage bus side.

## 7. Next steps

1. **Measure the bus electrically** (step 5 above): how low the thermostat pulls and the source current. The idle voltage (4.7 V) is already known.
2. **Capture for 24 hours or more,** including a heat/cool changeover and a box menu or learn-mode session, to confirm that nothing is ever sent downstream.
3. **Find out what the box actually acts on.** Read the box model. Watch a zone's valve or LED to see whether it follows p[8] or setpoint vs temperature, for example when a thermostat reports a high setpoint with 0 % demand.
4. ~~Add the checksum check to `decoder.cpp`~~ Done on 2026-11-14, together with init-frame decoding and logging of undecoded bursts.
5. **Then a single, supervised transmit test.** Build the driver, unplug one thermostat (option B), and send its ID with an unchanged setpoint. Check that the box shows it as a normal signal and the zone behaves the same. Only then change values.

### Verified vs guessed
- **Verified from captures:**
  - the checksum algorithm and constant;
  - the framing (the encoder reproduces all 98 frames);
  - no non-`02 38` traffic in about 19 minutes;
  - the 500 ms repeat;
  - the reporting intervals, the 4.5 s event re-send and the alternating toggle bit.
- **Verified in the live bus test on 2026-11-14 (section 8):**
  - no downstream traffic during 6 thermostat events (off/on, setpoint and mode changes);
  - the init frame format (`03` type byte);
  - no collision avoidance: two thermostats sent at the same moment and both frames were lost.
- **Verified from Watts manuals:**
  - bus-powered thermostats;
  - pairing that only listens on the box side;
  - PWM regulation in the thermostat;
  - wiring rules;
  - the External-control input on the Master H&C box.
- **Guesses:**
  - whether the box regulates from p[8] or from the setpoint;
  - what the box does when a thermostat goes silent;
  - that the coordinated change in the long capture was manual.

## 8. Live bus test, 2026-11-14 (VERIFIED)

The firmware logged every burst that did not decode, as raw level:duration pairs. A person changed thermostats by hand while the log ran, from 09:25 to 09:48 (local time).

**Events and what the bus carried**

| Time | Action | Bus traffic |
|---|---|---|
| 09:27:34 | Office (0x4584) woken from OFF (display was blank since 22:07 the day before) | `02` frames with setpoint 0.0, about one per second for 5 s, then setpoint 16.0 |
| 09:29:42–09:31:15 | Bathroom (0x456E) setpoint changed and set back | `02` reports only. One report with setpoint 0.0 for 1 s (OFF passed through) |
| 09:37:10–09:37:18 | Bedroom (0x4572) to OFF, then to Comfort (sun) | 6× `02` with setpoint 0.0, then **4× `03 38 45 72 00 CA 00 00 00 6C`** |
| 09:37:46 | Bedroom on Comfort | `02`, setpoint 22.0, demand 100 % |
| 09:42:28–09:43:19 | Bedroom OFF, then back to Reduced (moon) | `02` reports, plus a collision at 09:43:14 (see below) |
| 09:47:02–09:47:51 | Bedroom OFF test repeated | `02` reports only, no `03` (Comfort was passed through quickly) |

**Findings**
- **No downstream traffic.** In all 6 events, nothing came from the connection box. Every burst came from a thermostat.
- **Init frame = type byte `0x03`.** The layout and checksum are the same as a report. The thermostat sends it 4 times, about 0.5 s apart, when it goes from OFF to Comfort and stays there. The thermostat manual says it "will send now the ignition signal to the receiver" at that moment. The Master BUS pairing procedure uses it.
- **The thermostat reports only the mode it settles on.** Passing quickly through a mode in the menu (order: sun, moon, OFF) gives no report for that mode.
- **OFF is reported as setpoint 0.0.** When going to OFF, the thermostat sends about 6 reports one second apart, then stops its periodic reports. The Office went silent this way the night before.
- **No collision avoidance (VERIFIED).** At 09:43:14 the Bedroom's on-change report and the Bathroom's periodic report (due about 181 s after 09:40:15) overlapped. Both 0.5 s copies collided, so both frames were lost. A transmitting ESP must listen before it talks (no edges for at least 50 ms) and should send at random offsets.
- **Mode and schedule logic is in the box.** According to the Master BUS manual, in Reduced mode the box uses each zone's comfort setpoint minus its own dt, and in Automatic mode it follows its own per-zone programs. The thermostats never need to receive anything.

**Still not tested:** the box in "rF init" (pairing) mode, a heat/cool changeover, and the box's External-control input. The manual says the box only listens in "rF init". This test was skipped on purpose, because leaving the menu saves the zone assignment.

## 9. Heat/cool changeover, 2026-11-14 (VERIFIED)

The Living Room thermostat (0x702D) is the Master H&C thermostat. Only this thermostat can switch the house between heating (HOT) and cooling (CLD).

- **In CLD mode it sends frame type `0x00`** instead of `0x02`. The layout and the check byte are the same. Example: `00 38 70 2D 00 CB 00 D3 00 FC` (20.3 °C, setpoint 21.0).
- **Byte 0 is probably a set of flags.** Bit 1 = heating, bit 0 = init. That makes `0x02` a heating report, `0x00` a cooling report and `0x03` a heating init frame. A cooling init frame (`0x01`) was not seen (GUESS).
- **The other thermostats did not change.** During 2 minutes of CLD, the other three thermostats continued to send `02` reports with their heating setpoints. Each thermostat has one setpoint. The box applies the night offset (`dt`) and the cooling offset (Add/Sub 2 °C per zone) itself.
- **The Living Room reported 21.0 °C in CLD and 19.0 °C in HOT.** The master thermostat may keep a separate cooling setpoint (not confirmed).

**Open question.** All thermostat displays have a heating-demand icon and a cooling-demand icon. Do the other thermostats show the cooling icon when the Living Room is in CLD? If they do, they learn the house mode from the bus (for example from the `00` frames of the Living Room), and their frames could change to `00` after some time. Test: Living Room to CLD for about 10 minutes, watch the Office display and the bus log.
