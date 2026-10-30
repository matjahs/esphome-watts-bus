#include "decoder.h"

namespace esphome {
namespace watts_bus {

static constexpr uint32_t GAP_US = 5000;                // idle longer than this ends a frame
static constexpr uint64_t CONFIRM_WINDOW_US = 1500000;  // repeat must follow within 1.5 s
static constexpr size_t FRAME_BITS = 104;
static constexpr size_t PREAMBLE_BITS = 23;
static constexpr size_t DATA_START_BIT = PREAMBLE_BITS + 1;  // after the start bit

// Number of 450 us half-bit units in a duration; 0 when it fits neither 1 nor 2.
static uint8_t units_for(uint32_t duration_us) {
  if (duration_us >= 300 && duration_us <= 600) return 1;
  if (duration_us >= 750 && duration_us <= 1050) return 2;
  return 0;
}

static WattsMessage to_message(const Payload &p) {
  uint16_t setpoint_raw = static_cast<uint16_t>(p[6] << 8 | p[7]);

  WattsMessage m{};
  m.id = static_cast<uint16_t>(p[2] << 8 | p[3]);
  m.temperature = static_cast<int16_t>(p[4] << 8 | p[5]) / 10.0f;
  m.setpoint = (setpoint_raw - setpoint_raw % 5) / 10.0f;  // % 5 is the per-message toggle
  m.heat_demand = p[8];
  m.raw = p;
  return m;
}

void FrameDecoder::push(const Edge &edge) {
  if (edge.level == 1 && edge.duration_us > GAP_US) {
    flush();  // the frame ended when the line went idle, before this gap
    now_us_ += edge.duration_us;
    return;
  }
  now_us_ += edge.duration_us;

  uint8_t units = units_for(edge.duration_us);
  if (units == 0) {
    frame_ok_ = false;
    return;
  }
  half_bits_.insert(half_bits_.end(), units, edge.level);
}

void FrameDecoder::flush() {
  if (!half_bits_.empty() && frame_ok_) finish_frame_();
  half_bits_.clear();
  frame_ok_ = true;
}

bool FrameDecoder::pop(WattsMessage &out) {
  if (!has_ready_) return false;
  out = ready_;
  has_ready_ = false;
  return true;
}

void FrameDecoder::finish_frame_() {
  if (half_bits_.size() % 2 == 1) half_bits_.push_back(1);  // last half-bit merged into idle high

  Payload payload{};
  if (!decode_payload_(payload)) return;
  confirm_(payload);
}

bool FrameDecoder::decode_payload_(Payload &payload) const {
  if (half_bits_.size() != FRAME_BITS * 2) return false;

  std::array<uint8_t, FRAME_BITS> bits{};
  for (size_t i = 0; i < FRAME_BITS; i++) {
    uint8_t first = half_bits_[2 * i];
    uint8_t second = half_bits_[2 * i + 1];
    if (first == second) return false;  // not a Manchester pair
    bits[i] = first == 0 ? 1 : 0;       // low-high = 1, high-low = 0
  }

  for (size_t i = 0; i < PREAMBLE_BITS; i++) {
    if (bits[i] != 1) return false;
  }
  if (bits[PREAMBLE_BITS] != 0) return false;  // start bit

  for (size_t byte = 0; byte < payload.size(); byte++) {
    uint8_t value = 0;
    for (size_t bit = 0; bit < 8; bit++) {
      value = static_cast<uint8_t>(value << 1 | bits[DATA_START_BIT + byte * 8 + bit]);
    }
    payload[byte] = value;
  }
  return payload[0] == 0x02 && payload[1] == 0x38;
}

void FrameDecoder::confirm_(const Payload &payload) {
  bool is_repeat = has_pending_ && payload == pending_ && now_us_ - pending_at_us_ <= CONFIRM_WINDOW_US;
  if (!is_repeat) {
    pending_ = payload;
    pending_at_us_ = now_us_;
    has_pending_ = true;
    return;
  }

  has_pending_ = false;  // a third identical copy starts a new pair
  ready_ = to_message(payload);
  has_ready_ = true;
}

}  // namespace watts_bus
}  // namespace esphome
