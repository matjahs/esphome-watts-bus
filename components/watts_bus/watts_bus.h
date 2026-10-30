#pragma once

#include <vector>

#include "esphome/components/sensor/sensor.h"
#include "esphome/core/component.h"
#include "esphome/core/hal.h"

#include "decoder.h"

namespace esphome {
namespace watts_bus {

// One thermostat on the bus, identified by its 16-bit ID, with optional sensors.
class WattsThermostat {
 public:
  explicit WattsThermostat(uint16_t id) : id_(id) {}

  void set_temperature_sensor(sensor::Sensor *sensor) { temperature_ = sensor; }
  void set_setpoint_sensor(sensor::Sensor *sensor) { setpoint_ = sensor; }
  void set_heat_demand_sensor(sensor::Sensor *sensor) { heat_demand_ = sensor; }

  uint16_t get_id() const { return id_; }
  void publish(const WattsMessage &msg, uint32_t now_ms);
  void check_stale(uint32_t now_ms, uint32_t timeout_ms);

 protected:
  void publish_all_(float temperature, float setpoint, float heat_demand);

  uint16_t id_;
  sensor::Sensor *temperature_{nullptr};
  sensor::Sensor *setpoint_{nullptr};
  sensor::Sensor *heat_demand_{nullptr};
  uint32_t last_seen_ms_{0};
  bool stale_{true};  // nothing published yet, or already marked unavailable
};

// Listens read-only on the R/T line and feeds edges into the FrameDecoder.
class WattsBus : public Component {
 public:
  void set_pin(InternalGPIOPin *pin) { pin_ = pin; }
  void set_stale_timeout(uint32_t timeout_ms) { stale_timeout_ms_ = timeout_ms; }
  void register_thermostat(WattsThermostat *thermostat) { thermostats_.push_back(thermostat); }

  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

 protected:
  static void isr(WattsBus *bus);
  void drain_edges_();
  void dispatch_(const WattsMessage &msg);

  static constexpr size_t BUFFER_SIZE = 512;   // ~2.5 frames of edges
  static constexpr uint32_t IDLE_FLUSH_US = 5000;
  static constexpr uint32_t STALE_CHECK_MS = 1000;

  InternalGPIOPin *pin_{nullptr};
  ISRInternalGPIOPin isr_pin_;
  uint32_t stale_timeout_ms_{600000};

  // Ring buffer written by the ISR, read by loop().
  volatile uint32_t edge_time_us_[BUFFER_SIZE];
  volatile uint8_t edge_level_[BUFFER_SIZE];
  volatile size_t head_{0};
  volatile size_t tail_{0};
  volatile bool overflow_{false};

  uint32_t prev_edge_us_{0};
  uint8_t prev_level_{1};
  uint32_t last_stale_check_ms_{0};

  FrameDecoder decoder_;
  std::vector<WattsThermostat *> thermostats_;
  std::vector<uint16_t> reported_unknown_;
};

}  // namespace watts_bus
}  // namespace esphome
