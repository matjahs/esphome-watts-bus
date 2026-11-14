#pragma once  // include this header only once per compile

#include <array>
#include <cstdint>
#include <vector>


namespace esphome::watts_bus {
    // One stretch of constant line level, measured between two edges.
    struct Edge {
        uint8_t level; // level the line held (1 = idle/high)
        uint32_t duration_us; // how long it held that level
    };

    using Payload = std::array<uint8_t, 10>; // the 10 data bytes of a frame

    // payload[0]: frame type.
    static constexpr uint8_t FRAME_REPORT = 0x02; // periodic or on-change thermostat report, heating
    static constexpr uint8_t FRAME_REPORT_COOLING = 0x00; // same report while the house is in cooling (CLD)
    static constexpr uint8_t FRAME_INIT = 0x03;   // pairing signal, sent when the thermostat leaves OFF for Comfort

    // Expected value of payload[9]: CRC-8 (poly 0xE6, init 0x0F) over bytes 0..7,
    // then XOR with byte 8 (heat demand), which does not go through the CRC.
    uint8_t checksum(const Payload &payload);

    // A confirmed thermostat report.
    struct WattsMessage {
        uint16_t id;
        float temperature;
        float setpoint;
        uint8_t heat_demand;
        bool cooling; // reported by the Master H&C thermostat in CLD mode
        Payload raw;
    };

    // Turns edges into confirmed messages. Pure C++: no ESPHome or Arduino, so it
    // runs in the host test as well as on the ESP8266.
    class FrameDecoder {
    public:
        void push(const Edge &edge); // feed the next edge
        void flush(); // line went idle: finish the frame in progress
        bool pop(WattsMessage &out); // true once per confirmed message
        // True once per burst that did not decode as a thermostat report. `out`
        // gets its edges in order, starting with the first low after the idle gap.
        bool pop_rejected(std::vector<Edge> &out);

    private:
        void finish_frame_();

        bool decode_payload_(Payload &payload) const;

        void confirm_(const Payload &payload);

        void reject_();

        std::vector<uint8_t> half_bits_; // current frame, one entry per 450 us unit
        bool frame_ok_{true}; // false once a duration falls outside tolerance
        uint64_t now_us_{0}; // decoder clock: sum of all durations
        std::vector<Edge> edges_; // current burst as received, for pop_rejected()

        std::vector<Edge> rejected_;
        bool has_rejected_{false};

        Payload pending_{}; // first copy, waiting for its repeat
        uint64_t pending_at_us_{0};
        bool has_pending_{false};

        WattsMessage ready_{};
        bool has_ready_{false};
    };
} // namespace esphome::watts_bus
