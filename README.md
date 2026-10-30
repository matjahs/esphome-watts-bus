# esphome-watts-bus

Read-only [ESPHome](https://esphome.io) external component for the wired **Watts BUS** used by WFHT-BASIC H&C BUS / WFHT-LCD H&C BUS thermostats and the WFHC-MASTER H&C BUS wiring centre. It listens to the thermostat bus and exposes room temperature, setpoint and heat demand per thermostat in Home Assistant.

> [!IMPORTANT]
> Read-only. The component never drives the bus. Changing setpoints from Home Assistant is not supported: the frame check byte is not yet understood.

## Features

- Decodes every thermostat on the shared bus from a single tap point
- Per thermostat: room temperature, setpoint, heat demand (%)
- Accepts a message only after both transmitted copies match
- Marks sensors unavailable when a thermostat stops reporting (`stale_timeout`)
- Logs unconfigured thermostat IDs so you can discover them

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
| 0–1 | `02 38` header |
| 2–3 | thermostat ID |
| 4–5 | room temperature × 10 (°C) |
| 6–7 | setpoint × 10, plus a 0/1 toggle that alternates per message |
| 8 | heat demand (%) |
| 9 | check byte (XOR-linear, algorithm unknown) |

Setpoints come in 0.5 °C steps, so `setpoint = (raw - raw % 5) / 10`.

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
