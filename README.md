# esphome-watts-bus

Read-only [ESPHome](https://esphome.io) external component for the wired **Watts BUS** used by WFHT-BASIC H&C BUS / WFHT-LCD H&C BUS thermostats and the WFHC-MASTER H&C BUS wiring centre. It listens to the thermostat bus and exposes room temperature, setpoint and heat demand per thermostat in Home Assistant.

> [!IMPORTANT]
> Read-only. The component never drives the bus. Changing setpoints from Home Assistant is not supported. The bus is one-way (thermostat to wiring centre), see [`docs/feasibility.md`](docs/feasibility.md).

## Features

- Decodes every thermostat on the shared bus from a single tap point
- Per thermostat: room temperature, setpoint, heat demand (%)
- Heating/cooling state from the Master H&C thermostat (`cooling` binary sensor)
- Accepts a message only after both transmitted copies match
- Marks sensors unavailable when a thermostat stops reporting (`stale_timeout`)
- Logs unconfigured thermostat IDs so you can discover them
- Rejects frames with a wrong check byte
- Logs pairing (init) frames, and the raw timing of bursts that do not decode
- `on_frame` / `on_rejected` triggers to forward every frame (for example to MQTT), plus diagnostic sensors: `rejected_bursts` and a per-thermostat `report_interval`

## Hardware

The bus terminal block on each thermostat back plate is labelled `+ R/T -`:

| Terminal | Measured | Meaning |
|---|---|---|
| `+` | 4.8 V | supply |
| `R/T` | 4.7 V idle | single-wire data, idles high |
| `-` | 0 V | ground |

Tap `R/T` and `-` at any thermostat. Divide `R/T` down to ~3.1 V for the ESP8266 GPIO:

```
R/T  ──[10k]──┬── GPIO14 (D5)
              │
            [20k]
              │
 -   ─────────┴── GND
```

> [!WARNING]
> Do not connect `+` to the ESP and do not power the ESP from the bus. Power it from a separate USB supply. Measure ~3.1 V at the GPIO before connecting USB.

Tested on a NodeMCU V3 (ESP8266, CH340).

## Usage

```yaml
external_components:
  - source: github://matjahs/esphome-watts-bus@main
    components: [watts_bus]

watts_bus:
  pin: GPIO14
  stale_timeout: 10min   # optional, default 10min

sensor:
  - platform: watts_bus
    thermostat_id: 0x4584
    temperature:
      name: "Office Temperature"
    setpoint:
      name: "Office Setpoint"
    heat_demand:
      name: "Office Heat Demand"

  # Diagnostics: time since the previous report (lost reports show as longer gaps)
  - platform: watts_bus
    thermostat_id: 0x456E
    report_interval:
      name: "Bathroom Report Interval"

  # Master H&C thermostat: also report whether the house is cooling (CLD)
  - platform: watts_bus
    thermostat_id: 0x702D
    temperature:
      name: "Living Room Temperature"
    cooling:
      name: "Cooling"
```

Thermostat IDs differ per installation. Flash with only the `watts_bus:` block and `logger: level: DEBUG`, then read the IDs from the log:

```
[I][watts_bus]: Unconfigured thermostat 0x4584 (23.6 °C); add it under sensor: platform: watts_bus
```

Change a setpoint on one thermostat to see which ID belongs to which room.

### Configuration

**`watts_bus`**

| Option | Required | Default | Description |
|---|:---:|---|---|
| `pin` | ✅ | | Input pin connected to the divided `R/T` line |
| `stale_timeout` | | `10min` | Publish `unavailable` after this long without a message |

**`sensor` → `platform: watts_bus`**

| Option | Required | Description |
|---|:---:|---|
| `thermostat_id` | ✅ | 16-bit thermostat ID, e.g. `0x4584` |
| `temperature` | | Room temperature, °C |
| `setpoint` | | Setpoint, °C |
| `heat_demand` | | Heat demand, % |

All sensor options accept the usual [sensor](https://esphome.io/components/sensor/) settings (`name`, `device_id`, `filters`, …).

## Protocol

Reverse engineered from bus captures; see [`tools/`](tools/) and [`tests/fixtures/`](tests/fixtures/).

- Manchester code, half-bit ≈ 450 µs (~1.1 kbit/s); low→high = `1`, high→low = `0`
- 104 bits per frame: 23 preamble `1` bits, start bit `0`, 10 bytes MSB-first
- Every message is sent twice, ~0.4–0.5 s apart
- Thermostats report every ~2.5–3 min, and immediately when a setpoint changes

| Byte | Content |
|---|---|
| 0 | frame type: `02` report (heating), `00` report (cooling), `03` pairing (init) signal |
| 1 | `38` |
| 2–3 | thermostat ID |
| 4–5 | room temperature × 10 (°C) |
| 6–7 | setpoint × 10, plus a 0/1 toggle that alternates per message |
| 8 | heat demand (%) |
| 9 | check byte, see below |

Setpoints come in 0.5 °C steps, so `setpoint = (raw - raw % 5) / 10`. A thermostat in OFF reports setpoint 0.

Check byte: CRC-8 (polynomial `0xE6`, initial value `0x0F`) over bytes 0–7, then XOR with byte 8:

```
crc = 0x0F
for b in bytes[0..7]: crc ^= b; repeat 8: crc = (crc & 0x80) ? (crc << 1) ^ 0xE6 : crc << 1
bytes[9] = crc ^ bytes[8]
```

The bus has no collision avoidance. When two thermostats send at the same moment, both frames are lost.

## Forwarding frames

`on_frame` runs for every confirmed frame, with the variables `id`, `frame_type`, `temperature`, `setpoint`, `heat_demand` and `raw` (10 bytes as hex). `on_rejected` runs for every burst that did not decode, with `edges` and `duration_us`. Example with MQTT:

```yaml
watts_bus:
  pin: GPIO14
  rejected_bursts:
    name: "Rejected bursts"
  on_frame:
    - mqtt.publish_json:
        topic: watts-bus/frame
        payload: |-
          root["id"] = str_sprintf("%04X", id);
          root["type"] = frame_type;
          root["temperature"] = temperature;
          root["setpoint"] = setpoint;
          root["heat_demand"] = heat_demand;
          root["raw"] = raw;
  on_rejected:
    - mqtt.publish_json:
        topic: watts-bus/rejected
        payload: |-
          root["edges"] = edges;
          root["duration_us"] = duration_us;
```

## Development

The decoder (`components/watts_bus/decoder.*`) is plain C++17 without ESPHome dependencies and is tested on the host against real captures:

```bash
cmake -S . -B build
cmake --build build
./build/decoder_test
```

Validate the component with ESPHome:

```bash
esphome config example.yaml
esphome compile example.yaml
```

## License

MIT, see [LICENSE](LICENSE).

Not affiliated with or endorsed by Watts Water Technologies.
