#include "watts_bus.h"

#include <algorithm>
#include <cmath>

#include "esphome/core/helpers.h"
#include "esphome/core/log.h"

namespace esphome {
namespace watts_bus {

static const char *const TAG = "watts_bus";

void WattsThermostat::publish(const WattsMessage &msg, uint32_t now_ms) {
  last_seen_ms_ = now_ms;
  stale_ = false;
  publish_all_(msg.temperature, msg.setpoint, msg.heat_demand);
}

void WattsThermostat::check_stale(uint32_t now_ms, uint32_t timeout_ms) {
  if (stale_ || now_ms - last_seen_ms_ < timeout_ms) return;

  stale_ = true;
  ESP_LOGW(TAG, "Thermostat 0x%04X silent for %u s, marking unavailable", id_, (unsigned) (timeout_ms / 1000));
  publish_all_(NAN, NAN, NAN);
}

void WattsThermostat::publish_all_(float temperature, float setpoint, float heat_demand) {
  if (temperature_ != nullptr) temperature_->publish_state(temperature);
  if (setpoint_ != nullptr) setpoint_->publish_state(setpoint);
  if (heat_demand_ != nullptr) heat_demand_->publish_state(heat_demand);
}

// Runs on every edge: only timestamp and level, all decoding happens in loop().
void IRAM_ATTR WattsBus::isr(WattsBus *bus) {
  size_t next = (bus->head_ + 1) % BUFFER_SIZE;
  if (next == bus->tail_) {
    bus->overflow_ = true;
    return;
  }
  bus->edge_time_us_[bus->head_] = micros();
  bus->edge_level_[bus->head_] = bus->isr_pin_.digital_read();
  bus->head_ = next;
}

void WattsBus::setup() {
  pin_->setup();  // input only: this component never drives the bus
  isr_pin_ = pin_->to_isr();
  prev_level_ = pin_->digital_read();
  prev_edge_us_ = micros();
  pin_->attach_interrupt(WattsBus::isr, this, gpio::INTERRUPT_ANY_EDGE);
}

void WattsBus::loop() {
  drain_edges_();

  // Read the clock before checking the buffer: an edge that lands in between
  // is then newer than `now`, so the idle period we measured really happened.
  uint32_t now = micros();
  bool no_new_edges = head_ == tail_;
  if (no_new_edges && now - prev_edge_us_ > IDLE_FLUSH_US) {
    decoder_.flush();
    WattsMessage msg;
    if (decoder_.pop(msg)) dispatch_(msg);
  }

  uint32_t now_ms = millis();
  if (now_ms - last_stale_check_ms_ < STALE_CHECK_MS) return;
  last_stale_check_ms_ = now_ms;
  for (auto *thermostat : thermostats_) thermostat->check_stale(now_ms, stale_timeout_ms_);
}

void WattsBus::drain_edges_() {
  if (overflow_) {
    overflow_ = false;
    ESP_LOGW(TAG, "Edge buffer overflow, current frame lost");
  }

  while (tail_ != head_) {
    size_t index = tail_;
    uint32_t edge_us = edge_time_us_[index];
    uint8_t new_level = edge_level_[index];
    tail_ = (index + 1) % BUFFER_SIZE;

    // The decoder wants the level that was *held* until this edge, and for how long.
    decoder_.push(Edge{prev_level_, edge_us - prev_edge_us_});
    prev_edge_us_ = edge_us;
    prev_level_ = new_level;

    WattsMessage msg;
    if (decoder_.pop(msg)) dispatch_(msg);
  }
}

void WattsBus::dispatch_(const WattsMessage &msg) {
  ESP_LOGD(TAG, "0x%04X: %.1f °C, setpoint %.1f °C, demand %u%% [%s]", msg.id, msg.temperature, msg.setpoint,
           msg.heat_demand, format_hex_pretty(msg.raw.data(), msg.raw.size()).c_str());

  for (auto *thermostat : thermostats_) {
    if (thermostat->get_id() != msg.id) continue;
    thermostat->publish(msg, millis());
    return;
  }

  bool already_reported = std::find(reported_unknown_.begin(), reported_unknown_.end(), msg.id) != reported_unknown_.end();
  if (already_reported) return;
  reported_unknown_.push_back(msg.id);
  ESP_LOGI(TAG, "Unconfigured thermostat 0x%04X (%.1f °C); add it under sensor: platform: watts_bus", msg.id,
           msg.temperature);
}

void WattsBus::dump_config() {
  ESP_LOGCONFIG(TAG, "Watts BUS (read-only):");
  LOG_PIN("  Pin: ", pin_);
  ESP_LOGCONFIG(TAG, "  Stale timeout: %u s", (unsigned) (stale_timeout_ms_ / 1000));
  for (auto *thermostat : thermostats_) ESP_LOGCONFIG(TAG, "  Thermostat: 0x%04X", thermostat->get_id());
}

}  // namespace watts_bus
}  // namespace esphome
