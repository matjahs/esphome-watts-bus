#pragma once  // include this header only once per compile

#include <array>
#include <vector>


namespace esphome::watts_bus {
    // One stretch of constant line level, measured between two edges.
    struct Edge {
        uint8_t level; // level the line held (1 = idle/high)
        uint32_t duration_us; // how long it held that level
    };

    using Payload = std::array<uint8_t, 10>; // the 10 data bytes of a frame

    // A confirmed thermostat report.
    struct WattsMessage {
        uint16_t id;
        float temperature;
        float setpoint;
        uint8_t heat_demand;
        Payload raw;
    };

    // Turns edges into confirmed messages. Pure C++: no ESPHome or Arduino, so it
    // runs in the host test as well as on the ESP8266.
    class FrameDecoder {
    public:
        void push(const Edge &edge); // feed the next edge
        void flush(); // line went idle: finish the frame in progress
        bool pop(WattsMessage &out); // true once per confirmed message

    private:
        void finish_frame_();

        bool decode_payload_(Payload &payload) const;

        void confirm_(const Payload &payload);

        std::vector<uint8_t> half_bits_; // current frame, one entry per 450 us unit
        bool frame_ok_{true}; // false once a duration falls outside tolerance
        uint64_t now_us_{0}; // decoder clock: sum of all durations

        Payload pending_{}; // first copy, waiting for its repeat
        uint64_t pending_at_us_{0};
        bool has_pending_{false};

        WattsMessage ready_{};
        bool has_ready_{false};
    };
} // namespace esphome::watts_bus
